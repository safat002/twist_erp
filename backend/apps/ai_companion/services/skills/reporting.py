from __future__ import annotations

from decimal import Decimal
from typing import List, Union

from apps.analytics.models import CashflowSnapshot, SalesPerformanceSnapshot
from .base import (
    BaseSkill,
    ProactiveSuggestionPayload,
    SkillAction,
    SkillContext,
    SkillResponse,
)
from ..memory import MemoryRecord

KEYWORDS = {"report", "kpi", "dashboard", "trend", "performance", "forecast"}


class ReportingSkill(BaseSkill):
    name = "reporting"
    description = "Generates insights from analytics snapshots and assists with reporting tasks."
    priority = 20

    def _has_access(self, context: SkillContext) -> bool:
        if getattr(context.user, "is_system_admin", False):
            return True
        roles = {role.lower() for role in context.short_term.get("user_roles", [])}
        if not roles:
            return False
        keywords = ("analytics", "dashboard", "finance", "executive", "admin")
        return any(any(keyword in role for keyword in keywords) for role in roles)

    def is_authorised(self, context: SkillContext) -> bool:
        return self._has_access(context)

    def can_handle(self, message: str, context: SkillContext) -> bool:
        if context.module in {"analytics", "dashboard", "reporting"}:
            return True
        lowered = message.lower()
        return any(keyword in lowered for keyword in KEYWORDS)

    def _format_currency(self, value: Decimal) -> str:
        return f"{value:,.0f}"

    def _extract_growth(self, data_point: Union[dict, float, int, Decimal]) -> float | None:
        if isinstance(data_point, dict):
            raw = data_point.get("growth")
        else:
            raw = data_point
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, Decimal):
            return float(raw)
        return None

    def handle(self, message: str, context: SkillContext) -> SkillResponse:
        if not self._has_access(context):
            return SkillResponse(
                message="I can only surface analytics for finance or dashboard roles. Please ask an analytics owner to share the report.",
                intent="reporting.permission_denied",
                confidence=0.05,
            )
        if context.company is None:
            return SkillResponse(
                message="Select a company and I can break down its KPIs and dashboards for you.",
                intent="reporting.no_company",
                confidence=0.2,
            )

        sales = (
            SalesPerformanceSnapshot.objects.filter(company_id=context.company.id)
            .order_by("-snapshot_date")
            .first()
        )
        cashflow = (
            CashflowSnapshot.objects.filter(company_id=context.company.id)
            .order_by("-snapshot_date")
            .first()
        )

        if not sales and not cashflow:
            return SkillResponse(
                message="I could not find any analytics snapshots yet. Once the data warehouse runs, I'll have trends and KPIs ready for you.",
                intent="reporting.no_data",
                confidence=0.2,
            )

        parts: List[str] = []
        actions: List[SkillAction] = []
        proactive: List[ProactiveSuggestionPayload] = []
        memory_updates: List[MemoryRecord] = []

        if sales:
            if getattr(sales, "timeframe_start", None) and getattr(sales, "timeframe_end", None):
                period_label = f"{sales.timeframe_start:%d %b} -> {sales.timeframe_end:%d %b}"
            else:
                period_label = sales.period or "latest period"
            parts.append(
                f"Revenue for the last period ({period_label}) is **{self._format_currency(sales.total_revenue)}** across {sales.total_orders} orders."
            )
            if sales.sales_trend:
                growth = self._extract_growth(sales.sales_trend[-1])
                if growth is not None:
                    direction = "up" if growth >= 0 else "down"
                    parts.append(f"Trend shows {abs(growth):.1f}% {direction} week-over-week.")
                    if growth < -5:
                        proactive.append(
                            ProactiveSuggestionPayload(
                                title="Revenue is trending down",
                                body=f"Sales dropped {growth:.1f}% last period. Consider running a pipeline health report?",
                                metadata={"growth": growth, "period": sales.period},
                            )
                        )
            actions.append(
                SkillAction(
                    label="Build revenue report",
                    action="navigate",
                    payload={"path": "/analytics/revenue"},
                )
            )
            memory_updates.append(
                MemoryRecord(
                    key="last_sales_snapshot",
                    value={
                        "snapshot_date": str(sales.snapshot_date),
                        "period": sales.period,
                        "total_revenue": float(sales.total_revenue),
                    },
                    scope="company",
                    user=context.user,
                    company=context.company,
                )
            )

        if cashflow:
            parts.append(
                f"Net cash position stands at **{self._format_currency(cashflow.net_cash)}** with receivables {self._format_currency(cashflow.receivables_balance)} and payables {self._format_currency(cashflow.payables_balance)}."
            )
            if cashflow.net_cash < 0:
                proactive.append(
                    ProactiveSuggestionPayload(
                        title="Negative cashflow detected",
                        body="Cash outflows exceeded inflows this period. Shall I draft a cash preservation action list?",
                        metadata={"net_cash": float(cashflow.net_cash)},
                    )
                )
            actions.append(
                SkillAction(
                    label="Open cash dashboard",
                    action="navigate",
                    payload={"path": "/analytics/cashflow"},
                )
            )

        response_message = " ".join(parts)
        sources = []
        if sales:
            sources.append(f"sales_snapshot:{sales.snapshot_date}")
        if cashflow:
            sources.append(f"cashflow_snapshot:{cashflow.snapshot_date}")

        return SkillResponse(
            message=response_message,
            intent="reporting.summary",
            confidence=0.7,
            sources=sources,
            actions=actions,
            proactive_suggestions=proactive,
            memory_updates=memory_updates,
        )
