from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from django.conf import settings

from .base import BaseSkill, SkillContext, SkillResponse
from ..ai_service_v2 import ai_service_v2

logger = logging.getLogger(__name__)

PLAN_KEYWORDS = {
    "ai plan",
    "ai roadmap",
    "plan",
    "roadmap",
    "strategy",
    "assistant",
    "conversation",
}


class PlanSkill(BaseSkill):
    name = "plan"
    description = "Answers questions using the internal AI roadmap and design plan."
    priority = 60

    def __init__(self, memory_service):
        super().__init__(memory_service)
        self._cached_plan_text: Optional[str] = None

    def _load_plan_text(self) -> Optional[str]:
        if self._cached_plan_text:
            return self._cached_plan_text

        candidate_paths = [
            Path(settings.BASE_DIR).parent / "docs" / "ai_plan.md",
            Path(settings.BASE_DIR) / "docs" / "ai_plan.md",
        ]
        for path in candidate_paths:
            if path.exists():
                try:
                    self._cached_plan_text = path.read_text(encoding="utf-8")
                    return self._cached_plan_text
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed to read plan document %s: %s", path, exc)
        return None

    def can_handle(self, message: str, context: SkillContext) -> bool:
        lowered = message.lower()
        if context.module in {"ai", "strategy"}:
            return True
        return any(keyword in lowered for keyword in PLAN_KEYWORDS)

    def handle(self, message: str, context: SkillContext) -> SkillResponse:
        # Prefer vector-backed response if available
        rag_response = ai_service_v2.chat(
            f"Use the Twist ERP AI plan and roadmap documentation to answer this question:\n\n{message}",
            company_id=getattr(context.company, "id", None),
        )
        if rag_response.get("intent") != "fallback":
            return SkillResponse(
                message=rag_response.get("message"),
                intent="plan.answer",
                confidence=0.65,
                sources=rag_response.get("sources"),
            )

        plan_text = self._load_plan_text()
        if not plan_text:
            return SkillResponse(
                message="I could not load the AI plan document yet. Once it's indexed I'll be able to answer.",
                intent="plan.unavailable",
                confidence=0.1,
            )

        lowered = message.lower()
        sections = plan_text.split("\n\n")
        matches = [
            section.strip()
            for section in sections
            if any(keyword in section.lower() for keyword in lowered.split())
        ]
        if not matches:
            matches = sections[:5]

        snippet = "\n\n".join(matches[:3])
        answer = (
            "Here's what I found in the AI plan:\n\n"
            f"{snippet}\n\n"
            "Let me know if you want a deeper breakdown or actions derived from this."
        )
        return SkillResponse(
            message=answer,
            intent="plan.summary",
            confidence=0.4,
        )
