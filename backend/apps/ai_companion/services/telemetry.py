from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence

from django.contrib.auth import get_user_model
from django.utils import timezone

from ..models import AITelemetryEvent

UserModel = get_user_model()


class TelemetryService:
    """
    Stores and retrieves lightweight activity telemetry that can be fed back into AI context.
    """

    def record_event(
        self,
        *,
        event_type: str,
        user,
        company=None,
        conversation=None,
        payload: Optional[Dict[str, Any]] = None,
        source: str = "ai_companion",
    ) -> Optional[AITelemetryEvent]:
        if user is None:
            return None
        return AITelemetryEvent.objects.create(
            user=user,
            company=company,
            conversation=conversation,
            event_type=event_type,
            source=source,
            payload=payload or {},
        )

    def broadcast_event(
        self,
        *,
        event_type: str,
        company=None,
        users: Optional[Sequence] = None,
        conversation=None,
        payload: Optional[Dict[str, Any]] = None,
        source: str = "ai_companion",
        preferred_roles: Optional[Sequence[str]] = None,
    ) -> List[AITelemetryEvent]:
        """
        Broadcast a telemetry event to multiple users, inferring sensible recipients when none are supplied.
        """
        recipients = list(users or self._resolve_company_recipients(company=company, preferred_roles=preferred_roles))
        if not recipients:
            return []

        payload = payload or {}
        events = [
            AITelemetryEvent(
                user=user,
                company=company,
                conversation=conversation,
                event_type=event_type,
                source=source,
                payload=payload,
            )
            for user in recipients
        ]
        return list(AITelemetryEvent.objects.bulk_create(events))

    def event_exists(
        self,
        *,
        event_type: str,
        company=None,
        payload_filters: Optional[Dict[str, Any]] = None,
        within_hours: Optional[float] = 24.0,
    ) -> bool:
        """
        Guard helper to check if a similar telemetry event already exists within the provided window.
        """
        filters: Dict[str, Any] = {"event_type": event_type}
        if company is not None:
            filters["company"] = company
        if payload_filters:
            for key, value in payload_filters.items():
                filters[f"payload__{key}"] = value
        if within_hours is not None:
            filters["created_at__gte"] = timezone.now() - timedelta(hours=within_hours)
        return AITelemetryEvent.objects.filter(**filters).exists()

    def _resolve_company_recipients(
        self,
        *,
        company,
        preferred_roles: Optional[Sequence[str]] = None,
    ) -> Iterable:
        """
        Resolve users that should receive telemetry for the provided company.
        Prioritises preferred role holders, falls back to all active members, then system admins.
        """
        if company is None:
            return self._system_admins()

        from apps.users.models import UserCompanyRole  # local import to avoid circular dependency

        base_qs = UserCompanyRole.objects.filter(company=company, is_active=True).select_related("role")

        user_ids: List[int] = []
        if preferred_roles:
            user_ids.extend(
                base_qs.filter(role__name__in=preferred_roles).values_list("user_id", flat=True)
            )

        if not user_ids:
            user_ids.extend(base_qs.values_list("user_id", flat=True))

        if not user_ids:
            return self._system_admins()

        # Remove duplicates while preserving order
        seen = set()
        ordered_ids = []
        for user_id in user_ids:
            if user_id not in seen:
                seen.add(user_id)
                ordered_ids.append(user_id)

        return UserModel.objects.filter(id__in=ordered_ids, is_active=True)

    def _system_admins(self):
        return UserModel.objects.filter(is_system_admin=True, is_active=True)

    def recent_events(self, *, user, company=None, limit: int = 25) -> List[Dict[str, Any]]:
        if user is None:
            return []

        qs = AITelemetryEvent.objects.filter(user=user)
        if company:
            qs = qs.filter(company=company)
        events = qs.order_by("-created_at")[:limit]
        return [
            {
                "event_type": event.event_type,
                "source": event.source,
                "payload": event.payload,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]
