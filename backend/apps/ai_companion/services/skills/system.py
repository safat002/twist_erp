from __future__ import annotations

from .base import BaseSkill, SkillContext, SkillResponse


def _legacy_chat(message: str):
    try:
        from ..ai_service_v2 import chat as legacy_chat  # noqa
    except Exception:
        return {
            "message": "I'm still learning. Could you try rephrasing?",
            "intent": "fallback",
            "confidence": None,
            "sources": None,
        }
    return legacy_chat(message)


class SystemFallbackSkill(BaseSkill):
    name = "system_fallback"
    description = "Fallback skill that delegates to the legacy retrieval QA chain."
    priority = 999

    def can_handle(self, message: str, context: SkillContext) -> bool:
        return True

    def handle(self, message: str, context: SkillContext) -> SkillResponse:
        lowered = (message or "").strip().lower()
        greetings = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}
        if lowered in greetings or any(lowered.startswith(greet) for greet in greetings):
            return SkillResponse(
                message="Hi there! How can I help you in Twist ERP today?",
                intent="greeting",
                confidence=0.4,
            )

        result = _legacy_chat(message)
        return SkillResponse(
            message=result.get("message", "I'm still learning. Could you rephrase that?"),
            intent=result.get("intent", "fallback"),
            confidence=result.get("confidence"),
            sources=result.get("sources"),
        )
