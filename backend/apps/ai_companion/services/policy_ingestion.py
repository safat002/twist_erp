from __future__ import annotations

from typing import Iterable, List, Tuple

from django.db import transaction
from django.db.models import Q
from langchain_core.documents import Document

from apps.metadata.models import MetadataDefinition
from ..models import AIGuardrailTestCase, AIGuardrailTestStatus
from .ai_service_v2 import ai_service_v2


PolicyIngestionResult = Tuple[int, int]


def _definition_title(definition: MetadataDefinition) -> str:
    data = definition.definition if isinstance(definition.definition, dict) else {}
    return (
        definition.label
        or data.get("name")
        or data.get("title")
        or data.get("label")
        or definition.key
    )


def _render_policy_definition(definition: MetadataDefinition) -> str:
    data = definition.definition or {}
    title = _definition_title(definition)
    lines: List[str] = [
        f"Policy: {title}",
        f"Layer: {definition.get_layer_display()}",
        f"Version: {definition.version}",
    ]

    if isinstance(data, dict):
        for key in ("title", "summary", "purpose", "scope", "description"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                lines.append(f"{key.title()}: {value.strip()}")
        rules = data.get("rules") or data.get("sections")
        if isinstance(rules, list):
            for idx, item in enumerate(rules, 1):
                if isinstance(item, dict):
                    heading = item.get("title") or item.get("name") or f"Item {idx}"
                    body = item.get("body") or item.get("description") or ""
                    lines.append(f"{heading}: {body}".strip())
                else:
                    lines.append(str(item))
        elif isinstance(rules, dict):
            for key, value in rules.items():
                lines.append(f"{key}: {value}")
    elif isinstance(data, list):
        for idx, item in enumerate(data, 1):
            lines.append(f"{idx}. {item}")
    else:
        lines.append(str(data))

    return "\n".join(lines)


def _expected_phrases(definition: MetadataDefinition) -> List[str]:
    data = definition.definition or {}
    phrases: List[str] = []

    def _add_value(value):
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                phrases.append(trimmed)
        elif isinstance(value, list):
            for item in value[:3]:
                _add_value(item)

    if isinstance(data, dict):
        for key in ("summary", "purpose", "scope", "keywords"):
            _add_value(data.get(key))
        rules = data.get("rules") or data.get("sections")
        if isinstance(rules, list):
            for item in rules[:3]:
                if isinstance(item, dict):
                    _add_value(item.get("summary") or item.get("description"))
                else:
                    _add_value(item)
    elif isinstance(data, list):
        for item in data[:3]:
            _add_value(item)
    else:
        _add_value(data)

    # Deduplicate while preserving order
    seen = set()
    unique_phrases: List[str] = []
    for phrase in phrases:
        if phrase not in seen:
            seen.add(phrase)
            unique_phrases.append(phrase)
    return unique_phrases


def _policy_definitions_for_company(company) -> List[MetadataDefinition]:
    base_filter = Q(is_active=True, kind__in=["ENTITY", "FORM"]) & (
        Q(label__icontains="policy") | Q(key__icontains="policy")
    )
    if company is None:
        return list(
            MetadataDefinition.objects.filter(
                base_filter,
                company__isnull=True,
                company_group__isnull=True,
            ).order_by("-updated_at")
        )

    company_group = getattr(company, "company_group", None)
    query = MetadataDefinition.objects.filter(base_filter).filter(
        Q(company=company)
        | Q(company_group=company_group, company__isnull=True)
        | Q(company_group__isnull=True, company__isnull=True)
    )
    return list(query.order_by("-updated_at"))


def _documents_from_definitions(definitions: Iterable[MetadataDefinition], company) -> List[Document]:
    documents: List[Document] = []
    for definition in definitions:
        content = _render_policy_definition(definition)
        title = _definition_title(definition)
        metadata = {
            "policy_name": title,
            "layer": definition.get_layer_display(),
            "version": definition.version,
            "company_id": getattr(company, "id", None),
            "source": "metadata",
            "definition_id": definition.id,
        }
        documents.append(Document(page_content=content, metadata=metadata))
    return documents


def _sync_guardrail_tests(*, company, definitions: Iterable[MetadataDefinition]) -> int:
    active_ids: List[int] = []
    created = 0
    for definition in definitions:
        expected = _expected_phrases(definition)
        title = _definition_title(definition)
        defaults = {
            "prompt": f"What is the {title} policy?",
            "expected_phrases": expected,
            "metadata": {
                "definition_id": definition.id,
                "layer": definition.get_layer_display(),
                "version": definition.version,
            },
            "status": AIGuardrailTestStatus.ACTIVE,
        }
        guardrail, _ = AIGuardrailTestCase.objects.update_or_create(
            company=company,
            policy_name=title,
            defaults=defaults,
        )
        active_ids.append(guardrail.id)
        created += 1

    stale_qs = AIGuardrailTestCase.objects.filter(company=company)
    if active_ids:
        stale_qs = stale_qs.exclude(id__in=active_ids)
    stale_qs.update(status=AIGuardrailTestStatus.DISABLED)
    return created


@transaction.atomic
def ingest_policy_corpus_for_company(*, company) -> PolicyIngestionResult:
    """
    Index policy metadata definitions into the vector store and maintain guardrail test cases.
    Returns a tuple of (documents_indexed, guardrails_synced).
    """
    definitions = _policy_definitions_for_company(company)
    documents = _documents_from_definitions(definitions, company)

    if documents and ai_service_v2.embeddings:
        index_name = str(getattr(company, "id", "global"))
        ai_service_v2.index_documents_from_list(documents, index_name=index_name)

    guardrails_created = _sync_guardrail_tests(company=company, definitions=definitions)
    return len(documents), guardrails_created
