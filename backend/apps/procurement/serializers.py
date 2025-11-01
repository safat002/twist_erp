from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.budgeting.models import BudgetLine

from .models import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequisition,
    PurchaseRequisitionLine,
    Supplier,
)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            "id",
            "company",
            "code",
            "name",
            "email",
            "phone",
            "address",
            "payment_terms",
            "is_active",
            "payable_account",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        validated_data["company"] = company
        if request and request.user and "created_by" not in validated_data:
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class PurchaseRequisitionLineSerializer(serializers.ModelSerializer):
    procurement_class = serializers.CharField(source="procurement_class", read_only=True)
    budget_line_name = serializers.CharField(source="budget_line.product_name", read_only=True)
    budget_line_available_value = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseRequisitionLine
        fields = [
            "id",
            "requisition",
            "line_number",
            "budget_line",
            "budget_line_name",
            "budget_line_available_value",
            "cost_center",
            "product",
            "description",
            "quantity",
            "uom",
            "estimated_unit_cost",
            "estimated_total_cost",
            "needed_by",
            "procurement_class",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "requisition",
            "estimated_total_cost",
            "procurement_class",
            "metadata",
            "created_at",
            "updated_at",
            "budget_line_name",
            "budget_line_available_value",
        ]

    def get_budget_line_available_value(self, obj: PurchaseRequisitionLine) -> str:
        return f"{obj.budget_line.available_value}"


class PurchaseRequisitionSerializer(serializers.ModelSerializer):
    lines = PurchaseRequisitionLineSerializer(many=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PurchaseRequisition
        fields = [
            "id",
            "company",
            "requisition_number",
            "status",
            "status_display",
            "priority",
            "request_type",
            "is_emergency",
            "justification",
            "required_by",
            "total_estimated_value",
            "total_estimated_quantity",
            "workflow_state",
            "submitted_at",
            "approved_at",
            "rejected_at",
            "cancellation_reason",
            "cost_center",
            "requested_by",
            "approved_by",
            "lines",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "company",
            "requisition_number",
            "status",
            "status_display",
            "total_estimated_value",
            "total_estimated_quantity",
            "workflow_state",
            "submitted_at",
            "approved_at",
            "rejected_at",
            "requested_by",
            "approved_by",
            "created_at",
            "updated_at",
        ]

    def validate_lines(self, value):
        if not value:
            raise serializers.ValidationError("At least one line is required.")
        procurement_classes = {line.get("budget_line").procurement_class for line in value if line.get("budget_line")}
        if len(procurement_classes) > 1:
            raise serializers.ValidationError("All lines must use budget lines with the same procurement class.")
        return value

    def _build_line(self, requisition: PurchaseRequisition, line_data: dict, line_number: int) -> PurchaseRequisitionLine:
        budget_line: BudgetLine = line_data["budget_line"]
        quantity = Decimal(line_data.get("quantity") or "0")
        unit_cost = Decimal(line_data.get("estimated_unit_cost") or "0")
        instance = PurchaseRequisitionLine(
            requisition=requisition,
            line_number=line_data.get("line_number") or line_number,
            budget_line=budget_line,
            cost_center=line_data.get("cost_center") or requisition.cost_center,
            product=line_data.get("product"),
            description=line_data.get("description", ""),
            quantity=quantity,
            uom=line_data.get("uom"),
            estimated_unit_cost=unit_cost,
            needed_by=line_data.get("needed_by"),
            metadata=line_data.get("metadata") or {},
        )
        instance.estimated_total_cost = quantity * unit_cost
        instance.ensure_budget_capacity()
        instance.save()
        return instance

    def create(self, validated_data):
        lines_data = validated_data.pop("lines", [])
        request = self.context.get("request")
        company = getattr(request, "company", None)
        user = getattr(request, "user", None)
        if not validated_data.get("request_type") and lines_data:
            first_line = lines_data[0]
            if first_line.get("budget_line"):
                validated_data["request_type"] = first_line["budget_line"].procurement_class
        with transaction.atomic():
            requisition = PurchaseRequisition.objects.create(
                company=company,
                requested_by=user or validated_data.pop("requested_by", None),
                **validated_data,
            )
            for idx, line in enumerate(lines_data, start=1):
                self._build_line(requisition, line, idx)
            requisition.refresh_totals(commit=True)
        return requisition

    def update(self, instance, validated_data):
        lines_data = validated_data.pop("lines", None)
        if instance.status not in {PurchaseRequisition.Status.DRAFT}:
            raise serializers.ValidationError("Only draft requisitions can be modified.")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            for idx, line in enumerate(lines_data, start=1):
                self._build_line(instance, line, idx)
        instance.refresh_totals(commit=True)
        return instance


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    procurement_class = serializers.CharField(source="procurement_class", read_only=True)
    quantity_ordered = serializers.DecimalField(max_digits=15, decimal_places=3, source="quantity")
    product_name = serializers.CharField(source="product.name", read_only=True, default=None)
    budget_line_name = serializers.CharField(source="budget_line.product_name", read_only=True, default=None)
    remaining_quantity = serializers.SerializerMethodField()
    within_tolerance = serializers.BooleanField(read_only=True)

    class Meta:
        model = PurchaseOrderLine
        fields = [
            "id",
            "purchase_order",
            "line_number",
            "requisition_line",
            "budget_line",
            "budget_commitment",
            "product",
            "product_name",
            "description",
            "quantity_ordered",
            "expected_delivery_date",
            "unit_price",
            "tax_rate",
            "line_total",
            "tax_value",
            "tolerance_percent",
            "within_tolerance",
            "received_quantity",
            "status",
            "remaining_quantity",
            "metadata",
            "procurement_class",
            "budget_line_name",
        ]
        read_only_fields = [
            "purchase_order",
            "budget_commitment",
            "line_total",
            "tax_value",
            "within_tolerance",
            "received_quantity",
            "status",
            "remaining_quantity",
            "procurement_class",
            "product_name",
            "budget_line_name",
        ]

    def get_remaining_quantity(self, obj: PurchaseOrderLine) -> str:
        return f"{obj.remaining_quantity}"


class PurchaseOrderSerializer(serializers.ModelSerializer):
    lines = PurchaseOrderLineSerializer(many=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    cost_center_name = serializers.CharField(source="cost_center.name", read_only=True, default=None)
    request_type = serializers.CharField(source="requisition.request_type", read_only=True, default=None)
    request_type_display = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "company",
            "supplier",
            "supplier_name",
            "requisition",
            "cost_center",
            "cost_center_name",
            "order_number",
            "external_reference",
            "order_date",
            "expected_delivery_date",
            "currency",
            "subtotal",
            "tax_amount",
            "total_amount",
            "status",
            "status_display",
            "request_type",
            "request_type_display",
            "workflow_state",
            "is_emergency",
            "notes",
            "delivery_address",
            "approved_by",
            "approved_at",
            "issued_at",
            "closed_at",
            "created_by",
            "created_at",
            "updated_at",
            "lines",
        ]
        read_only_fields = [
            "company",
            "order_number",
            "subtotal",
            "tax_amount",
            "total_amount",
            "status",
            "status_display",
            "request_type",
            "request_type_display",
            "workflow_state",
            "approved_by",
            "approved_at",
            "issued_at",
            "closed_at",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def get_request_type_display(self, obj):
        if obj.requisition:
            return obj.requisition.get_request_type_display()
        return None

    def create(self, validated_data):
        lines_data = validated_data.pop("lines", [])
        request = self.context.get("request")
        company = getattr(request, "company", None)
        user = getattr(request, "user", None)
        with transaction.atomic():
            purchase_order = PurchaseOrder.objects.create(
                company=company,
                created_by=user,
                **validated_data,
            )
            for idx, line in enumerate(lines_data, start=1):
                PurchaseOrderLine.objects.create(
                    purchase_order=purchase_order,
                    line_number=line.get("line_number") or idx,
                    **line,
                )
            purchase_order.refresh_totals(commit=True)
        if purchase_order.requisition:
            purchase_order.requisition.mark_converted()
        return purchase_order

    def update(self, instance, validated_data):
        lines_data = validated_data.pop("lines", None)
        if instance.status not in {PurchaseOrder.Status.DRAFT, PurchaseOrder.Status.PENDING_APPROVAL}:
            raise serializers.ValidationError("Only draft or pending approval purchase orders can be modified.")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            for idx, line in enumerate(lines_data, start=1):
                PurchaseOrderLine.objects.create(
                    purchase_order=instance,
                    line_number=line.get("line_number") or idx,
                    **line,
                )
            instance.refresh_totals(commit=True)
        return instance
