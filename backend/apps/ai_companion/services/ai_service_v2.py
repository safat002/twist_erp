from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, List, Optional

from django.conf import settings
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
import torch
from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer, pipeline

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".md", ".rst", ".txt"}





class TransformerEmbedding(Embeddings):
    """Simple embedding wrapper compatible with LangChain vector stores."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        except Exception as exc:
            logger.warning(
                "Failed to load fast tokenizer for %s (%s); retrying with use_fast=False",
                model_name,
                exc,
            )
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.eval()

    def _embed_text(self, text: str) -> List[float]:
        inputs = self.tokenizer(
            text,
            truncation=True,
            padding=True,
            max_length=512,
            return_tensors="pt",
        )
        with torch.no_grad():
            outputs = self.model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1)
        return embeddings[0].cpu().tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_text(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_text(text)


def _iter_documents(source_directory: str) -> Iterable[Document]:
    base_path = Path(source_directory)
    if not base_path.exists():
        logger.warning("AI document path %s does not exist", source_directory)
        return []

    documents: List[Document] = []
    for path in base_path.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to read %s: %s", path, exc)
            continue
        metadata = {"source": str(path.relative_to(base_path))}
        documents.append(Document(page_content=text, metadata=metadata))
    return documents


class AIServiceV2:
    """Retrieval-augmented assistant powered by HuggingFace models."""

    @staticmethod
    def _coerce_int(value, default, minimum, maximum):
        try:
            coerced = int(value if value is not None else default)
        except (TypeError, ValueError):
            coerced = default
        return max(minimum, min(coerced, maximum))

    @staticmethod
    def _first_length(length_obj):
        if isinstance(length_obj, (list, tuple)):
            return int(length_obj[0]) if length_obj else 0
        if hasattr(length_obj, "tolist"):
            values = length_obj.tolist()
            if isinstance(values, (list, tuple)):
                return int(values[0]) if values else 0
            return int(values)
        if length_obj is None:
            return 0
        return int(length_obj)

    def __init__(self):
        cfg = getattr(settings, "AI_CONFIG", {})
        self.embeddings: TransformerEmbedding | None = None
        self.vector_stores: Dict[str, FAISS] = {}
        self.generator = None
        self.index_root: Optional[Path] = None
        self._mode = str(cfg.get("MODE", "full")).lower()
        self._enabled = bool(cfg.get("ENABLED", True)) and self._mode != "disabled"
        self._autoload = bool(cfg.get("AUTOLOAD", False)) and self._mode not in {"mock"}
        self._max_new_tokens = self._coerce_int(cfg.get("MAX_NEW_TOKENS"), 256, 32, 1024)
        self._max_prompt_tokens = self._coerce_int(
            cfg.get("MAX_PROMPT_TOKENS"),
            max(self._max_new_tokens * 2, 512),
            self._max_new_tokens,
            4096,
        )
        self._max_prompt_tokens = max(self._max_prompt_tokens, self._max_new_tokens + 32)
        self._should_load_embeddings = self._mode not in {"mock"}
        self._should_load_models = self._mode not in {"mock"}
        self._load_failed = False
        self._load_lock = Lock()
        if self._enabled and self._autoload and self._should_load_models:
            self._load_models()

    def _load_models(self) -> bool:
        embeddings_ok = True
        generator_ok = True
        if self._should_load_embeddings and self.embeddings is None:
            embeddings_ok = self._load_embedding_model()
        if self._should_load_models and self.generator is None:
            generator_ok = self._load_generator_model()
        return embeddings_ok and generator_ok

    def _index_path(self, index_name: str) -> Path:
        if self.index_root is None:
            raise RuntimeError("Vector store root is not configured.")
        return self.index_root / index_name / "faiss"

    def _load_vector_store(self, index_name: str) -> Optional[FAISS]:
        if not self.embeddings or not self.index_root:
            return None
        path = self._index_path(index_name)
        if not path.exists():
            return None
        try:
            store = FAISS.load_local(
                str(path),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
            self.vector_stores[index_name] = store
            logger.info("Loaded vector index '%s' from %s", index_name, path)
            return store
        except Exception as exc:
            logger.warning("Failed to load FAISS index '%s': %s", index_name, exc)
            return None

    def _ensure_ready(self, *, require_generator: bool = True) -> bool:
        if not self._enabled:
            return False
        if self._mode == "mock":
            return True
        if self._load_failed:
            return False

        with self._load_lock:
            if self._should_load_embeddings and self.embeddings is None:
                if not self._load_embedding_model():
                    return False

            if self._should_load_models and require_generator and self.generator is None:
                if not self._load_generator_model():
                    return False

        return True

    def _load_embedding_model(self) -> bool:
        # Safety check: Never load models in mock mode
        if self._mode == "mock":
            logger.info("Skipping embedding model load in mock mode")
            return True

        if self.embeddings is not None:
            return True

        cfg = getattr(settings, "AI_CONFIG", {})
        embedding_model = cfg.get("EMBEDDING_MODEL")
        persist_dir = cfg.get("VECTOR_DB_PATH")

        if not all([embedding_model, persist_dir]):
            logger.error("AI_CONFIG must define EMBEDDING_MODEL and VECTOR_DB_PATH")
            self._load_failed = True
            return False

        try:
            self.embeddings = TransformerEmbedding(model_name=embedding_model)
            self.index_root = Path(persist_dir)
            self.index_root.mkdir(parents=True, exist_ok=True)
            self._load_vector_store("global")
            logger.info("AI embedding model loaded successfully.")
            return True
        except Exception as exc:
            logger.exception("Failed to load AI embedding model: %s", exc)
            self.embeddings = None
            self._load_failed = True
            return False

    def _load_generator_model(self) -> bool:
        # Safety check: Never load models in mock mode
        if self._mode == "mock":
            logger.info("Skipping generator model load in mock mode")
            return True

        if self.generator is not None:
            return True

        cfg = getattr(settings, "AI_CONFIG", {})
        llm_model = cfg.get("LLM_MODEL")

        if not llm_model:
            logger.error("AI_CONFIG must define LLM_MODEL")
            self._load_failed = True
            return False

        try:
            try:
                tokenizer = AutoTokenizer.from_pretrained(llm_model)
            except Exception as exc:
                logger.warning(
                    "Failed to load fast tokenizer for %s (%s); retrying with use_fast=False",
                    llm_model,
                    exc,
                )
                tokenizer = AutoTokenizer.from_pretrained(llm_model, use_fast=False)

            model = AutoModelForCausalLM.from_pretrained(llm_model)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            if getattr(model.config, "pad_token_id", None) is None:
                model.config.pad_token_id = tokenizer.pad_token_id
            tokenizer.padding_side = "left"
            tokenizer.truncation_side = "left"
            tokenizer.model_max_length = max(
                getattr(tokenizer, "model_max_length", 0) or 0,
                self._max_prompt_tokens + self._max_new_tokens,
            )
            self.generator = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=self._max_new_tokens,
                do_sample=False,
                truncation=True,
                pad_token_id=model.config.pad_token_id,
            )
            logger.info("AI generator model loaded successfully for RAG assistant.")
            return True
        except Exception as exc:
            logger.exception("Failed to load AI generator model: %s", exc)
            self.generator = None
            self._load_failed = True
            return False

    def index_documents(self, source_directory: str, index_name: str = "global"):
        if not self._should_load_embeddings:
            logger.info("Skipping document indexing because AI mode '%s' disables embeddings.", self._mode)
            return
        if not self._ensure_ready(require_generator=False):
            if not self._enabled:
                logger.info("AI service disabled; skipping document indexing request.")
            else:
                logger.error("AI models not loaded; cannot index documents.")
            return

        documents = list(_iter_documents(source_directory))
        self.index_documents_from_list(documents, index_name=index_name)

    def index_documents_from_list(self, documents: List[Document], index_name: str = "global"):
        if not self._should_load_embeddings:
            logger.info("Skipping in-memory document indexing because AI mode '%s' disables embeddings.", self._mode)
            return
        if not self._ensure_ready(require_generator=False):
            if not self._enabled:
                logger.info("AI service disabled; skipping document indexing request.")
            else:
                logger.error("AI models not loaded; cannot index documents.")
            return

        if not documents:
            logger.warning("No documents found to index.")
            return

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(documents)

        store = self.vector_stores.get(index_name)
        if store is None:
            store = FAISS.from_documents(chunks, self.embeddings)
        else:
            store.add_documents(chunks)
        self.vector_stores[index_name] = store

        if self.index_root:
            index_path = self._index_path(index_name)
            os.makedirs(index_path.parent, exist_ok=True)
            store.save_local(str(index_path))
        logger.info("Indexed %s document chunks into '%s'.", len(chunks), index_name)

    def chat(self, message: str, **kwargs) -> Dict:
        if self._mode == "mock":
            trimmed = (message or "").strip()
            if len(trimmed) > 160:
                trimmed = f"{trimmed[:157]}..."
            return {
                "message": (
                    "AI is running in mock mode for development, so no heavy model is loaded right now. "
                    f'I received your prompt: "{trimmed or "No prompt provided"}".'
                ),
                "intent": "mock",
            }
        if not self._ensure_ready():
            if not self._enabled:
                return {
                    "message": "Hey! I'm currently switched off. Your admin can turn me back on whenever you need me.",
                    "intent": "fallback",
                }
            return {
                "message": "Oops, I'm having trouble getting started right now. Give me a moment and try again?",
                "intent": "fallback",
            }

        try:
            index_name = str(kwargs.get("company_id") or "global")
            store = self.vector_stores.get(index_name) or self._load_vector_store(index_name)
            if store is None and index_name != "global":
                store = self.vector_stores.get("global") or self._load_vector_store("global")
            if store is None:
                return {
                    "message": "Hmm, I don't have any knowledge base loaded yet. Could you ask me something else or try again later?",
                    "intent": "fallback",
                }

            docs = store.similarity_search(message, k=3)
            if not docs:
                return {
                    "message": "I searched my knowledge base but couldn't find anything helpful about that. Want to try rephrasing your question?",
                    "intent": "fallback",
                }

            context = "\n\n".join(
                f"[{doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
                for doc in docs
            )
            prompt = (
                "You're a friendly AI assistant helping people use Twist ERP. "
                "I'll give you some context from the documentation - use it to answer naturally and conversationally. "
                "If you're not sure about something, just say so honestly.\n\n"
                f"Context:\n{context}\n\nQuestion: {message}\nAnswer:"
            )
            prompt = self._truncate_prompt(prompt)
            raw = self.generator(prompt)[0]["generated_text"]
            if raw.startswith(prompt):
                answer_text = raw[len(prompt):].strip()
            else:
                answer_text = raw.split("Answer:", maxsplit=1)[-1].strip()
            if not answer_text or len(answer_text.split()) < 3:
                return {
                    "message": "I couldn't find detailed guidance in the knowledge base yet. Please check the Finance > Journals module or the help menu for Journal Voucher steps.",
                    "intent": "fallback",
                    "sources": [doc.metadata.get("source") for doc in docs],
                    "index": index_name,
                }
            return {
                "message": answer_text,
                "intent": "qa",
                "sources": [doc.metadata.get("source") for doc in docs],
                "index": index_name,
            }
        except Exception as exc:
            logger.exception("AI chat failed: %s", exc)
            return {
                "message": "Sorry, something went wrong while answering that.",
                "intent": "fallback",
            }

    def _truncate_prompt(self, prompt: str) -> str:
        if not self.generator or self._mode == "mock":
            return prompt
        tokenizer = getattr(self.generator, "tokenizer", None)
        model = getattr(self.generator, "model", None)
        if tokenizer is None or model is None:
            return prompt
        max_positions = getattr(model.config, "max_position_embeddings", None) or getattr(
            model.config, "n_positions", 1024
        )
        allowed_tokens = max_positions or 1024
        if self._max_new_tokens:
            allowed_tokens -= self._max_new_tokens
        allowed_tokens = max(32, min(self._max_prompt_tokens, allowed_tokens))
        token_info = tokenizer(prompt, add_special_tokens=False, return_length=True)
        prompt_length = self._first_length(token_info.get("length"))
        if prompt_length <= allowed_tokens:
            return prompt
        truncated = tokenizer(
            prompt,
            truncation=True,
            max_length=allowed_tokens,
            add_special_tokens=False,
            return_tensors="pt",
        )
        return tokenizer.decode(truncated["input_ids"][0], skip_special_tokens=True)


ai_service_v2 = AIServiceV2()


def chat(message: str, **kwargs) -> Dict:
    return ai_service_v2.chat(message, **kwargs)
