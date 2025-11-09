from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.db import models
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.notifications.models import Notification, NotificationSeverity
from apps.security.services.permission_service import PermissionService
from apps.security.models import (
    SecPermission,
    SecRolePermission,
    SecUserRole,
    SecUserRoleScope,
    SecScope,
    SecUserDirectPermission,
)

from .models import Budget, BudgetApproval, CostCenter, BudgetLine, BudgetVarianceAudit
from apps.procurement.models import PurchaseOrderLine
from apps.inventory.models import Product
from .models import BudgetItemCode


class BudgetNotificationService:
    @staticmethod
    def _notify(user, company, title: str, body: str = "", *, entity_type: str = "", entity_id: str = ""):
        if not user or not getattr(user, "id", None):
            return
        Notification.objects.create(
            company=company,
            user=user,
            title=title,
            body=body,
            severity=NotificationSeverity.INFO,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else "",
        )

    @classmethod
    def notify_budget_created(cls, budget: Budget):
        owner = getattr(budget.cost_center, "owner", None)
        cls._notify(owner, budget.company, f"Budget created: {budget.name}", entity_type="Budget", entity_id=budget.id)

    @classmethod
    def notify_entry_period_started(cls, budget: Budget):
        owner = getattr(budget.cost_center, "owner", None)
        cls._notify(owner, budget.company, f"Entry window started for {budget.name}")

    @classmethod
    def notify_entry_period_ending(cls, budget: Budget, days_remaining: int):
        owner = getattr(budget.cost_center, "owner", None)
        cls._notify(owner, budget.company, f"Entry window ends in {days_remaining} day(s) for {budget.name}")

    @classmethod
    def notify_entry_period_ended(cls, budget: Budget):
        owner = getattr(budget.cost_center, "owner", None)
        cls._notify(owner, budget.company, f"Entry window ended for {budget.name}")

    @classmethod
    def notify_approval_requested(cls, budget: Budget, cost_center: CostCenter, approver):
        cls._notify(approver, budget.company, f"Approval requested for {budget.name}")

    @classmethod
    def notify_approval_decision(cls, budget: Budget, cost_center: CostCenter, status: str, comments: str):
        owner = getattr(cost_center, "owner", None)
        cls._notify(owner, budget.company, f"Approval {status} for {budget.name}", comments)

    @classmethod
    def notify_budget_active(cls, budget: Budget):
        owner = getattr(budget.cost_center, "owner", None)
        cls._notify(owner, budget.company, f"Budget active: {budget.name}")

    @classmethod
    def notify_review_period_started(cls, budget: Budget):
        """Notify when review period starts"""
        owner = getattr(budget.cost_center, "owner", None)
        cls._notify(owner, budget.company, f"Review period started for {budget.name}",
                   entity_type="Budget", entity_id=budget.id)

    @classmethod
    def notify_review_period_ending(cls, budget: Budget, days_remaining: int):
        """Notify when review period is ending soon"""
        owner = getattr(budget.cost_center, "owner", None)
        cls._notify(owner, budget.company,
                   f"Review period ends in {days_remaining} day(s) for {budget.name}",
                   entity_type="Budget", entity_id=budget.id)

    @classmethod
    def notify_review_period_ended(cls, budget: Budget):
        """Notify when review period ends"""
        owner = getattr(budget.cost_center, "owner", None)
        cls._notify(owner, budget.company, f"Review period ended for {budget.name}",
                   entity_type="Budget", entity_id=budget.id)

    @classmethod
    def notify_item_sent_back_for_review(cls, budget_line: BudgetLine, sent_by):
        """Notify CC owner when item is sent back for review"""
        owner = getattr(budget_line.budget.cost_center, "owner", None)
        cls._notify(owner, budget_line.budget.company,
                   f"Item '{budget_line.item_name}' sent back for review",
                   f"Sent by: {sent_by.get_full_name() if sent_by else 'System'}",
                   entity_type="BudgetLine", entity_id=budget_line.id)


class BudgetPermissionService:
    @staticmethod
    def user_can_create_budget(user, company) -> bool:
        if getattr(user, "is_superuser", False):
            return True
        if not company:
            return False

        # Check for Budget Module Owner
        if BudgetPermissionService.user_is_budget_module_owner(user, company):
            return True

        # Check for Budget Moderator
        if BudgetPermissionService.user_is_budget_moderator(user, company):
            return True

        # Check for deputy owner of any cost center in the company
        if CostCenter.objects.filter(company=company, deputy_owner=user).exists():
            return True

        return False

    @staticmethod
    def user_can_enter_for_cost_center(user, cost_center: CostCenter) -> bool:
        if not user or not getattr(user, "id", None):
            return False
        # superusers/system admins can enter for any cost center
        if getattr(user, "is_superuser", False) or getattr(user, "is_system_admin", False):
            return True
        if cost_center.owner_id == user.id or cost_center.deputy_owner_id == user.id:
            return True
        return cost_center.budget_entry_users.filter(id=user.id).exists()

    @staticmethod
    def user_is_cost_center_owner(user, cost_center: CostCenter) -> bool:
        return bool(user and (cost_center.owner_id == user.id or cost_center.deputy_owner_id == user.id))

    @staticmethod
    def user_is_budget_module_owner(user, company) -> bool:
        if getattr(user, "is_superuser", False):
            return True
        if not company:
            return False
        return PermissionService.user_has_permission(user, "budgeting_approve_budget", f"company:{company.id}")

    @staticmethod
    def user_is_budget_moderator(user, company) -> bool:
        """Check if user has moderator role for budgets"""
        if getattr(user, "is_superuser", False):
            return True
        if not company:
            return False
        return PermissionService.user_has_permission(user, "budgeting_moderate_budget", f"company:{company.id}")

    @staticmethod
    def user_is_budget_name_approver(user, company) -> bool:
        """Only Superuser or Budget Module Owner/Co-Owner can approve budget names.

        Co-owner is expected to have the same permission as owner
        (e.g., "budgeting_approve_budget") via role assignment.
        """
        if getattr(user, "is_superuser", False):
            return True
        if not company:
            return False

        # Restrict strictly to module owner/co-owner permission.
        return BudgetPermissionService.user_is_budget_module_owner(user, company)


class BudgetAIService:
    """Lightweight AI-like helpers for price prediction and consumption forecasting.
    Uses simple statistics over historical data to avoid heavy ML dependencies.
    """

    @staticmethod
    def predict_price(company, item_code: str, lookback_days: int = 365) -> tuple[Decimal | None, dict]:
        """
        Predict next purchase price for an item using last 12 months PO history
        with a simple trend + average fallback.
        Returns (predicted_price, metadata)
        """
        from django.utils import timezone as dj_tz
        from django.db.models import Avg
        now = dj_tz.now()
        since = now - timedelta(days=lookback_days)

        qs = (
            PurchaseOrderLine.objects
            .filter(company=company, item_code=item_code, order__order_date__gte=since.date())
            .order_by("order__order_date")
        )
        prices = list(qs.values_list("unit_price", flat=True))
        count = len(prices)

        # No PO history: fallback to standard price policy
        if count == 0:
            try:
                price, src = BudgetPriceService.get_price_for_item(company, item_code)
                return price, {
                    "method": f"policy:{src}",
                    "confidence": 50,
                    "history_count": 0,
                }
            except Exception:
                return None, {"method": "none", "confidence": 0, "history_count": 0}

        # Predicted price based on last price and simple trend between first and last
        first = Decimal(prices[0])
        last = Decimal(prices[-1])
        trend = Decimal("0")
        if first and first != Decimal("0"):
            trend = (last - first) / first  # relative change over lookback

        # Average price as stabilizer
        # Compute average locally to avoid extra DB call
        avg_price = sum(Decimal(str(p)) for p in prices) / Decimal(str(count))

        # Blend last price nudged by trend with average (60/40)
        predicted = (last * (Decimal("1") + trend)) * Decimal("0.6") + (avg_price * Decimal("0.4"))

        # Confidence heuristic: more history → higher confidence, capped at 95
        confidence = min(50 + count * 5, 95)

        return predicted.quantize(Decimal("0.01")), {
            "method": "po_trend_avg_blend",
            "confidence": int(confidence),
            "history_count": count,
            "last_po_price": str(last),
            "avg_price": str(avg_price.quantize(Decimal("0.01"))),
            "trend_percent": str((trend * Decimal("100")).quantize(Decimal("0.01"))) if first != 0 else "0.00",
        }

    @staticmethod
    def forecast_consumption(budget_line: BudgetLine) -> tuple[Decimal | None, dict]:
        """
        Forecast consumption by extrapolating the current run rate across the budget period.
        If there is usage history (BudgetUsage), compute rate; otherwise, estimate from committed/consumed.
        Returns (projected_consumption_value, metadata)
        """
        from django.utils import timezone as dj_tz
        today = dj_tz.now().date()
        budget = budget_line.budget
        if not budget.period_start or not budget.period_end:
            return None, {"method": "insufficient_period"}

        total_days = (budget.period_end - budget.period_start).days + 1
        elapsed_days = max((today - budget.period_start).days + 1, 1)
        elapsed_days = min(elapsed_days, total_days)

        consumed_value = budget_line.consumed_value or Decimal("0")
        # Simple daily run rate
        daily_rate = consumed_value / Decimal(str(elapsed_days)) if elapsed_days > 0 else Decimal("0")
        projected = (daily_rate * Decimal(str(total_days))).quantize(Decimal("0.01"))

        will_exceed = projected > (budget_line.value_limit or Decimal("0"))
        # Confidence grows with elapsed coverage of period
        coverage = Decimal(str(elapsed_days)) / Decimal(str(total_days)) if total_days > 0 else Decimal("0")
        confidence = int(min(max(coverage * Decimal("100"), Decimal("10")), Decimal("95")))

        return projected, {
            "method": "run_rate_extrapolation",
            "confidence": confidence,
            "elapsed_days": elapsed_days,
            "total_days": total_days,
            "will_exceed_budget": will_exceed,
        }

    @staticmethod
    def collect_budget_alerts(budget: Budget) -> list[dict]:
        """Build alerts for a budget: threshold utilization and forecast exceedances."""
        alerts: list[dict] = []
        # Utilization threshold
        limit = budget.amount or Decimal("0")
        consumed = budget.consumed or Decimal("0")
        percent = (consumed / limit * Decimal("100")).quantize(Decimal("0.01")) if limit > 0 else Decimal("0")
        threshold = Decimal(str(budget.threshold_percent or 90))
        if limit > 0 and percent >= threshold:
            alerts.append({
                "type": "utilization_threshold",
                "message": f"Budget {budget.name} is {percent}% utilized (≥ {threshold}%).",
                "percent": str(percent),
            })

        # Forecast exceedances per line
        for line in budget.lines.all():
            projected, meta = BudgetAIService.forecast_consumption(line)
            if projected is None:
                continue
            if meta.get("will_exceed_budget"):
                alerts.append({
                    "type": "forecast_exceed",
                    "line_id": line.id,
                    "item": line.item_name,
                    "projected": str(projected),
                    "limit": str(line.value_limit or Decimal("0")),
                    "message": f"{line.item_name}: projected {projected} exceeds limit {line.value_limit}.",
                    "confidence": meta.get("confidence"),
                })
        return alerts


class BudgetGamificationService:
    """Gamification: badges, leaderboards, KPIs."""

    @staticmethod
    def _utilization_percent(budget: Budget) -> Decimal:
        limit = budget.amount or Decimal("0")
        consumed = budget.consumed or Decimal("0")
        if limit <= 0:
            return Decimal("0")
        return (consumed / limit * Decimal("100")).quantize(Decimal("0.01"))

    @staticmethod
    def _closest_to_100_rank_key(budget: Budget) -> Decimal:
        pct = BudgetGamificationService._utilization_percent(budget)
        return abs(pct - Decimal("100"))

    @staticmethod
    def compute_badges_for_budget(budget: Budget) -> list[dict]:
        badges: list[dict] = []

        # Early Bird: submitted in first 30% of entry period
        if budget.entry_start_date and budget.entry_end_date:
            total_days = (budget.entry_end_date - budget.entry_start_date).days + 1
            threshold_day = budget.entry_start_date + timedelta(days=int(total_days * 0.3))
            # The CC approval request marks entry submission
            first_approval = budget.approvals.filter(
                approver_type=BudgetApproval.ApproverType.COST_CENTER_OWNER
            ).order_by("created_at").first()
            if first_approval and first_approval.created_at.date() <= threshold_day:
                badges.append({"code": "early_bird", "name": "Early Bird", "reason": "Submitted in first 30% of entry period"})

        # Perfect Submission: zero variance
        if (budget.total_variance_count or 0) == 0:
            badges.append({"code": "perfect_submission", "name": "Perfect Submission", "reason": "No modifications (zero variance)"})

        # Sweet Spot: utilization 95%–105%
        pct = BudgetGamificationService._utilization_percent(budget)
        if pct >= Decimal("95") and pct <= Decimal("105"):
            badges.append({"code": "sweet_spot", "name": "Sweet Spot", "reason": f"Utilization {pct}% near 100%"})

        # Efficient Process: final approval within 2 days of submission
        first_approval = budget.approvals.filter(
            approver_type=BudgetApproval.ApproverType.COST_CENTER_OWNER
        ).order_by("created_at").first()
        if first_approval and budget.final_approved_at:
            delta = budget.final_approved_at - first_approval.created_at
            if delta.days < 2 or (delta.days == 2 and delta.seconds == 0):
                badges.append({"code": "efficient_process", "name": "Efficient Process", "reason": "Approved within 2 days of submission"})

        # Clear Review: no items held for further review
        if budget.lines.filter(is_held_for_review=True).count() == 0:
            badges.append({"code": "clear_review", "name": "Clear Review", "reason": "No lines held for further review"})

        return badges

    @staticmethod
    def leaderboard(company, limit: int = 10) -> list[dict]:
        qs = Budget.objects.filter(company=company).exclude(amount=Decimal("0")).order_by()
        rows = []
        for b in qs:
            pct = BudgetGamificationService._utilization_percent(b)
            rows.append({
                "budget_id": b.id,
                "name": b.name,
                "cost_center": getattr(b.cost_center, "name", None),
                "utilization_percent": str(pct),
                "distance_from_100": str(abs(pct - Decimal("100"))),
            })
        rows.sort(key=lambda r: Decimal(r["distance_from_100"]))
        return rows[:limit]

    @staticmethod
    def kpis(company) -> dict:
        qs = Budget.objects.filter(company=company)
        total = qs.count()
        zero_variance = qs.filter(total_variance_count=0).count()
        early_birds = 0
        for b in qs:
            if b.entry_start_date and b.entry_end_date:
                total_days = (b.entry_end_date - b.entry_start_date).days + 1
                threshold_day = b.entry_start_date + timedelta(days=int(total_days * 0.3))
                first_approval = b.approvals.filter(approver_type=BudgetApproval.ApproverType.COST_CENTER_OWNER).order_by("created_at").first()
                if first_approval and first_approval.created_at.date() <= threshold_day:
                    early_birds += 1
        best = None
        for b in qs:
            pct = BudgetGamificationService._utilization_percent(b)
            dist = abs(pct - Decimal("100"))
            item = {"budget_id": b.id, "name": b.name, "utilization_percent": str(pct), "distance_from_100": str(dist)}
            if best is None or dist < Decimal(best["distance_from_100"]):
                best = item
        return {
            "total_budgets": total,
            "zero_variance_rate": (zero_variance / total * 100) if total else 0,
            "early_submission_rate": (early_birds / total * 100) if total else 0,
            "best_utilization": best,
        }

class BudgetApprovalService:
    @staticmethod
    def request_cost_center_approvals(budget: Budget):
        cc = budget.cost_center
        approver = getattr(cc, "owner", None) or getattr(cc, "deputy_owner", None)
        obj, _ = BudgetApproval.objects.get_or_create(
            budget=budget,
            approver_type=BudgetApproval.ApproverType.COST_CENTER_OWNER,
            cost_center=cc,
            defaults={"approver": approver},
        )
        if not obj.approver and approver:
            obj.approver = approver
            obj.save(update_fields=["approver"])
        BudgetNotificationService.notify_approval_requested(budget, cc, obj.approver)

    @staticmethod
    def approve_by_cost_center_owner(budget: Budget, user, comments: str = "", modifications: Optional[dict] = None):
        # Try to find the pending approval for this user or for a cost center they own/deputy own
        base_qs = BudgetApproval.objects.filter(
            budget=budget,
            approver_type=BudgetApproval.ApproverType.COST_CENTER_OWNER,
            status=BudgetApproval.Status.PENDING,
        ).select_related("cost_center")
        approval = base_qs.filter(approver=user).first()
        if not approval:
            approval = base_qs.filter(
                models.Q(cost_center__owner=user) | models.Q(cost_center__deputy_owner=user)
            ).first()
        if not approval:
            return
        # Only finalize approval when all items in this CC are cleared (approved or sent back)
        # Otherwise, keep the task pending and just record comments/modifications
        try:
            cc = approval.cost_center or getattr(budget, 'cost_center', None)
            cleared = False
            if cc:
                lines = list(budget.lines.all())
                cc_lines = [bl for bl in lines if (getattr(bl, 'metadata', {}) or {}).get('cost_center_id') == cc.id or getattr(budget, 'cost_center_id', None) == cc.id]
                if cc_lines:
                    total = len(cc_lines)
                    ok = 0
                    for bl in cc_lines:
                        m = getattr(bl, 'metadata', {}) or {}
                        if m.get('approved') is True or getattr(bl, 'sent_back_for_review', False):
                            ok += 1
                    cleared = (ok == total)
        except Exception:
            cleared = False

        # Always store comments/modifications
        approval.comments = comments or ""
        approval.modifications_made = modifications or {}
        if cleared:
            approval.status = BudgetApproval.Status.APPROVED
            approval.approver = user or approval.approver
            approval.decision_date = timezone.now()
            approval.save(update_fields=["status", "comments", "modifications_made", "approver", "decision_date"])
            # Move to moderator review per workflow
            budget.status = Budget.STATUS_PENDING_MODERATOR_REVIEW
            budget.save(update_fields=["status", "updated_at"])
        else:
            approval.save(update_fields=["comments", "modifications_made"])  # keep pending

    @staticmethod
    def reject_by_cost_center_owner(budget: Budget, user, comments: str = ""):
        base_qs = BudgetApproval.objects.filter(
            budget=budget,
            approver_type=BudgetApproval.ApproverType.COST_CENTER_OWNER,
            status=BudgetApproval.Status.PENDING,
        ).select_related("cost_center")
        approval = base_qs.filter(approver=user).first()
        if not approval:
            approval = base_qs.filter(
                models.Q(cost_center__owner=user) | models.Q(cost_center__deputy_owner=user)
            ).first()
        if not approval:
            return
        approval.status = BudgetApproval.Status.REJECTED
        approval.comments = comments or ""
        approval.approver = user or approval.approver
        approval.decision_date = timezone.now()
        approval.save(update_fields=["status", "comments", "approver", "decision_date"])
        # Send back to entry
        budget.status = Budget.STATUS_ENTRY_OPEN
        budget.save(update_fields=["status", "updated_at"])

    @staticmethod
    def request_final_approval(budget: Budget):
        # Locate users who have 'budgeting_approve_budget' on this company and assign approvals
        company = budget.company
        perm = SecPermission.objects.filter(code="budgeting_approve_budget").first()
        approvers = []
        if perm:
            # Role-based approvers with matching scope
            role_ids = list(SecRolePermission.objects.filter(permission=perm).values_list("role_id", flat=True))
            if role_ids:
                user_roles = SecUserRole.objects.filter(role_id__in=role_ids)
                if perm.scope_required:
                    # Must have a scope for this company
                    scope_qs = SecScope.objects.filter(scope_type="company", object_id=str(company.id))
                    urs = SecUserRoleScope.objects.filter(scope__in=scope_qs, user_role__in=user_roles)
                    approvers.extend([ur.user_role.user for ur in urs.select_related("user_role", "user_role__user")])
                else:
                    approvers.extend([ur.user for ur in user_roles.select_related("user")])

            # Direct-user permission holders
            direct_qs = SecUserDirectPermission.objects.filter(permission=perm)
            if perm.scope_required:
                scope_qs = SecScope.objects.filter(scope_type="company", object_id=str(company.id))
                direct_qs = direct_qs.filter(scope__in=scope_qs)
            approvers.extend([dp.user for dp in direct_qs.select_related("user")])

        # Deduplicate approvers
        seen = set()
        unique_approvers = []
        for u in approvers:
            if not u:
                continue
            if u.id in seen:
                continue
            seen.add(u.id)
            unique_approvers.append(u)

        created_any = False
        created_for_users: list = []
        if not unique_approvers:
            # Create a generic final approval record without an explicit approver
            _, created = BudgetApproval.objects.get_or_create(
                budget=budget,
                approver_type=BudgetApproval.ApproverType.BUDGET_MODULE_OWNER,
                defaults={"status": BudgetApproval.Status.PENDING},
            )
            created_any = created or created_any
        else:
            for user in unique_approvers:
                obj, created = BudgetApproval.objects.get_or_create(
                    budget=budget,
                    approver_type=BudgetApproval.ApproverType.BUDGET_MODULE_OWNER,
                    approver=user,
                    defaults={"status": BudgetApproval.Status.PENDING},
                )
                if created:
                    created_any = True
                    created_for_users.append(user)

        budget.status = Budget.STATUS_PENDING_FINAL_APPROVAL
        budget.save(update_fields=["status", "updated_at"])

        # Notify intended approvers when the final-approval task is created
        try:
            if created_any:
                title = f"Budget final approval requested: {budget.name}"
                body = "Moderator review complete. Please review and approve."
                if created_for_users:
                    for u in created_for_users:
                        if not u:
                            continue
                        Notification.objects.create(
                            company=budget.company,
                            user=u,
                            title=title,
                            body=body,
                            severity=NotificationSeverity.INFO,
                            entity_type="Budget",
                            entity_id=str(budget.id),
                        )
        except Exception:
            pass
        return True

    @staticmethod
    def request_budget_name_approval(budget: Budget):
        import logging
        logger = logging.getLogger(__name__)
        company = budget.company
        approvers = []

        # Find Budget Module Owners
        perm = SecPermission.objects.filter(code="budgeting_approve_budget").first()
        if perm:
            role_ids = list(SecRolePermission.objects.filter(permission=perm).values_list("role_id", flat=True))
            if role_ids:
                user_roles = SecUserRole.objects.filter(role_id__in=role_ids)
                if perm.scope_required:
                    scope_qs = SecScope.objects.filter(scope_type="company", object_id=str(company.id))
                    urs = SecUserRoleScope.objects.filter(scope__in=scope_qs, user_role__in=user_roles)
                    approvers.extend([ur.user_role.user for ur in urs.select_related("user_role", "user_role__user")])
                else:
                    approvers.extend([ur.user for ur in user_roles.select_related("user")])

            direct_qs = SecUserDirectPermission.objects.filter(permission=perm)
            if perm.scope_required:
                scope_qs = SecScope.objects.filter(scope_type="company", object_id=str(company.id))
                direct_qs = direct_qs.filter(scope__in=scope_qs)
            approvers.extend([dp.user for dp in direct_qs.select_related("user")])

        # NOTE: For name approval, only Budget Module Owners (or superuser) are required.
        # Do NOT include deputy owners to avoid multiple pending tasks that linger after first approval.

        # Deduplicate approvers
        seen = set()
        unique_approvers = []
        for u in approvers:
            if not u:
                continue
            if u.id in seen:
                continue
            seen.add(u.id)
            unique_approvers.append(u)

        created = 0
        for user in unique_approvers:
            _, was_created = BudgetApproval.objects.get_or_create(
                budget=budget,
                approver_type=BudgetApproval.ApproverType.BUDGET_NAME_APPROVER,
                approver=user,
                defaults={"status": BudgetApproval.Status.PENDING},
            )
            if was_created:
                created += 1
        try:
            logger.info(f"[BudgetApprovalService.request_budget_name_approval] budget_id={budget.id} approvers={len(unique_approvers)} created={created}")
        except Exception:
            pass
        
        return True


@dataclass
class PricePolicy:
    primary: str
    secondary: str
    tertiary: str
    avg_lookback_days: int = 365
    fallback_on_zero: bool = True


class BudgetPriceService:
    @staticmethod
    def get_company_policy(company) -> PricePolicy:
        try:
            from .models import BudgetPricePolicy  # type: ignore
        except Exception:
            BudgetPricePolicy = None  # type: ignore
        default = PricePolicy(primary="standard", secondary="last_po", tertiary="avg", avg_lookback_days=365, fallback_on_zero=True)
        if not company or not BudgetPricePolicy:
            return default
        policy = BudgetPricePolicy.objects.filter(company=company).first()
        if not policy:
            return default
        return PricePolicy(
            primary=policy.primary_source,
            secondary=policy.secondary_source,
            tertiary=policy.tertiary_source,
            avg_lookback_days=policy.avg_lookback_days or 365,
            fallback_on_zero=policy.fallback_on_zero,
        )

    @staticmethod
    def _standard_price(company, item_code):
        # Group-scoped lookup for item code
        bic = None
        if company and getattr(company, 'company_group_id', None):
            bic = BudgetItemCode.objects.filter(company__company_group_id=company.company_group_id, code=item_code).first()
        if not bic and company:
            bic = BudgetItemCode.objects.filter(company=company, code=item_code).first()
        if bic and bic.standard_price is not None:
            return bic.standard_price
        prod = Product.objects.filter(company=company, code=item_code).first()
        return getattr(prod, "cost_price", None)

    @staticmethod
    def _last_po_price(company, item_code):
        prod = Product.objects.filter(company=company, code=item_code).first()
        if not prod:
            return None
        pol = (
            PurchaseOrderLine.objects.select_related("purchase_order")
            .filter(product=prod, purchase_order__company=company)
            .order_by("-purchase_order__order_date", "-id")
            .first()
        )
        return pol.unit_price if pol else None

    @staticmethod
    def _avg_price(company, item_code, lookback_days: int):
        from django.db import models as dj_models
        prod = Product.objects.filter(company=company, code=item_code).first()
        if not prod:
            return None
        since = timezone.now().date() - timedelta(days=lookback_days or 365)
        qs = (
            PurchaseOrderLine.objects.select_related("purchase_order")
            .filter(product=prod, purchase_order__company=company, purchase_order__order_date__gte=since)
        )
        if not qs.exists():
            return None
        agg = qs.aggregate(avg=dj_models.Avg("unit_price"))
        return agg.get("avg")

    @classmethod
    def get_price_for_item(cls, company, item_code: str) -> tuple[Decimal, str]:
        policy = cls.get_company_policy(company)
        sources = [policy.primary, policy.secondary, policy.tertiary]
        for src in sources:
            price = None
            if src == "standard":
                price = cls._standard_price(company, item_code)
            elif src == "last_po":
                price = cls._last_po_price(company, item_code)
            elif src == "avg":
                price = cls._avg_price(company, item_code, policy.avg_lookback_days)
            elif src == "manual_only":
                price = None
            if price is not None:
                return Decimal(price), src
        if policy.fallback_on_zero:
            return Decimal("0"), "manual"
        raise ValueError("Price not found; manual price required")

    @staticmethod
    def approve_by_module_owner(budget: Budget, user, comments: str = ""):
        approval = BudgetApproval.objects.filter(
            budget=budget,
            approver_type=BudgetApproval.ApproverType.BUDGET_MODULE_OWNER,
        ).first()
        if approval and approval.status == BudgetApproval.Status.PENDING:
            approval.status = BudgetApproval.Status.APPROVED
            approval.comments = comments or ""
            approval.approver = user or approval.approver
            approval.decision_date = timezone.now()
            approval.save(update_fields=["status", "comments", "approver", "decision_date"])
        # Mark budget approved; activation can be separate based on dates
        budget.status = Budget.STATUS_APPROVED
        budget.approved_by = user
        budget.approved_at = timezone.now()
        budget.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

    @staticmethod
    def reject_by_module_owner(budget: Budget, user, comments: str = ""):
        approval = BudgetApproval.objects.filter(
            budget=budget,
            approver_type=BudgetApproval.ApproverType.BUDGET_MODULE_OWNER,
        ).first()
        if approval and approval.status == BudgetApproval.Status.PENDING:
            approval.status = BudgetApproval.Status.REJECTED
            approval.comments = comments or ""
            approval.approver = user or approval.approver
            approval.decision_date = timezone.now()
            approval.save(update_fields=["status", "comments", "approver", "decision_date"])
        # Send back to entry stage for rework
        budget.status = Budget.STATUS_ENTRY_OPEN
        budget.save(update_fields=["status", "updated_at"])

    @staticmethod
    def send_back_to_cost_center(budget: Budget, user, comments: str = ""):
        BudgetApproval.objects.create(
            budget=budget,
            approver_type=BudgetApproval.ApproverType.BUDGET_MODULE_OWNER,
            status=BudgetApproval.Status.SENT_BACK,
            comments=comments or "",
            approver=user,
        )
        budget.status = Budget.STATUS_ENTRY_OPEN
        budget.save(update_fields=["status", "updated_at"])


class BudgetReviewPeriodService:
    """Service for managing review period and grace period logic"""

    @staticmethod
    def transition_to_review_period(budget: Budget) -> bool:
        """
        Transition budget from entry period to review period.
        This happens after entry period + grace period ends.
        Returns True if transition was successful.
        """
        from datetime import date
        today = date.today()

        # Check if entry period has ended
        if not budget.entry_end_date or budget.entry_end_date >= today:
            return False

        # Calculate review start date if not set
        if not budget.review_start_date:
            budget.review_start_date = budget.calculate_review_start_date()

        # Check if grace period has ended (if review start date is today or past)
        if budget.review_start_date and budget.review_start_date <= today:
            # Transition to review period
            if budget.status == Budget.STATUS_ENTRY_OPEN:
                budget.status = Budget.STATUS_ENTRY_CLOSED_REVIEW_PENDING
                budget.save(update_fields=["status", "review_start_date", "updated_at"])

            # Enable review period if dates are set
            if budget.review_end_date and budget.review_enabled:
                budget.status = Budget.STATUS_REVIEW_OPEN
                budget.save(update_fields=["status", "updated_at"])
                BudgetNotificationService.notify_review_period_started(budget)
                return True

        return False

    @staticmethod
    def can_edit_budget_line_in_review_period(budget_line: BudgetLine, user) -> tuple[bool, str]:
        """
        Check if a budget line can be edited during review period.
        Returns (can_edit, reason_if_not)
        """
        budget = budget_line.budget

        # If not in review period, use normal rules
        if not budget.is_review_period_active():
            return True, ""

        # During review period, only sent-back items can be edited
        if not budget_line.sent_back_for_review:
            return False, "Item was not sent back for review. Cannot edit during review period."

        # Check if user is CC owner/deputy
        cc = budget.cost_center
        if not cc:
            return False, "No cost center associated with budget."

        is_owner = BudgetPermissionService.user_is_cost_center_owner(user, cc)
        if not is_owner:
            return False, "Only cost center owners can edit during review period."

        return True, ""

    @staticmethod
    def send_item_back_for_review(budget_line: BudgetLine, user, reason: str = "") -> bool:
        """
        Mark a budget line item as sent back for review.
        This allows CC owners to edit it during review period.
        Returns True if successful.
        """
        from django.utils import timezone

        budget = budget_line.budget

        # Can only send back during certain states (typically after entry period)
        allowed_states = {
            Budget.STATUS_ENTRY_CLOSED_REVIEW_PENDING,
            Budget.STATUS_REVIEW_OPEN,
            Budget.STATUS_PENDING_CC_APPROVAL,
            Budget.STATUS_CC_APPROVED,
        }

        if budget.status not in allowed_states:
            return False

        # Mark as sent back
        budget_line.sent_back_for_review = True
        budget_line.held_reason = reason
        budget_line.held_by = user
        budget_line.held_until_date = budget.review_end_date if budget.review_end_date else None
        budget_line.save(update_fields=[
            "sent_back_for_review",
            "held_reason",
            "held_by",
            "held_until_date",
            "updated_at"
        ])

        # Notify CC owner
        BudgetNotificationService.notify_item_sent_back_for_review(budget_line, user)

        return True

    @staticmethod
    def update_budget_line_with_variance_tracking(
        budget_line: BudgetLine,
        user,
        new_qty: Optional[Decimal] = None,
        new_price: Optional[Decimal] = None,
        new_value: Optional[Decimal] = None,
        reason: str = "",
        role: str = "cc_owner",
        metadata: Optional[dict] = None
    ) -> BudgetLine:
        """
        Update a budget line and create variance audit trail.
        Used during review period edits.
        """
        from django.utils import timezone

        # Store original values if not already set
        if budget_line.original_qty_limit == Decimal("0"):
            budget_line.original_qty_limit = budget_line.qty_limit
        if budget_line.original_unit_price == Decimal("0"):
            budget_line.original_unit_price = budget_line.standard_price
        if budget_line.original_value_limit == Decimal("0"):
            budget_line.original_value_limit = budget_line.value_limit

        # Store old values for audit
        old_qty = budget_line.qty_limit
        old_price = budget_line.standard_price
        old_value = budget_line.value_limit

        # Update values
        if new_qty is not None:
            budget_line.qty_limit = new_qty
        if new_price is not None:
            budget_line.standard_price = new_price
        if new_value is not None:
            budget_line.value_limit = new_value

        # Calculate variances
        budget_line.qty_variance = budget_line.qty_limit - budget_line.original_qty_limit
        budget_line.price_variance = budget_line.standard_price - budget_line.original_unit_price
        budget_line.value_variance = budget_line.value_limit - budget_line.original_value_limit

        # Calculate variance percentage
        if budget_line.original_value_limit > 0:
            budget_line.variance_percent = (
                (budget_line.value_variance / budget_line.original_value_limit) * Decimal("100")
            )

        # Track modification
        budget_line.modified_by = user
        budget_line.modified_at = timezone.now()
        budget_line.modification_reason = reason

        if metadata is not None:
            budget_line.metadata = metadata

        budget_line.save()

        # Create audit record
        budget = budget_line.budget
        # Determine change type based on effective changes
        qty_changed = (new_qty is not None and new_qty != old_qty)
        price_changed = (new_price is not None and new_price != old_price) or (new_value is not None and new_value != old_value)
        if qty_changed and price_changed:
            change_type = BudgetVarianceAudit.ChangeType.BOTH_CHANGE
        elif qty_changed:
            change_type = BudgetVarianceAudit.ChangeType.QTY_CHANGE
        else:
            change_type = BudgetVarianceAudit.ChangeType.PRICE_CHANGE

        BudgetVarianceAudit.objects.create(
            budget_line=budget_line,
            modified_by=user,
            change_type=change_type,
            role_of_modifier=role,
            original_qty=old_qty,
            new_qty=budget_line.qty_limit,
            original_price=old_price,
            new_price=budget_line.standard_price,
            original_value=old_value,
            new_value=budget_line.value_limit,
            justification=reason,
        )

        # Update budget-level variance totals
        budget.total_variance_count = budget.lines.exclude(value_variance=Decimal("0")).count()
        budget.total_variance_amount = budget.lines.aggregate(
            total=Sum("value_variance")
        )["total"] or Decimal("0")
        budget.save(update_fields=["total_variance_count", "total_variance_amount", "updated_at"])

        return budget_line

    @staticmethod
    def close_review_period(budget: Budget) -> bool:
        """
        Close the review period and auto-forward non-held items to final approval.
        Returns True if successful.
        """
        from datetime import date

        if not budget.is_review_period_active():
            return False

        # Disable review period
        budget.review_enabled = False

        # Auto-forward non-held items to final approval: mark as not_reviewed
        try:
            auto_lines = budget.lines.filter(is_held_for_review=False)
            for bl in auto_lines:
                meta = getattr(bl, 'metadata', {}) or {}
                if not meta.get('not_reviewed'):
                    meta['not_reviewed'] = True
                    bl.metadata = meta
                    bl.save(update_fields=["metadata", "updated_at"])
        except Exception:
            pass

        # Move directly to final approval per policy
        try:
            BudgetApprovalService.request_final_approval(budget)
        except Exception:
            # Fallback to moderator review if final approval could not be requested
            budget.status = Budget.STATUS_PENDING_MODERATOR_REVIEW
            budget.save(update_fields=["review_enabled", "status", "updated_at"])
            BudgetNotificationService.notify_review_period_ended(budget)
            return True

        budget.status = Budget.STATUS_PENDING_FINAL_APPROVAL
        budget.save(update_fields=["review_enabled", "status", "updated_at"])
        BudgetNotificationService.notify_review_period_ended(budget)
        return True

    @staticmethod
    def check_and_auto_transition_budgets():
        """
        Background task to automatically transition budgets through review period states.
        Should be called periodically (e.g., daily cron job).
        """
        from datetime import date
        today = date.today()

        # Find budgets that should enter review period
        entry_closed_budgets = Budget.objects.filter(
            status=Budget.STATUS_ENTRY_OPEN,
            entry_end_date__lt=today,
        )

        for budget in entry_closed_budgets:
            BudgetReviewPeriodService.transition_to_review_period(budget)

        # Find budgets whose review period should end
        review_ending_budgets = Budget.objects.filter(
            status=Budget.STATUS_REVIEW_OPEN,
            review_end_date__lt=today,
        )

        for budget in review_ending_budgets:
            BudgetReviewPeriodService.close_review_period(budget)

        # Find budgets in review period ending soon (3 days warning)
        from datetime import timedelta
        warning_date = today + timedelta(days=3)
        review_ending_soon = Budget.objects.filter(
            status=Budget.STATUS_REVIEW_OPEN,
            review_end_date=warning_date,
        )

        for budget in review_ending_soon:
            BudgetNotificationService.notify_review_period_ending(budget, 3)


class BudgetModeratorService:
    """Service for budget moderator operations"""

    @staticmethod
    def add_remark_to_line(
        budget_line: BudgetLine,
        user,
        remark_text: str,
        remark_template_id: Optional[int] = None
    ) -> BudgetLine:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Adding remark to line {budget_line.id}")
        """
        Add moderator remark to a budget line.
        Optionally increment usage count if using a template.
        """
        from django.utils import timezone
        from .models import BudgetRemarkTemplate

        budget_line.moderator_remarks = remark_text
        budget_line.moderator_remarks_by = user
        budget_line.moderator_remarks_at = timezone.now()
        budget_line.save(update_fields=["moderator_remarks", "moderator_remarks_by", "moderator_remarks_at", "updated_at"])

        # Increment template usage if template was used
        if remark_template_id:
            try:
                template = BudgetRemarkTemplate.objects.get(id=remark_template_id)
                template.usage_count = models.F("usage_count") + 1
                template.save(update_fields=["usage_count"])
            except BudgetRemarkTemplate.DoesNotExist:
                pass

        # Workflow change: when a moderator remarks an item, ensure a final approval task
        # exists for this budget (so it appears under Final Approvals for module owners).
        budget = budget_line.budget
        from .models import BudgetApproval as BA
        # Avoid duplicates and skip if already finalized/active
        terminal_statuses = {
            Budget.STATUS_APPROVED,
            Budget.STATUS_AUTO_APPROVED,
            Budget.STATUS_ACTIVE,
        }
        if budget and budget.status not in terminal_statuses:
            exists = BA.objects.filter(
                budget=budget,
                approver_type=BA.ApproverType.BUDGET_MODULE_OWNER,
                status=BA.Status.PENDING,
            ).exists()
            if not exists:
                logger.info(f"Requesting final approval for budget {budget.id}")
                # This will also move budget to PENDING_FINAL_APPROVAL
                BudgetApprovalService.request_final_approval(budget)
                logger.info(f"Final approval requested for budget {budget.id}")

        return budget_line

    @staticmethod
    def complete_moderator_review(budget: Budget, user, summary_notes: str = "") -> bool:
        """
        Mark budget as reviewed by moderator and move to next stage.
        Returns True if successful.
        """
        from django.utils import timezone

        # New rule: allow moderation anytime before review_end_date; block after it
        today = timezone.now().date()
        try:
            end = getattr(budget, "review_end_date", None)
        except Exception:
            end = None
        if end is not None and today > end:
            return False

        # Mark as reviewed
        budget.moderator_reviewed_by = user
        budget.moderator_reviewed_at = timezone.now()
        budget.status = Budget.STATUS_MODERATOR_REVIEWED

        # Add summary notes to metadata if provided
        if summary_notes:
            metadata = budget.metadata or {}
            metadata["moderator_summary"] = summary_notes
            budget.metadata = metadata

        budget.save(update_fields=["moderator_reviewed_by", "moderator_reviewed_at", "status", "metadata", "updated_at"])

        # After moderator review, request final approval from budget module owners
        try:
            BudgetApprovalService.request_final_approval(budget)
        except Exception:
            # Do not fail the action if final approval request cannot be created
            pass

        # Notify budget module owner that moderator review is complete
        from apps.notifications.models import Notification, NotificationSeverity
        # Find budget module owners to notify
        try:
            company = budget.company
            perm = SecPermission.objects.filter(code="budgeting_approve_budget").first()
            if perm:
                role_ids = list(SecRolePermission.objects.filter(permission=perm).values_list("role_id", flat=True))
                if role_ids:
                    user_roles = SecUserRole.objects.filter(role_id__in=role_ids)
                    if perm.scope_required:
                        scope_qs = SecScope.objects.filter(scope_type="company", object_id=str(company.id))
                        urs = SecUserRoleScope.objects.filter(scope__in=scope_qs, user_role__in=user_roles)
                        for ur in urs.select_related("user_role", "user_role__user"):
                            approver = ur.user_role.user
                            if approver:
                                Notification.objects.create(
                                    company=company,
                                    user=approver,
                                    title=f"Moderator review complete: {budget.name}",
                                    body=f"Reviewed by {user.get_full_name() if user else 'System'}",
                                    severity=NotificationSeverity.INFO,
                                    entity_type="Budget",
                                    entity_id=str(budget.id),
                                )
        except Exception:
            pass

        return True

    @staticmethod
    def get_budgets_pending_moderation(company):
        """Get all budgets pending moderator review for a company"""
        qs = Budget.objects.filter(
            status=Budget.STATUS_PENDING_MODERATOR_REVIEW
        )
        if company is not None:
            qs = qs.filter(company=company)
        return qs.select_related("cost_center", "approved_by").order_by("-updated_at")

    @staticmethod
    def get_moderator_review_summary(budget: Budget) -> dict:
        """Get summary of moderator review status for a budget"""
        lines_with_remarks = budget.lines.exclude(moderator_remarks="").count()
        total_lines = budget.lines.count()
        sent_back_count = budget.lines.filter(sent_back_for_review=True).count()

        return {
            "budget_id": budget.id,
            "budget_name": (str(budget) if budget else None),
            "status": budget.status,
            "moderator_reviewed": budget.status == Budget.STATUS_MODERATOR_REVIEWED,
            "moderator_reviewed_by": budget.moderator_reviewed_by.get_full_name() if budget.moderator_reviewed_by else None,
            "moderator_reviewed_at": budget.moderator_reviewed_at,
            "total_lines": total_lines,
            "lines_with_remarks": lines_with_remarks,
            "sent_back_count": sent_back_count,
            "variance_count": budget.total_variance_count,
            "variance_amount": str(budget.total_variance_amount),
        }

    @staticmethod
    def batch_add_remarks(
        budget_line_ids: list,
        user,
        remark_text: str,
        remark_template_id: Optional[int] = None
    ) -> dict:
        """
        Add the same remark to multiple budget lines at once.
        Returns dict with success count and failed IDs.
        """
        from django.utils import timezone
        from .models import BudgetRemarkTemplate

        success_count = 0
        failed_ids = []

        for line_id in budget_line_ids:
            try:
                budget_line = BudgetLine.objects.get(id=line_id)
                budget_line.moderator_remarks = remark_text
                budget_line.moderator_remarks_by = user
                budget_line.moderator_remarks_at = timezone.now()
                budget_line.save(update_fields=["moderator_remarks", "moderator_remarks_by", "moderator_remarks_at", "updated_at"])
                success_count += 1
            except BudgetLine.DoesNotExist:
                failed_ids.append(line_id)

        # Increment template usage once per batch
        if remark_template_id and success_count > 0:
            try:
                template = BudgetRemarkTemplate.objects.get(id=remark_template_id)
                template.usage_count = models.F("usage_count") + success_count
                template.save(update_fields=["usage_count"])
            except BudgetRemarkTemplate.DoesNotExist:
                pass

        # After adding remarks, trigger final approval for the affected budgets
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Attempting to trigger final approval for budgets after batch remarks.")
        
        from .models import Budget
        budget_ids = BudgetLine.objects.filter(id__in=budget_line_ids).values_list('budget_id', flat=True).distinct()
        budgets = Budget.objects.filter(id__in=budget_ids)
        logger.info(f"Found {len(budgets)} budgets to process for final approval.")
        for budget in budgets:
            from .models import BudgetApproval as BA
            # Avoid duplicates and skip if already finalized/active
            terminal_statuses = {
                Budget.STATUS_APPROVED,
                Budget.STATUS_AUTO_APPROVED,
                Budget.STATUS_ACTIVE,
            }
            if budget and budget.status not in terminal_statuses:
                exists = BA.objects.filter(
                    budget=budget,
                    approver_type=BA.ApproverType.BUDGET_MODULE_OWNER,
                    status=BA.Status.PENDING,
                ).exists()
                if not exists:
                    logger.info(f"Requesting final approval for budget {budget.id}")
                    BudgetApprovalService.request_final_approval(budget)
                else:
                    logger.info(f"Final approval for budget {budget.id} already exists.")
            else:
                logger.info(f"Budget {budget.id} is in a terminal status, skipping final approval request.")

        return {
            "success_count": success_count,
            "failed_ids": failed_ids,
            "total_attempted": len(budget_line_ids)
        }

    @staticmethod
    def batch_send_back_for_review(
        budget_line_ids: list,
        user,
        reason: str = ""
    ) -> dict:
        """
        Send multiple budget line items back for review at once.
        Returns dict with success count and failed IDs.
        """
        from django.utils import timezone

        success_count = 0
        failed_ids = []

        for line_id in budget_line_ids:
            try:
                budget_line = BudgetLine.objects.get(id=line_id)
                budget = budget_line.budget

                # Check if budget is in allowed state
                allowed_states = {
                    Budget.STATUS_ENTRY_CLOSED_REVIEW_PENDING,
                    Budget.STATUS_REVIEW_OPEN,
                    Budget.STATUS_PENDING_CC_APPROVAL,
                    Budget.STATUS_CC_APPROVED,
                }

                if budget.status in allowed_states:
                    budget_line.sent_back_for_review = True
                    budget_line.held_reason = reason
                    budget_line.held_by = user
                    budget_line.held_until_date = budget.review_end_date if budget.review_end_date else None
                    budget_line.save(update_fields=[
                        "sent_back_for_review",
                        "held_reason",
                        "held_by",
                        "held_until_date",
                        "updated_at"
                    ])
                    success_count += 1
                else:
                    failed_ids.append(line_id)

            except BudgetLine.DoesNotExist:
                failed_ids.append(line_id)

        return {
            "success_count": success_count,
            "failed_ids": failed_ids,
            "total_attempted": len(budget_line_ids)
        }

    @staticmethod
    def batch_apply_template_to_category(
        budget_id: int,
        category: str,
        user,
        remark_template_id: int
    ) -> dict:
        """
        Apply a remark template to all budget lines in a specific category.
        Returns dict with success count.
        """
        from .models import BudgetRemarkTemplate

        try:
            template = BudgetRemarkTemplate.objects.get(id=remark_template_id)
            budget = Budget.objects.get(id=budget_id)

            # Get all lines in this category
            lines = budget.lines.filter(category=category)
            line_ids = list(lines.values_list('id', flat=True))

            # Use batch_add_remarks
            result = BudgetModeratorService.batch_add_remarks(
                budget_line_ids=line_ids,
                user=user,
                remark_text=template.template_text,
                remark_template_id=remark_template_id
            )

            return result

        except (BudgetRemarkTemplate.DoesNotExist, Budget.DoesNotExist):
            return {
                "success_count": 0,
                "failed_ids": [],
                "total_attempted": 0,
                "error": "Template or budget not found"
            }


class BudgetAutoApprovalService:
    """Service for auto-approval of budgets"""

    @staticmethod
    def auto_approve_budget(budget: Budget) -> bool:
        """
        Auto-approve a budget if conditions are met.
        Returns True if auto-approved.
        """
        from django.utils import timezone
        from datetime import date

        # Check if budget should be auto-approved
        if not budget.should_auto_approve():
            return False

        # Find the role specified for auto-approval credit
        auto_approve_role = budget.auto_approve_by_role or "system"

        # Mark as auto-approved
        budget.status = Budget.STATUS_AUTO_APPROVED
        budget.auto_approved_at = timezone.now()

        # Also mark as approved for workflow
        budget.approved_at = timezone.now()
        # approved_by is left NULL to indicate it was auto-approved

        # Add metadata about auto-approval
        metadata = budget.metadata or {}
        metadata["auto_approval_info"] = {
            "approved_at": str(timezone.now()),
            "role": auto_approve_role,
            "reason": "Auto-approved at budget start date"
        }
        budget.metadata = metadata

        budget.save(update_fields=[
            "status",
            "auto_approved_at",
            "approved_at",
            "metadata",
            "updated_at"
        ])

        # Notify relevant parties
        try:
            from apps.notifications.models import Notification, NotificationSeverity

            # Notify cost center owner
            if budget.cost_center and budget.cost_center.owner:
                Notification.objects.create(
                    company=budget.company,
                    user=budget.cost_center.owner,
                    title=f"Budget auto-approved: {budget.name}",
                    body=f"Budget was automatically approved at start date",
                    severity=NotificationSeverity.INFO,
                    entity_type="Budget",
                    entity_id=str(budget.id),
                )

            # Notify budget module owners
            perm = SecPermission.objects.filter(code="budgeting_approve_budget").first()
            if perm:
                role_ids = list(SecRolePermission.objects.filter(permission=perm).values_list("role_id", flat=True))
                if role_ids:
                    user_roles = SecUserRole.objects.filter(role_id__in=role_ids)
                    if perm.scope_required:
                        scope_qs = SecScope.objects.filter(scope_type="company", object_id=str(budget.company.id))
                        urs = SecUserRoleScope.objects.filter(scope__in=scope_qs, user_role__in=user_roles)
                        for ur in urs.select_related("user_role", "user_role__user"):
                            approver = ur.user_role.user
                            if approver:
                                Notification.objects.create(
                                    company=budget.company,
                                    user=approver,
                                    title=f"Budget auto-approved: {budget.name}",
                                    body=f"Budget reached start date and was auto-approved",
                                    severity=NotificationSeverity.INFO,
                                    entity_type="Budget",
                                    entity_id=str(budget.id),
                                )
        except Exception:
            pass

        return True

    @staticmethod
    def check_and_auto_approve_budgets():
        """
        Background task to check and auto-approve budgets.
        Should be called periodically (e.g., daily cron job).
        """
        from datetime import date
        today = date.today()

        # Find budgets that should be auto-approved
        budgets_to_approve = Budget.objects.filter(
            auto_approve_if_not_approved=True,
            period_start__lte=today,
        ).exclude(
            status__in={
                Budget.STATUS_APPROVED,
                Budget.STATUS_AUTO_APPROVED,
                Budget.STATUS_ACTIVE,
                Budget.STATUS_EXPIRED,
                Budget.STATUS_CLOSED
            }
        )

        approved_count = 0
        for budget in budgets_to_approve:
            if BudgetAutoApprovalService.auto_approve_budget(budget):
                approved_count += 1

        return {
            "checked": budgets_to_approve.count(),
            "approved": approved_count
        }

    @staticmethod
    def get_budgets_pending_auto_approval(company) -> list:
        """Get budgets that will be auto-approved soon"""
        from datetime import date, timedelta

        today = date.today()
        next_week = today + timedelta(days=7)

        budgets = Budget.objects.filter(
            company=company,
            auto_approve_if_not_approved=True,
            period_start__range=(today, next_week),
        ).exclude(
            status__in={
                Budget.STATUS_APPROVED,
                Budget.STATUS_AUTO_APPROVED,
                Budget.STATUS_ACTIVE,
                Budget.STATUS_EXPIRED,
                Budget.STATUS_CLOSED
            }
        ).select_related("cost_center").order_by("period_start")

        return list(budgets)


class BudgetCloningService:
    """Service for cloning budgets"""

    @staticmethod
    def clone_budget(
        source_budget: Budget,
        new_period_start,
        new_period_end,
        new_name: Optional[str] = None,
        clone_lines: bool = True,
        apply_adjustment_factor: Optional[Decimal] = None,
        user = None
    ) -> Budget:
        """
        Clone a budget to create a new one.

        Args:
            source_budget: The budget to clone from
            new_period_start: Start date for the new budget
            new_period_end: End date for the new budget
            new_name: Optional new name (defaults to source name + " (Copy)")
            clone_lines: Whether to clone budget lines (default True)
            apply_adjustment_factor: Optional multiplier for all values (e.g., 1.1 for 10% increase)
            user: User creating the clone

        Returns:
            The newly created budget
        """
        from django.utils import timezone
        from datetime import timedelta

        # Create new budget with cloned attributes
        new_budget = Budget()

        # Copy basic attributes
        new_budget.company = source_budget.company
        new_budget.cost_center = source_budget.cost_center
        new_budget.budget_type = source_budget.budget_type
        new_budget.name = new_name or f"{source_budget.name} (Copy)"

        # Set new period
        new_budget.period_start = new_period_start
        new_budget.period_end = new_period_end

        # Calculate entry period based on source budget's duration
        if source_budget.entry_start_date and source_budget.entry_end_date:
            entry_duration = (source_budget.entry_end_date - source_budget.entry_start_date).days
            new_budget.entry_start_date = new_period_start
            new_budget.entry_end_date = new_period_start + timedelta(days=entry_duration)

        # Copy duration settings
        new_budget.duration_type = source_budget.duration_type
        new_budget.custom_duration_days = source_budget.custom_duration_days

        # Copy period controls
        new_budget.entry_enabled = source_budget.entry_enabled
        new_budget.grace_period_days = source_budget.grace_period_days
        new_budget.review_enabled = source_budget.review_enabled
        new_budget.budget_impact_enabled = source_budget.budget_impact_enabled

        # Copy auto-approval settings
        new_budget.auto_approve_if_not_approved = source_budget.auto_approve_if_not_approved
        new_budget.auto_approve_by_role = source_budget.auto_approve_by_role

        # Copy other settings
        new_budget.threshold_percent = source_budget.threshold_percent

        # Set status to draft
        new_budget.status = Budget.STATUS_DRAFT
        new_budget.workflow_state = "draft"

        # Set creator
        new_budget.created_by = user

        # Add metadata about cloning
        new_budget.metadata = {
            "cloned_from": str(source_budget.id),
            "cloned_at": str(timezone.now()),
            "cloned_by": user.username if user else None,
            "adjustment_factor": str(apply_adjustment_factor) if apply_adjustment_factor else None
        }

        new_budget.save()

        # Clone budget lines if requested
        if clone_lines:
            for source_line in source_budget.lines.all():
                new_line = BudgetLine()

                # Copy basic attributes
                new_line.budget = new_budget
                new_line.sequence = source_line.sequence
                new_line.procurement_class = source_line.procurement_class
                new_line.item_code = source_line.item_code
                new_line.product = source_line.product
                new_line.item_name = source_line.item_name
                new_line.category = source_line.category
                new_line.project_code = source_line.project_code

                # Copy/adjust quantities and prices
                if apply_adjustment_factor:
                    new_line.qty_limit = source_line.qty_limit * apply_adjustment_factor
                    new_line.value_limit = source_line.value_limit * apply_adjustment_factor
                    new_line.standard_price = source_line.standard_price  # Don't adjust price
                else:
                    new_line.qty_limit = source_line.qty_limit
                    new_line.value_limit = source_line.value_limit
                    new_line.standard_price = source_line.standard_price

                new_line.tolerance_percent = source_line.tolerance_percent
                new_line.budget_owner = source_line.budget_owner
                new_line.is_active = source_line.is_active
                new_line.notes = source_line.notes

                # Initialize original values for variance tracking
                new_line.original_qty_limit = new_line.qty_limit
                new_line.original_unit_price = new_line.standard_price
                new_line.original_value_limit = new_line.value_limit

                # Reset consumption and variance fields
                new_line.consumed_quantity = Decimal("0")
                new_line.consumed_value = Decimal("0")
                new_line.qty_variance = Decimal("0")
                new_line.price_variance = Decimal("0")
                new_line.value_variance = Decimal("0")
                new_line.variance_percent = Decimal("0")

                # Reset review-related fields
                new_line.is_held_for_review = False
                new_line.sent_back_for_review = False
                new_line.moderator_remarks = ""

                new_line.save()

        # Recalculate totals for new budget
        new_budget.recalculate_totals(commit=True)

        return new_budget

    @staticmethod
    def clone_budget_with_variance_analysis(
        source_budget: Budget,
        new_period_start,
        new_period_end,
        use_actual_consumption: bool = False,
        user = None
    ) -> Budget:
        """
        Clone a budget using actual consumption data from the source budget.
        If use_actual_consumption is True, sets new budget limits based on actual consumption.
        """
        adjustment_factor = None

        if use_actual_consumption:
            # Calculate average consumption percentage
            if source_budget.amount > 0:
                consumption_rate = source_budget.consumed / source_budget.amount
                # Use actual consumption as the basis for new budget
                adjustment_factor = consumption_rate

        return BudgetCloningService.clone_budget(
            source_budget=source_budget,
            new_period_start=new_period_start,
            new_period_end=new_period_end,
            new_name=f"{source_budget.name} - Next Period",
            clone_lines=True,
            apply_adjustment_factor=adjustment_factor,
            user=user
        )
