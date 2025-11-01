from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from .models import Asset, AssetMaintenancePlan, DepreciationRun, DowntimeLog, AssetDisposal
from apps.hr.models import EmployeeAssetAssignment


class AssetSerializer(serializers.ModelSerializer):
    book_value = serializers.SerializerMethodField()
    depreciation_to_date = serializers.SerializerMethodField()
    monthly_depreciation = serializers.SerializerMethodField()
    months_in_service = serializers.SerializerMethodField()
    next_maintenance = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = [
            "id",
            "name",
            "code",
            "barcode",
            "category",
            "location",
            "manufacturer",
            "model_number",
            "serial_number",
            "acquisition_date",
            "cost",
            "residual_value",
            "depreciation_method",
            "useful_life_months",
            "status",
            "is_active",
            "depreciation_expense_account",
            "accumulated_depreciation_account",
            "book_value",
            "depreciation_to_date",
            "monthly_depreciation",
            "months_in_service",
            "next_maintenance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "book_value",
            "depreciation_to_date",
            "monthly_depreciation",
            "months_in_service",
            "next_maintenance",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        if not company and request and request.user.is_authenticated:
            company = request.user.companies.filter(is_active=True).first()
        if not company:
            raise serializers.ValidationError({"company": "Active company context is required."})
        return Asset.objects.create(company=company, **validated_data)

    def get_book_value(self, obj: Asset) -> Decimal:
        return float(obj.book_value())

    def get_depreciation_to_date(self, obj: Asset) -> Decimal:
        return float(obj.depreciation_to_date())

    def get_monthly_depreciation(self, obj: Asset) -> Decimal:
        return float(obj.monthly_depreciation())

    def get_months_in_service(self, obj: Asset) -> int:
        return obj.months_in_service()

    def get_next_maintenance(self, obj: Asset):
        task = obj.next_maintenance()
        if not task:
            return None
        return {
            "id": task.id,
            "title": task.title,
            "scheduled_date": task.scheduled_date,
            "due_date": task.due_date,
            "status": task.status,
            "assigned_to": task.assigned_to,
        }


class AssetRegisterSerializer(AssetSerializer):
    pass


class MaintenanceTaskSerializer(serializers.ModelSerializer):
    asset_code = serializers.ReadOnlyField(source="asset.code")
    asset_name = serializers.ReadOnlyField(source="asset.name")
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = AssetMaintenancePlan
        fields = [
            "id",
            "asset",
            "asset_code",
            "asset_name",
            "title",
            "description",
            "maintenance_type",
            "scheduled_date",
            "due_date",
            "completed_at",
            "status",
            "assigned_to",
            "frequency_months",
            "cost_estimate",
            "notes",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "asset_code",
            "asset_name",
            "is_overdue",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        scheduled = attrs.get("scheduled_date") or getattr(self.instance, "scheduled_date", None)
        due = attrs.get("due_date") or getattr(self.instance, "due_date", None)
        if scheduled and due and due < scheduled:
            raise serializers.ValidationError({"due_date": "Due date cannot be earlier than scheduled date."})
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        if not company and request and request.user.is_authenticated:
            company = request.user.companies.filter(is_active=True).first()
        if not company and "asset" in validated_data:
            company = validated_data["asset"].company
        if not company:
            raise serializers.ValidationError({"company": "Active company context is required."})
        validated_data["company"] = company
        return super().create(validated_data)

    def get_is_overdue(self, obj: AssetMaintenancePlan) -> bool:
        return obj.is_overdue


class DepreciationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepreciationRun
        fields = [
            "id",
            "company",
            "period",
            "total_amount",
            "voucher",
            "created_at",
        ]
        read_only_fields = ["id", "company", "total_amount", "voucher", "created_at"]


class DowntimeLogSerializer(serializers.ModelSerializer):
    asset_code = serializers.ReadOnlyField(source="asset.code")
    duration_minutes = serializers.ReadOnlyField()

    class Meta:
        model = DowntimeLog
        fields = [
            "id",
            "asset",
            "asset_code",
            "company",
            "reason",
            "started_at",
            "ended_at",
            "impact_percent",
            "notes",
            "duration_minutes",
            "created_at",
        ]
        read_only_fields = ["id", "asset_code", "duration_minutes", "created_at"]


class AssetDisposalSerializer(serializers.ModelSerializer):
    asset_code = serializers.ReadOnlyField(source="asset.code")
    posted = serializers.SerializerMethodField()

    class Meta:
        model = AssetDisposal
        fields = [
            "id",
            "asset",
            "asset_code",
            "company",
            "method",
            "disposal_date",
            "reason",
            "proceeds_amount",
            "nbv_at_disposal",
            "status",
            "voucher",
            "asset_cost_account",
            "accumulated_dep_account",
            "proceeds_account",
            "gain_loss_account",
            "created_at",
            "posted",
        ]
        read_only_fields = ["id", "company", "status", "voucher", "created_at", "posted"]

    def get_posted(self, obj):
        return obj.status == "POSTED"

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        if not company and request and request.user.is_authenticated:
            company = request.user.companies.filter(is_active=True).first()
        if not company:
            raise serializers.ValidationError({"company": "Active company context is required."})
        asset = validated_data.get("asset")
        if asset and asset.company_id != company.id:
            raise serializers.ValidationError({"asset": "Asset does not belong to active company."})
        validated_data["company"] = company
        # default NBV if not provided
        if not validated_data.get("nbv_at_disposal"):
            validated_data["nbv_at_disposal"] = asset.book_value(validated_data.get("disposal_date"))
        return super().create(validated_data)


class EmployeeAssetAssignmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source="employee.full_name")

    class Meta:
        model = EmployeeAssetAssignment
        fields = [
            "id",
            "employee",
            "employee_name",
            "asset_code",
            "asset_name",
            "asset_type",
            "serial_number",
            "assignment_date",
            "return_date",
            "status",
            "liability_amount",
            "notes",
        ]
