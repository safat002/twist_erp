from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from django.db.models import QuerySet

from backend.modules.report_builder import (
    apply_filters,
    apply_sorting,
    evaluate_calculations,
    prepare_dataset,
)
from apps.report_builder.models import ReportDefinition
from .registry import DatasetRuntime, resolve_dataset


@dataclass
class ReportExecutionResult:
    rows: list[Dict[str, Any]]
    fields: list[Dict[str, Any]]
    total_available: int
    limit: Optional[int]
    dataset: DatasetRuntime


class ReportQueryEngine:
    """
    Executes report definitions against metadata-backed datasets.
    """

    def __init__(self, *, report: ReportDefinition, company, user):
        if not company:
            raise ValueError("Company context is required to execute a report.")
        self.report = report
        self.company = company
        self.user = user
        self.definition = report.definition or {}

    def run_preview(self, limit: Optional[int] = None) -> ReportExecutionResult:
        dataset = resolve_dataset(
            self.definition.get("data_source") or {},
            company=self.company,
            user=self.user,
        )

        queryset = self._apply_transformations(dataset.queryset, dataset.field_map)
        total_available = queryset.count()

        limit_value = self._determine_limit(limit, dataset)
        fields_config = self.definition.get("fields") or []
        rows, field_meta = prepare_dataset(
            queryset,
            fields_config,
            dataset.field_map,
            limit=limit_value,
        )

        calculations = self.definition.get("calculations") or []
        rows = evaluate_calculations(rows, calculations)

        return ReportExecutionResult(
            rows=rows,
            fields=field_meta,
            total_available=total_available,
            limit=limit_value,
            dataset=dataset,
        )

    def _apply_transformations(self, queryset: QuerySet, field_map: Dict[str, str]) -> QuerySet:
        filters = self.definition.get("filters")
        sorts = self.definition.get("sorts")

        queryset = apply_filters(queryset, filters, field_map)
        queryset = apply_sorting(queryset, sorts, field_map)
        return queryset

    def _determine_limit(self, limit: Optional[int], dataset: DatasetRuntime) -> Optional[int]:
        definition_limit = self.definition.get("limit")
        candidates = [value for value in [limit, definition_limit, dataset.default_limit] if value]
        if not candidates:
            return None
        return min(int(value) for value in candidates if isinstance(value, (int, float)))
