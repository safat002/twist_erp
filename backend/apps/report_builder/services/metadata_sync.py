from __future__ import annotations

from typing import Any, Dict

from django.utils import timezone

from apps.metadata.models import MetadataDefinition
from apps.metadata.services import MetadataScope, create_metadata_version


def sync_report_metadata(report, *, user=None, publish: bool = False) -> MetadataDefinition:
    """
    Persist the report definition into the metadata registry.

    This creates a new metadata version on every save so we retain full history.
    """
    from apps.report_builder.models import ReportDefinition  # Local import to avoid cycles

    if not isinstance(report, ReportDefinition):
        raise TypeError("sync_report_metadata expects a ReportDefinition instance.")

    scope = _scope_for_report(report)
    payload = _build_definition_payload(report)
    summary = _build_summary(report)
    status = "active" if publish or report.status == "active" else "draft"

    metadata = create_metadata_version(
        key=report.metadata_key,
        kind="REPORT",
        layer=report.layer,
        scope=scope,
        definition=payload,
        summary=summary,
        description=report.description or "",
        status=status,
        user=user,
    )

    if status == "active":
        metadata.activate(user=user)

    update_kwargs: Dict[str, Any] = {
        "metadata": metadata,
        "version": metadata.version,
        "updated_at": timezone.now(),
    }
    if status == "active":
        update_kwargs["status"] = "active"
        update_kwargs["is_active"] = True
        update_kwargs["last_published_at"] = timezone.now()

    ReportDefinition.objects.filter(pk=report.pk).update(**update_kwargs)

    # Keep in-memory instance in sync for downstream usage.
    for field, value in update_kwargs.items():
        setattr(report, field, value)

    return metadata


def _scope_for_report(report) -> MetadataScope:
    if report.scope_type == "COMPANY" and report.company:
        return MetadataScope.for_company(report.company)
    if report.scope_type == "GROUP" and report.company_group:
        return MetadataScope.for_group(report.company_group)
    return MetadataScope.global_scope()


def _build_definition_payload(report) -> Dict[str, Any]:
    definition = report.definition or {}
    return {
        "report": {
            "name": report.name,
            "slug": report.slug,
            "description": report.description,
            "data_source": definition.get("data_source", {}),
            "fields": definition.get("fields", []),
            "filters": definition.get("filters", []),
            "sorts": definition.get("sorts", []),
            "groupings": definition.get("groupings", []),
            "calculations": definition.get("calculations", []),
            "limit": definition.get("limit"),
        },
        "permissions": report.required_permission_codes(),
    }


def _build_summary(report) -> Dict[str, Any]:
    definition = report.definition or {}
    field_count = len(definition.get("fields") or [])
    source = definition.get("data_source") or {}
    summary = {
        "field_count": field_count,
        "data_source": {
            "type": source.get("type"),
            "key": source.get("key") or source.get("slug"),
            "label": source.get("label"),
        },
    }
    summary.update(report.summary or {})
    return summary
