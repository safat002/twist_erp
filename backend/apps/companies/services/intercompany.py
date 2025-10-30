from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from django.db import transaction

from ..models import Company, InterCompanyLink

logger = logging.getLogger(__name__)

MirrorHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


class InterCompanyRegistry:
    """Registry of handlers capable of mirroring a source transaction into a counterparty company."""

    def __init__(self):
        self._handlers: Dict[str, MirrorHandler] = {}

    def register(self, entity: str, handler: MirrorHandler) -> None:
        logger.debug("Registering inter-company handler for %s", entity)
        self._handlers[entity.lower()] = handler

    def get(self, entity: str) -> Optional[MirrorHandler]:
        return self._handlers.get(entity.lower())


registry = InterCompanyRegistry()


@dataclass
class InterCompanyResult:
    link: InterCompanyLink
    mirrored_payload: Optional[Dict[str, Any]]


class InterCompanyTransactionService:
    """
    Helper that records inter-company links and invokes registered handlers to mirror transactions.
    """

    def __init__(self, entity: str):
        self.entity = entity.lower()

    def register_handler(self, handler: MirrorHandler) -> None:
        registry.register(self.entity, handler)

    def record(
        self,
        *,
        initiating_company: Company,
        counterparty_company: Company,
        source_record_id: str,
        payload: Dict[str, Any],
    ) -> InterCompanyResult:
        if initiating_company.company_group_id != counterparty_company.company_group_id:
            raise ValueError("Inter-company transactions must belong to the same company group.")

        with transaction.atomic():
            link, created = InterCompanyLink.objects.get_or_create(
                company_group=initiating_company.company_group,
                initiating_company=initiating_company,
                counterparty_company=counterparty_company,
                source_entity=self.entity,
                source_record_id=str(source_record_id),
                defaults={"status": "pending"},
            )
            if not created:
                logger.info(
                    "Inter-company link already exists for %s/%s; updating timestamp only.",
                    self.entity,
                    source_record_id,
                )
                link.save(update_fields=["updated_at"])

            mirrored_payload = None
            handler = registry.get(self.entity)
            if handler:
                try:
                    mirrored_payload = handler(payload)
                    link.status = "mirrored"
                    link.save(update_fields=["status", "updated_at"])
                except Exception as exc:
                    logger.exception("Inter-company handler failed for %s: %s", self.entity, exc)
                    link.status = "error"
                    link.save(update_fields=["status", "updated_at"])
                    raise
            else:
                logger.debug("No registered handler for inter-company entity '%s'.", self.entity)

        return InterCompanyResult(link=link, mirrored_payload=mirrored_payload)
