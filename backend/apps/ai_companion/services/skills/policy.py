from __future__ import annotations

from typing import List

from apps.metadata.models import MetadataDefinition
from .base import (
    BaseSkill,
    ProactiveSuggestionPayload,
    SkillAction,
    SkillContext,
    SkillResponse,
)
from ..memory import MemoryRecord

KEYWORDS = {"policy", "compliance", "rule", "approval matrix", "governance"}


class PolicySkill(BaseSkill):
    name = "policy"
    description = "Explains company policies, approval rules, and recommended next steps."
    priority = 30

    def _has_access(self, context: SkillContext) -> bool:
        if getattr(context.user, "is_system_admin", False):
            return True
        roles = {role.lower() for role in context.short_term.get("user_roles", [])}
        if not roles:
            return False
        keywords = ("policy", "compliance", "admin", "hr", "legal")
        return any(any(keyword in role for keyword in keywords) for role in roles)

    def is_authorised(self, context: SkillContext) -> bool:
        return self._has_access(context)

    def can_handle(self, message: str, context: SkillContext) -> bool:
        if context.module in {"policy", "compliance"}:
            return True
        lowered = message.lower()
        return any(keyword in lowered for keyword in KEYWORDS)

    def handle(self, message: str, context: SkillContext) -> SkillResponse:
        if not self._has_access(context):
            return SkillResponse(
                message="I can only share policy details with compliance or admin roles. Please ask a policy owner to grant access.",
                intent="policy.permission_denied",
                confidence=0.05,
            )

        company = context.company or context.user.default_company
        if company is None:
            return SkillResponse(
                message="Once you select a company I can look up its policy overrides and approval rules.",
                intent="policy.no_company",
                confidence=0.2,
            )

        definitions = (
            MetadataDefinition.objects.filter(kind__in=["ENTITY", "FORM"], key__icontains="policy")
            .order_by("-updated_at")[:5]
        )
        parts: List[str] = []
        actions: List[SkillAction] = []
        memory_updates: List[MemoryRecord] = []
        suggestions: List[ProactiveSuggestionPayload] = []
        policy_titles: List[str] = []

        if definitions:
            for definition in definitions:
                layer = (
                    definition.get_layer_display()
                    if hasattr(definition, "get_layer_display")
                    else definition.layer
                )
                payload = definition.definition if isinstance(definition.definition, dict) else {}
                title = (
                    definition.label
                    or payload.get("name")
                    or payload.get("title")
                    or payload.get("label")
                    or definition.key
                )
                policy_titles.append(title)
                parts.append(f"- {title} ({layer}) version {definition.version}.")
            actions.append(
                SkillAction(
                    label="View policy library",
                    action="navigate",
                    payload={"path": "/policies"},
                )
            )
            memory_updates.append(
                MemoryRecord(
                    key="policy_snapshot",
                    value={"policies": policy_titles},
                    scope="company",
                    user=context.user,
                    company=company,
                )
            )
        else:
            parts.append(
                "I could not find formal policy definitions yet. You can add them from the Metadata workspace."
            )

        lowered = message.lower()
        if "approval" in lowered:
            suggestions.append(
                ProactiveSuggestionPayload(
                    title="Set up approval routing",
                    body="Would you like me to draft an approval matrix based on current roles and thresholds?",
                    metadata={"module": "approvals"},
                )
            )

        response_message = "Here are the policies I can reference:\n" + "\n".join(parts)

        return SkillResponse(
            message=response_message,
            intent="policy.summary",
            confidence=0.55,
            actions=actions,
            proactive_suggestions=suggestions,
            memory_updates=memory_updates,
        )
