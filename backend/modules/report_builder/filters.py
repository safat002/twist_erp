from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional

from django.db.models import Q, QuerySet

LOGIC_AND = "AND"
LOGIC_OR = "OR"


def apply_filters(
    queryset: QuerySet,
    filters: Optional[Iterable[Dict[str, Any]]],
    field_map: Mapping[str, str],
) -> QuerySet:
    """
    Apply a sequence of filter specifications to a queryset.

    Each filter spec supports:
        - field: logical field identifier from the report definition.
        - operator: equals|not_equals|contains|icontains|gte|lte|gt|lt|between|in|is_null.
        - value: scalar or list depending on operator.
        - logic: AND/OR to combine with the accumulated predicate (defaults to AND).
    """
    if not filters:
        return queryset

    accumulated: Optional[Q] = None

    for spec in filters:
        q_obj = _compile_filter(spec, field_map)
        if q_obj is None:
            continue

        logic = (spec.get("logic") or LOGIC_AND).upper()
        if accumulated is None:
            accumulated = q_obj
        elif logic == LOGIC_OR:
            accumulated = accumulated | q_obj
        else:
            accumulated = accumulated & q_obj

    if accumulated is not None:
        queryset = queryset.filter(accumulated)

    return queryset


def _compile_filter(spec: Dict[str, Any], field_map: Mapping[str, str]) -> Optional[Q]:
    field_key = spec.get("field")
    if not field_key:
        return None

    field_path = field_map.get(field_key) or field_key
    operator = (spec.get("operator") or "equals").lower()

    if operator == "equals":
        return Q(**{field_path: spec.get("value")})

    if operator == "not_equals":
        return ~Q(**{field_path: spec.get("value")})

    if operator == "contains":
        return Q(**{f"{field_path}__contains": spec.get("value")})

    if operator == "icontains":
        return Q(**{f"{field_path}__icontains": spec.get("value")})

    if operator == "gte":
        return Q(**{f"{field_path}__gte": spec.get("value")})

    if operator == "lte":
        return Q(**{f"{field_path}__lte": spec.get("value")})

    if operator == "gt":
        return Q(**{f"{field_path}__gt": spec.get("value")})

    if operator == "lt":
        return Q(**{f"{field_path}__lt": spec.get("value")})

    if operator == "between":
        values = spec.get("value") or []
        if len(values) == 2:
            return Q(**{f"{field_path}__gte": values[0], f"{field_path}__lte": values[1]})
        return None

    if operator == "in":
        values = spec.get("value")
        if isinstance(values, (list, tuple, set)):
            return Q(**{f"{field_path}__in": list(values)})
        return None

    if operator == "is_null":
        return Q(**{f"{field_path}__isnull": bool(spec.get("value", True))})

    # Unsupported operator
    return None
