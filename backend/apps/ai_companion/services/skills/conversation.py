"""
Conversation Skill - Intelligent natural language conversation using Gemini
Handles greetings, help requests, explanations, and general ERP questions
"""

import logging
from typing import List

import google.generativeai as genai
from django.conf import settings

from apps.ai_companion.models import AIConfiguration, AIMessage
from apps.ai_companion.services.api_key_manager import APIKeyManager
from apps.ai_companion.services.ai_service_v2 import ai_service_v2
from .base import BaseSkill, SkillContext, SkillResponse, MemoryRecord

logger = logging.getLogger(__name__)


class ConversationSkill(BaseSkill):
    """
    Handles general conversation, help, and explanations.
    Uses Gemini AI for intelligent, context-aware responses.
    """

    name = "conversation"
    description = "Handles general conversation, greetings, help requests, and ERP explanations"
    priority = 50  # Lower priority than specific skills

    def can_handle(self, message: str, context: SkillContext) -> bool:
        """
        Handles general conversation, greetings, and help requests.
        Falls back to this if no other skill matches.
        """
        lowered = message.lower().strip()

        # Greetings
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
        if any(lowered.startswith(greet) for greet in greetings):
            return True

        # Help requests
        if any(word in lowered for word in ["help", "how to", "how do i", "what is", "explain"]):
            return True

        # Questions
        if lowered.endswith("?"):
            return True

        # Default fallback
        return False

    def handle(self, message: str, context: SkillContext) -> SkillResponse:
        """Handle conversation using Gemini AI"""

        try:
            # Check if AI is enabled
            config = AIConfiguration.get_config()
            if not config.ai_assistant_enabled:
                return SkillResponse(
                    message="Hey! I'm currently switched off. Your administrator can turn me back on if you need my help.",
                    intent="error",
                    confidence=1.0
                )

            # Build context-aware prompt
            prompt = self._build_conversation_prompt(message, context)

            # Check if we have Gemini API keys available
            from apps.ai_companion.services.api_key_manager import APIKeyManager
            has_gemini_keys = APIKeyManager.get_available_key() is not None

            response_text = None

            # Prefer Gemini when API keys are available (faster and better)
            if has_gemini_keys:
                try:
                    response_text = self._call_gemini(prompt, context)
                except Exception as e:
                    logger.warning(f"Gemini failed, trying local RAG: {e}")
                    response_text = None

            # Fall back to local RAG if Gemini not available or failed
            if not response_text:
                ai_cfg = getattr(settings, "AI_CONFIG", {})
                mode = str(ai_cfg.get("MODE", "mock")).lower()

                if mode in {"full", "local", "rag"}:
                    try:
                        rag = ai_service_v2.chat(message, company_id=getattr(context.company, "id", None))
                        response_text = rag.get("message")
                    except Exception as e:
                        logger.warning(f"Local RAG failed: {e}")
                        response_text = None

            # Final fallback
            if not response_text:
                raise Exception("No AI provider available")

            # Extract memory if any
            memory_updates = self._extract_memory_from_response(response_text, context)

            return SkillResponse(
                message=response_text,
                intent="conversation",
                confidence=0.85,
                memory_updates=memory_updates
            )

        except Exception as e:
            logger.exception(f"Conversation skill error: {e}")
            return self._fallback_response(message)

    def _build_conversation_prompt(self, message: str, context: SkillContext) -> str:
        """Build comprehensive prompt for Gemini"""

        user_name = context.user.get_full_name() if context.user else "User"
        company_name = context.company.name if context.company else "your company"

        # Format conversation history
        history_text = self._format_history(context.history)

        # Get user preferences
        preferences = context.long_term
        pref_text = self._format_preferences(preferences)

        # Current context
        current_page = context.current_page or "unknown"
        current_module = context.module or "unknown"

        prompt = f"""Hey! You're helping {user_name} at {company_name} with their Twist ERP system. They're currently on the {current_page} page in the {current_module} module.

Here's what you need to know:

**Recent conversation:**
{history_text}

**What they prefer:**
{pref_text}

**What you can help with in Twist ERP:**
- **Procurement**: Purchase orders, suppliers, receiving goods (GRN)
- **Finance**: Accounts, journal entries, receivables (AR), payables (AP), banking
- **Inventory**: Stock levels, warehouses, moving items around
- **Sales**: Sales orders, customers, invoices
- **Production**: Work orders, bills of materials (BOM), manufacturing
- **HR**: Employees, payroll, attendance, leave
- **Assets**: Equipment tracking, depreciation, maintenance
- **Projects**: Project tracking, tasks, budgets

**How to respond:**
- Talk naturally like you're chatting with a colleague
- Keep it short and sweet (2-4 sentences usually works)
- If they ask for specific data like "show me my purchase orders" or "what's my cash balance", let them know you can totally help with that
- If they want you to do something like "approve PO 123" or "create a sales order", guide them through it step by step
- Don't use corporate-speak or jargon unless you have to
- If you don't know something, just say so - no need to pretend
- Never start with "As an AI assistant" or similar - just talk normally

**Their message:**
"{message}"

**Your response (just answer directly, like you're having a conversation):**"""

        return prompt

    def _format_history(self, history: List[AIMessage]) -> str:
        """Format conversation history"""
        if not history:
            return "(No recent conversation)"

        lines = []
        for msg in history[-10:]:  # Last 10 messages
            role = msg.role.capitalize()
            content = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
            lines.append(f"{role}: {content}")

        return "\n".join(lines)

    def _format_preferences(self, preferences: dict) -> str:
        """Format user preferences"""
        if not preferences:
            return "(No preferences set)"

        lines = []
        for key, value in preferences.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines) if lines else "(No preferences set)"

    def _call_gemini(self, prompt: str, context: SkillContext) -> str:
        """Call Gemini API with automatic key rotation"""

        config = AIConfiguration.get_config()

        def process_with_key(api_key, key_obj):
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name=config.gemini_model,
                generation_config={
                    "temperature": config.temperature,
                    "max_output_tokens": min(config.max_tokens, 1024),  # Limit for conversation
                }
            )
            response = model.generate_content(prompt)
            return response.text

        result = APIKeyManager.process_with_retry(
            operation_func=process_with_key,
            operation_name="conversation",
            max_retries=config.max_retries,
            user=context.user,
            company=context.company
        )

        if not result:
            raise Exception("No API key available for conversation")

        return result

    def _extract_memory_from_response(self, response: str, context: SkillContext) -> List[MemoryRecord]:
        """
        Extract any preferences or facts that should be remembered.
        For now, this is a placeholder. In the future, we could parse the conversation
        for statements like "remember that I prefer..." or "my default warehouse is..."
        """
        # TODO: Implement intelligent memory extraction
        return []

    def _fallback_response(self, message: str) -> SkillResponse:
        """Fallback response when Gemini fails"""
        lowered = message.lower().strip()

        # Handle greetings
        if any(lowered.startswith(greet) for greet in ["hi", "hello", "hey"]):
            return SkillResponse(
                message=f"Hey there! What can I help you with in Twist ERP today?",
                intent="greeting",
                confidence=0.9
            )

        # Handle help
        if "help" in lowered:
            return SkillResponse(
                message=(
                    "I'm here to help you with all sorts of things! I can:\n"
                    "- Answer questions about how things work in the ERP\n"
                    "- Look up data like purchase orders, invoices, or stock levels\n"
                    "- Walk you through different processes\n"
                    "- Explain business concepts in simple terms\n\n"
                    "What do you need help with?"
                ),
                intent="help",
                confidence=0.9
            )

        # Default
        return SkillResponse(
            message="I want to help, but I'm not quite sure what you mean. Could you rephrase that or tell me what you're trying to do?",
            intent="fallback",
            confidence=0.5
        )
