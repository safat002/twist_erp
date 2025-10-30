from __future__ import annotations

from typing import Any, Dict, Optional


from apps.companies.models import Company, CompanyGroup
from .models import AuditLog


def log_audit_event(
    *,
    user,
    company: Optional[Company],
    company_group: Optional[CompanyGroup],
    action: str,
    entity_type: str,
    entity_id: str,
    description: str = "",
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    correlation_id: str = "",
) -> AuditLog:
    """Persist an audit log entry while handling optional context gracefully."""
    return AuditLog.objects.create(
        user=user,
        company=company,
        company_group=company_group or getattr(company, "company_group", None),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        description=description,
        before_value=before,
        after_value=after,
        ip_address=ip_address,
        correlation_id=correlation_id,
    )
