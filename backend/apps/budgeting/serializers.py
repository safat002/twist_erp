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
    BudgetItemCode,
    BudgetApproval,
    BudgetRemarkTemplate,
    BudgetVarianceAudit,
)
from apps.inventory.models import UnitOfMeasure


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
        if company is None and request is not None:
            user = getattr(request, "user", None)
            if user is not None:
                company = getattr(user, "default_company", None)
        if company is None:
            raise serializers.ValidationError({"detail": "No active company selected. Please select a company and try again."})
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
    modified_by_display = serializers.SerializerMethodField()
    held_by_display = serializers.SerializerMethodField()
    moderator_remarks_by_display = serializers.SerializerMethodField()

    class Meta:
        model = BudgetLine
        fields = [
            "id",
            "budget",
            "budget_name",
            "sequence",
            "procurement_class",
            "item_code",
            "product",
            "item_name",
            "category",
            "project_code",
            # Current limits
            "qty_limit",
            "value_limit",
            "standard_price",
            "tolerance_percent",
            # Original values for variance tracking
            "original_qty_limit",
            "original_unit_price",
            "original_value_limit",
            # Variance tracking
            "qty_variance",
            "price_variance",
            "value_variance",
            "variance_percent",
            # Consumption
            "consumed_quantity",
            "consumed_value",
            "committed_quantity",
            "committed_value",
            "remaining_quantity",
            "remaining_value",
            "available_quantity",
            "available_value",
            # Modification tracking
            "modified_by",
            "modified_by_display",
            "modified_at",
            "modification_reason",
            # Held items
            "is_held_for_review",
            "held_by",
            "held_by_display",
            "held_reason",
            "held_until_date",
            "sent_back_for_review",
            # Moderator remarks
            "moderator_remarks",
            "moderator_remarks_by",
            "moderator_remarks_by_display",
            "moderator_remarks_at",
            "cc_owner_modification_notes",
            # AI projections
            "projected_consumption_value",
            "projected_consumption_confidence",
            "will_exceed_budget",
            # General
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
            "qty_variance",
            "price_variance",
            "value_variance",
            "variance_percent",
            "modified_by_display",
            "held_by_display",
            "moderator_remarks_by_display",
            "created_at",
            "updated_at",
        ]

    def get_remaining_value(self, obj: BudgetLine) -> str:
        return f"{obj.remaining_value}"

    def validate(self, attrs):
        # Enforce item code vs product linkage per budget type
        budget = attrs.get("budget")
        if not budget and self.instance:
            budget = self.instance.budget
        if budget and getattr(budget, "budget_type", None) == Budget.TYPE_REVENUE:
            # Revenue budgets must be product-based
            product = attrs.get("product") or (self.instance.product if self.instance else None)
            if not product:
                raise serializers.ValidationError({"product": "Product is required for revenue budgets."})
            # If product present and no item_code/name provided, derive basic values for display
            if not attrs.get("item_code") and hasattr(product, "code"):
                attrs["item_code"] = product.code
            if not attrs.get("item_name") and hasattr(product, "name"):
                attrs["item_name"] = product.name
        else:
            # Non-revenue budgets should be based on item code; product optional/ignored
            if not attrs.get("item_code") and not (self.instance and self.instance.item_code):
                raise serializers.ValidationError({"item_code": "Item code is required for non-revenue budgets."})
        return attrs

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

    def get_modified_by_display(self, obj: BudgetLine) -> str | None:
        user = obj.modified_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    def get_held_by_display(self, obj: BudgetLine) -> str | None:
        user = obj.held_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    def get_moderator_remarks_by_display(self, obj: BudgetLine) -> str | None:
        user = obj.moderator_remarks_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)


class BudgetApprovalSerializer(serializers.ModelSerializer):
    approver_name = serializers.SerializerMethodField()
    cost_center_name = serializers.SerializerMethodField()

    class Meta:
        model = BudgetApproval
        fields = "__all__"

    def get_approver_name(self, obj: BudgetApproval) -> str | None:
        u = obj.approver
        return getattr(u, "get_full_name", lambda: None)() or getattr(u, "username", None) if u else None

    def get_cost_center_name(self, obj: BudgetApproval) -> str | None:
        return getattr(obj.cost_center, "name", None)


class BudgetSerializer(serializers.ModelSerializer):
    available = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    line_count = serializers.IntegerField(read_only=True)
    lines = BudgetLineSerializer(many=True, read_only=True)
    is_entry_period_active = serializers.SerializerMethodField()
    is_review_period_active = serializers.SerializerMethodField()
    is_budget_impact_active = serializers.SerializerMethodField()
    pending_approvals = serializers.SerializerMethodField()
    user_can_enter = serializers.SerializerMethodField()
    approvals = BudgetApprovalSerializer(many=True, read_only=True)
    duration_display = serializers.SerializerMethodField()
    moderator_reviewed_by_display = serializers.SerializerMethodField()
    final_approved_by_display = serializers.SerializerMethodField()
    activated_by_display = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            "id",
            "cost_center",
            "name",
            "budget_type",
            # Duration and period configuration
            "duration_type",
            "duration_display",
            "custom_duration_days",
            "period_start",
            "period_end",
            # Entry period
            "entry_start_date",
            "entry_end_date",
            "entry_enabled",
            # Review period and grace
            "grace_period_days",
            "review_start_date",
            "review_end_date",
            "review_enabled",
            # Budget impact period
            "budget_impact_start_date",
            "budget_impact_end_date",
            "budget_impact_enabled",
            # Legacy date fields (backward compatibility)
            "budget_active_date",
            "budget_expire_date",
            # Auto-approval
            "auto_approve_if_not_approved",
            "auto_approve_by_role",
            "auto_approved_at",
            # Amounts and variance
            "amount",
            "consumed",
            "committed",
            "remaining",
            "total_variance_amount",
            "total_variance_count",
            "threshold_percent",
            # Status and workflow
            "status",
            "workflow_state",
            # Moderator review tracking
            "moderator_reviewed_by",
            "moderator_reviewed_by_display",
            "moderator_reviewed_at",
            # Final approval tracking
            "final_approved_by",
            "final_approved_by_display",
            "final_approved_at",
            # Activation tracking
            "activated_by",
            "activated_by_display",
            "activated_at",
            # Relations
            "line_count",
            "lines",
            "approvals",
            # Metadata and helpers
            "metadata",
            "available",
            "is_entry_period_active",
            "is_review_period_active",
            "is_budget_impact_active",
            "pending_approvals",
            "user_can_enter",
            # Timestamps
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "line_count",
            "available",
            "consumed",
            "committed",
            "remaining",
            "amount",
            "total_variance_amount",
            "total_variance_count",
            "is_entry_period_active",
            "is_review_period_active",
            "is_budget_impact_active",
            "pending_approvals",
            "user_can_enter",
            "duration_display",
            "moderator_reviewed_by_display",
            "final_approved_by_display",
            "activated_by_display",
            "auto_approved_at",
            "moderator_reviewed_at",
            "final_approved_at",
            "activated_at",
        ]
        extra_kwargs = {
            "cost_center": {"required": False, "allow_null": True},
        }

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["available"] = f"{instance.available}"
        return rep

    def get_is_entry_period_active(self, obj: Budget) -> bool:
        return obj.is_entry_period_active()

    def get_is_review_period_active(self, obj: Budget) -> bool:
        return obj.is_review_period_active()

    def get_is_budget_impact_active(self, obj: Budget) -> bool:
        return obj.is_budget_impact_active()

    def get_duration_display(self, obj: Budget) -> str:
        return obj.get_duration_display()

    def get_pending_approvals(self, obj: Budget):
        qs = obj.get_pending_cost_center_approvals()
        try:
            return BudgetApprovalSerializer(qs, many=True).data if qs else []
        except Exception:
            return []

    def get_user_can_enter(self, obj: Budget) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return obj.can_user_enter_budget(user) if user else False

    def get_moderator_reviewed_by_display(self, obj: Budget) -> str | None:
        user = obj.moderator_reviewed_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    def get_final_approved_by_display(self, obj: Budget) -> str | None:
        user = obj.final_approved_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    def get_activated_by_display(self, obj: Budget) -> str | None:
        user = obj.activated_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        company = getattr(request, "company", None) if request else None
        if company is None and user is not None:
            company = getattr(user, "default_company", None)
        if company is None:
            raise serializers.ValidationError({"detail": "No active company selected. Please select a company and try again."})
        validated_data.setdefault("created_by", user)
        return Budget.objects.create(company=company, **validated_data)

    def update(self, instance, validated_data):
        user = self.context.get("request").user if self.context.get("request") else None
        if user and hasattr(instance, "updated_by"):
            validated_data["updated_by"] = user
        return super().update(instance, validated_data)

    def validate(self, attrs):
        # Require entry window on create
        if self.instance is None:
            es = attrs.get("entry_start_date")
            ee = attrs.get("entry_end_date")
            if not es or not ee:
                raise serializers.ValidationError({
                    "entry_start_date": "Required",
                    "entry_end_date": "Required",
                })
            if es and ee and ee < es:
                raise serializers.ValidationError("entry_end_date cannot be before entry_start_date")
        return attrs


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


class BudgetItemCodeSerializer(serializers.ModelSerializer):
    uom_name = serializers.ReadOnlyField(source="uom.name")

    class Meta:
        model = BudgetItemCode
        fields = [
            "id",
            "company",
            "code",
            "name",
            "category",
            "uom",
            "uom_name",
            "standard_price",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        return BudgetItemCode.objects.create(company=company, **validated_data)


class BudgetUnitOfMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitOfMeasure
        fields = [
            "id",
            "company",
            "code",
            "name",
            "short_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        user = getattr(request, "user", None)
        return UnitOfMeasure.objects.create(company=company, created_by=user, **validated_data)


class BudgetRemarkTemplateSerializer(serializers.ModelSerializer):
    """Serializer for budget remark templates"""
    created_by_display = serializers.SerializerMethodField()

    class Meta:
        model = BudgetRemarkTemplate
        fields = [
            "id",
            "company",
            "name",
            "template_text",
            "remark_type",
            "is_predefined",
            "is_shared",
            "usage_count",
            "created_by",
            "created_by_display",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company", "usage_count", "created_by", "created_by_display", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        user = getattr(request, "user", None)
        validated_data["company"] = company
        validated_data["created_by"] = user
        return BudgetRemarkTemplate.objects.create(**validated_data)

    def get_created_by_display(self, obj: BudgetRemarkTemplate) -> str | None:
        user = obj.created_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    # No shared_with relation in current model; keep output minimal


class BudgetVarianceAuditSerializer(serializers.ModelSerializer):
    """Serializer for budget variance audit trail"""
    modified_by_display = serializers.SerializerMethodField()
    budget_line_display = serializers.SerializerMethodField()

    class Meta:
        model = BudgetVarianceAudit
        fields = [
            "id",
            "budget_line",
            "budget_line_display",
            "modified_by",
            "modified_by_display",
            "change_type",
            "role_of_modifier",
            "original_qty",
            "new_qty",
            "qty_delta",
            "original_price",
            "new_price",
            "price_delta",
            "original_value",
            "new_value",
            "value_delta",
            "justification",
            "review_period_active",
            "grace_period_active",
            "created_at",
        ]
        read_only_fields = [
            "budget_line_display",
            "modified_by_display",
            "qty_delta",
            "price_delta",
            "value_delta",
            "created_at",
        ]

    def get_modified_by_display(self, obj: BudgetVarianceAudit) -> str | None:
        user = obj.modified_by
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None)

    def get_budget_line_display(self, obj: BudgetVarianceAudit) -> dict:
        """Get budget line details for display"""
        line = obj.budget_line
        return {
            "id": line.id,
            "item_code": line.item_code,
            "item_name": line.item_name,
            "budget_name": line.budget.name,
        }
