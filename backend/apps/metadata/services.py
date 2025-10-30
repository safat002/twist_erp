from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Dict, Optional

from django.db import transaction

from apps.companies.models import Company, CompanyGroup
from .models import MetadataDefinition

LAYER_ORDER = ["CORE", "INDUSTRY_PACK", "GROUP_CUSTOM", "COMPANY_OVERRIDE"]


@dataclass
class MetadataScope:
    scope_type: str
    company_group: Optional[Any] = None  # CompanyGroup
    company: Optional[Any] = None  # Company

    @classmethod
    def for_company(cls, company) -> "MetadataScope":
        return cls(scope_type="COMPANY", company=company, company_group=getattr(company, "company_group", None))

    @classmethod
    def for_group(cls, company_group) -> "MetadataScope":
        return cls(scope_type="GROUP", company_group=company_group)

    @classmethod
    def global_scope(cls) -> "MetadataScope":
        return cls(scope_type="GLOBAL")


@transaction.atomic
def create_metadata_version(
    *,
    key: str,
    kind: str,
    layer: str,
    scope: MetadataScope,
    definition: Dict[str, Any],
    summary: Optional[Dict[str, Any]] = None,
    description: str = "",
    status: str = "draft",
    user=None,
) -> MetadataDefinition:
    """Create a new metadata version, automatically incrementing the version counter."""

    version = MetadataDefinition.next_version(
        key=key,
        kind=kind,
        layer=layer,
        scope_type=scope.scope_type,
        company_group=scope.company_group,
        company=scope.company,
    )
    instance = MetadataDefinition.objects.create(
        key=key,
        kind=kind,
        label=definition.get("label") or definition.get("name") or key,
        layer=layer,
        scope_type=scope.scope_type,
        company_group=scope.company_group,
        company=scope.company,
        version=version,
        status=status,
        is_active=status == "active",
        definition=definition,
        summary=summary or {},
        description=description,
        created_by=user,
        updated_by=user,
    )
    return instance


def get_active_metadata(*, key: str, kind: str, scope: MetadataScope) -> Optional[MetadataDefinition]:
    """Fetch the active metadata definition for a given scope."""
    return (
        MetadataDefinition.objects.filter(
            key=key,
            kind=kind,
            scope_type=scope.scope_type,
            company_group=scope.company_group,
            company=scope.company,
            status="active",
            is_active=True,
        )
        .order_by("-version")
        .first()
    )


def resolve_metadata(
    *,
    key: str,
    kind: str,
    company: Optional[Company] = None,
    company_group: Optional[CompanyGroup] = None,
) -> Dict[str, Any]:
    if company and not company_group:
        company_group = company.company_group

    layers = []

    core_layer = _latest_definition(
        key=key,
        kind=kind,
        scope_type="GLOBAL",
    )
    if core_layer:
        layers.append(core_layer)

    if company_group and company_group.industry_pack_type:
        pack_layer = _latest_definition(
            key=key,
            kind=kind,
            scope_type="GROUP",
            filters={"summary__industry_pack": company_group.industry_pack_type},
        )
        if pack_layer:
            layers.append(pack_layer)

    if company_group:
        group_layer = _latest_definition(
            key=key,
            kind=kind,
            scope_type="GROUP",
            company_group=company_group,
        )
        if group_layer:
            layers.append(group_layer)

    if company:
        company_layer = _latest_definition(
            key=key,
            kind=kind,
            scope_type="COMPANY",
            company=company,
        )
        if company_layer:
            layers.append(company_layer)

    merged: Dict[str, Any] = {}
    sources: Dict[str, int] = {}
    for definition in layers:
        merged = _deep_merge(merged, definition.definition or {})
        sources[definition.scope_type] = definition.version

    return {
        "key": key,
        "kind": kind,
        "definition": merged,
        "sources": sources,
    }


def _latest_definition(
    *,
    key: str,
    kind: str,
    scope_type: str,
    company_group: Optional[CompanyGroup] = None,
    company: Optional[Company] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> Optional[MetadataDefinition]:
    qs = MetadataDefinition.objects.filter(
        key=key,
        kind=kind,
        scope_type=scope_type,
        status="active",
        is_active=True,
    )
    if company_group is not None:
        qs = qs.filter(company_group=company_group)
    if company is not None:
        qs = qs.filter(company=company)
    if filters:
        qs = qs.filter(**filters)
    return qs.order_by("-version").first()


def _deep_merge(base: Any, incoming: Any) -> Dict[str, Any]:
    if not isinstance(base, dict):
        base = {}
    if not isinstance(incoming, dict):
        return copy.deepcopy(incoming)

    merged = copy.deepcopy(base)
    for key, value in incoming.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged
