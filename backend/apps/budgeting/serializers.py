from __future__ import annotations

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import (
    Budget,
    BudgetConsumptionSnapshot,
    BudgetLine,
    BudgetOverrideRequest,
    BudgetUsage,
    CostCenter,
)


class CostCenterSerializer(serializers.ModelSerializer):
    owner_display = serializers.SerializerMethodField()
    deputy_owner_display = serializers.SerializerMethodField()
    active_budget_count = serializers.SerializerMethodField()

    class Meta:
        model = CostCenter
        fields = [
            "id",
            "code",
            "name",
            "cost_center_type",
            "parent",
            "owner",
            "owner_display",
            "deputy_owner",
            "deputy_owner_display",
            "default_currency",
            "description",
            "is_active",
            "tags",
            "kpi_snapshot",
            "active_budget_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "active_budget_count", "owner_display", "deputy_owner_display"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        company_group = getattr(company, "company_group", None)
        return CostCenter.objects.create(company=company, company_group=company_group, **validated_data)

    def get_owner_display(self, obj: CostCenter) -> str | None:
        user = getattr(obj, "owner", None)
        if not user:
            return None
        name = getattr(user, "get_full_name", lambda: None)()
        return name or getattr(user, "username", None)

    def get_deputy_owner_display(self, obj: CostCenter) -> str | None:
        user = getattr(obj, "deputy_owner", None)
        if not user:
            return None
        name = getattr(user, "get_full_name", lambda: None)()
        return name or getattr(user, "username", None)

    def get_active_budget_count(self, obj: CostCenter) -> int:
        today = timezone.now().date()
        return obj.budgets.filter(period_start__lte=today, period_end__gte=today, status=Budget.STATUS_ACTIVE).count()


class BudgetLineSerializer(serializers.ModelSerializer):
    remaining_value = serializers.SerializerMethodField()
    remaining_quantity = serializers.SerializerMethodField()
    budget_name = serializers.ReadOnlyField(source="budget.name")
    committed_value = serializers.SerializerMethodField()
    committed_quantity = serializers.SerializerMethodField()
    available_value = serializers.SerializerMethodField()
    available_quantity = serializers.SerializerMethodField()

    class Meta:
        model = BudgetLine
        fields = [
            "id",
            "budget",
            "budget_name",
            "sequence",
            "procurement_class",
            "item_code",
            "item_name",
            "category",
            "project_code",
            "qty_limit",
            "value_limit",
            "standard_price",
            "tolerance_percent",
            "consumed_quantity",
            "consumed_value",
            "committed_quantity",
            "committed_value",
            "remaining_quantity",
            "remaining_value",
            "available_quantity",
            "available_value",
            "budget_owner",
            "is_active",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "consumed_quantity",
            "consumed_value",
            "remaining_quantity",
            "remaining_value",
            "committed_quantity",
            "committed_value",
            "available_quantity",
            "available_value",
            "created_at",
            "updated_at",
        ]

    def get_remaining_value(self, obj: BudgetLine) -> str:
        return f"{obj.remaining_value}"

    def get_remaining_quantity(self, obj: BudgetLine) -> str:
        return f"{obj.remaining_quantity}"

    def get_committed_value(self, obj: BudgetLine) -> str:
        return f"{obj.committed_value}"

    def get_committed_quantity(self, obj: BudgetLine) -> str:
        return f"{obj.committed_quantity}"

    def get_available_value(self, obj: BudgetLine) -> str:
        return f"{obj.available_value}"

    def get_available_quantity(self, obj: BudgetLine) -> str:
        return f"{obj.available_quantity}"


class BudgetSerializer(serializers.ModelSerializer):
    available = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    line_count = serializers.IntegerField(read_only=True)
    lines = BudgetLineSerializer(many=True, read_only=True)

    class Meta:
        model = Budget
        fields = [
            "id",
            "cost_center",
            "name",
            "budget_type",
            "period_start",
            "period_end",
            "amount",
            "consumed",
            "threshold_percent",
            "status",
            "workflow_state",
            "line_count",
            "lines",
            "metadata",
            "available",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "line_count", "available", "consumed", "amount"]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["available"] = f"{instance.available}"
        return rep

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        validated_data.setdefault("created_by", getattr(request, "user", None))
        return Budget.objects.create(company=company, **validated_data)

    def update(self, instance, validated_data):
        user = self.context.get("request").user if self.context.get("request") else None
        if user and hasattr(instance, "updated_by"):
            validated_data["updated_by"] = user
        return super().update(instance, validated_data)


class BudgetUsageSerializer(serializers.ModelSerializer):
    budget = serializers.CharField(source="budget_line.budget.name", read_only=True)
    cost_center = serializers.SerializerMethodField()

    class Meta:
        model = BudgetUsage
        fields = [
            "id",
            "budget_line",
            "budget",
            "cost_center",
            "usage_date",
            "usage_type",
            "quantity",
            "amount",
            "reference_type",
            "reference_id",
            "description",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["created_at", "budget", "cost_center"]

    def get_cost_center(self, obj: BudgetUsage) -> str:
        return str(obj.budget_line.budget.cost_center)


class BudgetOverrideRequestSerializer(serializers.ModelSerializer):
    cost_center_name = serializers.ReadOnlyField(source="cost_center.name")
    budget_line_name = serializers.ReadOnlyField(source="budget_line.item_name")
    requested_by_display = serializers.SerializerMethodField()
    approver_display = serializers.SerializerMethodField()

    class Meta:
        model = BudgetOverrideRequest
        fields = [
            "id",
            "cost_center",
            "cost_center_name",
            "budget_line",
            "budget_line_name",
            "requested_by",
            "requested_by_display",
            "approver",
            "approver_display",
            "status",
            "reason",
            "requested_quantity",
            "requested_amount",
            "decision_notes",
            "reference_type",
            "reference_id",
            "severity",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["approved_at", "created_at", "updated_at", "requested_by_display", "approver_display"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = validated_data.get("company")
        if not company and request:
            company = getattr(request, "company", None)
        if not company and validated_data.get("cost_center") is not None:
            company = validated_data["cost_center"].company
        if request and request.user and "requested_by" not in validated_data:
            validated_data["requested_by"] = request.user
        validated_data["company"] = company
        return super().create(validated_data)

    def get_requested_by_display(self, obj: BudgetOverrideRequest) -> str | None:
        user = obj.requested_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    def get_approver_display(self, obj: BudgetOverrideRequest) -> str | None:
        user = obj.approver
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)


class BudgetSnapshotSerializer(serializers.ModelSerializer):
    budget_name = serializers.ReadOnlyField(source="budget.name")

    class Meta:
        model = BudgetConsumptionSnapshot
        fields = [
            "id",
            "budget",
            "budget_name",
            "snapshot_date",
            "total_limit",
            "total_consumed",
            "total_remaining",
            "metrics",
            "created_at",
        ]
        read_only_fields = ["created_at"]
