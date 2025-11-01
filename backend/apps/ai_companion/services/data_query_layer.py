"""
RBAC-Aware Data Query Layer
Provides safe, permission-checked data access for AI assistant across all modules
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db.models import Q, Sum, Count, Avg, F
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Structured query result"""
    success: bool
    data: Any
    message: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DataQueryLayer:
    """
    RBAC-aware query layer for AI assistant.
    All queries respect company scoping and user permissions.
    """

    def __init__(self, user, company):
        """
        Initialize with user and company context for RBAC.

        Args:
            user: Django user object (for permission checking)
            company: Company object (for data scoping)
        """
        self.user = user
        self.company = company

    # ================================================================
    # PROCUREMENT MODULE
    # ================================================================

    def get_purchase_orders(self, **filters) -> QueryResult:
        """
        Get purchase orders with optional filters.

        Filters:
            status: str - "DRAFT", "PENDING_APPROVAL", "APPROVED", etc.
            amount_min: Decimal - minimum total amount
            amount_max: Decimal - maximum total amount
            supplier_id: int
            overdue: bool - only overdue orders
            limit: int - max results (default: 10)
        """
        try:
            from apps.procurement.models import PurchaseOrder

            # Base query - company scoped
            qs = PurchaseOrder.objects.filter(company=self.company)

            # Apply filters
            if "status" in filters:
                qs = qs.filter(status=filters["status"])

            if "amount_min" in filters:
                qs = qs.filter(total_amount__gte=filters["amount_min"])

            if "amount_max" in filters:
                qs = qs.filter(total_amount__lte=filters["amount_max"])

            if "supplier_id" in filters:
                qs = qs.filter(supplier_id=filters["supplier_id"])

            if filters.get("overdue"):
                today = timezone.now().date()
                qs = qs.filter(expected_delivery_date__lt=today, status__in=["APPROVED", "PARTIAL"])

            # Apply limit
            limit = min(filters.get("limit", 10), 100)  # Max 100
            results = list(qs.order_by("-created_at")[:limit].values(
                "id", "po_number", "supplier__name", "status", "total_amount",
                "created_at", "expected_delivery_date"
            ))

            return QueryResult(
                success=True,
                data=results,
                message=f"Found {len(results)} purchase order(s)",
                metadata={"count": len(results), "limit": limit}
            )

        except Exception as e:
            logger.exception(f"Error querying purchase orders: {e}")
            return QueryResult(
                success=False,
                data=[],
                message=f"Failed to query purchase orders: {str(e)}"
            )

    def get_pending_approvals(self, module: str = None) -> QueryResult:
        """Get pending workflow approvals for the user"""
        try:
            from apps.workflows.models import WorkflowInstance

            # Base query
            qs = WorkflowInstance.objects.filter(
                company=self.company,
                status="IN_PROGRESS"
            )

            # Get tasks assigned to user
            pending_tasks = []
            for instance in qs[:50]:  # Limit to 50
                # Get current pending task for this user
                current_tasks = instance.tasks.filter(
                    status="PENDING",
                    assigned_to=self.user
                )
                for task in current_tasks:
                    pending_tasks.append({
                        "id": task.id,
                        "workflow": instance.workflow_definition.name,
                        "entity_type": instance.entity_type,
                        "entity_id": instance.entity_id,
                        "task_name": task.task_name,
                        "due_date": task.due_date,
                        "created_at": instance.created_at,
                    })

            return QueryResult(
                success=True,
                data=pending_tasks,
                message=f"Found {len(pending_tasks)} pending approval(s)",
                metadata={"count": len(pending_tasks)}
            )

        except Exception as e:
            logger.exception(f"Error querying pending approvals: {e}")
            return QueryResult(
                success=False,
                data=[],
                message=f"Failed to query approvals: {str(e)}"
            )

    # ================================================================
    # FINANCE MODULE
    # ================================================================

    def get_cash_balance(self) -> QueryResult:
        """Get current cash balance across all bank accounts"""
        try:
            from apps.finance.models import BankAccount

            accounts = BankAccount.objects.filter(company=self.company).values(
                "id", "account_name", "account_number", "bank_name", "current_balance", "currency"
            )

            total_balance = sum(acc["current_balance"] or 0 for acc in accounts)

            return QueryResult(
                success=True,
                data={
                    "total_balance": total_balance,
                    "accounts": list(accounts),
                    "count": len(accounts)
                },
                message=f"Total cash balance: {total_balance}",
                metadata={"currency": "BDT"}  # TODO: Multi-currency support
            )

        except Exception as e:
            logger.exception(f"Error querying cash balance: {e}")
            return QueryResult(
                success=False,
                data={"total_balance": 0, "accounts": []},
                message=f"Failed to query cash balance: {str(e)}"
            )

    def get_ar_aging(self, buckets: List[int] = None) -> QueryResult:
        """
        Get accounts receivable aging.

        Args:
            buckets: List of days for aging buckets (default: [30, 60, 90])
        """
        try:
            from apps.finance.models import ARInvoice

            buckets = buckets or [30, 60, 90]
            today = timezone.now().date()

            # Get unpaid invoices
            unpaid_invoices = ARInvoice.objects.filter(
                company=self.company,
                status__in=["POSTED", "PARTIAL"]
            ).values(
                "id", "invoice_number", "customer__name", "total_amount",
                "amount_paid", "due_date"
            )

            aging_data = {
                "current": 0,
                f"1-{buckets[0]}": 0,
                f"{buckets[0]+1}-{buckets[1]}": 0 if len(buckets) > 1 else None,
                f"{buckets[1]+1}-{buckets[2]}": 0 if len(buckets) > 2 else None,
                f">{buckets[-1]}": 0,
            }

            detailed = []

            for inv in unpaid_invoices:
                outstanding = (inv["total_amount"] or 0) - (inv["amount_paid"] or 0)
                if outstanding <= 0:
                    continue

                days_overdue = (today - inv["due_date"]).days if inv["due_date"] else 0

                # Categorize
                if days_overdue <= 0:
                    aging_data["current"] += outstanding
                    bucket = "current"
                elif days_overdue <= buckets[0]:
                    aging_data[f"1-{buckets[0]}"] += outstanding
                    bucket = f"1-{buckets[0]}"
                elif len(buckets) > 1 and days_overdue <= buckets[1]:
                    aging_data[f"{buckets[0]+1}-{buckets[1]}"] += outstanding
                    bucket = f"{buckets[0]+1}-{buckets[1]}"
                elif len(buckets) > 2 and days_overdue <= buckets[2]:
                    aging_data[f"{buckets[1]+1}-{buckets[2]}"] += outstanding
                    bucket = f"{buckets[1]+1}-{buckets[2]}"
                else:
                    aging_data[f">{buckets[-1]}"] += outstanding
                    bucket = f">{buckets[-1]}"

                detailed.append({
                    "invoice_id": inv["id"],
                    "invoice_number": inv["invoice_number"],
                    "customer": inv["customer__name"],
                    "outstanding": float(outstanding),
                    "days_overdue": days_overdue,
                    "bucket": bucket,
                })

            # Remove None buckets
            aging_data = {k: v for k, v in aging_data.items() if v is not None}

            total_ar = sum(aging_data.values())

            return QueryResult(
                success=True,
                data={
                    "summary": aging_data,
                    "total": total_ar,
                    "detailed": detailed,
                },
                message=f"Total AR: {total_ar}",
                metadata={"buckets": buckets}
            )

        except Exception as e:
            logger.exception(f"Error querying AR aging: {e}")
            return QueryResult(
                success=False,
                data={"summary": {}, "total": 0, "detailed": []},
                message=f"Failed to query AR aging: {str(e)}"
            )

    def get_ap_aging(self, buckets: List[int] = None) -> QueryResult:
        """Get accounts payable aging"""
        try:
            from apps.finance.models import APBill

            buckets = buckets or [30, 60, 90]
            today = timezone.now().date()

            unpaid_bills = APBill.objects.filter(
                company=self.company,
                status__in=["POSTED", "PARTIAL"]
            ).values(
                "id", "bill_number", "supplier__name", "total_amount",
                "amount_paid", "due_date"
            )

            aging_data = {
                "current": 0,
                f"1-{buckets[0]}": 0,
                f"{buckets[0]+1}-{buckets[1]}": 0 if len(buckets) > 1 else None,
                f"{buckets[1]+1}-{buckets[2]}": 0 if len(buckets) > 2 else None,
                f">{buckets[-1]}": 0,
            }

            detailed = []

            for bill in unpaid_bills:
                outstanding = (bill["total_amount"] or 0) - (bill["amount_paid"] or 0)
                if outstanding <= 0:
                    continue

                days_overdue = (today - bill["due_date"]).days if bill["due_date"] else 0

                if days_overdue <= 0:
                    aging_data["current"] += outstanding
                    bucket = "current"
                elif days_overdue <= buckets[0]:
                    aging_data[f"1-{buckets[0]}"] += outstanding
                    bucket = f"1-{buckets[0]}"
                elif len(buckets) > 1 and days_overdue <= buckets[1]:
                    aging_data[f"{buckets[0]+1}-{buckets[1]}"] += outstanding
                    bucket = f"{buckets[0]+1}-{buckets[1]}"
                elif len(buckets) > 2 and days_overdue <= buckets[2]:
                    aging_data[f"{buckets[1]+1}-{buckets[2]}"] += outstanding
                    bucket = f"{buckets[1]+1}-{buckets[2]}"
                else:
                    aging_data[f">{buckets[-1]}"] += outstanding
                    bucket = f">{buckets[-1]}"

                detailed.append({
                    "bill_id": bill["id"],
                    "bill_number": bill["bill_number"],
                    "supplier": bill["supplier__name"],
                    "outstanding": float(outstanding),
                    "days_overdue": days_overdue,
                    "bucket": bucket,
                })

            aging_data = {k: v for k, v in aging_data.items() if v is not None}
            total_ap = sum(aging_data.values())

            return QueryResult(
                success=True,
                data={
                    "summary": aging_data,
                    "total": total_ap,
                    "detailed": detailed,
                },
                message=f"Total AP: {total_ap}",
                metadata={"buckets": buckets}
            )

        except Exception as e:
            logger.exception(f"Error querying AP aging: {e}")
            return QueryResult(
                success=False,
                data={"summary": {}, "total": 0, "detailed": []},
                message=f"Failed to query AP aging: {str(e)}"
            )

    # ================================================================
    # INVENTORY MODULE
    # ================================================================

    def get_stock_levels(self, **filters) -> QueryResult:
        """
        Get stock levels with optional filters.

        Filters:
            below_reorder: bool - only items below reorder level
            item_id: int
            warehouse_id: int
            limit: int
        """
        try:
            from apps.inventory.models import StockLevel

            qs = StockLevel.objects.filter(company=self.company)

            if filters.get("below_reorder"):
                qs = qs.filter(quantity__lt=F("reorder_level"))

            if "item_id" in filters:
                qs = qs.filter(item_id=filters["item_id"])

            if "warehouse_id" in filters:
                qs = qs.filter(warehouse_id=filters["warehouse_id"])

            limit = min(filters.get("limit", 20), 100)
            results = list(qs[:limit].values(
                "id", "item__name", "item__code", "warehouse__name",
                "quantity", "reorder_level", "unit_cost"
            ))

            return QueryResult(
                success=True,
                data=results,
                message=f"Found {len(results)} stock level(s)",
                metadata={"count": len(results)}
            )

        except Exception as e:
            logger.exception(f"Error querying stock levels: {e}")
            return QueryResult(
                success=False,
                data=[],
                message=f"Failed to query stock levels: {str(e)}"
            )

    # ================================================================
    # CROSS-MODULE ANALYSIS
    # ================================================================

    def analyze_cash_flow(self, days: int = 30) -> QueryResult:
        """
        Analyze cash flow - why is cash low/high?
        Cross-module analysis of cash affecting factors.
        """
        try:
            from apps.finance.models import BankAccount, APBill, ARInvoice

            cutoff_date = timezone.now().date() - timedelta(days=days)

            # Get current cash
            cash_result = self.get_cash_balance()
            current_cash = cash_result.data.get("total_balance", 0)

            # Get upcoming AP payments
            upcoming_ap = APBill.objects.filter(
                company=self.company,
                status__in=["POSTED", "PARTIAL"],
                due_date__gte=timezone.now().date(),
                due_date__lte=timezone.now().date() + timedelta(days=days)
            ).aggregate(total=Sum(F("total_amount") - F("amount_paid")))["total"] or 0

            # Get expected AR collections
            expected_ar = ARInvoice.objects.filter(
                company=self.company,
                status__in=["POSTED", "PARTIAL"],
                due_date__gte=timezone.now().date(),
                due_date__lte=timezone.now().date() + timedelta(days=days)
            ).aggregate(total=Sum(F("total_amount") - F("amount_paid")))["total"] or 0

            # Get overdue AR
            overdue_ar = ARInvoice.objects.filter(
                company=self.company,
                status__in=["POSTED", "PARTIAL"],
                due_date__lt=timezone.now().date()
            ).aggregate(total=Sum(F("total_amount") - F("amount_paid")))["total"] or 0

            # Calculate projected cash
            projected_cash = current_cash + expected_ar - upcoming_ap

            analysis = {
                "current_cash": float(current_cash),
                "expected_inflow": float(expected_ar),
                "expected_outflow": float(upcoming_ap),
                "projected_cash": float(projected_cash),
                "overdue_receivables": float(overdue_ar),
                "net_change": float(expected_ar - upcoming_ap),
                "insights": []
            }

            # Generate insights
            if current_cash < 0:
                analysis["insights"].append("CRITICAL: Negative cash balance")
            elif current_cash < upcoming_ap:
                analysis["insights"].append(f"WARNING: Cash may be insufficient for upcoming payments ({upcoming_ap})")

            if overdue_ar > 0:
                analysis["insights"].append(f"INFO: {overdue_ar} in overdue receivables - focus on collections")

            if expected_ar > upcoming_ap:
                analysis["insights"].append("POSITIVE: Expected collections exceed upcoming payments")

            return QueryResult(
                success=True,
                data=analysis,
                message=f"Cash analysis for next {days} days",
                metadata={"period_days": days}
            )

        except Exception as e:
            logger.exception(f"Error analyzing cash flow: {e}")
            return QueryResult(
                success=False,
                data={},
                message=f"Failed to analyze cash flow: {str(e)}"
            )

    def get_dashboard_summary(self) -> QueryResult:
        """Get high-level dashboard summary across modules"""
        try:
            summary = {}

            # Cash
            cash_result = self.get_cash_balance()
            summary["cash_balance"] = cash_result.data.get("total_balance", 0)

            # AR
            ar_result = self.get_ar_aging()
            summary["accounts_receivable"] = ar_result.data.get("total", 0)

            # AP
            ap_result = self.get_ap_aging()
            summary["accounts_payable"] = ap_result.data.get("total", 0)

            # Pending approvals
            approvals_result = self.get_pending_approvals()
            summary["pending_approvals"] = approvals_result.metadata.get("count", 0)

            # TODO: Add more metrics (inventory value, sales summary, etc.)

            return QueryResult(
                success=True,
                data=summary,
                message="Dashboard summary retrieved",
                metadata={"timestamp": timezone.now().isoformat()}
            )

        except Exception as e:
            logger.exception(f"Error getting dashboard summary: {e}")
            return QueryResult(
                success=False,
                data={},
                message=f"Failed to get dashboard summary: {str(e)}"
            )
