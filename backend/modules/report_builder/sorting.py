from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping

from django.db.models import QuerySet


def apply_sorting(
    queryset: QuerySet,
    sorts: Iterable[Dict[str, Any]] | None,
    field_map: Mapping[str, str],
) -> QuerySet:
    """Apply sort instructions to a queryset based on the report definition."""
    if not sorts:
        return queryset

    ordering = []
    for spec in sorts:
        field_key = spec.get("field")
        if not field_key:
            continue
        field_path = field_map.get(field_key) or field_key
        direction = (spec.get("direction") or "asc").lower()
        if direction == "desc":
            field_path = f"-{field_path}"
        ordering.append(field_path)

    if ordering:
        queryset = queryset.order_by(*ordering)
    return queryset
