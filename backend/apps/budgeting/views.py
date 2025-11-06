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

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = (
            Budget.objects.select_related("cost_center", "company", "approved_by")
            .prefetch_related("lines")
            .order_by("-period_start")
        )
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        company = getattr(self.request, "company", None)
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
        BudgetApprovalService.approve_by_cost_center_owner(
            budget,
            request.user,
            request.data.get("comments", ""),
            request.data.get("modifications", {}),
        )
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def reject_cc(self, request, pk=None):
        budget = self.get_object()
        if budget.status not in {Budget.STATUS_PENDING_CC_APPROVAL}:
            return Response({"detail": "Budget is not pending cost center approvals."}, status=status.HTTP_400_BAD_REQUEST)
        BudgetApprovalService.reject_by_cost_center_owner(budget, request.user, request.data.get("comments", ""))
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def request_final_approval(self, request, pk=None):
        budget = self.get_object()
        if budget.status not in {Budget.STATUS_CC_APPROVED}:
            return Response({"detail": "Budget needs CC approval before final approval."}, status=status.HTTP_400_BAD_REQUEST)
        BudgetApprovalService.request_final_approval(budget)
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def approve_final(self, request, pk=None):
        budget = self.get_object()
        if budget.status not in {Budget.STATUS_PENDING_FINAL_APPROVAL}:
            return Response({"detail": "Budget is not pending final approval."}, status=status.HTTP_400_BAD_REQUEST)
        BudgetApprovalService.approve_by_module_owner(budget, request.user, request.data.get("comments", ""))
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def reject_final(self, request, pk=None):
        budget = self.get_object()
        if budget.status not in {Budget.STATUS_PENDING_FINAL_APPROVAL}:
            return Response({"detail": "Budget is not pending final approval."}, status=status.HTTP_400_BAD_REQUEST)
        BudgetApprovalService.reject_by_module_owner(budget, request.user, request.data.get("comments", ""))
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
        data = BudgetGamificationService.kpis(company)
        return Response(data)

    @action(detail=True, methods=["get"])
    def lines(self, request, pk=None):
        budget = self.get_object()
        serializer = BudgetLineSerializer(budget.lines.all(), many=True, context={"request": request})
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
                {"detail": "Budget is not in moderator review stage."},
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

        # Check if user is moderator
        if not BudgetPermissionService.user_is_budget_moderator(request.user, company):
            return Response(
                {"detail": "Only moderators can view the moderation queue."},
                status=status.HTTP_403_FORBIDDEN
            )

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
        qs = BudgetLine.objects.select_related("budget", "budget__cost_center", "budget_owner")
        if company:
            qs = qs.filter(budget__company=company)
        # Server-side filters for tighter lookups
        # cost_center: numeric id of CostCenter
        cost_center_id = self.request.query_params.get("cost_center")
        if cost_center_id:
            try:
                qs = qs.filter(budget__cost_center_id=int(cost_center_id))
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

    def perform_create(self, serializer):
        budget = serializer.validated_data["budget"]
        if getattr(self.request, "company", None) and budget.company != self.request.company:
            raise serializers.ValidationError("Budget does not belong to the active company.")
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

        # Check review period restrictions
        if budget.is_review_period_active():
            can_edit, reason = BudgetReviewPeriodService.can_edit_budget_line_in_review_period(instance, user)
            if not can_edit:
                raise serializers.ValidationError(reason)

            # During review period, use variance tracking update
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
                role="cc_owner"
            )
            budget.recalculate_totals(commit=True)
            return

        # Normal editing restrictions (not in review period)
        editable = budget.status in {Budget.STATUS_DRAFT, Budget.STATUS_ENTRY_OPEN}
        cc_owner_window = budget.status == Budget.STATUS_PENDING_CC_APPROVAL and (
            budget.cost_center and (budget.cost_center.owner_id == user.id or budget.cost_center.deputy_owner_id == user.id)
        )
        if not (editable or cc_owner_window):
            raise serializers.ValidationError("This budget is not editable in its current status.")

        instance = serializer.save()
        budget.recalculate_totals(commit=True)

    def perform_destroy(self, instance):
        budget = instance.budget
        user = self.request.user
        editable = budget.status in {Budget.STATUS_DRAFT, Budget.STATUS_ENTRY_OPEN}
        cc_owner_window = budget.status == Budget.STATUS_PENDING_CC_APPROVAL and (
            budget.cost_center and (budget.cost_center.owner_id == user.id or budget.cost_center.deputy_owner_id == user.id)
        )
        if not (editable or cc_owner_window):
            raise serializers.ValidationError("This budget is not editable in its current status.")
        instance.delete()
        budget.recalculate_totals(commit=True)

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
            qs = qs.filter(company__company_group_id=company.company_group_id)
        elif company:
            qs = qs.filter(company=company)
        return qs

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
            qs = qs.filter(company__company_group_id=company.company_group_id)
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
            qs = qs.filter(company__company_group_id=company.company_group_id)
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
        # Show declared budgets whose entry window covers today (regardless of status)
        qs = Budget.objects.filter(cost_center__isnull=True)
        qs = qs.filter(entry_start_date__lte=today, entry_end_date__gte=today)
        if company:
            qs = qs.filter(company=company)
        data = [
            {
                "id": b.id,
                "name": b.name,
                "budget_type": b.budget_type,
                "period_start": b.period_start,
                "period_end": b.period_end,
            }
            for b in qs.order_by("-period_start")
        ]
        return Response(data)


class EntrySummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        company = getattr(request, "company", None)
        declared_id = request.query_params.get("budget")
        declared = None
        if declared_id:
            declared = Budget.objects.filter(pk=declared_id, cost_center__isnull=True).first()
        cc_qs = CostCenter.objects.all()
        if company:
            cc_qs = cc_qs.filter(company=company)
        cc_qs = cc_qs.filter(models.Q(owner=user) | models.Q(deputy_owner=user) | models.Q(budget_entry_users=user))
        permitted_ids = list(cc_qs.values_list("id", flat=True).distinct())
        bl_qs = BudgetLine.objects.filter(budget__cost_center_id__in=permitted_ids)
        if company:
            bl_qs = bl_qs.filter(budget__company=company)
        if declared:
            bl_qs = bl_qs.filter(
                budget__budget_type=declared.budget_type,
                budget__period_start=declared.period_start,
                budget__period_end=declared.period_end,
            )
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
            declared = Budget.objects.get(pk=declared_id, cost_center__isnull=True)
            cc = CostCenter.objects.get(pk=cost_center_id)
        except (Budget.DoesNotExist, CostCenter.DoesNotExist):
            return Response({"detail": "Invalid budget or cost center"}, status=status.HTTP_404_NOT_FOUND)
        # Find latest revision for this cc under declared
        cc_budget = (
            Budget.objects.filter(
                company=company or declared.company,
                cost_center=cc,
                budget_type=declared.budget_type,
                period_start=declared.period_start,
                period_end=declared.period_end,
            )
            .order_by("-revision_no", "-id")
            .first()
        )
        if not cc_budget:
            # lazily create editable CC budget
            cc_budget = Budget.objects.create(
                company=declared.company,
                cost_center=cc,
                budget_type=declared.budget_type,
                period_start=declared.period_start,
                period_end=declared.period_end,
                name=declared.name,
                entry_start_date=declared.entry_start_date,
                entry_end_date=declared.entry_end_date,
                threshold_percent=declared.threshold_percent,
                parent_declared=declared,
                status=Budget.STATUS_DRAFT,
                revision_no=1,
            )
        serializer = BudgetLineSerializer(cc_budget.lines.all(), many=True, context={"request": request})
        return Response({
            "cc_budget": BudgetSerializer(cc_budget, context={"request": request}).data,
            "lines": serializer.data,
        })


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
            declared = Budget.objects.get(pk=declared_budget_id, cost_center__isnull=True)
        except CostCenter.DoesNotExist:
            return Response({"detail": "Cost center not found"}, status=status.HTTP_404_NOT_FOUND)
        except Budget.DoesNotExist:
            return Response({"detail": "Declared budget not found"}, status=status.HTTP_404_NOT_FOUND)
        # Permission and entry window
        if not BudgetPermissionService.user_can_enter_for_cost_center(user, cc):
            return Response({"detail": "Not permitted for this cost center"}, status=status.HTTP_403_FORBIDDEN)
        if not declared.is_entry_period_active():
            return Response({"detail": "Entry period is not active"}, status=status.HTTP_400_BAD_REQUEST)
        # Find latest CC budget; if not editable, create new revision
        latest = (
            Budget.objects.filter(
                company=company or declared.company,
                cost_center=cc,
                budget_type=declared.budget_type,
                period_start=declared.period_start,
                period_end=declared.period_end,
            )
            .order_by("-revision_no", "-id")
            .first()
        )
        if latest and latest.status in {Budget.STATUS_DRAFT, Budget.STATUS_ENTRY_OPEN}:
            cc_budget = latest
        else:
            next_rev = (latest.revision_no + 1) if latest else 1
            cc_budget = Budget.objects.create(
                company=declared.company,
                cost_center=cc,
                budget_type=declared.budget_type,
                period_start=declared.period_start,
                period_end=declared.period_end,
                name=declared.name,
                entry_start_date=declared.entry_start_date,
                entry_end_date=declared.entry_end_date,
                threshold_percent=declared.threshold_percent,
                parent_declared=declared,
                status=Budget.STATUS_DRAFT,
                revision_no=next_rev,
            )
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
        value_limit = (unit_price or Decimal("0")) * qty
        line = BudgetLine.objects.create(
            budget=cc_budget,
            procurement_class=procurement_class,
            item_code=item_code,
            item_name=item_name or item_code,
            qty_limit=qty,
            standard_price=unit_price,
            manual_unit_price=(unit_price if source == "manual" else None),
            value_limit=value_limit,
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
            declared = Budget.objects.get(pk=declared_budget_id, cost_center__isnull=True)
        except (CostCenter.DoesNotExist, Budget.DoesNotExist):
            return Response({"detail": "Invalid cost center or budget"}, status=status.HTTP_404_NOT_FOUND)
        # Find latest revision for this CC
        cc_budget = (
            Budget.objects.filter(
                company=declared.company,
                cost_center=cc,
                budget_type=declared.budget_type,
                period_start=declared.period_start,
                period_end=declared.period_end,
            )
            .order_by("-revision_no", "-id")
            .first()
        )
        if not cc_budget:
            return Response({"detail": "No entries found for this cost center"}, status=status.HTTP_400_BAD_REQUEST)
        if cc_budget.status not in {Budget.STATUS_DRAFT, Budget.STATUS_ENTRY_OPEN}:
            # create a new revision when trying to submit again
            cc_budget = Budget.objects.create(
                company=declared.company,
                cost_center=cc,
                budget_type=declared.budget_type,
                period_start=declared.period_start,
                period_end=declared.period_end,
                name=declared.name,
                entry_start_date=declared.entry_start_date,
                entry_end_date=declared.entry_end_date,
                threshold_percent=declared.threshold_percent,
                parent_declared=declared,
                status=Budget.STATUS_DRAFT,
                revision_no=(cc_budget.revision_no + 1),
            )
        # Submit for CC approval
        cc_budget.submit_for_approval(user=request.user)
        BudgetApprovalService.request_cost_center_approvals(cc_budget)
        return Response(BudgetSerializer(cc_budget, context={"request": request}).data)


class BudgetApprovalQueueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import BudgetApproval as BA
        approvals = BA.objects.select_related("budget", "cost_center").filter(
            approver=request.user, status=BA.Status.PENDING
        ).order_by("-created_at")
        data = []
        for a in approvals:
            data.append({
                "id": a.id,
                "budget_id": a.budget_id,
                "budget_name": a.budget.name,
                "approver_type": a.approver_type,
                "status": a.status,
                "cost_center": getattr(a.cost_center, "name", None),
                "created_at": a.created_at,
            })
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
