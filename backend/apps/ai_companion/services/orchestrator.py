from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from django.db import models, transaction
from django.utils import timezone

from ..models import (
    AIFeedback,
    AIConversation,
    AIMessage,
    AIProactiveSuggestion,
    AISkillProfile,
    AITrainingExample,
    AITrainingExampleStatus,
)
from .context_builder import ContextBuilder
from .memory import MemoryService
from .telemetry import TelemetryService
from .skills.base import BaseSkill, SkillContext, SkillResponse
from .skills.action_execution import ActionExecutionSkill
from .skills.conversation import ConversationSkill
from .skills.data_migration import DataMigrationSkill
from .skills.data_query import DataQuerySkill
from .skills.document_extraction import DocumentExtractionSkill
from .skills.plan import PlanSkill
from .skills.policy import PolicySkill
from .skills.reporting import ReportingSkill
from .skills.system import SystemFallbackSkill

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorConfig:
    proactive_threshold_minutes: int = 15
    max_history_messages: int = 25


class AIOrchestrator:
    """
    Central coordinator for the AI companion. It manages skill routing, memory,
    conversation persistence, feedback, and proactive insights.
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self.memory = MemoryService()
        self.telemetry = TelemetryService()
        self.context_builder = ContextBuilder(self.memory, self.telemetry)
        self._skills: Dict[str, BaseSkill] = {}
        self._register_default_skills()

    # ------------------------------------------------------------------ #
    # Skill registration                                                  #
    # ------------------------------------------------------------------ #
    def register_skill(self, skill: BaseSkill) -> None:
        logger.debug("Registering AI skill %s", skill.name)
        self._skills[skill.name] = skill

    def _register_default_skills(self):
        # High-priority skills (specific actions)
        self.register_skill(ActionExecutionSkill(self.memory))  # Priority: 15
        self.register_skill(DataQuerySkill(self.memory))  # Priority: 20

        # Medium-priority skills (domain-specific)
        self.register_skill(DataMigrationSkill(self.memory))
        self.register_skill(DocumentExtractionSkill(self.memory))
        self.register_skill(ReportingSkill(self.memory))
        self.register_skill(PolicySkill(self.memory))
        self.register_skill(PlanSkill(self.memory))

        # Low-priority skills (general conversation and fallback)
        self.register_skill(ConversationSkill(self.memory))  # Priority: 50
        self.register_skill(SystemFallbackSkill(self.memory))  # Priority: 999 (last resort)

    # ------------------------------------------------------------------ #
    # Conversation helpers                                               #
    # ------------------------------------------------------------------ #
    def _get_or_create_conversation(self, user, company, conversation_id=None, context=None):
        if conversation_id:
            try:
                convo = AIConversation.objects.get(conversation_id=conversation_id, user=user)
                if context:
                    convo.context.update(context)
                    convo.save(update_fields=["context", "updated_at"])
                return convo
            except AIConversation.DoesNotExist:
                logger.warning("Conversation %s not found for user %s", conversation_id, user)

        convo = AIConversation.objects.create(
            user=user,
            company=company,
            context=context or {},
        )
        return convo

    def _store_message(self, conversation: AIConversation, role: str, content: str, **kwargs):
        return AIMessage.objects.create(
            conversation=conversation,
            role=role,
            content=content,
            intent=kwargs.get("intent"),
            confidence=kwargs.get("confidence"),
            metadata=kwargs.get("metadata", {}),
        )

    def _record_skill_usage(self, conversation: AIConversation, skill: BaseSkill, success: bool):
        profile, _ = AISkillProfile.objects.get_or_create(
            user=conversation.user,
            company=conversation.company,
            skill_name=skill.name,
        )
        profile.usage_count += 1
        if success:
            profile.success_count += 1
        profile.last_used_at = timezone.now()
        profile.save(update_fields=["usage_count", "success_count", "last_used_at"])

    def _legacy_chat(self, message: str, *, company=None, metadata: Optional[Dict[str, Any]] = None) -> Dict:
        try:
            from .ai_service_v2 import chat as legacy_chat  # noqa
        except Exception as exc:
            logger.warning("Legacy QA chain unavailable: %s", exc)
            return {"message": "Hmm, I'm having some trouble with that. Could you try asking in a different way?", "intent": "fallback"}
        return legacy_chat(
            message,
            company_id=getattr(company, "id", None),
            metadata=metadata or {},
        )

    # ------------------------------------------------------------------ #
    # Routing                                                             #
    # ------------------------------------------------------------------ #
    def _select_skill(self, message: str, context: SkillContext) -> BaseSkill:
        # 1. Prefer skill indicated via context
        if context.preferred_skill and context.preferred_skill in self._skills:
            return self._skills[context.preferred_skill]

        # 2. Ask each skill if it can handle the message
        candidates: List[BaseSkill] = []
        for skill in self._skills.values():
            try:
                if skill.can_handle(message, context) and skill.is_authorised(context):
                    candidates.append(skill)
            except Exception as exc:
                logger.exception("Skill %s.can_handle failed: %s", skill.name, exc)

        if candidates:
            # Pick the one with highest priority (lower number => higher priority)
            candidates.sort(key=lambda s: s.priority)
            return candidates[0]

        # 3. Fall back to the system skill
        return self._skills["system_fallback"]

    # ------------------------------------------------------------------ #
    # Public chat interface                                               #
    # ------------------------------------------------------------------ #
    def chat(self, *, message: str, user, company=None, conversation_id=None, metadata=None) -> Dict:
        metadata = metadata or {}
        context = SkillContext(
            user=user,
            company=company,
            current_page=metadata.get("page"),
            module=metadata.get("module"),
            extra=metadata.get("extra") or {},
            preferred_skill=metadata.get("preferred_skill"),
        )
        bundle = self.context_builder.build(user=user, company=company, metadata=metadata)
        context.short_term = bundle.short_term
        context.long_term = bundle.long_term
        context.telemetry = bundle.telemetry
        context.extra.setdefault("short_term", {}).update(bundle.short_term)
        context.extra.setdefault("long_term", {}).update(bundle.long_term)
        context.extra["telemetry"] = bundle.telemetry

        with transaction.atomic():
            conversation = self._get_or_create_conversation(
                user=user,
                company=company,
                conversation_id=conversation_id,
                context=metadata,
            )
            user_message = self._store_message(conversation, "user", message, metadata=metadata)
            self.telemetry.record_event(
                event_type="chat.user_message",
                user=user,
                company=company,
                conversation=conversation,
                payload={
                    "module": context.module,
                    "page": context.current_page,
                    "message_length": len(message),
                },
            )

            history = list(
                conversation.messages.order_by("-created_at")[: self.config.max_history_messages]
            )
            history.reverse()
            context.history = history

            skill = self._select_skill(message, context)
            conversation.active_skill = skill.name
            conversation.save(update_fields=["active_skill", "updated_at"])

            try:
                result = skill.handle(message=message, context=context)
                success = True
            except Exception as exc:
                logger.exception("Skill %s failed: %s", skill.name, exc)
                legacy = self._legacy_chat(message, company=company, metadata=metadata)
                result = SkillResponse(
                    message=legacy.get("message"),
                    intent=legacy.get("intent", "fallback"),
                    confidence=legacy.get("confidence"),
                    sources=legacy.get("sources"),
                )
                success = False

            action_payloads = [action.to_dict() for action in result.actions]
            assistant_message = self._store_message(
                conversation,
                "assistant",
                result.message,
                intent=result.intent,
                confidence=result.confidence,
                metadata={
                    "sources": result.sources,
                    "actions": action_payloads,
                    "skill": skill.name,
                    "context": {
                        "short_term": context.short_term,
                        "long_term": context.long_term,
                    },
                },
            )
            self._record_skill_usage(conversation, skill, success)
            self.telemetry.record_event(
                event_type="chat.assistant_response",
                user=user,
                company=company,
                conversation=conversation,
                payload={
                    "intent": result.intent,
                    "skill": skill.name,
                    "confidence": result.confidence,
                    "actions": [action["action"] for action in action_payloads],
                },
            )

        # Update memory with new facts extracted from skill response
        if result.memory_updates:
            for memory in result.memory_updates:
                self.memory.save(memory)

        # Persist proactive suggestions if provided
        if result.proactive_suggestions:
            for suggestion in result.proactive_suggestions:
                suggestion = AIProactiveSuggestion.objects.create(
                    user=user,
                    company=company,
                    title=suggestion.title,
                    body=suggestion.body,
                    metadata=suggestion.metadata,
                    source_skill=skill.name,
                )
                # Mirror to Notification Center
                try:
                    from apps.notifications.models import Notification, NotificationSeverity
                    sev = (suggestion.severity or "info").lower()
                    notif_sev = NotificationSeverity.INFO
                    if sev == "warning":
                        notif_sev = NotificationSeverity.WARNING
                    elif sev == "critical":
                        notif_sev = NotificationSeverity.CRITICAL
                    Notification.objects.create(
                        company=company,
                        company_group=company.company_group,
                        created_by=None,
                        user=user,
                        title=suggestion.title,
                        body=suggestion.body,
                        severity=notif_sev,
                        group_key="ai.suggestion",
                        entity_type="AI_SUGGESTION",
                        entity_id=str(suggestion.id),
                    )
                except Exception:
                    logger.exception("Failed to mirror AI suggestion to Notification Center")
                self.telemetry.record_event(
                    event_type="proactive.created",
                    user=user,
                    company=company,
                    conversation=conversation,
                    payload={
                        "title": suggestion.title,
                        "skill": skill.name,
                        "metadata": suggestion.metadata,
                    },
                )

        return {
            "conversation_id": str(conversation.conversation_id),
            "message": result.message,
            "intent": result.intent,
            "confidence": result.confidence,
            "sources": result.sources,
            "actions": action_payloads,
            "suggestions": [
                suggestion.to_dict() for suggestion in (result.proactive_suggestions or [])
            ],
            "skill": skill.name,
            "context": {
                "short_term": context.short_term,
                "long_term": context.long_term,
            },
        }

    # ------------------------------------------------------------------ #
    # Feedback / suggestions                                              #
    # ------------------------------------------------------------------ #
    def record_feedback(self, conversation_id: str, user, rating: str, notes: str = ""):
        try:
            conversation = AIConversation.objects.get(conversation_id=conversation_id, user=user)
        except AIConversation.DoesNotExist:
            logger.warning("Cannot record feedback; conversation %s not found", conversation_id)
            return

        assistant_message = (
            conversation.messages.filter(role="assistant").order_by("-created_at").first()
        )
        user_message = (
            conversation.messages.filter(role="user").order_by("-created_at").first()
        )
        feedback = AIFeedback.objects.create(
            conversation=conversation,
            message=assistant_message,
            rating=rating,
            notes=notes,
            feedback_type="thumbs",
            payload={
                "assistant_message_id": getattr(assistant_message, "id", None),
                "user_message_id": getattr(user_message, "id", None),
            },
        )
        self.telemetry.record_event(
            event_type=f"feedback.{rating}",
            user=user,
            company=conversation.company,
            conversation=conversation,
            payload={
                "notes": notes,
                "assistant_message_id": getattr(assistant_message, "id", None),
                "skill": (assistant_message.metadata or {}).get("skill") if assistant_message else None,
            },
        )

        if assistant_message:
            prompt_text = user_message.content if user_message else ""
            metadata = {
                "intent": assistant_message.intent,
                "skill": (assistant_message.metadata or {}).get("skill"),
                "rating": rating,
                "notes": notes,
            }
            AITrainingExample.objects.create(
                user=conversation.user,
                company=conversation.company,
                feedback=feedback,
                prompt=prompt_text,
                completion=assistant_message.content,
                source="feedback",
                status=(
                    AITrainingExampleStatus.APPROVED
                    if rating == "up"
                    else AITrainingExampleStatus.REVIEW
                ),
                metadata=metadata,
            )

    def get_pending_suggestions(self, user, company=None) -> Iterable[AIProactiveSuggestion]:
        qs = AIProactiveSuggestion.objects.filter(user=user, status="pending")
        if company:
            qs = qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
        return qs.order_by("-created_at")

    def mark_suggestion(self, suggestion_id: int, status: str):
        try:
            suggestion = AIProactiveSuggestion.objects.get(pk=suggestion_id)
        except AIProactiveSuggestion.DoesNotExist:
            return
        suggestion.status = status
        suggestion.delivered_at = timezone.now()
        suggestion.save(update_fields=["status", "delivered_at", "updated_at"])
        self.telemetry.record_event(
            event_type=f"suggestion.{status}",
            user=suggestion.user,
            company=suggestion.company,
            payload={
                "suggestion_id": suggestion.id,
                "alert_type": suggestion.alert_type,
                "source_skill": suggestion.source_skill,
            },
        )


# Singleton orchestrator used across the app
orchestrator = AIOrchestrator()
