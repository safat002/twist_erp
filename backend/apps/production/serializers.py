from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Iterable, List

from django.db import transaction
from rest_framework import serializers

from apps.companies.models import Company
from apps.inventory.models import Product, Warehouse

from .models import (
    BillOfMaterial,
    BillOfMaterialComponent,
    MaterialIssue,
    MaterialIssueLine,
    ProductionReceipt,
    WorkOrder,
    WorkOrderComponent,
)


def _require_company(context: Dict[str, Any]) -> Company:
    request = context.get("request")
    company = getattr(request, "company", None)
    if company is None and request is not None:
        company_id = request.META.get("HTTP_X_COMPANY_ID")
        if company_id:
            company = Company.objects.filter(pk=company_id).first()
            if company:
                setattr(request, "company", company)
    if company is None:
        raise serializers.ValidationError("Active company context is required.")
    return company


class BillOfMaterialComponentSerializer(serializers.ModelSerializer):
    component_detail = serializers.SerializerMethodField()

    class Meta:
        model = BillOfMaterialComponent
        fields = [
            "id",
            "sequence",
            "component",
            "component_detail",
            "quantity",
            "uom",
            "scrap_percent",
            "warehouse",
        ]

    def get_component_detail(self, obj: BillOfMaterialComponent) -> Dict[str, Any]:
        return {
            "id": obj.component_id,
            "code": obj.component.code,
            "name": obj.component.name,
        }


class BillOfMaterialSerializer(serializers.ModelSerializer):
    components = BillOfMaterialComponentSerializer(many=True)

    class Meta:
        model = BillOfMaterial
        fields = [
            "id",
            "code",
            "product",
            "name",
            "version",
            "status",
            "is_primary",
            "effective_from",
            "effective_to",
            "revision_notes",
            "components",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["code", "created_at", "updated_at"]

    def validate_components(self, components: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
        if not components:
            raise serializers.ValidationError("Bill of materials requires at least one component.")
        return components

    @transaction.atomic
    def create(self, validated_data: Dict[str, Any]) -> BillOfMaterial:
        components = validated_data.pop("components", [])
        company = _require_company(self.context)
        request = self.context["request"]
        validated_data["company"] = company
        validated_data["company_group"] = company.company_group
        validated_data["created_by"] = request.user
        bom = BillOfMaterial.objects.create(**validated_data)
        self._save_components(bom, components)
        return bom

    @transaction.atomic
    def update(self, instance: BillOfMaterial, validated_data: Dict[str, Any]) -> BillOfMaterial:
        components = validated_data.pop("components", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = self.context["request"].user
        instance.save()
        if components is not None:
            instance.components.all().delete()
            self._save_components(instance, components)
        return instance

    def _save_components(self, bom: BillOfMaterial, components: List[Dict[str, Any]]):
        items = []
        for index, component in enumerate(components, start=1):
            product_value = component.get("component")
            product = product_value if isinstance(product_value, Product) else Product.objects.get(pk=product_value)
            uom_value = component.get("uom")
            warehouse_value = component.get("warehouse")
            uom_id = getattr(uom_value, "pk", uom_value)
            warehouse_id = getattr(warehouse_value, "pk", warehouse_value)
            items.append(
                BillOfMaterialComponent(
                    bom=bom,
                    sequence=component.get("sequence") or index,
                    component=product,
                    quantity=Decimal(component.get("quantity") or 0),
                    uom_id=uom_id,
                    scrap_percent=component.get("scrap_percent") or Decimal("0.00"),
                    warehouse_id=warehouse_id,
                )
            )
        BillOfMaterialComponent.objects.bulk_create(items)


class WorkOrderComponentSerializer(serializers.ModelSerializer):
    component_detail = serializers.SerializerMethodField()
    remaining_quantity = serializers.DecimalField(max_digits=15, decimal_places=3, read_only=True)

    class Meta:
        model = WorkOrderComponent
        fields = [
            "id",
            "component",
            "component_detail",
            "required_quantity",
            "issued_quantity",
            "remaining_quantity",
            "uom",
            "scrap_percent",
            "preferred_warehouse",
        ]

    def get_component_detail(self, obj: WorkOrderComponent) -> Dict[str, Any]:
        return {
            "id": obj.component_id,
            "code": obj.component.code,
            "name": obj.component.name,
        }


class MaterialIssueLineSerializer(serializers.ModelSerializer):
    product_detail = serializers.SerializerMethodField()

    class Meta:
        model = MaterialIssueLine
        fields = ["id", "component", "product", "product_detail", "quantity", "warehouse"]

    def get_product_detail(self, obj: MaterialIssueLine) -> Dict[str, Any]:
        return {"id": obj.product_id, "code": obj.product.code, "name": obj.product.name}


class MaterialIssueSerializer(serializers.ModelSerializer):
    lines = MaterialIssueLineSerializer(many=True, read_only=True)

    class Meta:
        model = MaterialIssue
        fields = ["id", "issue_number", "issue_date", "notes", "lines", "created_at"]


class ProductionReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionReceipt
        fields = [
            "id",
            "receipt_number",
            "receipt_date",
            "quantity_good",
            "quantity_scrap",
            "warehouse",
            "notes",
            "created_at",
        ]


class WorkOrderSerializer(serializers.ModelSerializer):
    components = WorkOrderComponentSerializer(many=True, read_only=True)
    issues = MaterialIssueSerializer(many=True, read_only=True)
    receipts = ProductionReceiptSerializer(many=True, read_only=True)

    class Meta:
        model = WorkOrder
        fields = [
            "id",
            "number",
            "product",
            "bom",
            "quantity_planned",
            "quantity_completed",
            "status",
            "priority",
            "scheduled_start",
            "scheduled_end",
            "actual_start",
            "actual_end",
            "warehouse",
            "notes",
            "components",
            "issues",
            "receipts",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["number", "quantity_completed", "actual_start", "actual_end", "created_at", "updated_at"]

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        scheduled_start = attrs.get("scheduled_start") or getattr(self.instance, "scheduled_start", None)
        scheduled_end = attrs.get("scheduled_end") or getattr(self.instance, "scheduled_end", None)
        if scheduled_end and scheduled_start and scheduled_end < scheduled_start:
            raise serializers.ValidationError("Scheduled end cannot be before scheduled start.")
        return attrs

    @transaction.atomic
    def create(self, validated_data: Dict[str, Any]) -> WorkOrder:
        company = _require_company(self.context)
        request = self.context["request"]
        validated_data["company"] = company
        validated_data["company_group"] = company.company_group
        validated_data["created_by"] = request.user
        return WorkOrder.objects.create(**validated_data)

    @transaction.atomic
    def update(self, instance: WorkOrder, validated_data: Dict[str, Any]) -> WorkOrder:
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = self.context["request"].user
        instance.save()
        return instance


class MaterialIssueCreateSerializer(serializers.Serializer):
    issue_date = serializers.DateField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    lines = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def validate_lines(self, lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not lines:
            raise serializers.ValidationError("Provide at least one line to issue.")
        for line in lines:
            if "component" not in line or "quantity" not in line:
                raise serializers.ValidationError("Each line requires component and quantity.")
            if Decimal(line.get("quantity") or 0) <= 0:
                raise serializers.ValidationError("Quantity must be greater than zero.")
        return lines


class ProductionReceiptCreateSerializer(serializers.Serializer):
    receipt_date = serializers.DateField(required=False)
    quantity_good = serializers.DecimalField(max_digits=15, decimal_places=3)
    quantity_scrap = serializers.DecimalField(max_digits=15, decimal_places=3, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_quantity_good(self, value: Decimal) -> Decimal:
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value
