from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db import models
from django.db.models import Count, F, Max, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from django.conf import settings
from django.db import IntegrityError, DatabaseError
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.utils import log_audit_event

from .models import (
    Budget,
    BudgetConsumptionSnapshot,
    BudgetLine,
    BudgetOverrideRequest,
    BudgetUsage,
    CostCenter,
    BudgetItemCode,
    BudgetItemCategory,
    BudgetItemSubCategory,
    BudgetRemarkTemplate,
    BudgetVarianceAudit,
    BudgetApproval,
    BudgetApprovalLine,
)
from .serializers import (
    BudgetLineSerializer,
    BudgetOverrideRequestSerializer,
    BudgetSerializer,
    BudgetSnapshotSerializer,
    BudgetUsageSerializer,
    CostCenterSerializer,
    BudgetItemCodeSerializer,
    BudgetUnitOfMeasureSerializer,
    BudgetItemCategorySerializer,
    BudgetItemSubCategorySerializer,
    BudgetRemarkTemplateSerializer,
    BudgetVarianceAuditSerializer,
    BudgetPricePolicySerializer,
    BudgetApprovalSerializer,
)
from apps.inventory.models import UnitOfMeasure
from difflib import SequenceMatcher
import math
from apps.permissions.permissions import has_permission
from apps.security.services.permission_service import PermissionService
from .services import (
    BudgetApprovalService,
    BudgetNotificationService,
    BudgetPriceService,
    BudgetPermissionService,
    BudgetReviewPeriodService,
    BudgetModeratorService,
    BudgetAutoApprovalService,
    BudgetCloningService,
    BudgetAIService,
    BudgetGamificationService,
)
from apps.procurement.models import PurchaseOrderLine
from apps.inventory.models import Product


class CostCenterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CostCenterSerializer

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = CostCenter.objects.select_related("company", "company_group", "owner", "deputy_owner")
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit_event(
            user=self.request.user,
            company=getattr(self.request, "company", None),
            company_group=getattr(getattr(self.request, "company", None), "company_group", None),
            action="COST_CENTER_CREATED",
            entity_type="CostCenter",
            entity_id=str(instance.id),
            description=f"Cost center {instance.code} created.",
            after=serializer.data,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit_event(
            user=self.request.user,
            company=getattr(self.request, "company", None),
            company_group=getattr(getattr(self.request, "company", None), "company_group", None),
            action="COST_CENTER_UPDATED",
            entity_type="CostCenter",
            entity_id=str(instance.id),
            description=f"Cost center {instance.code} updated.",
            after=serializer.data,
        )


class BudgetViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BudgetSerializer

    def create(self, request, *args, **kwargs):
        company = getattr(request, "company", None)
        if not BudgetPermissionService.user_can_create_budget(request.user, company):
            return Response(
                {"detail": "You do not have permission to create budgets."},
                status=status.HTTP_403_FORBIDDEN
            )

        is_approver = BudgetPermissionService.user_is_budget_name_approver(request.user, company)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # All budgets start as name DRAFT; approvers can immediately approve via queue
        registry_only = not bool(serializer.validated_data.get('cost_center'))
        self.perform_create(serializer)
        instance = serializer.instance
        # Ensure name_status starts as DRAFT
        try:
            if getattr(instance, 'name_status', None) != Budget.NAME_STATUS_DRAFT:
                instance.name_status = Budget.NAME_STATUS_DRAFT
                instance.save(update_fields=["name_status", "updated_at"])
        except Exception:
            pass
        # Issue name approval tasks
        try:
            BudgetApprovalService.request_budget_name_approval(instance)
        except Exception:
            pass

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        user = getattr(self.request, "user", None)
        qs = (
            Budget.objects.select_related("cost_center", "company", "approved_by")
            .prefetch_related("lines")
            .order_by("-period_start")
        )
        # Superusers can see across companies; others scoped to active company
        if company and not getattr(user, "is_superuser", False):
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        company = getattr(self.request, "company", None)
        import logging
        logger = logging.getLogger(__name__)
        try:
            # Company is set in serializer.create via request context; avoid passing twice
            instance = serializer.save()
        except IntegrityError as exc:
            raise serializers.ValidationError({"detail": "A budget already exists for this company, type and period."}) from exc
        except DatabaseError as exc:
            raise serializers.ValidationError({"detail": "Unable to save budget. Please verify the data."}) from exc
        try:
            BudgetNotificationService.notify_budget_created(instance)
        except Exception:
            pass
        # Log state after creation
        try:
            logger.info(f"[BudgetViewSet.perform_create] Created budget id={instance.id} status={instance.status} cost_center={getattr(instance, 'cost_center_id', None)} line_count={getattr(instance, 'lines', None).count() if getattr(instance, 'lines', None) is not None else 'n/a'}")
        except Exception:
            pass
        log_audit_event(
            user=self.request.user,
            company=company,
            company_group=getattr(company, "company_group", None),
            action="BUDGET_CREATED",
            entity_type="Budget",
            entity_id=str(instance.id),
            description=f"Budget {instance.name} created.",
            after=serializer.data,
        )

    def perform_update(self, serializer):
        instance = serializer.save(updated_by=self.request.user)
        log_audit_event(
            user=self.request.user,
            company=getattr(self.request, "company", None),
            company_group=getattr(getattr(self.request, "company", None), "company_group", None),
            action="BUDGET_UPDATED",
            entity_type="Budget",
            entity_id=str(instance.id),
            description=f"Budget {instance.name} updated.",
            after=serializer.data,
        )

    @action(detail=True, methods=["post"])
    def approve_name(self, request, pk=None):
        budget = self.get_object()
        # Permission: only module owner/co-owner or superuser can approve name
        if not BudgetPermissionService.user_is_budget_name_approver(request.user, getattr(budget, 'company', None)):
            return Response({"detail": "You are not allowed to approve budget names."}, status=status.HTTP_403_FORBIDDEN)

        # Approve name (independent from workflow)
        budget.name_status = Budget.NAME_STATUS_APPROVED
        budget.name_approved_by = request.user
        try:
            from django.utils import timezone as dj_tz
            budget.name_approved_at = dj_tz.now()
        except Exception:
            pass
        try:
            budget.save(update_fields=["name_status", "name_approved_by", "name_approved_at", "updated_at"])
        except Exception:
            budget.save()

        # Mark this user's approval as approved
        qs = BudgetApproval.objects.filter(budget=budget, approver_type=BudgetApproval.ApproverType.BUDGET_NAME_APPROVER)
        approval = qs.filter(approver=request.user).first()
        if approval and approval.status == BudgetApproval.Status.PENDING:
            approval.status = BudgetApproval.Status.APPROVED
            approval.decision_date = timezone.now()
            approval.save(update_fields=["status", "decision_date"])

        # Auto-complete remaining pending name-approval tasks for this budget so the queue clears
        pending_others = qs.filter(status=BudgetApproval.Status.PENDING)
        if pending_others.exists():
            pending_others.update(status=BudgetApproval.Status.APPROVED, decision_date=timezone.now())

        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"], url_path="request_name_approval")
    def request_name_approval(self, request, pk=None):
        """
        Ensure budget has pending name-approval tasks.
        Useful if the budget was created in DRAFT by an approver.
        """
        budget = self.get_object()
        try:
            BudgetApprovalService.request_budget_name_approval(budget)
        except Exception:
            pass
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def reject_name(self, request, pk=None):
        budget = self.get_object()
        # Permission: only module owner/co-owner or superuser can reject name
        if not BudgetPermissionService.user_is_budget_name_approver(request.user, getattr(budget, 'company', None)):
            return Response({"detail": "You are not allowed to reject budget names."}, status=status.HTTP_403_FORBIDDEN)
        budget.name_status = Budget.NAME_STATUS_REJECTED
        try:
            budget.save(update_fields=["name_status", "updated_at"])
        except Exception:
            budget.save()

        qs = BudgetApproval.objects.filter(budget=budget, approver_type=BudgetApproval.ApproverType.BUDGET_NAME_APPROVER)
        # Mark this user's task rejected
        approval = qs.filter(approver=request.user).first()
        if approval and approval.status == BudgetApproval.Status.PENDING:
            approval.status = BudgetApproval.Status.REJECTED
            approval.decision_date = timezone.now()
            approval.save(update_fields=["status", "decision_date"])
        # Reject remaining pending tasks
        pending_others = qs.filter(status=BudgetApproval.Status.PENDING)
        if pending_others.exists():
            pending_others.update(status=BudgetApproval.Status.REJECTED, decision_date=timezone.now())

        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        # Backward-compatible submit: move to CC approval per new workflow
        return self.submit_for_approval(request, pk)

    @action(detail=True, methods=["post"])
    def open_entry(self, request, pk=None):
        budget = self.get_object()
        budget.open_entry(user=request.user)
        try:
            BudgetNotificationService.notify_entry_period_started(budget)
        except Exception:
            pass
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def close_entry(self, request, pk=None):
        """Manually disable entry (override) without changing dates or status."""
        budget = self.get_object()
        try:
            # Only toggle the flag; do not change status to preserve workflow
            if hasattr(budget, 'entry_enabled'):
                budget.entry_enabled = False
                budget.save(update_fields=["entry_enabled", "updated_at"])
        except Exception:
            return Response({"detail": "Failed to close entry window"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            BudgetNotificationService.notify_entry_period_ended(budget)
        except Exception:
            pass
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def submit_for_approval(self, request, pk=None):
        budget = self.get_object()
        if budget.status not in {Budget.STATUS_DRAFT, Budget.STATUS_ENTRY_OPEN}:
            return Response({"detail": "Can only submit draft or entry-open budgets."}, status=status.HTTP_400_BAD_REQUEST)
        budget.submit_for_approval(user=request.user)
        BudgetApprovalService.request_cost_center_approvals(budget)
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        # Backward-compatible approve: treat as final approval then activate
        response = self.approve_final(request, pk)
        return response

    @action(detail=True, methods=["post"])
    def approve_cc(self, request, pk=None):
        budget = self.get_object()
        if budget.status not in {Budget.STATUS_PENDING_CC_APPROVAL}:
            return Response({"detail": "Budget is not pending cost center approvals."}, status=status.HTTP_400_BAD_REQUEST)
        # Enforce business rule: CC owner can approve only while entry window (dates) is open (ignore status)
        try:
            today = timezone.now().date()
            es = getattr(budget, 'entry_start_date', None)
            ee = getattr(budget, 'entry_end_date', None)
            enabled = bool(getattr(budget, 'entry_enabled', True))
            if (not enabled) or (es and today < es) or (ee and today > ee):
                return Response({"detail": "Entry period is closed; CC approvals are disabled."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            pass
        from .models import BudgetApproval as BA
        comments = request.data.get("comments", "")
        modifications = request.data.get("modifications", {})
        target_cc_id = request.data.get("cost_center") or request.data.get("cost_center_id")

        # Superuser/system-admin path: allow approving a specific CC task (or the only pending one)
        if getattr(request.user, "is_superuser", False) or getattr(request.user, "is_system_admin", False):
            qs = BA.objects.filter(
                budget=budget,
                approver_type=BA.ApproverType.COST_CENTER_OWNER,
                status=BA.Status.PENDING,
            )
            if target_cc_id:
                qs = qs.filter(cost_center_id=target_cc_id)
            approval = qs.first()
            if not approval:
                return Response({"detail": "No pending CC approval found for the specified cost center."}, status=status.HTTP_400_BAD_REQUEST)
            # Finalize only if all CC items are cleared (approved or sent back)
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
            if cleared:
                approval.status = BA.Status.APPROVED
                approval.comments = comments or ""
                approval.modifications_made = modifications or {}
                approval.approver = request.user
                from django.utils import timezone
                approval.decision_date = timezone.now()
                approval.save(update_fields=["status", "comments", "modifications_made", "approver", "decision_date"])
                budget.status = Budget.STATUS_PENDING_MODERATOR_REVIEW
                budget.save(update_fields=["status", "updated_at"])
            else:
                approval.comments = comments or ""
                approval.modifications_made = modifications or {}
                approval.save(update_fields=["comments", "modifications_made"])  # keep pending
            return Response(self.get_serializer(budget).data)

        # Normal path: owner/deputy resolves approval by user or their CC
        BudgetApprovalService.approve_by_cost_center_owner(
            budget,
            request.user,
            comments,
            modifications,
        )
        # Check if all CC lines are now cleared and advance status if so
        all_cleared = True
        for line in budget.lines.all():
            if (line.metadata or {}).get('cost_center_id') == budget.cost_center_id:
                if not (line.metadata or {}).get('approved') and not line.sent_back_for_review:
                    all_cleared = False
                    break
        if all_cleared:
            budget.status = Budget.STATUS_PENDING_MODERATOR_REVIEW
            budget.save(update_fields=["status", "updated_at"])
            
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def reject_cc(self, request, pk=None):
        budget = self.get_object()
        if budget.status not in {Budget.STATUS_PENDING_CC_APPROVAL}:
            return Response({"detail": "Budget is not pending cost center approvals."}, status=status.HTTP_400_BAD_REQUEST)
        from .models import BudgetApproval as BA
        comments = request.data.get("comments", "")
        target_cc_id = request.data.get("cost_center") or request.data.get("cost_center_id")

        if getattr(request.user, "is_superuser", False) or getattr(request.user, "is_system_admin", False):
            qs = BA.objects.filter(
                budget=budget,
                approver_type=BA.ApproverType.COST_CENTER_OWNER,
                status=BA.Status.PENDING,
            )
            if target_cc_id:
                qs = qs.filter(cost_center_id=target_cc_id)
            approval = qs.first()
            if not approval:
                return Response({"detail": "No pending CC approval found for the specified cost center."}, status=status.HTTP_400_BAD_REQUEST)
            # Reject, send back to entry
            approval.status = BA.Status.REJECTED
            approval.comments = comments or ""
            approval.approver = request.user
            from django.utils import timezone
            approval.decision_date = timezone.now()
            approval.save(update_fields=["status", "comments", "approver", "decision_date"])
            budget.status = Budget.STATUS_ENTRY_OPEN
            budget.save(update_fields=["status", "updated_at"])
            return Response(self.get_serializer(budget).data)

        BudgetApprovalService.reject_by_cost_center_owner(budget, request.user, comments)
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def request_final_approval(self, request, pk=None):
        budget = self.get_object()
        # Allow direct final-approval request for registry-only budgets (no lines)
        try:
            line_count = getattr(budget, "lines", None).count() if getattr(budget, "lines", None) is not None else 0
        except Exception:
            line_count = 0

        if budget.status in {Budget.STATUS_DRAFT, Budget.STATUS_ENTRY_OPEN} and line_count == 0:
            # Bypass CC approval for company-level registry without line items
            BudgetApprovalService.request_final_approval(budget)
            return Response(self.get_serializer(budget).data)

        if budget.status not in {Budget.STATUS_CC_APPROVED}:
            return Response({"detail": "Budget needs CC approval before final approval."}, status=status.HTTP_400_BAD_REQUEST)
        BudgetApprovalService.request_final_approval(budget)
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def approve_final(self, request, pk=None):
        budget = self.get_object()
        if budget.status not in {Budget.STATUS_PENDING_FINAL_APPROVAL}:
            return Response({"detail": "Budget is not pending final approval."}, status=status.HTTP_400_BAD_REQUEST)
        # Permission: superuser or module owner for company
        try:
            from .services import BudgetPermissionService
            is_owner = BudgetPermissionService.user_is_budget_module_owner(request.user, budget.company)
        except Exception:
            is_owner = False
        if not (getattr(request.user, "is_superuser", False) or is_owner):
            return Response({"detail": "Not permitted"}, status=status.HTTP_403_FORBIDDEN)
        BudgetPriceService.approve_by_module_owner(budget, request.user, request.data.get("comments", ""))
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def reject_final(self, request, pk=None):
        budget = self.get_object()
        if budget.status not in {Budget.STATUS_PENDING_FINAL_APPROVAL}:
            return Response({"detail": "Budget is not pending final approval."}, status=status.HTTP_400_BAD_REQUEST)
        # Permission: superuser or module owner for company
        try:
            from .services import BudgetPermissionService
            is_owner = BudgetPermissionService.user_is_budget_module_owner(request.user, budget.company)
        except Exception:
            is_owner = False
        if not (getattr(request.user, "is_superuser", False) or is_owner):
            return Response({"detail": "Not permitted"}, status=status.HTTP_403_FORBIDDEN)
        BudgetPriceService.reject_by_module_owner(budget, request.user, request.data.get("comments", ""))
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        budget = self.get_object()
        budget.mark_active(user=request.user)
        try:
            BudgetNotificationService.notify_budget_active(budget)
        except Exception:
            pass
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        budget = self.get_object()
        budget.close(user=request.user)
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def recalculate(self, request, pk=None):
        budget = self.get_object()
        budget.recalculate_totals(commit=True)
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def compute_forecasts(self, request, pk=None):
        """Compute and persist consumption forecasts for all lines of this budget."""
        budget = self.get_object()
        updated = 0
        for line in budget.lines.all():
            projected, meta = BudgetAIService.forecast_consumption(line)
            if projected is None:
                continue
            line.projected_consumption_value = projected
            line.projected_consumption_confidence = meta.get("confidence")
            line.will_exceed_budget = bool(meta.get("will_exceed_budget"))
            line.save(update_fields=[
                "projected_consumption_value",
                "projected_consumption_confidence",
                "will_exceed_budget",
                "updated_at",
            ])
            updated += 1
        return Response({"updated": updated})

    @action(detail=True, methods=["get"])
    def alerts(self, request, pk=None):
        """Return current budget alerts (utilization threshold and forecast exceed)."""
        budget = self.get_object()
        alerts = BudgetAIService.collect_budget_alerts(budget)
        return Response({"alerts": alerts})

    @action(detail=True, methods=["get"])
    def badges(self, request, pk=None):
        """Return badges earned by this budget."""
        budget = self.get_object()
        badges = BudgetGamificationService.compute_badges_for_budget(budget)
        return Response({"badges": badges})

    @action(detail=False, methods=["get"], url_path="leaderboard")
    def leaderboard(self, request):
        """Company leaderboard ranked by closeness to 100% utilization."""
        company = getattr(request, "company", None)
        limit = request.query_params.get("limit")
        try:
            limit = int(limit) if limit else 10
        except Exception:
            limit = 10
        rows = BudgetGamificationService.leaderboard(company, limit=limit)
        return Response({"results": rows})

    @action(detail=False, methods=["get"], url_path="kpis")
    def kpis(self, request):
        """Company-level gamification KPIs."""
        company = getattr(request, "company", None)
        kpis = BudgetGamificationService.kpis(company)
        return Response(kpis)

    @action(detail=True, methods=["get"])
    def lines(self, request, pk=None):
        budget = self.get_object()
        serializer = BudgetLineSerializer(budget.lines.all(), many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="all_lines")
    def all_lines(self, request, pk=None):
        """
        Return lines for the selected budget limited to cost-center budgets that are
        approved by CC owner (or at a later workflow stage). This aligns the
        moderator dashboard to only surface items that passed CC approval.

        Rules:
        - Identify the declared budget (selected budget if declared, or its parent otherwise)
        - Collect CC child budgets for that declared budget
        - Keep only CC budgets where either:
            a) budget.status in allowed post-CC-approval statuses, OR
            b) declared budget has an approved BudgetApproval record for that cost center
        - Exclude declared budget's own lines to avoid duplicate/unreviewable items
        """
        budget = self.get_object()

        # Determine base declared budget and group
        if getattr(budget, "parent_declared_id", None):
            declared = budget.parent_declared
        else:
            declared = budget

        # Collect CC child budgets under this declared budget
        cc_qs = declared.cc_budgets.all()

        # Build allowed statuses (post CC-approval)
        allowed_statuses = {
            Budget.STATUS_CC_APPROVED,
            Budget.STATUS_PENDING_MODERATOR_REVIEW,
            Budget.STATUS_MODERATOR_REVIEWED,
            Budget.STATUS_PENDING_FINAL_APPROVAL,
            Budget.STATUS_APPROVED,
            Budget.STATUS_AUTO_APPROVED,
            Budget.STATUS_ACTIVE,
        }

        # Resolve approved CCs across declared and all CC budgets via BudgetApproval table
        try:
            from .models import BudgetApproval as BA
            cc_budget_ids = list(cc_qs.values_list("id", flat=True))
            approved_cc_ids = set(
                BA.objects.filter(
                    budget_id__in=[declared.id, *cc_budget_ids],
                    approver_type=BA.ApproverType.COST_CENTER_OWNER,
                    status=BA.Status.APPROVED,
                ).values_list("cost_center_id", flat=True)
            )
        except Exception:
            approved_cc_ids = set()

        # Filter CC budgets by either status or approved record on declared
        cc_allowed_ids = list(
            cc_qs.filter(
                models.Q(status__in=allowed_statuses) | models.Q(cost_center_id__in=list(approved_cc_ids))
            ).values_list("id", flat=True)
        )

        # Build queryset with OR conditions instead of union for DB compatibility
        from django.db.models import Q
        qs = BudgetLine.objects.none()
        cond = Q()
        if cc_allowed_ids:
            cond |= Q(budget_id__in=cc_allowed_ids)
        if approved_cc_ids:
            cond |= Q(budget_id=declared.id, metadata__cost_center_id__in=list(approved_cc_ids))
        if cond:
            qs = BudgetLine.objects.filter(cond)
        else:
            # Fallback: if no approvals data or CC child budgets found, show declared budget lines
            qs = BudgetLine.objects.filter(budget_id=declared.id)
        serializer = BudgetLineSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def start_review_period(self, request, pk=None):
        """Manually start the review period for this budget"""
        budget = self.get_object()

        # Validate budget state
        if budget.status not in {Budget.STATUS_ENTRY_OPEN, Budget.STATUS_ENTRY_CLOSED_REVIEW_PENDING}:
            return Response(
                {"detail": "Can only start review period from entry open or entry closed state."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Enable review period
        success = BudgetReviewPeriodService.transition_to_review_period(budget)

        if not success:
            return Response(
                {"detail": "Cannot start review period. Check entry period dates and grace period."},
                status=status.HTTP_400_BAD_REQUEST
            )

        log_audit_event(
            user=request.user,
            company=budget.company,
            company_group=getattr(budget.company, "company_group", None),
            action="BUDGET_REVIEW_PERIOD_STARTED",
            entity_type="Budget",
            entity_id=str(budget.id),
            description=f"Review period started for {budget.name}"
        )

        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def close_review_period(self, request, pk=None):
        """Manually close the review period for this budget"""
        budget = self.get_object()

        success = BudgetReviewPeriodService.close_review_period(budget)

        if not success:
            return Response(
                {"detail": "Cannot close review period. Review period is not active."},
                status=status.HTTP_400_BAD_REQUEST
            )

        log_audit_event(
            user=request.user,
            company=budget.company,
            company_group=getattr(budget.company, "company_group", None),
            action="BUDGET_REVIEW_PERIOD_CLOSED",
            entity_type="Budget",
            entity_id=str(budget.id),
            description=f"Review period closed for {budget.name}"
        )

        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["get"])
    def review_period_status(self, request, pk=None):
        """Get detailed review period status for this budget"""
        budget = self.get_object()

        # Count sent-back items
        sent_back_count = budget.lines.filter(sent_back_for_review=True).count()
        total_lines = budget.lines.count()
        variance_lines = budget.lines.exclude(value_variance=Decimal("0")).count()

        return Response({
            "is_review_period_active": budget.is_review_period_active(),
            "review_enabled": budget.review_enabled,
            "review_start_date": budget.review_start_date,
            "review_end_date": budget.review_end_date,
            "grace_period_days": budget.grace_period_days,
            "entry_end_date": budget.entry_end_date,
            "calculated_review_start": budget.calculate_review_start_date(),
            "sent_back_items_count": sent_back_count,
            "total_items_count": total_lines,
            "variance_items_count": variance_lines,
            "total_variance_amount": str(budget.total_variance_amount),
            "status": budget.status,
        })

    @action(detail=True, methods=["post"])
    def complete_moderator_review(self, request, pk=None):
        """Mark budget as reviewed by moderator"""
        budget = self.get_object()

        # Check if user is moderator
        if not BudgetPermissionService.user_is_budget_moderator(request.user, budget.company):
            return Response(
                {"detail": "Only moderators can complete review."},
                status=status.HTTP_403_FORBIDDEN
            )

        summary_notes = request.data.get("summary_notes", "")
        success = BudgetModeratorService.complete_moderator_review(
            budget=budget,
            user=request.user,
            summary_notes=summary_notes
        )

        if not success:
            return Response(
                {"detail": "Review period ended; cannot complete review."},
                status=status.HTTP_400_BAD_REQUEST
            )

        log_audit_event(
            user=request.user,
            company=budget.company,
            company_group=getattr(budget.company, "company_group", None),
            action="MODERATOR_REVIEW_COMPLETED",
            entity_type="Budget",
            entity_id=str(budget.id),
            description=f"Moderator review completed for {budget.name}",
            after={"summary_notes": summary_notes}
        )

        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["get"])
    def moderator_review_summary(self, request, pk=None):
        """Get moderator review summary for this budget"""
        budget = self.get_object()
        summary = BudgetModeratorService.get_moderator_review_summary(budget)
        return Response(summary)

    @action(detail=False, methods=["get"])
    def moderator_queue(self, request):
        """Get all budgets pending moderator review"""
        company = getattr(request, "company", None)

        # Allow superusers or moderators
        if not (getattr(request.user, "is_superuser", False) or BudgetPermissionService.user_is_budget_moderator(request.user, company)):
            return Response({"detail": "Only moderators can view the moderation queue."}, status=status.HTTP_403_FORBIDDEN)

        budgets = BudgetModeratorService.get_budgets_pending_moderation(company)
        serializer = self.get_serializer(budgets, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def pending_auto_approval(self, request):
        """Get budgets that will be auto-approved soon"""
        company = getattr(request, "company", None)
        budgets = BudgetAutoApprovalService.get_budgets_pending_auto_approval(company)
        serializer = self.get_serializer(budgets, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def trigger_auto_approval(self, request, pk=None):
        """Manually trigger auto-approval for a budget"""
        budget = self.get_object()

        # Check permission
        if not BudgetPermissionService.user_is_budget_module_owner(request.user, budget.company):
            return Response(
                {"detail": "Only budget module owners can trigger auto-approval."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if budget has auto-approval enabled
        if not budget.auto_approve_if_not_approved:
            return Response(
                {"detail": "Auto-approval is not enabled for this budget."},
                status=status.HTTP_400_BAD_REQUEST
            )

        success = BudgetAutoApprovalService.auto_approve_budget(budget)

        if not success:
            return Response(
                {"detail": "Budget does not meet auto-approval conditions."},
                status=status.HTTP_400_BAD_REQUEST
            )

        log_audit_event(
            user=request.user,
            company=budget.company,
            company_group=getattr(budget.company, "company_group", None),
            action="BUDGET_AUTO_APPROVED",
            entity_type="Budget",
            entity_id=str(budget.id),
            description=f"Budget {budget.name} auto-approved"
        )

        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def clone(self, request, pk=None):
        """
        Clone this budget to create a new one.
        Request body: {
            "new_period_start": "2025-01-01",
            "new_period_end": "2025-12-31",
            "new_name": "Budget 2025" (optional),
            "clone_lines": true (optional, default true),
            "apply_adjustment_factor": 1.1 (optional, e.g., 1.1 for 10% increase),
            "use_actual_consumption": false (optional)
        }
        """
        source_budget = self.get_object()

        # Check permission
        if not BudgetPermissionService.user_can_create_budget(request.user, source_budget.company):
            return Response(
                {"detail": "You do not have permission to create budgets."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Parse request data
        from datetime import datetime
        new_period_start = request.data.get("new_period_start")
        new_period_end = request.data.get("new_period_end")
        new_name = request.data.get("new_name")
        clone_lines = request.data.get("clone_lines", True)
        apply_adjustment_factor = request.data.get("apply_adjustment_factor")
        use_actual_consumption = request.data.get("use_actual_consumption", False)

        if not new_period_start or not new_period_end:
            return Response(
                {"detail": "new_period_start and new_period_end are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse dates
        try:
            new_period_start = datetime.strptime(new_period_start, "%Y-%m-%d").date()
            new_period_end = datetime.strptime(new_period_end, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse adjustment factor if provided
        if apply_adjustment_factor:
            try:
                apply_adjustment_factor = Decimal(str(apply_adjustment_factor))
            except (ValueError, TypeError):
                return Response(
                    {"detail": "Invalid adjustment_factor. Must be a number."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Clone the budget
        if use_actual_consumption:
            new_budget = BudgetCloningService.clone_budget_with_variance_analysis(
                source_budget=source_budget,
                new_period_start=new_period_start,
                new_period_end=new_period_end,
                use_actual_consumption=use_actual_consumption,
                user=request.user
            )
        else:
            new_budget = BudgetCloningService.clone_budget(
                source_budget=source_budget,
                new_period_start=new_period_start,
                new_period_end=new_period_end,
                new_name=new_name,
                clone_lines=clone_lines,
                apply_adjustment_factor=apply_adjustment_factor,
                user=request.user
            )

        log_audit_event(
            user=request.user,
            company=source_budget.company,
            company_group=getattr(source_budget.company, "company_group", None),
            action="BUDGET_CLONED",
            entity_type="Budget",
            entity_id=str(new_budget.id),
            description=f"Budget cloned from '{source_budget.name}' to '{new_budget.name}'",
            after={
                "source_budget_id": str(source_budget.id),
                "new_budget_id": str(new_budget.id),
                "adjustment_factor": str(apply_adjustment_factor) if apply_adjustment_factor else None,
                "use_actual_consumption": use_actual_consumption
            }
        )

        return Response(self.get_serializer(new_budget).data, status=status.HTTP_201_CREATED)


class BudgetLineViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BudgetLineSerializer

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        user = getattr(self.request, "user", None)
        qs = (
            BudgetLine.objects
            .select_related(
                "budget",
                "budget__cost_center",
                "budget_owner",
                "sub_category",
                "budget_item",
                "budget_item__category_ref",
                "budget_item__sub_category_ref",
            )
        )
        if company and not getattr(user, "is_superuser", False):
            qs = qs.filter(budget__company=company)
        # Server-side filters for tighter lookups
        # cost_center: numeric id of CostCenter. Match either per-line metadata or the budget's cost_center.
        cost_center_id = self.request.query_params.get("cost_center")
        if cost_center_id:
            try:
                cid = int(cost_center_id)
                qs = qs.filter(models.Q(metadata__cost_center_id=cid) | models.Q(budget__cost_center_id=cid))
            except (TypeError, ValueError):
                pass

        # budget: filter by a specific budget id
        budget_id = self.request.query_params.get("budget")
        if budget_id:
            try:
                qs = qs.filter(budget_id=int(budget_id))
            except (TypeError, ValueError):
                pass

        # q: free-text search across item_name and item_code
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(models.Q(item_name__icontains=q) | models.Q(item_code__icontains=q))

        # product: inventory product id – approximate match via product name/code
        product_id = self.request.query_params.get("product") or self.request.query_params.get("product_id")
        if product_id:
            try:
                from apps.inventory.models import Product  # local import to avoid circulars
                prod = Product.objects.filter(id=int(product_id)).first()
                if prod:
                    name = (getattr(prod, "name", None) or "").strip()
                    code = (getattr(prod, "code", None) or getattr(prod, "sku", None) or "").strip()
                    cond = models.Q()
                    if name:
                        cond |= models.Q(item_name__icontains=name)
                    if code:
                        cond |= models.Q(item_code__iexact=code)
                    if cond:
                        qs = qs.filter(cond)
            except Exception:
                # ignore bad product id
                pass
        return qs

    @action(detail=False, methods=["get"], url_path="aggregate")
    def aggregate(self, request):
        """
        Aggregate final approved budget quantities for a given item and cost center on a specific date.

        Query params:
          - cost_center (int) required
          - product (int) required (inventory Product id)
          - date (YYYY-MM-DD) optional, defaults to today
        """
        from datetime import datetime
        from decimal import Decimal
        from django.db.models import Sum, Q
        from .models import Budget

        cost_center = request.query_params.get("cost_center")
        product = request.query_params.get("product") or request.query_params.get("product_id")
        item_code_id = request.query_params.get("item_code_id")
        date_str = request.query_params.get("date")
        pid = None
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else timezone.now().date()
        except Exception:
            target_date = timezone.now().date()

        if not cost_center or (not product and not item_code_id):
            return Response({"detail": "cost_center and one of product or item_code_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cid = int(cost_center)
        except (TypeError, ValueError):
            return Response({"detail": "Invalid cost_center."}, status=status.HTTP_400_BAD_REQUEST)

        qs = self.get_queryset()

        # Filter to relevant cost center lines (either line metadata or budget's cost center)
        qs = qs.filter(
            Q(budget__cost_center_id=cid) |
            Q(metadata__cost_center_id=cid)
        )

        allowed_statuses = [
            getattr(Budget, "STATUS_AUTO_APPROVED", "AUTO_APPROVED"),
            getattr(Budget, "STATUS_APPROVED", "APPROVED"),
            getattr(Budget, "STATUS_ACTIVE", "ACTIVE"),
        ]
        qs = qs.filter(
            budget__status__in=allowed_statuses,
            budget__period_start__lte=target_date,
            budget__period_end__gte=target_date,
        )
        qs = qs.filter(final_decision=BudgetLine.FinalDecision.APPROVED)

        if item_code_id:
            try:
                bic = BudgetItemCode.objects.filter(id=int(item_code_id)).first()
                if bic:
                    qs = qs.filter(item_code__iexact=bic.code)
            except Exception:
                pass
        elif product:
            try:
                pid = int(product)
                from apps.inventory.models import Product as InvProduct
                prod = InvProduct.objects.filter(id=pid).first()
                if prod:
                    name = (getattr(prod, "name", None) or "").strip()
                    code = (getattr(prod, "code", None) or getattr(prod, "sku", None) or "").strip()
                    cond = Q()
                    if name:
                        cond |= Q(item_name__icontains=name)
                    if code:
                        cond |= Q(item_code__iexact=code)
                    if cond:
                        qs = qs.filter(cond)
            except Exception:
                pass

        agg = qs.aggregate(
            total_qty=Sum("qty_limit"),
            total_used=Sum("consumed_quantity"),
        )
        total_qty = agg.get("total_qty") or Decimal("0")
        total_used = agg.get("total_used") or Decimal("0")
        remaining = total_qty - total_used

        bic_for_uom = None
        if item_code_id:
            try:
                bic_for_uom = BudgetItemCode.objects.select_related("uom").filter(id=int(item_code_id)).first()
            except Exception:
                bic_for_uom = None

        uom_label = ""
        try:
            first_line = qs.order_by("id").select_related("budget_item").first()
            if first_line:
                if getattr(first_line, "budget_item", None) and getattr(first_line.budget_item, "unit_of_measure", None):
                    uom_label = getattr(first_line.budget_item.unit_of_measure, "name", None) or getattr(first_line.budget_item.unit_of_measure, "code", "")
                if not uom_label:
                    meta = getattr(first_line, "metadata", {}) or {}
                    uom_label = meta.get("uom_name") or meta.get("uom_code") or meta.get("uom") or ""
                if not uom_label:
                    source_item = bic_for_uom
                    if not source_item and first_line.item_code:
                        company_group_id = getattr(getattr(first_line.budget, "company", None), "company_group_id", None)
                        item_code_qs = BudgetItemCode.objects.select_related("uom").filter(code=first_line.item_code)
                        if company_group_id:
                            item_code_qs = item_code_qs.filter(
                                Q(company__company_group_id=company_group_id) |
                                Q(company_group_id=company_group_id)
                            )
                        source_item = item_code_qs.first()
                    if source_item and getattr(source_item, "uom", None):
                        uom_label = getattr(source_item.uom, "name", None) or getattr(source_item.uom, "code", "")
        except Exception:
            uom_label = ""

        if not uom_label and bic_for_uom and getattr(bic_for_uom, "uom", None):
            uom_label = getattr(bic_for_uom.uom, "name", None) or getattr(bic_for_uom.uom, "code", "")

        return Response({
            "date": target_date.isoformat(),
            "cost_center": cid,
            "product": pid,
            "approved_quantity": float(total_qty),
            "consumed_quantity": float(total_used),
            "remaining_quantity": float(remaining),
            "uom": uom_label,
        })

    def perform_create(self, serializer):
        budget = serializer.validated_data["budget"]
        if getattr(self.request, "company", None) and budget.company != self.request.company:
            raise serializers.ValidationError("Budget does not belong to the active company.")
        # Enforce name approval prior to entry
        try:
            if getattr(budget, 'name_status', None) and budget.name_status != Budget.NAME_STATUS_APPROVED:
                raise serializers.ValidationError("Budget name is not approved.")
        except Exception:
            pass
        # Entry period enforcement: allow create only during entry window by authorized users
        if not budget.is_entry_period_active():
            raise serializers.ValidationError("Entry period is not active for this budget.")
        user = getattr(self.request, "user", None)
        cc = budget.cost_center
        if cc is None:
            # Company-wide budget: require company-level permission
            if not PermissionService.user_has_permission(user, "budgeting_manage_budget_plan", f"company:{budget.company_id}"):
                raise serializers.ValidationError("You are not allowed to enter lines for this company budget.")
        else:
            # Cost-center budget: owner/deputy/entry-users
            if not (
                (cc.owner_id and user and user.id == cc.owner_id)
                or (cc.deputy_owner_id and user and user.id == cc.deputy_owner_id)
                or cc.budget_entry_users.filter(id=getattr(user, 'id', None)).exists()
            ):
                raise serializers.ValidationError("You are not allowed to enter budget lines for this cost center.")
        # Derive procurement_class from budget type if not provided
        pc = serializer.validated_data.get("procurement_class")
        if not pc:
            try:
                bt = getattr(budget, 'budget_type', None)
                from .models import Budget as _Budget, BudgetLine as _BudgetLine
                pc_map = {
                    getattr(_Budget, 'TYPE_OPEX', 'opex'): _BudgetLine.ProcurementClass.SERVICE_ITEM,
                    getattr(_Budget, 'TYPE_CAPEX', 'capex'): _BudgetLine.ProcurementClass.CAPEX_ITEM,
                }
                serializer.validated_data["procurement_class"] = pc_map.get(bt, _BudgetLine.ProcurementClass.STOCK_ITEM)
            except Exception:
                pass
        sequence = serializer.validated_data.get("sequence")
        if not sequence:
            max_seq = budget.lines.aggregate(max_sequence=Max("sequence")).get("max_sequence") or 0
            serializer.validated_data["sequence"] = max_seq + 1
        instance = serializer.save()
        budget.recalculate_totals(commit=True)
        log_audit_event(
            user=self.request.user,
            company=budget.company,
            company_group=getattr(budget.company, "company_group", None),
            action="BUDGET_LINE_CREATED",
            entity_type="BudgetLine",
            entity_id=str(instance.id),
            description=f"Budget line {instance.item_name} added to {budget.name}.",
            after=BudgetLineSerializer(instance).data,
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        budget = instance.budget
        user = self.request.user

        # Determine editing windows
        # Allow edits during entry period regardless of status, for permitted users.
        editable = budget.status in {Budget.STATUS_DRAFT, Budget.STATUS_ENTRY_OPEN}
        if not editable and budget.is_entry_period_active():
            # Check entry permissions similar to perform_create
            cc = getattr(budget, 'cost_center', None)
            if not cc:
                # Company-wide: require company-level permission
                try:
                    if PermissionService.user_has_permission(user, "budgeting_manage_budget_plan", f"company:{budget.company_id}"):
                        editable = True
                except Exception:
                    editable = False
                # Fallback: if user holds a pending CC approval task for this budget and this line's CC, allow edit
                if not editable:
                    try:
                        from .models import BudgetApproval as BA
                        meta = getattr(instance, 'metadata', {}) or {}
                        cc_id = meta.get('cost_center_id')
                        if cc_id:
                            has_task = BA.objects.filter(
                                budget=budget,
                                approver_type=BA.ApproverType.COST_CENTER_OWNER,
                                status=BA.Status.PENDING,
                                cost_center_id=cc_id,
                            ).filter(
                                models.Q(approver=user) | models.Q(cost_center__owner=user) | models.Q(cost_center__deputy_owner=user)
                            ).exists()
                            if has_task:
                                editable = True
                    except Exception:
                        pass
            else:
                try:
                    if (
                        (cc.owner_id and user.id == cc.owner_id)
                        or (cc.deputy_owner_id and user.id == cc.deputy_owner_id)
                        or cc.budget_entry_users.filter(id=user.id).exists()
                    ):
                        editable = True
                except Exception:
                    editable = False
        cc_owner_window = False
        if budget.status == Budget.STATUS_PENDING_CC_APPROVAL:
            if getattr(user, 'is_superuser', False) or getattr(user, 'is_system_admin', False):
                cc_owner_window = True
            else:
                cc = getattr(budget, 'cost_center', None)
                if not cc:
                    try:
                        meta = getattr(instance, 'metadata', {}) or {}
                        cc_id = meta.get('cost_center_id')
                        if cc_id:
                            cc = CostCenter.objects.filter(pk=cc_id).first()
                    except Exception:
                        cc = None
                # Allow cost center owner/deputy to edit
                if cc and (cc.owner_id == getattr(user, 'id', None) or cc.deputy_owner_id == getattr(user, 'id', None)):
                    cc_owner_window = True
                else:
                    # Fallback: allow user who holds the pending CC approval task
                    try:
                        from .models import BudgetApproval as BA
                        has_task = BA.objects.filter(
                            budget=budget,
                            approver_type=BA.ApproverType.COST_CENTER_OWNER,
                            status=BA.Status.PENDING,
                        ).filter(
                            models.Q(approver=user) |
                            models.Q(cost_center__owner=user) |
                            models.Q(cost_center__deputy_owner=user)
                        ).exists()
                        if has_task:
                            cc_owner_window = True
                    except Exception:
                        pass
        final_approver_window = (
            budget.status == Budget.STATUS_PENDING_FINAL_APPROVAL
            and (
                getattr(user, 'is_superuser', False)
                or getattr(user, 'is_system_admin', False)
                or BudgetPermissionService.user_is_budget_module_owner(user, budget.company)
            )
        )

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"budget.status: {budget.status}")
        logger.info(f"user.is_superuser: {getattr(user, 'is_superuser', False)}")
        logger.info(f"editable: {editable}")
        logger.info(f"cc_owner_window: {cc_owner_window}")
        logger.info(f"final_approver_window: {final_approver_window}")

        if cc_owner_window or editable or final_approver_window:
            # If review period is active and NOT a CC-owner window, apply variance tracking
            if budget.is_review_period_active() and not cc_owner_window and not editable:
                validated_data = serializer.validated_data
                new_qty = validated_data.get("qty_limit")
                new_price = validated_data.get("standard_price")
                new_value = validated_data.get("value_limit")
                reason = validated_data.get("modification_reason", "Updated during review period")

                instance = BudgetReviewPeriodService.update_budget_line_with_variance_tracking(
                    budget_line=instance,
                    user=user,
                    new_qty=new_qty,
                    new_price=new_price,
                    new_value=new_value,
                    reason=reason,
                    role="cc_owner",
                    metadata=serializer.validated_data.get('metadata')
                )
            else:
                instance = serializer.save()
            budget.recalculate_totals(commit=True)
            return

        raise serializers.ValidationError("This budget is not editable in its current status.")

    def perform_destroy(self, instance):
        budget = instance.budget
        user = self.request.user
        editable = budget.status in {Budget.STATUS_DRAFT, Budget.STATUS_ENTRY_OPEN}
        cc_owner_window = False
        if budget.status == Budget.STATUS_PENDING_CC_APPROVAL:
            if getattr(user, 'is_superuser', False) or getattr(user, 'is_system_admin', False):
                cc_owner_window = True
            else:
                cc = getattr(budget, 'cost_center', None)
                if not cc:
                    try:
                        meta = getattr(instance, 'metadata', {}) or {}
                        cc_id = meta.get('cost_center_id')
                        if cc_id:
                            cc = CostCenter.objects.filter(pk=cc_id).first()
                    except Exception:
                        cc = None
                if cc and (cc.owner_id == getattr(user, 'id', None) or cc.deputy_owner_id == getattr(user, 'id', None)):
                    cc_owner_window = True
                else:
                    try:
                        from .models import BudgetApproval as BA
                        has_task = BA.objects.filter(
                            budget=budget,
                            approver_type=BA.ApproverType.COST_CENTER_OWNER,
                            status=BA.Status.PENDING,
                        ).filter(
                            models.Q(approver=user) |
                            models.Q(cost_center__owner=user) |
                            models.Q(cost_center__deputy_owner=user)
                        ).exists()
                        if has_task:
                            cc_owner_window = True
                    except Exception:
                        pass
        final_approver_window = (
            budget.status == Budget.STATUS_PENDING_FINAL_APPROVAL
            and (
                getattr(user, 'is_superuser', False)
                or getattr(user, 'is_system_admin', False)
                or BudgetPermissionService.user_is_budget_module_owner(user, budget.company)
            )
        )

        if not (editable or cc_owner_window or final_approver_window):
            raise serializers.ValidationError("This budget is not editable in its current status.")
        instance.delete()

    @action(detail=True, methods=["post"])
    def send_back_for_review(self, request, pk=None):
        """
        Mark this budget line item as sent back for review.
        This allows CC owners to edit it during review period.
        """
        budget_line = self.get_object()
        reason = request.data.get("reason", "")

        success = BudgetReviewPeriodService.send_item_back_for_review(
            budget_line=budget_line,
            user=request.user,
            reason=reason
        )

        if not success:
            return Response(
                {"detail": "Cannot send back item in current budget status."},
                status=status.HTTP_400_BAD_REQUEST
            )

        log_audit_event(
            user=request.user,
            company=budget_line.budget.company,
            company_group=getattr(budget_line.budget.company, "company_group", None),
            action="BUDGET_LINE_SENT_BACK_FOR_REVIEW",
            entity_type="BudgetLine",
            entity_id=str(budget_line.id),
            description=f"Budget line '{budget_line.item_name}' sent back for review",
            after={"reason": reason}
        )

        return Response(BudgetLineSerializer(budget_line, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def can_edit_in_review(self, request, pk=None):
        """Check if this budget line can be edited during review period"""
        budget_line = self.get_object()
        can_edit, reason = BudgetReviewPeriodService.can_edit_budget_line_in_review_period(
            budget_line, request.user
        )
        return Response({
            "can_edit": can_edit,
            "reason": reason,
            "is_review_period_active": budget_line.budget.is_review_period_active(),
            "sent_back_for_review": budget_line.sent_back_for_review
        })

    @action(detail=True, methods=["post"])
    def add_moderator_remark(self, request, pk=None):
        """
        Add moderator remark to this budget line.
        Moderators can add remarks to guide CC owners.
        """
        budget_line = self.get_object()
        remark_text = request.data.get("remark_text", "")
        remark_template_id = request.data.get("remark_template_id")

        if not remark_text:
            return Response(
                {"detail": "Remark text is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user is moderator
        if not BudgetPermissionService.user_is_budget_moderator(request.user, budget_line.budget.company):
            return Response(
                {"detail": "Only moderators can add remarks."},
                status=status.HTTP_403_FORBIDDEN
            )

        updated_line = BudgetModeratorService.add_remark_to_line(
            budget_line=budget_line,
            user=request.user,
            remark_text=remark_text,
            remark_template_id=remark_template_id
        )

        log_audit_event(
            user=request.user,
            company=budget_line.budget.company,
            company_group=getattr(budget_line.budget.company, "company_group", None),
            action="MODERATOR_REMARK_ADDED",
            entity_type="BudgetLine",
            entity_id=str(budget_line.id),
            description=f"Moderator remark added to '{budget_line.item_name}'",
            after={"remark": remark_text}
        )

        return Response(BudgetLineSerializer(updated_line, context={"request": request}).data)

    @action(detail=False, methods=["post"])
    def batch_add_remarks(self, request):
        """
        Add the same remark to multiple budget lines at once.
        Request body: {
            "budget_line_ids": [1, 2, 3],
            "remark_text": "...",
            "remark_template_id": 123  (optional)
        }
        """
        company = getattr(request, "company", None)

        # Check if user is moderator
        if not BudgetPermissionService.user_is_budget_moderator(request.user, company):
            return Response(
                {"detail": "Only moderators can add batch remarks."},
                status=status.HTTP_403_FORBIDDEN
            )

        budget_line_ids = request.data.get("budget_line_ids", [])
        remark_text = request.data.get("remark_text", "")
        remark_template_id = request.data.get("remark_template_id")

        if not budget_line_ids or not remark_text:
            return Response(
                {"detail": "budget_line_ids and remark_text are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = BudgetModeratorService.batch_add_remarks(
            budget_line_ids=budget_line_ids,
            user=request.user,
            remark_text=remark_text,
            remark_template_id=remark_template_id
        )

        log_audit_event(
            user=request.user,
            company=company,
            company_group=getattr(company, "company_group", None),
            action="BATCH_MODERATOR_REMARKS_ADDED",
            entity_type="BudgetLine",
            entity_id="multiple",
            description=f"Batch remarks added to {result['success_count']} items",
            after=result
        )

        return Response(result)

    @action(detail=False, methods=["post"])
    def batch_send_back_for_review(self, request):
        """
        Send multiple budget lines back for review at once.
        Request body: {
            "budget_line_ids": [1, 2, 3],
            "reason": "..."
        }
        """
        company = getattr(request, "company", None)

        # Check if user is moderator or has appropriate permission
        if not BudgetPermissionService.user_is_budget_moderator(request.user, company):
            return Response(
                {"detail": "Only moderators can send items back for review."},
                status=status.HTTP_403_FORBIDDEN
            )

        budget_line_ids = request.data.get("budget_line_ids", [])
        reason = request.data.get("reason", "")

        if not budget_line_ids:
            return Response(
                {"detail": "budget_line_ids is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = BudgetModeratorService.batch_send_back_for_review(
            budget_line_ids=budget_line_ids,
            user=request.user,
            reason=reason
        )

        log_audit_event(
            user=request.user,
            company=company,
            company_group=getattr(company, "company_group", None),
            action="BATCH_ITEMS_SENT_BACK_FOR_REVIEW",
            entity_type="BudgetLine",
            entity_id="multiple",
            description=f"Batch sent back {result['success_count']} items for review",
            after=result
        )

        return Response(result)

    @action(detail=False, methods=["post"], url_path="batch_moderator_approve")
    def batch_moderator_approve(self, request):
        """
        Approve multiple budget lines as a moderator.
        Request body: { "budget_line_ids": [1, 2, 3] }
        """
        company = getattr(request, "company", None)
        user = request.user

        if not BudgetPermissionService.user_is_budget_moderator(user, company):
            return Response(
                {"detail": "Only moderators can approve lines."},
                status=status.HTTP_403_FORBIDDEN
            )

        budget_line_ids = request.data.get("budget_line_ids", [])
        if not budget_line_ids:
            return Response({"detail": "budget_line_ids are required."}, status=status.HTTP_400_BAD_REQUEST)

        lines_to_approve = BudgetLine.objects.filter(id__in=budget_line_ids)
        
        # Verify all lines belong to the moderator's company
        for line in lines_to_approve:
            if line.budget.company != company:
                return Response({"detail": "You can only approve lines within your company."}, status=status.HTTP_403_FORBIDDEN)

        updated_count = 0
        for line in lines_to_approve:
            metadata = line.metadata or {}
            metadata['moderator_approved'] = True
            line.metadata = metadata
            line.save(update_fields=["metadata"])
            updated_count += 1

        return Response({"detail": f"{updated_count} lines approved by moderator."})

    @action(detail=False, methods=["post"])
    def batch_apply_template_to_category(self, request):
        """
        Apply a remark template to all budget lines in a specific category.
        Request body: {
            "budget_id": 123,
            "category": "OPEX",
            "remark_template_id": 456
        }
        """
        company = getattr(request, "company", None)

        # Check if user is moderator
        if not BudgetPermissionService.user_is_budget_moderator(request.user, company):
            return Response(
                {"detail": "Only moderators can apply batch templates."},
                status=status.HTTP_403_FORBIDDEN
            )

        budget_id = request.data.get("budget_id")
        category = request.data.get("category")
        remark_template_id = request.data.get("remark_template_id")

        if not all([budget_id, category, remark_template_id]):
            return Response(
                {"detail": "budget_id, category, and remark_template_id are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = BudgetModeratorService.batch_apply_template_to_category(
            budget_id=budget_id,
            category=category,
            user=request.user,
            remark_template_id=remark_template_id
        )

        log_audit_event(
            user=request.user,
            company=company,
            company_group=getattr(company, "company_group", None),
            action="BATCH_TEMPLATE_APPLIED_TO_CATEGORY",
            entity_type="Budget",
            entity_id=str(budget_id),
            description=f"Template applied to category '{category}' - {result['success_count']} items",
            after=result
        )

        return Response(result)


class BudgetUsageViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BudgetUsageSerializer

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = BudgetUsage.objects.select_related("budget_line", "budget_line__budget", "created_by")
        if company:
            qs = qs.filter(budget_line__budget__company=company)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        budget = instance.budget_line.budget
        log_audit_event(
            user=self.request.user,
            company=budget.company,
            company_group=getattr(budget.company, "company_group", None),
            action="BUDGET_USAGE_RECORDED",
            entity_type="BudgetUsage",
            entity_id=str(instance.id),
            description=f"Usage recorded against {instance.budget_line.item_name}",
            after=serializer.data,
        )


class BudgetOverrideRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BudgetOverrideRequestSerializer

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = BudgetOverrideRequest.objects.select_related(
            "cost_center",
            "budget_line",
            "requested_by",
            "approver",
        )
        if company:
            qs = qs.filter(company=company)
        return qs

    @action(detail=True, methods=["get"], url_path="price_prediction")
    def price_prediction(self, request, pk=None):
        """Predict price for this budget line's item_code using PO history and policy."""
        line = self.get_object()
        item_code = line.item_code
        if not item_code:
            return Response({"detail": "Line has no item_code to predict."}, status=status.HTTP_400_BAD_REQUEST)
        price, meta = BudgetAIService.predict_price(line.budget.company, item_code)
        if price is None:
            return Response({"detail": "No data for price prediction."}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            "predicted_price": str(price),
            **meta,
        })

    @action(detail=True, methods=["get"], url_path="consumption_forecast")
    def consumption_forecast(self, request, pk=None):
        """Forecast consumption for this line based on current run rate."""
        line = self.get_object()
        projected, meta = BudgetAIService.forecast_consumption(line)
        if projected is None:
            return Response({"detail": "Insufficient data to forecast."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "projected_consumption_value": str(projected),
            **meta,
        })

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        override = self.get_object()
        if override.status != BudgetOverrideRequest.STATUS_PENDING:
            return Response({"detail": "Override already processed."}, status=status.HTTP_400_BAD_REQUEST)
        override.mark(BudgetOverrideRequest.STATUS_APPROVED, user=request.user, notes=request.data.get("notes", ""))
        log_audit_event(
            user=request.user,
            company=override.company,
            company_group=getattr(override.company, "company_group", None),
            action="BUDGET_OVERRIDE_APPROVED",
            entity_type="BudgetOverrideRequest",
            entity_id=str(override.id),
            description=f"Override for {override.requested_amount} approved.",
        )
        return Response(self.get_serializer(override).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        override = self.get_object()
        if override.status != BudgetOverrideRequest.STATUS_PENDING:
            return Response({"detail": "Override already processed."}, status=status.HTTP_400_BAD_REQUEST)
        override.mark(BudgetOverrideRequest.STATUS_REJECTED, user=request.user, notes=request.data.get("notes", ""))
        log_audit_event(
            user=request.user,
            company=override.company,
            company_group=getattr(override.company, "company_group", None),
            action="BUDGET_OVERRIDE_REJECTED",
            entity_type="BudgetOverrideRequest",
            entity_id=str(override.id),
            description="Override request rejected.",
        )
        return Response(self.get_serializer(override).data)


class BudgetAvailabilityCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cost_center_id = request.data.get("cost_center")
        amount = request.data.get("amount")
        procurement_class = request.data.get("procurement_class")
        if not cost_center_id or amount is None:
            return Response({"detail": "cost_center and amount required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(amount))
        except Exception:
            return Response({"detail": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cost_center = CostCenter.objects.get(pk=cost_center_id)
        except CostCenter.DoesNotExist:
            return Response({"detail": "Cost center not found"}, status=status.HTTP_404_NOT_FOUND)

        today = timezone.now().date()
        budget_filter = {
            "cost_center": cost_center,
            "period_start__lte": today,
            "period_end__gte": today,
            "status__in": [Budget.STATUS_ACTIVE, Budget.STATUS_APPROVED],
        }
        line_filters = {"budget__cost_center": cost_center, "budget__status__in": [Budget.STATUS_ACTIVE, Budget.STATUS_APPROVED]}
        if procurement_class:
            line_filters["procurement_class"] = procurement_class
            budget_filter["lines__procurement_class"] = procurement_class

        active_budgets = Budget.objects.filter(**budget_filter).distinct()
        if not active_budgets.exists():
            return Response({"available": False, "reason": "No active budget found"})

        line_totals = (
            BudgetLine.objects.filter(**line_filters, budget__in=active_budgets)
            .aggregate(
                total_limit=Coalesce(Sum("value_limit"), Decimal("0")),
                total_consumed=Coalesce(Sum("consumed_value"), Decimal("0")),
            )
        )

        total_limit = line_totals.get("total_limit", Decimal("0"))
        total_consumed = line_totals.get("total_consumed", Decimal("0"))
        available_value = total_limit - total_consumed

        return Response(
            {
                "available": available_value >= amount,
                "available_amount": f"{available_value}",
                "requested": f"{amount}",
            }
        )


class BudgetWorkspaceSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, "company", None)
        budgets = Budget.objects.select_related("cost_center").prefetch_related("lines")
        overrides = BudgetOverrideRequest.objects.select_related("cost_center", "requested_by")
        cost_centers = CostCenter.objects.all()
        if company:
            budgets = budgets.filter(company=company)
            overrides = overrides.filter(company=company)
            cost_centers = cost_centers.filter(company=company)

        budgets_by_status = budgets.values("status").annotate(count=Count("id"), total=Sum("amount"))
        status_map = {row["status"]: {"count": row["count"], "total": row["total"] or Decimal("0")} for row in budgets_by_status}

        active_lines = BudgetLine.objects.filter(budget__in=budgets)
        line_stats = []
        for line in active_lines:
            limit = line.value_limit or Decimal("0")
            consumed = line.consumed_value or Decimal("0")
            utilisation = (consumed / limit * Decimal("100")) if limit else Decimal("0")
            line_stats.append((utilisation, line))
        line_stats.sort(key=lambda item: item[0], reverse=True)
        top_variances = [entry[1] for entry in line_stats[:5]]

        pending_overrides = overrides.filter(status=BudgetOverrideRequest.STATUS_PENDING).order_by("-created_at")[:5]

        response = {
            "cost_center_count": cost_centers.count(),
            "budget_count": budgets.count(),
            "budgets_by_status": status_map,
            "pending_override_count": overrides.filter(status=BudgetOverrideRequest.STATUS_PENDING).count(),
            "pending_overrides": BudgetOverrideRequestSerializer(pending_overrides, many=True).data,
            "top_variances": [
                {
                    "line_id": line.id,
                    "budget": line.budget.name,
                    "item_name": line.item_name,
                    "consumed_value": float(line.consumed_value),
                    "value_limit": float(line.value_limit),
                    "utilisation_percent": float(
                        (line.consumed_value / line.value_limit * 100) if line.value_limit else 0
                    ),
                }
                for line in top_variances
            ],
        }
        return Response(response)


class BudgetSnapshotViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BudgetSnapshotSerializer

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = BudgetConsumptionSnapshot.objects.select_related("budget", "budget__cost_center")
        if company:
            qs = qs.filter(budget__company=company)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        budget = instance.budget
        log_audit_event(
            user=self.request.user,
            company=budget.company,
            company_group=getattr(budget.company, "company_group", None),
            action="BUDGET_SNAPSHOT_CREATED",
            entity_type="BudgetConsumptionSnapshot",
            entity_id=str(instance.id),
            description=f"Snapshot captured for {budget.name}",
        )


class BudgetItemCodeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BudgetItemCodeSerializer

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = BudgetItemCode.objects.select_related("company", "uom", "category_ref", "sub_category_ref").order_by('code')
        if company and getattr(company, 'company_group_id', None):
            # Group-scoped: share item codes across companies in the same group
            qs = qs.filter(company_group_id=company.company_group_id)
        elif company:
            # Fallback for items that might not be in a group
            qs = qs.filter(company=company)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        # Optional simple search by code/name
        q = request.query_params.get('q')
        if q:
            qs = qs.filter(models.Q(code__icontains=q) | models.Q(name__icontains=q))
        try:
            limit = int(request.query_params.get('limit') or 1000)
        except Exception:
            limit = 1000
        serializer = self.get_serializer(qs[:limit], many=True)
        return Response({"results": serializer.data})

    def perform_create(self, serializer):
        serializer.save()

    def create(self, request, *args, **kwargs):
        # Permission check: creating item codes requires budgeting_manage_item_codes
        company = getattr(request, "company", None)
        if not has_permission(request.user, 'budgeting_manage_item_codes', company):
            return Response({"detail": "Missing permission: budgeting_manage_item_codes"}, status=status.HTTP_403_FORBIDDEN)
        # Similarity suggestions before creating item code
        try:
            code = (request.data.get('code') or '').strip()
            name = (request.data.get('name') or '').strip()
            force = (str(request.query_params.get('force') or request.data.get('force') or '')).lower() in {'1','true','yes','on'}
            # Suggestion engine configuration
            suggest_cfg = getattr(settings, 'BUDGETING_ITEM_CODE_SUGGESTIONS', {})
            suggest_enabled = bool(suggest_cfg.get('enabled', True))
            use_embeddings = bool(suggest_cfg.get('use_embeddings', True))
            embed_threshold = float(suggest_cfg.get('embedding_threshold', 0.70))
            fuzzy_threshold = float(suggest_cfg.get('fuzzy_threshold', 0.50))
            candidate_limit = int(suggest_cfg.get('candidate_limit', 200))
            results_limit = int(suggest_cfg.get('results_limit', 5))

            if suggest_enabled and company and (code or name) and not force:
                qs = BudgetItemCode.objects.all()
                if getattr(company, 'company_group_id', None):
                    qs = qs.filter(company__company_group_id=company.company_group_id)
                else:
                    qs = qs.filter(company=company)

                # Strict duplicate on NAME: block create unless force is set
                if name and qs.filter(name__iexact=name).exists():
                    return Response({
                        "detail": "An item code with this name already exists for your company group.",
                        "name": ["duplicate"],
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Preselect candidate pool (prefer name match; code may be empty)
                criteria = models.Q()
                if name:
                    criteria |= models.Q(name__icontains=name)
                if code:
                    criteria |= models.Q(code__icontains=code)
                candidates = list(qs.filter(criteria)[:candidate_limit]) if (name or code) else []
                # If no substring candidates (e.g., typos), sample a small set for fuzzy matching
                if not candidates:
                    candidates = list(qs[:candidate_limit])

                # Try vector similarity first (if AI embeddings are available)
                similar = []
                try:
                    from apps.ai_companion.services.ai_service_v2 import ai_service_v2  # local import
                    emb = getattr(ai_service_v2, 'embeddings', None)
                    if emb is None and hasattr(ai_service_v2, '_ensure_ready'):
                        try:
                            ai_service_v2._ensure_ready(require_generator=False)
                            emb = getattr(ai_service_v2, 'embeddings', None)
                        except Exception:
                            emb = None
                    if emb is not None and use_embeddings:
                        query_text = f"{code} {name}".strip()
                        qv = emb.embed_query(query_text)
                        # cosine similarity helper
                        def _cos(a, b):
                            da = math.sqrt(sum(x*x for x in a)) or 1.0
                            db = math.sqrt(sum(x*x for x in b)) or 1.0
                            return sum(x*y for x, y in zip(a, b)) / (da * db)
                        cand_texts = [f"{(c.code or '').strip()} {(c.name or '').strip()}".strip() for c in candidates]
                        dvs = emb.embed_documents(cand_texts)
                        sims = [(_cos(qv, dv), c) for dv, c in zip(dvs, candidates)]
                        # threshold tuned for embeddings (higher than fuzzy)
                        sims = [(s, c) for s, c in sims if s >= embed_threshold]
                        sims.sort(key=lambda t: t[0], reverse=True)
                        similar = [{"id": c.id, "code": c.code, "name": c.name, "uom": getattr(c.uom, 'name', None)} for s, c in sims[:results_limit]]
                except Exception:
                    similar = []

                # Fallback to fuzzy if no vector result
                if not similar and candidates:
                    scored = []
                    for c in candidates:
                        score_code = SequenceMatcher(a=code.lower(), b=(c.code or '').lower()).ratio() if code else 0
                        score_name = SequenceMatcher(a=name.lower(), b=(c.name or '').lower()).ratio() if name else 0
                        score = max(score_code, score_name)
                        if score >= fuzzy_threshold:
                            scored.append((score, c))
                    scored.sort(key=lambda t: t[0], reverse=True)
                    similar = [{"id": c.id, "code": c.code, "name": c.name, "uom": getattr(c.uom, 'name', None)} for _, c in scored[:results_limit]]

                if similar:
                    try:
                        from apps.ai_companion.models import AIProactiveSuggestion
                        AIProactiveSuggestion.objects.create(
                            user=request.user,
                            company=company,
                            title="Similar Item Codes found",
                            body=f"Codes similar to '{code or name}' exist.",
                            metadata={"proposed": {"code": code, "name": name}, "similar": similar},
                            source_skill="budgeting_item_code",
                            alert_type="info",
                        )
                    except Exception:
                        pass
                    return Response({"detail": "Similar item codes exist", "similar": similar, "hint": "Pass force=1 to create anyway."}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            print(f"[BudgetItemCodeViewSet] Similarity check failed: {e}")
        return super().create(request, *args, **kwargs)


class BudgetItemCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BudgetItemCategorySerializer

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = BudgetItemCategory.objects.select_related("company").order_by('code')
        if company and getattr(company, 'company_group_id', None):
            qs = qs.filter(company_group_id=company.company_group_id)
        elif company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save()


class BudgetItemSubCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BudgetItemSubCategorySerializer

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = BudgetItemSubCategory.objects.select_related("company", "category").order_by('category_id', 'code')
        if company and getattr(company, 'company_group_id', None):
            qs = qs.filter(company_group_id=company.company_group_id)
        elif company:
            qs = qs.filter(company=company)
        category_id = self.request.query_params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs

    def perform_create(self, serializer):
        serializer.save()


class BudgetUnitOfMeasureViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BudgetUnitOfMeasureSerializer

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = UnitOfMeasure.objects.all().order_by('code', 'id')
        if company and getattr(company, 'company_group_id', None):
            qs = qs.filter(company__company_group_id=company.company_group_id)
        elif company:
            qs = qs.filter(company=company)
        return qs

    def list(self, request, *args, **kwargs):
        # Deduplicate by code within the company group so each UOM shows once
        queryset = self.get_queryset()
        by_code = {}
        for u in queryset:
            if u.code not in by_code:
                by_code[u.code] = u
        serializer = self.get_serializer(list(by_code.values()), many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save()

    def create(self, request, *args, **kwargs):
        # Permission check: creating UOMs requires budgeting_manage_uoms
        company = getattr(request, "company", None)
        if not has_permission(request.user, 'budgeting_manage_uoms', company):
            return Response({"detail": "Missing permission: budgeting_manage_uoms"}, status=status.HTTP_403_FORBIDDEN)
        # Similarity suggestions before creating UOM
        try:
            code = (request.data.get('code') or '').strip()
            name = (request.data.get('name') or '').strip()
            force = (str(request.query_params.get('force') or request.data.get('force') or '')).lower() in {'1','true','yes','on'}
            if company and (code or name) and not force:
                qs = UnitOfMeasure.objects.all()
                if getattr(company, 'company_group_id', None):
                    qs = qs.filter(company__company_group_id=company.company_group_id)
                else:
                    qs = qs.filter(company=company)
                if code and qs.filter(code__iexact=code).exists():
                    return Response({"detail": "A UOM with this code already exists for your company group.", "code": ["duplicate"]}, status=status.HTTP_400_BAD_REQUEST)

                candidates = list(qs.filter(models.Q(code__icontains=code) | models.Q(name__icontains=name))[:50])

                # Try vector similarity if embeddings available
                similar = []
                try:
                    from apps.ai_companion.services.ai_service_v2 import ai_service_v2  # local import
                    emb = getattr(ai_service_v2, 'embeddings', None)
                    if emb is None and hasattr(ai_service_v2, '_ensure_ready'):
                        try:
                            ai_service_v2._ensure_ready(require_generator=False)
                            emb = getattr(ai_service_v2, 'embeddings', None)
                        except Exception:
                            emb = None
                    if emb is not None:
                        query_text = f"{code} {name}".strip()
                        qv = emb.embed_query(query_text)
                        def _cos(a, b):
                            da = math.sqrt(sum(x*x for x in a)) or 1.0
                            db = math.sqrt(sum(x*x for x in b)) or 1.0
                            return sum(x*y for x, y in zip(a, b)) / (da * db)
                        cand_texts = [f"{(u.code or '').strip()} {(u.name or '').strip()}".strip() for u in candidates]
                        dvs = emb.embed_documents(cand_texts)
                        sims = [(_cos(qv, dv), u) for dv, u in zip(dvs, candidates)]
                        sims = [(s, u) for s, u in sims if s >= 0.75]
                        sims.sort(key=lambda t: t[0], reverse=True)
                        similar = [{"id": u.id, "code": u.code, "name": u.name} for s, u in sims[:5]]
                except Exception:
                    similar = []

                # Fallback to fuzzy
                if not similar and candidates:
                    scored = []
                    for u in candidates:
                        score_code = SequenceMatcher(a=code.lower(), b=(u.code or '').lower()).ratio() if code else 0
                        score_name = SequenceMatcher(a=name.lower(), b=(u.name or '').lower()).ratio() if name else 0
                        score = max(score_code, score_name)
                        if score >= 0.6:
                            scored.append((score, u))
                    scored.sort(key=lambda t: t[0], reverse=True)
                    similar = [{"id": u.id, "code": u.code, "name": u.name} for _, u in scored[:5]]

                if similar:
                    try:
                        from apps.ai_companion.models import AIProactiveSuggestion
                        AIProactiveSuggestion.objects.create(
                            user=request.user,
                            company=company,
                            title="Similar UOMs found",
                            body=f"UOMs similar to '{code or name}' exist.",
                            metadata={"proposed": {"code": code, "name": name}, "similar": similar},
                            source_skill="budgeting_uom",
                            alert_type="info",
                        )
                    except Exception:
                        pass
                    return Response({"detail": "Similar UOMs exist", "similar": similar, "hint": "Pass force=1 to create anyway."}, status=status.HTTP_409_CONFLICT)
        except Exception:
            pass
        return super().create(request, *args, **kwargs)


class PermittedCostCentersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        company = getattr(request, "company", None)
        qs = CostCenter.objects.select_related("company", "owner", "deputy_owner")
        if company:
            qs = qs.filter(company=company)
        # Admins/staff: see all active cost centers in scope
        if getattr(user, "is_superuser", False) or getattr(user, "is_system_admin", False) or getattr(user, "is_staff", False):
            base_qs = qs.filter(is_active=True)
        else:
            base_qs = qs.filter(
                models.Q(owner=user) | models.Q(deputy_owner=user) | models.Q(budget_entry_users=user)
            )
        base_qs = base_qs.distinct().order_by("code")
        # Fallback: if none matched (e.g., initial setup), show all active to avoid empty UX for first-time setup
        if not base_qs.exists():
            base_qs = qs.filter(is_active=True).order_by("code")
        data = [
            {"id": cc.id, "code": cc.code, "name": cc.name}
            for cc in base_qs
        ]
        return Response(data)


class DeclaredBudgetsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, "company", None)
        today = timezone.now().date()
        cost_center_id = request.query_params.get("cost_center")

        data = []
        # Show all budgets with active entry period (not just company-wide)
        declared_qs = Budget.objects.all()
        # Only show budgets whose entry window is active AND name is approved
        try:
            declared_qs = declared_qs.filter(name_status=Budget.NAME_STATUS_APPROVED)
        except Exception:
            pass
        declared_qs = declared_qs.filter(entry_enabled=True, entry_start_date__lte=today, entry_end_date__gte=today)
        if company:
            declared_qs = declared_qs.filter(company=company)
        for b in declared_qs.order_by("-period_start"):
            data.append({
                "id": b.id,
                "name": b.name,
                "display_name": str(b),  # Add display_name for better rendering
                "budget_type": b.budget_type,
                "period_start": b.period_start,
                "period_end": b.period_end,
            })

        # Cost-center specific budgets: visible only to that CC's permitted users
        if cost_center_id:
            try:
                cc = CostCenter.objects.get(pk=int(cost_center_id))
                # Permission check: owner, deputy, or in entry users
                user = request.user
                permitted = (
                    (cc.owner_id and user.id == cc.owner_id)
                    or (cc.deputy_owner_id and user.id == cc.deputy_owner_id)
                    or cc.budget_entry_users.filter(id=user.id).exists()
                )
                if permitted:
                    cc_qs = Budget.objects.filter(cost_center=cc)
                    try:
                        cc_qs = cc_qs.filter(name_status=Budget.NAME_STATUS_APPROVED)
                    except Exception:
                        pass
                    cc_qs = cc_qs.filter(entry_enabled=True, entry_start_date__lte=today, entry_end_date__gte=today)
                    if company:
                        cc_qs = cc_qs.filter(company=company)
                    for b in cc_qs.order_by("-period_start"):
                        data.append({
                            "id": b.id,
                            "name": b.name,
                            "display_name": str(b),
                            "budget_type": b.budget_type,
                            "period_start": b.period_start,
                            "period_end": b.period_end,
                        })
            except (ValueError, CostCenter.DoesNotExist):
                pass

        return Response(data)


class EntrySummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        company = getattr(request, "company", None)
        declared_id = request.query_params.get("budget")
        declared = None
        if declared_id:
            # Allow budgets with or without cost centers
            declared = Budget.objects.filter(pk=declared_id).first()
        cc_qs = CostCenter.objects.all()
        if company:
            cc_qs = cc_qs.filter(company=company)
        cc_qs = cc_qs.filter(models.Q(owner=user) | models.Q(deputy_owner=user) | models.Q(budget_entry_users=user))
        permitted_ids = list(cc_qs.values_list("id", flat=True).distinct())
        # Accumulate lines under declared budget, tagged by cost_center in metadata
        bl_qs = BudgetLine.objects.all()
        if company:
            bl_qs = bl_qs.filter(budget__company=company)
        if declared:
            bl_qs = bl_qs.filter(budget_id=declared.id)
        if permitted_ids:
            bl_qs = bl_qs.filter(metadata__cost_center_id__in=[int(x) for x in permitted_ids])
        agg = bl_qs.aggregate(
            items=models.Count("id"),
            value=models.Sum("value_limit"),
            used=models.Sum("consumed_value"),
        )
        items = agg.get("items") or 0
        value = agg.get("value") or Decimal("0")
        used = agg.get("used") or Decimal("0")
        remaining = value - used
        return Response({
            "items": items,
            "value": f"{value}",
            "used": f"{used}",
            "remaining": f"{remaining}",
        })


class EntryLinesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, "company", None)
        declared_id = request.query_params.get("budget")
        cost_center_id = request.query_params.get("cost_center")
        if not (declared_id and cost_center_id):
            return Response({"detail": "budget and cost_center are required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Allow budgets with or without cost centers
            declared = Budget.objects.get(pk=declared_id)
            cc = CostCenter.objects.get(pk=cost_center_id)
        except (Budget.DoesNotExist, CostCenter.DoesNotExist):
            return Response({"detail": "Invalid budget or cost center"}, status=status.HTTP_404_NOT_FOUND)
        # Enforce name approval and applicable CC scope
        try:
            if getattr(declared, 'name_status', None) and declared.name_status != Budget.NAME_STATUS_APPROVED:
                return Response({"detail": "Budget name is not approved."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            pass
        try:
            app_cc = getattr(declared, 'applicable_cost_centers', None)
            if app_cc is not None and app_cc.exists():
                if not app_cc.filter(pk=cc.id).exists():
                    return Response({"detail": "This budget is not open for this cost center."}, status=status.HTTP_403_FORBIDDEN)
        except Exception:
            pass
        # Lines are accumulated under the declared budget; filter by CC tag in metadata
        try:
            cc_id = int(cost_center_id)
        except Exception:
            return Response({"detail": "Invalid cost_center"}, status=status.HTTP_400_BAD_REQUEST)
        # Always use Python-side filter for broad DB compatibility
        raw_qs = BudgetLine.objects.filter(budget_id=declared.id)
        filtered = [bl for bl in raw_qs if (getattr(bl, 'metadata', {}) or {}).get('cost_center_id') == cc_id]
        lines = BudgetLineSerializer(filtered, many=True, context={"request": request}).data
        # Return minimal cc_budget info needed by UI
        cc_data = {
            "id": declared.id,
            "name": declared.name,
            "period_start": declared.period_start,
            "period_end": declared.period_end,
            "is_entry_period_active": declared.is_entry_period_active(),
        }
        return Response({"cc_budget": cc_data, "lines": lines})


class LastPriceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        item_code = request.query_params.get("item_code")
        company = getattr(request, "company", None)
        if not item_code:
            return Response({"detail": "item_code required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            price, source = BudgetPriceService.get_price_for_item(company, item_code)
        except Exception:
            price, source = Decimal("0"), "manual"
        return Response({"unit_price": f"{price}", "source": source})


class AddBudgetItemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        company = getattr(request, "company", None)
        user = request.user
        cost_center_id = request.data.get("cost_center")
        declared_budget_id = request.data.get("budget")
        item_code = request.data.get("item_code")
        item_name = request.data.get("item_name")
        qty = request.data.get("quantity")
        manual_unit_price = request.data.get("manual_unit_price")
        # Derive procurement class from declared budget type (ignore client override)
        if False:
            pass  # placeholder for readability
        if not (cost_center_id and declared_budget_id and item_code and qty is not None):
            return Response({"detail": "cost_center, budget, item_code, quantity are required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            qty = Decimal(str(qty))
        except Exception:
            return Response({"detail": "Invalid quantity"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            cc = CostCenter.objects.get(pk=cost_center_id)
            # Allow budgets with or without cost centers
            declared = Budget.objects.get(pk=declared_budget_id)
        except CostCenter.DoesNotExist:
            return Response({"detail": "Cost center not found"}, status=status.HTTP_404_NOT_FOUND)
        except Budget.DoesNotExist:
            return Response({"detail": "Declared budget not found"}, status=status.HTTP_404_NOT_FOUND)
        # Permission and entry window
        # Enforce applicable cost centers scope if specified
        try:
            app_cc = getattr(declared, 'applicable_cost_centers', None)
            if app_cc is not None and app_cc.exists():
                if not app_cc.filter(pk=cc.id).exists():
                    return Response({"detail": "This budget is not open for this cost center."}, status=status.HTTP_403_FORBIDDEN)
        except Exception:
            pass
        # Enforce name approval (budget-level) before entry
        try:
            if getattr(declared, 'name_status', None) and declared.name_status != Budget.NAME_STATUS_APPROVED:
                return Response({"detail": "Budget name is not approved."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            pass
        if not BudgetPermissionService.user_can_enter_for_cost_center(user, cc):
            return Response({"detail": "Not permitted for this cost center"}, status=status.HTTP_403_FORBIDDEN)
        if not declared.is_entry_period_active():
            # Allow superusers/system admins to bypass entry window during admin/testing
            if not (getattr(user, "is_superuser", False) or getattr(user, "is_system_admin", False)):
                return Response({"detail": "Entry period is not active"}, status=status.HTTP_400_BAD_REQUEST)
        # Accumulate under declared budget instead of creating CC-specific budgets
        cc_budget = declared
        # Decide procurement class based on declared budget type
        try:
            if declared.budget_type == Budget.TYPE_OPEX:
                procurement_class = BudgetLine.ProcurementClass.SERVICE_ITEM
            elif declared.budget_type == Budget.TYPE_CAPEX:
                procurement_class = BudgetLine.ProcurementClass.CAPEX_ITEM
            else:
                procurement_class = BudgetLine.ProcurementClass.STOCK_ITEM
        except Exception:
            procurement_class = BudgetLine.ProcurementClass.STOCK_ITEM
        # Decide procurement class based on declared budget type
        try:
            if declared.budget_type == Budget.TYPE_OPEX:
                procurement_class = BudgetLine.ProcurementClass.SERVICE_ITEM
            elif declared.budget_type == Budget.TYPE_CAPEX:
                procurement_class = BudgetLine.ProcurementClass.CAPEX_ITEM
            else:
                procurement_class = BudgetLine.ProcurementClass.STOCK_ITEM
        except Exception:
            procurement_class = BudgetLine.ProcurementClass.STOCK_ITEM
        # Resolve price
        if manual_unit_price is not None:
            try:
                unit_price = Decimal(str(manual_unit_price))
                source = "manual"
            except Exception:
                return Response({"detail": "Invalid manual_unit_price"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                unit_price, source = BudgetPriceService.get_price_for_item(company, item_code)
            except Exception:
                unit_price, source = Decimal("0"), "manual"
        # Validate non-zero unit price
        try:
            if unit_price is None or Decimal(str(unit_price)) <= Decimal("0"):
                return Response({"detail": "Unit price must be greater than 0. Set standard price or enter manual."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"detail": "Invalid unit price"}, status=status.HTTP_400_BAD_REQUEST)
        value_limit = (unit_price or Decimal("0")) * qty
        # Compute next sequence within this declared budget
        try:
            max_seq = (
                BudgetLine.objects
                .filter(budget_id=cc_budget.id)
                .aggregate(max_seq=models.Max("sequence"))
                .get("max_seq")
            ) or 0
            next_sequence = int(max_seq) + 1
        except Exception:
            next_sequence = 1
        line = BudgetLine.objects.create(
            budget=cc_budget,
            sequence=next_sequence,
            procurement_class=procurement_class,
            item_code=item_code,
            item_name=item_name or item_code,
            qty_limit=qty,
            standard_price=unit_price,
            manual_unit_price=(unit_price if source == "manual" else None),
            value_limit=value_limit,
            metadata={"cost_center_id": cc.id},
            budget_owner=request.user,
        )
        cc_budget.recalculate_totals(commit=True)
        return Response(BudgetLineSerializer(line, context={"request": request}).data, status=status.HTTP_201_CREATED)


class SubmitEntryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cost_center_id = request.data.get("cost_center")
        declared_budget_id = request.data.get("budget")
        if not (cost_center_id and declared_budget_id):
            return Response({"detail": "cost_center and budget are required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            cc = CostCenter.objects.get(pk=cost_center_id)
            # Allow budgets with or without cost centers
            declared = Budget.objects.get(pk=declared_budget_id)
        except (CostCenter.DoesNotExist, Budget.DoesNotExist):
            return Response({"detail": "Invalid cost center or budget"}, status=status.HTTP_404_NOT_FOUND)
        # Tag lines for this cost center as submitted (metadata flag)
        try:
            # Use Python-side filter for broad DB compatibility
            raw_qs = BudgetLine.objects.filter(budget_id=declared.id)
            for bl in raw_qs:
                meta = dict(getattr(bl, 'metadata', {}) or {})
                if meta.get('cost_center_id') == cc.id:
                    meta['submitted'] = True
                    bl.metadata = meta
                    bl.save(update_fields=['metadata', 'updated_at'])
        except Exception:
            return Response({"detail": "Failed to submit entries"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Create pending approval for CC owner and move budget to pending CC approval
        try:
            from .models import BudgetApproval as BA
            approver = getattr(cc, "owner", None) or getattr(cc, "deputy_owner", None)
            approval, created = BA.objects.get_or_create(
                budget=declared,
                approver_type=BA.ApproverType.COST_CENTER_OWNER,
                cost_center=cc,
                status=BA.Status.PENDING,
                defaults={"approver": approver},
            )
            # Ensure approval line scope contains all CC lines in PENDING
            try:
                from .models import BudgetApprovalLine as BAL
                # Scope: lines in this budget that belong to the CC (metadata.cost_center_id or budget.cost_center)
                raw_qs = BudgetLine.objects.filter(budget_id=declared.id)
                for bl in raw_qs:
                    meta = getattr(bl, 'metadata', {}) or {}
                    belongs = (meta.get('cost_center_id') == cc.id) or (getattr(declared, 'cost_center_id', None) == cc.id)
                    if not belongs:
                        continue
                    # Create scope row if not exists
                    BAL.objects.get_or_create(
                        approval=approval,
                        line=bl,
                        defaults={"stage": BAL.Stage.CC_APPROVAL, "status": BAL.LineStatus.PENDING}
                    )
            except Exception:
                pass
            if approver and approval.approver_id is None:
                approval.approver = approver
                approval.save(update_fields=["approver"])
            if declared.status in {Budget.STATUS_DRAFT, Budget.STATUS_ENTRY_OPEN}:
                declared.status = Budget.STATUS_PENDING_CC_APPROVAL
                declared.save(update_fields=["status", "updated_at"])
            try:
                BudgetNotificationService.notify_approval_requested(declared, cc, approval.approver)
            except Exception:
                pass
        except Exception:
            pass
        return Response({"detail": "Submitted for CC owner approval", "budget": BudgetSerializer(declared, context={"request": request}).data})


class BudgetPricePolicyView(APIView):
    permission_classes = [IsAuthenticated]

    def get_company(self, request):
        company = getattr(request, "company", None)
        if not company and getattr(request, "user", None):
            company = getattr(request.user, "default_company", None)
        return company

    def get(self, request):
        from .models import BudgetPricePolicy
        company = self.get_company(request)
        if not company:
            return Response({"detail": "Active company is required."}, status=status.HTTP_400_BAD_REQUEST)
        policy_obj = BudgetPricePolicy.objects.filter(company=company).first()
        if policy_obj:
            data = BudgetPricePolicySerializer(policy_obj, context={"request": request}).data
            data["persisted"] = True
            return Response(data)
        # Fall back to effective policy (defaults) without persisting
        effective = BudgetPriceService.get_company_policy(company)
        data = {
            "company": getattr(company, "id", None),
            "primary_source": effective.primary,
            "secondary_source": effective.secondary,
            "tertiary_source": effective.tertiary,
            "avg_lookback_days": effective.avg_lookback_days,
            "fallback_on_zero": effective.fallback_on_zero,
            "persisted": False,
        }
        return Response(data)

    def patch(self, request):
        from .models import BudgetPricePolicy
        company = self.get_company(request)
        if not company:
            return Response({"detail": "Active company is required."}, status=status.HTTP_400_BAD_REQUEST)
        # Permission: module owner or superuser
        if not (getattr(request.user, "is_superuser", False) or BudgetPermissionService.user_is_budget_module_owner(request.user, company)):
            return Response({"detail": "Not permitted"}, status=status.HTTP_403_FORBIDDEN)
        obj = BudgetPricePolicy.objects.filter(company=company).first()
        serializer = BudgetPricePolicySerializer(obj, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        if obj:
            instance = serializer.save()
        else:
            instance = serializer.create(serializer.validated_data)
        return Response(BudgetPricePolicySerializer(instance, context={"request": request}).data)


class BudgetApprovalViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing budget approval tasks and approving/rejecting them.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = BudgetApprovalSerializer

    def get_queryset(self):
        user = self.request.user
        company = getattr(self.request, "company", None)
        
        qs = BudgetApproval.objects.select_related("budget", "budget__company", "cost_center", "approver")

        if company and not getattr(user, "is_superuser", False):
            qs = qs.filter(budget__company=company)

        if getattr(user, "is_superuser", False):
            return qs.order_by("-created_at")
        
        predicate = Q(approver=user)
        
        try:
            from .services import BudgetPermissionService
            is_module_owner = BudgetPermissionService.user_is_budget_module_owner(user, company)
        except Exception:
            is_module_owner = False

        if is_module_owner:
            predicate |= (
                Q(approver_type=BudgetApproval.ApproverType.BUDGET_MODULE_OWNER)
                & (Q(approver=user) | Q(approver__isnull=True))
            )
        # Allow CC owners/deputies to access CC approval tasks without explicit approver assignment
        predicate |= (
            Q(approver__isnull=True)
            & Q(approver_type=BudgetApproval.ApproverType.COST_CENTER_OWNER)
            & (Q(cost_center__owner=user) | Q(cost_center__deputy_owner=user))
        )
            
        return qs.filter(predicate).order_by("-created_at")

    def retrieve(self, request, *args, **kwargs):
        approval_instance = self.get_object()
        budget = approval_instance.budget
        
        # Scoped lines via BudgetApprovalLine
        from .models import BudgetApprovalLine as BAL
        stage = BAL.Stage.FINAL_APPROVAL if approval_instance.approver_type == BudgetApproval.ApproverType.BUDGET_MODULE_OWNER else BAL.Stage.CC_APPROVAL
        scoped = BAL.objects.select_related("line").filter(approval=approval_instance, stage=stage)
        lines = [x.line for x in scoped]

        approval_data = self.get_serializer(approval_instance).data
        approval_data['scoped_lines'] = BudgetLineSerializer(lines, many=True, context={"request": request}).data
        # Backward-compat fields used by some UIs
        if approval_instance.approver_type == BudgetApproval.ApproverType.BUDGET_MODULE_OWNER:
            approval_data['remarked_lines'] = approval_data['scoped_lines']
            approval_data['not_reviewed_lines'] = []
        return Response(approval_data)

    @action(detail=True, methods=["post"])
    def approve_lines(self, request, pk=None):
        approval_instance = self.get_object()
        line_ids = request.data.get("line_ids", [])

        if not line_ids:
            return Response({"detail": "line_ids are required."}, status=status.HTTP_400_BAD_REQUEST)

        from .models import BudgetApproval as BA, BudgetApprovalLine as BAL
        stage = BAL.Stage.FINAL_APPROVAL if approval_instance.approver_type == BA.ApproverType.BUDGET_MODULE_OWNER else BAL.Stage.CC_APPROVAL
        # Validate scope
        scoped_map = {x.line_id: x for x in BAL.objects.filter(approval=approval_instance, stage=stage, line_id__in=line_ids)}
        missing = [lid for lid in line_ids if lid not in scoped_map]
        if missing:
            return Response({"detail": "Some lines do not belong to this approval task.", "missing": missing}, status=status.HTTP_400_BAD_REQUEST)

        lines_to_approve = BudgetLine.objects.filter(id__in=list(scoped_map.keys()), budget=approval_instance.budget)

        if approval_instance.approver_type == BA.ApproverType.BUDGET_MODULE_OWNER:
            # Final approver: update line final_decision
            from django.utils import timezone
            for line in lines_to_approve:
                line.final_decision = line.FinalDecision.APPROVED
                line.final_decision_by = request.user
                line.final_decision_at = timezone.now()
                md = line.metadata or {}
                md['final_approved'] = True
                md.pop('final_rejected', None)
                line.metadata = md
                line.save(update_fields=["final_decision", "final_decision_by", "final_decision_at", "metadata"])
                al = scoped_map.get(line.id)
                if al:
                    al.status = BAL.LineStatus.APPROVED
                    al.save(update_fields=["status", "updated_at"])

            remaining = approval_instance.approval_lines.filter(stage=stage, status=BAL.LineStatus.PENDING).count()
            if remaining == 0 and approval_instance.status == BA.Status.PENDING:
                from django.utils import timezone
                approval_instance.status = BA.Status.APPROVED
                if not approval_instance.approver:
                    approval_instance.approver = request.user
                approval_instance.decision_date = timezone.now()
                approval_instance.save(update_fields=["status", "approver", "decision_date"])
        elif approval_instance.approver_type == BA.ApproverType.COST_CENTER_OWNER:
            # CC approver: update line cc_decision
            from django.utils import timezone
            for line in lines_to_approve:
                line.cc_decision = line.CCDecision.APPROVED
                line.cc_decision_by = request.user
                line.cc_decision_at = timezone.now()
                md = line.metadata or {}
                md['approved'] = True
                md['rejected'] = False
                line.metadata = md
                line.save(update_fields=["cc_decision", "cc_decision_by", "cc_decision_at", "metadata"])
                al = scoped_map.get(line.id)
                if al:
                    al.status = BAL.LineStatus.APPROVED
                    al.save(update_fields=["status", "updated_at"])

            remaining = approval_instance.approval_lines.filter(stage=stage, status=BAL.LineStatus.PENDING).count()
            if remaining == 0 and approval_instance.status == BA.Status.PENDING:
                from django.utils import timezone
                approval_instance.status = BA.Status.APPROVED
                if not approval_instance.approver:
                    approval_instance.approver = request.user
                approval_instance.decision_date = timezone.now()
                approval_instance.save(update_fields=["status", "approver", "decision_date"])

        return Response({"detail": f"{len(lines_to_approve)} lines approved.", "remaining": remaining})

    @action(detail=True, methods=["post"])
    def reject_lines(self, request, pk=None):
        """Final approver: reject selected lines (mark as final_rejected). For CC approver, prefer send_back endpoints."""
        approval_instance = self.get_object()
        line_ids = request.data.get("line_ids", [])
        if not line_ids:
            return Response({"detail": "line_ids are required."}, status=status.HTTP_400_BAD_REQUEST)

        from .models import BudgetApproval as BA, BudgetApprovalLine as BAL
        if approval_instance.approver_type != BA.ApproverType.BUDGET_MODULE_OWNER:
            return Response({"detail": "Reject lines is only supported for final approvers."}, status=status.HTTP_400_BAD_REQUEST)
        # Validate scope
        stage = BAL.Stage.FINAL_APPROVAL
        scoped_map = {x.line_id: x for x in BAL.objects.filter(approval=approval_instance, stage=stage, line_id__in=line_ids)}
        missing = [lid for lid in line_ids if lid not in scoped_map]
        if missing:
            return Response({"detail": "Some lines do not belong to this approval task.", "missing": missing}, status=status.HTTP_400_BAD_REQUEST)

        lines_to_reject = BudgetLine.objects.filter(id__in=list(scoped_map.keys()), budget=approval_instance.budget)

        # Mark final_rejected
        from django.utils import timezone
        for line in lines_to_reject:
            line.final_decision = line.FinalDecision.REJECTED
            line.final_decision_by = request.user
            line.final_decision_at = timezone.now()
            metadata = line.metadata or {}
            metadata['final_rejected'] = True
            metadata.pop('final_approved', None)
            line.metadata = metadata
            line.save(update_fields=["final_decision", "final_decision_by", "final_decision_at", "metadata"])
            al = scoped_map.get(line.id)
            if al:
                al.status = BAL.LineStatus.REJECTED
                al.save(update_fields=["status", "updated_at"])

        remaining = approval_instance.approval_lines.filter(stage=stage, status=BAL.LineStatus.PENDING).count()
        if remaining == 0 and approval_instance.status == BA.Status.PENDING:
            # Consider task completed
            approval_instance.status = BA.Status.APPROVED
            if not approval_instance.approver:
                approval_instance.approver = request.user
            approval_instance.decision_date = timezone.now()
            approval_instance.save(update_fields=["status", "approver", "decision_date"])

        return Response({"detail": f"{len(lines_to_reject)} lines rejected.", "remaining": remaining})


class BudgetApprovalQueueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import logging
        logger = logging.getLogger(__name__)
        from django.db.models import Q
        from .models import BudgetApproval as BA, BudgetLine, CostCenter, Budget

        company = getattr(request, "company", None)
        base_qs = BA.objects.select_related("budget", "budget__company", "cost_center")

        # Only pending approvals are relevant for the queue
        qs = base_qs.filter(status=BA.Status.PENDING)

        user = request.user

        # Scope by active company when available (superuser sees across companies)
        if company and not getattr(user, "is_superuser", False):
            qs = qs.filter(budget__company=company)

        if getattr(user, "is_superuser", False):
            # Superusers see all pending approvals in scope (per docs: superuser has all access)
            approvals = qs.order_by("-created_at")
        else:
            # Build dynamic visibility per docs
            # 1) Directly assigned approvals
            predicate = Q(approver=user)

            # 2) CC Owner/Deputy: include records without explicit approver
            predicate |= (
                Q(approver__isnull=True)
                & Q(approver_type=BA.ApproverType.COST_CENTER_OWNER)
                & (Q(cost_center__owner=user) | Q(cost_center__deputy_owner=user))
            )

            # 3) Budget Module Owner: include generic final-approval records if user has role
            try:
                from .services import BudgetPermissionService
                is_module_owner = BudgetPermissionService.user_is_budget_module_owner(user, company)
            except Exception:
                is_module_owner = False

            if is_module_owner:
                predicate |= (
                    Q(approver_type=BA.ApproverType.BUDGET_MODULE_OWNER)
                    & (Q(approver=user) | Q(approver__isnull=True))
                )

            approvals = qs.filter(predicate).order_by("-created_at")

        # Build data grouped by approval (each approval already scoped to a budget/cost center)
        data = []
        by_type_count = {"name": 0, "cc": 0, "final": 0}

        for a in approvals:
            budget = a.budget
            if not budget:
                continue
            # For CC approvals, compute whether CC can approve (entry window dates, ignore status)
            cc_can_approve = True
            try:
                if a.approver_type == BA.ApproverType.COST_CENTER_OWNER:
                    today = timezone.now().date()
                    es = getattr(budget, 'entry_start_date', None)
                    ee = getattr(budget, 'entry_end_date', None)
                    enabled = bool(getattr(budget, 'entry_enabled', True))
                    if not enabled:
                        cc_can_approve = False
                    elif es and today < es:
                        cc_can_approve = False
                    elif ee and today > ee:
                        cc_can_approve = False
                    else:
                        cc_can_approve = True
            except Exception:
                cc_can_approve = True
            try:
                if a.approver_type == BA.ApproverType.BUDGET_NAME_APPROVER:
                    by_type_count["name"] += 1
                elif a.approver_type == BA.ApproverType.COST_CENTER_OWNER:
                    by_type_count["cc"] += 1
                elif a.approver_type == BA.ApproverType.BUDGET_MODULE_OWNER:
                    by_type_count["final"] += 1
            except Exception:
                pass

            display_status = "pending"
            stage_value = BudgetApprovalLine.Stage.CC_APPROVAL if a.approver_type == BA.ApproverType.COST_CENTER_OWNER else BudgetApprovalLine.Stage.FINAL_APPROVAL
            scoped_entries = list(
                a.approval_lines.filter(stage=stage_value).select_related("line", "line__budget")
            )
            total_count = len(scoped_entries)
            approved_count = sum(1 for entry in scoped_entries if entry.status == BudgetApprovalLine.LineStatus.APPROVED)
            pending_count = sum(1 for entry in scoped_entries if entry.status == BudgetApprovalLine.LineStatus.PENDING)
            sent_back_count = sum(1 for entry in scoped_entries if entry.status == BudgetApprovalLine.LineStatus.SENT_BACK)

            if a.approver_type == BA.ApproverType.COST_CENTER_OWNER:
                if total_count == 0:
                    display_status = "pending"
                elif sent_back_count and sent_back_count == total_count:
                    display_status = "sent_back"
                elif approved_count == total_count:
                    display_status = "approved"
                elif approved_count and approved_count < total_count:
                    display_status = "partially_approved"
                else:
                    display_status = "pending"
            elif a.approver_type == BA.ApproverType.BUDGET_MODULE_OWNER:
                if total_count == 0:
                    display_status = "pending_final"
                elif approved_count == total_count:
                    display_status = "approved"
                elif approved_count and approved_count < total_count:
                    display_status = "partially_approved"
                elif sent_back_count == total_count:
                    display_status = "sent_back"
                else:
                    display_status = "pending_final"

            if a.approver_type == BA.ApproverType.BUDGET_MODULE_OWNER:
                grouped_lines = {}
                for entry in scoped_entries:
                    line = entry.line
                    meta = getattr(line, "metadata", {}) or {}
                    cid = meta.get("cost_center_id") or getattr(line.budget, "cost_center_id", None)
                    grouped_lines.setdefault(cid, []).append(entry)

                if not grouped_lines:
                    grouped_lines = {getattr(budget, "cost_center_id", None): scoped_entries}

                for grouped_cc_id, entries in grouped_lines.items():
                    subset_total = len(entries)
                    subset_pending = sum(1 for entry in entries if entry.status == BudgetApprovalLine.LineStatus.PENDING)
                    subset_approved = sum(1 for entry in entries if entry.status == BudgetApprovalLine.LineStatus.APPROVED)
                    subset_sent = sum(1 for entry in entries if entry.status == BudgetApprovalLine.LineStatus.SENT_BACK)

                    if subset_total == 0:
                        subset_display = "pending_final"
                    elif subset_approved == subset_total:
                        subset_display = "approved"
                    elif subset_approved and subset_approved < subset_total:
                        subset_display = "partially_approved"
                    elif subset_sent == subset_total:
                        subset_display = "sent_back"
                    else:
                        subset_display = "pending_final"

                    if grouped_cc_id:
                        cost_center = CostCenter.objects.filter(pk=grouped_cc_id).first()
                    else:
                        cost_center = getattr(budget, "cost_center", None)
                    if cost_center:
                        cc_display = getattr(cost_center, "name", None) or getattr(cost_center, "code", "Cost Center")
                    else:
                        cc_display = "Company-wide"

                    data.append({
                        "id": f"{a.id}_{grouped_cc_id or 'company'}",
                        "approval_id": a.id,
                        "budget_id": a.budget_id,
                        "cc_budget_id": None,
                        "budget_name": str(budget),
                        "budget_type": getattr(budget, "budget_type", None),
                        "budget_status": getattr(budget, "status", None),
                        "approver_type": a.approver_type,
                        "status": a.status,
                        "display_status": subset_display,
                        "approved_count": subset_approved,
                        "total_count": subset_total,
                        "pending_count": subset_pending,
                        "cc_can_approve": False,
                        "cost_center": cc_display,
                        "cost_center_id": grouped_cc_id,
                        "created_at": a.created_at,
                    })
                continue
            else:
                cost_center = a.cost_center or getattr(budget, "cost_center", None)
                cc_id = getattr(cost_center, 'id', None)
                if a.approver_type == BA.ApproverType.BUDGET_MODULE_OWNER:
                    cc_display = "Company-wide"
                elif cost_center:
                    cc_display = getattr(cost_center, "name", None) or getattr(cost_center, "code", "Cost Center")
                else:
                    cc_display = "Company-wide"
    
                cc_budget_id = None
                if cc_id:
                    try:
                        cc_budget = Budget.objects.filter(parent_declared=budget, cost_center_id=cc_id).order_by('-revision_no').first()
                        cc_budget_id = getattr(cc_budget, 'id', None)
                    except Exception:
                        cc_budget_id = None

                data.append({
                    "id": f"{a.id}_{cc_id or 'company'}",
                    "approval_id": a.id,
                    "budget_id": a.budget_id,
                    "cc_budget_id": cc_budget_id,
                    "budget_name": str(budget),
                    "budget_type": getattr(budget, "budget_type", None),
                    "budget_status": getattr(budget, "status", None),
                    "approver_type": a.approver_type,
                    "status": a.status,
                    "display_status": display_status,
                    "approved_count": approved_count,
                    "total_count": total_count,
                    "pending_count": pending_count,
                    "cc_can_approve": cc_can_approve,
                    "cost_center": cc_display,
                    "cost_center_id": cc_id,
                    "created_at": a.created_at,
                })

        # Fallback: include registry-only budgets pending final approval even if
        # a BudgetApproval record is missing (older records). Only visible to
        # superusers or budget module owners.
        try:
            present_budget_ids = {row.get("budget_id") for row in data if row.get("budget_id")}
            base_fb = Budget.objects.filter(status=Budget.STATUS_PENDING_FINAL_APPROVAL, cost_center__isnull=True)
            if company and not getattr(user, "is_superuser", False):
                base_fb = base_fb.filter(company=company)

            include_fb = getattr(user, "is_superuser", False)
            if not include_fb:
                try:
                    from .services import BudgetPermissionService
                    include_fb = BudgetPermissionService.user_is_budget_module_owner(user, company)
                except Exception:
                    include_fb = False

            if include_fb:
                for b in base_fb:
                    try:
                        if b.id in present_budget_ids:
                            continue
                        # registry-only condition: no lines
                        try:
                            has_lines = getattr(b, "lines", None) and b.lines.exists()
                        except Exception:
                            has_lines = False
                        if has_lines:
                            continue
                        data.append({
                            "id": f"fb_{b.id}",
                            "budget_id": b.id,
                            "budget_name": str(b),
                            "budget_type": getattr(b, "budget_type", None),
                            "budget_status": getattr(b, "status", None),
                            "approver_type": BA.ApproverType.BUDGET_MODULE_OWNER,
                            "status": BA.Status.PENDING,
                            "cost_center": "Company-wide",
                            "cost_center_id": None,
                            "created_at": getattr(b, "created_at", None),
                        })
                    except Exception:
                        continue
        except Exception:
            pass

        # Fallback: include name-approval budgets (registry-only, no lines)
        try:
            present_budget_ids = {row.get("budget_id") for row in data if row.get("budget_id")}
            try:
                name_fb = Budget.objects.filter(name_status=Budget.NAME_STATUS_DRAFT)
            except Exception:
                name_fb = Budget.objects.filter(status=getattr(Budget, 'STATUS_PENDING_NAME_APPROVAL', 'pending_name_approval'))
            if company and not getattr(user, "is_superuser", False):
                name_fb = name_fb.filter(company=company)

            include_name = getattr(user, "is_superuser", False)
            if not include_name:
                try:
                    from .services import BudgetPermissionService
                    include_name = BudgetPermissionService.user_is_budget_name_approver(user, company)
                except Exception:
                    include_name = False

            if include_name:
                for b in name_fb:
                    try:
                        if b.id in present_budget_ids:
                            continue
                        try:
                            has_lines = getattr(b, "lines", None) and b.lines.exists()
                        except Exception:
                            has_lines = False
                        if has_lines:
                            continue
                        data.append({
                            "id": f"nba_{b.id}",
                            "budget_id": b.id,
                            "budget_name": str(b),
                            "budget_type": getattr(b, "budget_type", None),
                            "budget_status": getattr(b, "status", None),
                            "approver_type": BA.ApproverType.BUDGET_NAME_APPROVER,
                            "status": BA.Status.PENDING,
                            "cost_center": "Company-wide",
                            "cost_center_id": None,
                            "created_at": getattr(b, "created_at", None),
                        })
                    except Exception:
                        continue
        except Exception:
            pass

        # Note: Do NOT include registry Approved budgets via fallback.
        # Approved indicates name approval is complete.
        # Including Approved would cause already-approved budgets to linger as "pending" in the queue.

        try:
            logger.info(f"[BudgetApprovalQueueView] rows={len(data)} type_counts={by_type_count}")
        except Exception:
            pass
        try:
            print(f"[BudgetApprovalQueueView] rows={len(data)} type_counts={by_type_count}")
        except Exception:
            pass

        return Response(data)
        


class BudgetRemarkTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing budget remark templates"""
    permission_classes = [IsAuthenticated]
    serializer_class = BudgetRemarkTemplateSerializer

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        user = self.request.user
        qs = BudgetRemarkTemplate.objects.select_related("company", "created_by")

        if company:
            qs = qs.filter(company=company)

        # Filter by templates user has access to:
        # - Templates they created
        # - Predefined templates
        # - Public/shared templates (is_shared=True)
        qs = qs.filter(
            models.Q(created_by=user) |
            models.Q(is_predefined=True) |
            models.Q(is_shared=True)
        ).distinct()

        return qs.order_by("-usage_count", "name")

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit_event(
            user=self.request.user,
            company=getattr(self.request, "company", None),
            company_group=getattr(getattr(self.request, "company", None), "company_group", None),
            action="REMARK_TEMPLATE_CREATED",
            entity_type="BudgetRemarkTemplate",
            entity_id=str(instance.id),
            description=f"Remark template '{instance.name}' created.",
            after=serializer.data,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit_event(
            user=self.request.user,
            company=getattr(self.request, "company", None),
            company_group=getattr(getattr(self.request, "company", None), "company_group", None),
            action="REMARK_TEMPLATE_UPDATED",
            entity_type="BudgetRemarkTemplate",
            entity_id=str(instance.id),
            description=f"Remark template '{instance.name}' updated.",
            after=serializer.data,
        )

    @action(detail=True, methods=["post"])
    def increment_usage(self, request, pk=None):
        """Increment the usage count when a template is used"""
        template = self.get_object()
        template.usage_count = models.F("usage_count") + 1
        template.save(update_fields=["usage_count"])
        template.refresh_from_db()
        return Response(self.get_serializer(template).data)


class BudgetVarianceAuditViewSet(viewsets.ReadOnlyModelViewSet):
    """ReadOnly ViewSet for viewing budget variance audit trail"""
    permission_classes = [IsAuthenticated]
    serializer_class = BudgetVarianceAuditSerializer

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = BudgetVarianceAudit.objects.select_related(
            "budget_line__budget",
            "modified_by"
        ).order_by("-created_at")

        if company:
            qs = qs.filter(budget_line__budget__company=company)

        # Filter by budget_line if provided
        budget_line_id = self.request.query_params.get("budget_line")
        if budget_line_id:
            qs = qs.filter(budget_line_id=budget_line_id)

        # Filter by budget if provided
        budget_id = self.request.query_params.get("budget")
        if budget_id:
            qs = qs.filter(budget_line__budget_id=budget_id)

        # Filter by change type if provided
        change_type = self.request.query_params.get("change_type")
        if change_type:
            qs = qs.filter(change_type=change_type)

        return qs
