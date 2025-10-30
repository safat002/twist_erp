from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from django.db.models import Prefetch

from apps.data_migration.models import MigrationJob, migration_enums
from apps.users.models import UserCompanyRole

from ..models import UserAIPreference

from .memory import MemoryService
from .telemetry import TelemetryService


@dataclass
class ContextBundle:
    short_term: Dict[str, Any]
    long_term: Dict[str, Any]
    telemetry: List[Dict[str, Any]]


class ContextBuilder:
    """
    Aggregates short-term context, long-term memory, and telemetry snapshots for the orchestrator.
    """

    def __init__(self, memory_service: MemoryService, telemetry_service: TelemetryService):
        self.memory = memory_service
        self.telemetry = telemetry_service

    def build(
        self,
        *,
        user,
        company=None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextBundle:
        metadata = metadata or {}
        short_term = self._build_short_term_context(user=user, company=company, metadata=metadata)
        long_term = self._build_long_term_memory(user=user, company=company)
        telemetry = self.telemetry.recent_events(user=user, company=company, limit=15)
        return ContextBundle(short_term=short_term, long_term=long_term, telemetry=telemetry)

    # ------------------------------------------------------------------ #
    # Short-term context helpers                                         #
    # ------------------------------------------------------------------ #
    def _build_short_term_context(
        self,
        *,
        user,
        company=None,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        active_record = metadata.get("record") or (metadata.get("extra") or {}).get("record")
        return {
            "active_record": active_record,
            "user_roles": self._user_roles(user=user, company=company),
            "user_permissions": self._user_permissions(user=user, company=company),
            "preferences": self._user_preferences(user=user, company=company),
            "company": self._company_metadata(company),
            "pending_migrations": self._pending_migrations(company),
        }

    def _user_roles(self, *, user, company=None) -> List[str]:
        if user is None or not user.is_authenticated:
            return []

        qs = UserCompanyRole.objects.filter(user=user, is_active=True).select_related("role")
        if company is not None:
            qs = qs.filter(company=company)
        roles = []
        for membership in qs:
            if membership.role:
                roles.append(membership.role.name)
        if getattr(user, "is_system_admin", False):
            roles.append("System Admin")
        return roles

    def _user_permissions(self, *, user, company=None) -> List[str]:
        if user is None or not user.is_authenticated:
            return []

        qs = (
            UserCompanyRole.objects.filter(user=user, is_active=True)
            .select_related("role")
            .prefetch_related(Prefetch("role__permissions"))
        )
        if company is not None:
            qs = qs.filter(company=company)

        permissions: set[str] = set()
        for membership in qs:
            role = membership.role
            if not role:
                continue
            for code in role.permissions.values_list("code", flat=True):
                permissions.add(code)

        if getattr(user, "is_system_admin", False) or getattr(user, "is_superuser", False):
            permissions.add("*")

        return sorted(permissions)

    def _user_preferences(self, *, user, company=None) -> Dict[str, Any]:
        if user is None or not user.is_authenticated:
            return {"global": {}, "company": {} if company else {}}

        qs = UserAIPreference.objects.filter(user=user)
        global_prefs: Dict[str, Any] = {}
        company_pref_map: Dict[int, Dict[str, Any]] = {}

        for pref in qs:
            if pref.company_id is None:
                global_prefs[pref.key] = pref.value
            else:
                company_pref_map.setdefault(pref.company_id, {})[pref.key] = pref.value

        if company is not None:
            return {
                "global": global_prefs,
                "company": company_pref_map.get(company.id, {}),
            }

        return {
            "global": global_prefs,
            "companies": {
                str(company_id): values for company_id, values in company_pref_map.items()
            },
        }

    def _company_metadata(self, company) -> Optional[Dict[str, Any]]:
        if company is None:
            return None

        group = getattr(company, "company_group", None)
        return {
            "id": company.id,
            "code": company.code,
            "name": company.name,
            "currency_code": company.currency_code,
            "fiscal_year_start": company.fiscal_year_start.isoformat()
            if getattr(company, "fiscal_year_start", None)
            else None,
            "group": {
                "id": group.id,
                "name": group.name,
                "industry": getattr(group, "industry_pack_type", None),
            }
            if group
            else None,
        }

    def _pending_migrations(self, company) -> List[Dict[str, Any]]:
        if company is None:
            return []

        terminal_statuses = {
            migration_enums.MigrationJobStatus.COMMITTED,
            migration_enums.MigrationJobStatus.ROLLED_BACK,
        }
        jobs = (
            MigrationJob.objects.filter(company=company)
            .exclude(status__in=terminal_statuses)
            .order_by("-updated_at")[:3]
        )
        pending = []
        for job in jobs:
            pending.append(
                {
                    "id": job.id,
                    "job_id": str(job.migration_job_id),
                    "status": job.status,
                    "target": job.target_model or job.entity_name_guess,
                    "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                }
            )
        return pending

    # ------------------------------------------------------------------ #
    # Long-term memory helpers                                           #
    # ------------------------------------------------------------------ #
    def _build_long_term_memory(self, *, user, company=None) -> Dict[str, Any]:
        return {
            "user": self._serialize_memories(
                self.memory.recall(user=user, company=company, scope="user"), limit=5
            ),
            "company": self._serialize_memories(
                self.memory.recall(user=user, company=company, scope="company"), limit=5
            ),
            "global": self._serialize_memories(
                self.memory.recall(scope="global"), limit=5
            ),
        }

    def _serialize_memories(self, memories, *, limit: int) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for memory in memories[:limit]:
            results.append(
                {
                    "key": memory.key,
                    "value": memory.value,
                    "scope": memory.scope,
                    "updated_at": memory.updated_at.isoformat(),
                    "tags": memory.tags,
                }
            )
        return results
