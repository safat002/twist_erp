from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Iterable, List, Optional, Sequence

from django.contrib.auth import get_user_model
from django.db.models import F, Q, Sum
from django.utils import timezone

from apps.budgeting.models import Budget
from apps.companies.models import Company
from apps.finance.models import Invoice
from apps.inventory.models import StockLevel
from apps.users.models import UserCompanyRole

from ..models import AIProactiveSuggestion
from apps.notifications.models import Notification, NotificationSeverity

logger = logging.getLogger(__name__)
User = get_user_model()


class AlertEngine:
    """
    Lightweight rule engine that scans operational data and emits proactive AI suggestions.
    """

    RULE_OVERDUE_AR = "finance.overdue_receivables"
    RULE_LOW_STOCK = "inventory.low_stock"
    RULE_BUDGET_THRESHOLD = "budget.threshold"

    def run(self, company: Optional[Company] = None) -> int:
        companies: Iterable[Company]
        if company:
            companies = [company]
        else:
            companies = Company.objects.filter(is_active=True)

        total = 0
        for tenant in companies:
            total += self._check_overdue_receivables(tenant)
            total += self._check_low_stock(tenant)
            total += self._check_budget_thresholds(tenant)
        return total

    # ------------------------------------------------------------------ #
    # Rules                                                              #
    # ------------------------------------------------------------------ #
    def _check_overdue_receivables(self, company: Company) -> int:
        today = timezone.now().date()
        invoices = (
            Invoice.objects.filter(
                company=company,
                invoice_type="AR",
                status__in=["POSTED", "PARTIAL"],
                due_date__lt=today,
            )
            .annotate(outstanding=F("total_amount") - F("paid_amount"))
            .filter(outstanding__gt=0)
        )
        if not invoices.exists():
            return 0

        records = list(
            invoices.values("invoice_number", "due_date", "outstanding")[:50]
        )
        count = len(records)
        total_outstanding = sum((entry["outstanding"] or Decimal("0.00")) for entry in records)
        oldest_days = max((today - entry["due_date"]).days for entry in records if entry["due_date"])

        severity = AIProactiveSuggestion.AlertSeverity.WARNING
        if oldest_days >= 14 or total_outstanding >= Decimal("50000"):
            severity = AIProactiveSuggestion.AlertSeverity.CRITICAL

        top_invoices = ", ".join(entry["invoice_number"] for entry in records[:5])
        body = (
            f"{count} receivable invoice(s) are overdue for {oldest_days} day(s). "
            f"Outstanding balance: {self._format_currency(total_outstanding, company.currency_code)}."
        )
        if top_invoices:
            body += f" Examples: {top_invoices}."

        metadata = {
            "rule_code": self.RULE_OVERDUE_AR,
            "count": count,
            "amount": str(total_outstanding),
            "oldest_days": oldest_days,
            "invoice_numbers": [entry["invoice_number"] for entry in records],
        }

        recipients = self._resolve_recipients(
            company,
            preferred_roles=["Finance Manager", "Accountant", "Controller"],
            permission_codes=["finance.view_reports", "finance.manage_invoices"],
        )
        return self._emit_alerts(
            company=company,
            recipients=recipients,
            rule_code=self.RULE_OVERDUE_AR,
            title="Overdue receivables detected",
            body=body,
            severity=severity,
            metadata=metadata,
            alert_type="finance",
        )

    def _check_low_stock(self, company: Company) -> int:
        low_stock_rows = (
            StockLevel.objects.filter(company=company, product__reorder_level__gt=0)
            .values(
                "product_id",
                "product__code",
                "product__name",
                "product__reorder_level",
                "product__reorder_quantity",
            )
            .annotate(total_qty=Sum("quantity"))
        )
        at_risk: List[dict] = []
        for row in low_stock_rows:
            reorder_level = row["product__reorder_level"] or Decimal("0")
            total_qty = row["total_qty"] or Decimal("0")
            if total_qty < reorder_level:
                at_risk.append(
                    {
                        "code": row["product__code"],
                        "name": row["product__name"],
                        "quantity": str(total_qty),
                        "reorder_level": str(reorder_level),
                        "reorder_quantity": str(row.get("product__reorder_quantity") or 0),
                    }
                )

        if not at_risk:
            return 0

        severity = AIProactiveSuggestion.AlertSeverity.WARNING
        if any(Decimal(item["quantity"]) <= 0 for item in at_risk):
            severity = AIProactiveSuggestion.AlertSeverity.CRITICAL

        top_items = ", ".join(
            f"{item['code']} ({item['quantity']})" for item in at_risk[:5]
        )
        body = f"{len(at_risk)} product(s) are below reorder level. {top_items}"
        metadata = {
            "rule_code": self.RULE_LOW_STOCK,
            "items": at_risk[:10],
        }

        recipients = self._resolve_recipients(
            company,
            preferred_roles=["Inventory Manager", "Warehouse Manager"],
            permission_codes=["inventory.view_stock"],
        )
        return self._emit_alerts(
            company=company,
            recipients=recipients,
            rule_code=self.RULE_LOW_STOCK,
            title="Inventory levels require attention",
            body=body,
            severity=severity,
            metadata=metadata,
            alert_type="inventory",
        )

    def _check_budget_thresholds(self, company: Company) -> int:
        budgets = Budget.objects.filter(company=company, status=Budget.STATUS_ACTIVE)
        breaches: List[dict] = []
        for budget in budgets:
            if budget.amount <= 0:
                continue
            utilization = (budget.consumed / budget.amount) * Decimal("100")
            threshold = Decimal(str(budget.threshold_percent or 90))
            if utilization < threshold:
                continue
            breaches.append(
                {
                    "cost_center": budget.cost_center.code,
                    "fiscal_year": budget.fiscal_year,
                    "utilization_pct": float(round(utilization, 2)),
                    "threshold_pct": float(threshold),
                }
            )

        if not breaches:
            return 0

        severity = AIProactiveSuggestion.AlertSeverity.WARNING
        if any(item["utilization_pct"] >= 100 for item in breaches):
            severity = AIProactiveSuggestion.AlertSeverity.CRITICAL

        headline = ", ".join(
            f"{item['cost_center']} ({item['utilization_pct']}%)" for item in breaches[:5]
        )
        body = (
            f"{len(breaches)} cost center(s) have crossed their budget threshold. "
            f"Top alerts: {headline}."
        )
        metadata = {
            "rule_code": self.RULE_BUDGET_THRESHOLD,
            "breaches": breaches[:10],
        }

        recipients = self._resolve_recipients(
            company,
            preferred_roles=["Finance Manager", "Budget Owner"],
            permission_codes=["budgeting.view_budgets"],
        )
        return self._emit_alerts(
            company=company,
            recipients=recipients,
            rule_code=self.RULE_BUDGET_THRESHOLD,
            title="Budget threshold exceeded",
            body=body,
            severity=severity,
            metadata=metadata,
            alert_type="budget",
        )

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #
    def _emit_alerts(
        self,
        *,
        company: Company,
        recipients: Sequence,
        rule_code: str,
        title: str,
        body: str,
        severity: str,
        metadata: dict,
        alert_type: str,
    ) -> int:
        if not recipients:
            logger.debug("AlertEngine %s skipped: no recipients in %s", rule_code, company)
            return 0

        created = 0
        for user in recipients:
            if not user or not user.is_active:
                continue
            existing = AIProactiveSuggestion.objects.filter(
                user=user,
                company=company,
                metadata__rule_code=rule_code,
                status="pending",
            ).first()
            if existing:
                existing.title = title
                existing.body = body
                existing.severity = severity
                existing.alert_type = alert_type
                existing.metadata = metadata
                existing.save(update_fields=["title", "body", "severity", "alert_type", "metadata", "updated_at"])
                # Mirror to Notification Center (upsert latest unread notification)
                notif_sev = NotificationSeverity.CRITICAL if severity == AIProactiveSuggestion.AlertSeverity.CRITICAL else (
                    NotificationSeverity.WARNING if severity == AIProactiveSuggestion.AlertSeverity.WARNING else NotificationSeverity.INFO
                )
                Notification.objects.create(
                    company=company,
                    company_group=company.company_group,
                    created_by=None,
                    user=user,
                    title=title,
                    body=body,
                    severity=notif_sev,
                    group_key=rule_code,
                    entity_type="AI_SUGGESTION",
                    entity_id=str(existing.id),
                )
                continue

            suggestion = AIProactiveSuggestion.objects.create(
                user=user,
                company=company,
                title=title,
                body=body,
                metadata=metadata,
                alert_type=alert_type,
                severity=severity,
                source_skill="alert_engine",
            )
            notif_sev = NotificationSeverity.CRITICAL if severity == AIProactiveSuggestion.AlertSeverity.CRITICAL else (
                NotificationSeverity.WARNING if severity == AIProactiveSuggestion.AlertSeverity.WARNING else NotificationSeverity.INFO
            )
            Notification.objects.create(
                company=company,
                company_group=company.company_group,
                created_by=None,
                user=user,
                title=title,
                body=body,
                severity=notif_sev,
                group_key=rule_code,
                entity_type="AI_SUGGESTION",
                entity_id=str(suggestion.id),
            )
            created += 1
        return created

    def _resolve_recipients(
        self,
        company: Company,
        preferred_roles: Optional[Sequence[str]] = None,
        permission_codes: Optional[Sequence[str]] = None,
    ) -> List:
        qs = (
            UserCompanyRole.objects.filter(company=company, is_active=True)
            .select_related("user", "role")
            .prefetch_related("role__permissions")
        )

        if preferred_roles:
            role_filter = Q()
            for role_name in preferred_roles:
                role_filter |= Q(role__name__iexact=role_name) | Q(role__name__icontains=role_name)
            qs = qs.filter(role_filter)

        if permission_codes:
            qs = qs.filter(role__permissions__code__in=permission_codes)

        users: List = []
        seen: set = set()
        for membership in qs:
            user = membership.user
            if not user or not user.is_active:
                continue
            if permission_codes:
                codes = set(membership.role.permissions.values_list("code", flat=True))
                if not codes.intersection(set(permission_codes)):
                    continue
            if user.id in seen:
                continue
            seen.add(user.id)
            users.append(user)

        if not users:
            fallback = User.objects.filter(is_system_admin=True, is_active=True)
            users.extend(list(fallback))
        return users

    @staticmethod
    def _format_currency(amount: Decimal, currency: Optional[str]) -> str:
        curr = currency or "BDT"
        return f"{curr} {round(amount, 2):,.2f}"
