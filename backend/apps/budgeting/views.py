from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db import models
from django.db.models import Count, F, Max, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
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
)
from .serializers import (
    BudgetLineSerializer,
    BudgetOverrideRequestSerializer,
    BudgetSerializer,
    BudgetSnapshotSerializer,
    BudgetUsageSerializer,
    CostCenterSerializer,
)


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
        instance = serializer.save(company=company, created_by=self.request.user)
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
        budget = self.get_object()
        if budget.status not in {Budget.STATUS_DRAFT, Budget.STATUS_PROPOSED}:
            return Response({"detail": "Only draft budgets can be submitted."}, status=status.HTTP_400_BAD_REQUEST)
        budget.status = Budget.STATUS_PROPOSED
        budget.workflow_state = "submitted"
        budget.updated_by = request.user
        budget.save(update_fields=["status", "workflow_state", "updated_by", "updated_at"])
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        budget = self.get_object()
        if budget.status not in {Budget.STATUS_PROPOSED, Budget.STATUS_UNDER_REVIEW}:
            return Response({"detail": "Budget must be proposed or under review to approve."}, status=status.HTTP_400_BAD_REQUEST)
        budget.mark_active(user=request.user)
        log_audit_event(
            user=request.user,
            company=budget.company,
            company_group=getattr(budget.company, "company_group", None),
            action="BUDGET_APPROVED",
            entity_type="Budget",
            entity_id=str(budget.id),
            description=f"Budget {budget.name} approved.",
        )
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        budget = self.get_object()
        budget.lock(user=request.user)
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

    @action(detail=True, methods=["get"])
    def lines(self, request, pk=None):
        budget = self.get_object()
        serializer = BudgetLineSerializer(budget.lines.all(), many=True, context={"request": request})
        return Response(serializer.data)


class BudgetLineViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BudgetLineSerializer

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = BudgetLine.objects.select_related("budget", "budget__cost_center", "budget_owner")
        if company:
            qs = qs.filter(budget__company=company)
        return qs

    def perform_create(self, serializer):
        budget = serializer.validated_data["budget"]
        if getattr(self.request, "company", None) and budget.company != self.request.company:
            raise serializers.ValidationError("Budget does not belong to the active company.")
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
        instance = serializer.save()
        instance.budget.recalculate_totals(commit=True)

    def perform_destroy(self, instance):
        budget = instance.budget
        instance.delete()
        budget.recalculate_totals(commit=True)


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
            "status__in": [Budget.STATUS_ACTIVE, Budget.STATUS_LOCKED],
        }
        line_filters = {"budget__cost_center": cost_center, "budget__status__in": [Budget.STATUS_ACTIVE, Budget.STATUS_LOCKED]}
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
