from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional

from django.db.models import Q

from ..models import AIUserMemory

logger = logging.getLogger(__name__)


@dataclass
class MemoryRecord:
    key: str
    value: dict
    scope: str = "user"
    user: Any = None
    company: Any = None
    tags: Optional[List[str]] = None


class MemoryService:
    """
    Lightweight interface for storing and retrieving user/company memory.
    """

    def save(self, record: MemoryRecord):
        if not record.key:
            logger.warning("Attempted to save memory without key.")
            return

        obj, _ = AIUserMemory.objects.update_or_create(
            user=record.user if record.scope != "global" else None,
            company=record.company if record.scope in {"company", "user"} else None,
            scope=record.scope,
            key=record.key,
            defaults={
                "value": record.value,
                "tags": record.tags or [],
            },
        )
        logger.debug("Saved memory %s (scope=%s)", obj.key, obj.scope)

    def recall(self, *, user=None, company=None, scope: str = "user", key: Optional[str] = None) -> Iterable[AIUserMemory]:
        qs = AIUserMemory.objects.all()
        if scope == "user":
            qs = qs.filter(user=user)
        elif scope == "company":
            qs = qs.filter(Q(company=company) | Q(scope="global"))
        elif scope == "global":
            qs = qs.filter(scope="global")

        if key:
            qs = qs.filter(key=key)

        return qs.order_by("-updated_at")
