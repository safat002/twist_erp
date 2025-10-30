from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from django.utils import timezone

from ...models import AIMessage
from ..memory import MemoryRecord, MemoryService


@dataclass
class SkillAction:
    label: str
    action: str
    payload: Optional[Dict[str, Any]] = None

    def to_dict(self):
        return {
            "label": self.label,
            "action": self.action,
            "payload": self.payload or {},
        }


@dataclass
class ProactiveSuggestionPayload:
    title: str
    body: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "title": self.title,
            "body": self.body,
            "metadata": self.metadata,
        }


@dataclass
class SkillResponse:
    message: str
    intent: str
    confidence: Optional[float] = None
    sources: Optional[List[Any]] = None
    actions: List[SkillAction] = field(default_factory=list)
    memory_updates: List[MemoryRecord] = field(default_factory=list)
    proactive_suggestions: List[ProactiveSuggestionPayload] = field(default_factory=list)


@dataclass
class SkillContext:
    user: Any
    company: Any
    current_page: Optional[str] = None
    module: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    preferred_skill: Optional[str] = None
    history: List[AIMessage] = field(default_factory=list)
    short_term: Dict[str, Any] = field(default_factory=dict)
    long_term: Dict[str, Any] = field(default_factory=dict)
    telemetry: List[Dict[str, Any]] = field(default_factory=list)


class BaseSkill(abc.ABC):
    """
    Base contract for AI assistant skills. Each skill declares when it should
    handle a request and returns a structured response containing actions,
    memory updates, and optional proactive notifications.
    """

    name: str = "base"
    description: str = ""
    priority: int = 100  # lower number -> higher priority

    def __init__(self, memory_service: MemoryService):
        self.memory = memory_service

    @abc.abstractmethod
    def can_handle(self, message: str, context: SkillContext) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def handle(self, message: str, context: SkillContext) -> SkillResponse:
        raise NotImplementedError

    def is_authorised(self, context: SkillContext) -> bool:
        return True

    def timestamp(self):
        return timezone.now()
