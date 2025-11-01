from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Tuple

from django.db.models import QuerySet


def prepare_dataset(
    queryset: QuerySet,
    fields: Iterable[Dict[str, Any]] | None,
    field_map: Mapping[str, str],
    *,
    limit: int | None = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Materialize queryset rows according to the requested field specs.

    Returns a tuple of (rows, field_metadata) where field_metadata includes
    the alias, label, and source path for each field in the output.
    """
    if limit:
        queryset = queryset[:limit]

    if not fields:
        rows = list(queryset.values())
        field_meta = [{"key": key, "label": key, "path": key} for key in rows[0].keys()] if rows else []
        return rows, field_meta

    aliases: List[Tuple[str, str, Dict[str, Any]]] = []
    value_fields: List[str] = []

    for field in fields:
        alias = field.get("alias") or field.get("id") or field.get("key") or field.get("field")
        if not alias:
            continue
        path = _resolve_field_path(field, field_map)
        if not path:
            continue
        value_fields.append(path)
        aliases.append((alias, path, field))

    if not aliases:
        rows = list(queryset.values())
        field_meta = [{"key": key, "label": key, "path": key} for key in rows[0].keys()] if rows else []
        return rows, field_meta

    # Deduplicate selected fields while preserving order for the query.
    deduped_fields = list(dict.fromkeys(value_fields))
    raw_rows = list(queryset.values(*deduped_fields))

    prepared_rows: List[Dict[str, Any]] = []
    for record in raw_rows:
        prepared_rows.append({alias: record.get(path) for alias, path, _ in aliases})

    field_meta = [
        {
            "key": alias,
            "label": field.get("label") or alias.replace("_", " ").title(),
            "path": path,
            "source": field.get("source") or {},
        }
        for alias, path, field in aliases
    ]
    return prepared_rows, field_meta


def _resolve_field_path(field: Dict[str, Any], field_map: Mapping[str, str]) -> str | None:
    if path := field.get("path"):
        return path
    source = field.get("source") or {}
    if source_path := source.get("path"):
        return source_path
    field_key = field.get("field") or field.get("id") or field.get("key")
    if not field_key:
        return None
    return field_map.get(field_key) or field_key
