from __future__ import annotations

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.permissions.drf_permissions import HasPermission
from apps.report_builder.models import ReportDefinition
from apps.report_builder.serializers import (
    ReportDefinitionSerializer,
    ReportPreviewRequestSerializer,
)
from apps.report_builder.services import ReportQueryEngine, get_available_datasets, sync_report_metadata


class ReportDefinitionViewSet(viewsets.ModelViewSet):
    serializer_class = ReportDefinitionSerializer
    permission_classes = [IsAuthenticated, HasPermission]
    permission_code = "can_build_reports"

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = ReportDefinition.objects.all().select_related("metadata", "company", "company_group")
        if company:
            qs = qs.filter(
                Q(scope_type="GLOBAL")
                | Q(scope_type="GROUP", company_group=company.company_group)
                | Q(scope_type="COMPANY", company=company)
            )
        return qs.order_by("-updated_at")

    def perform_create(self, serializer):
        company = getattr(self.request, "company", None)
        if not company:
            raise ValidationError({"detail": "Active company context is required."})

        scope_type = serializer.validated_data.get("scope_type") or "COMPANY"
        company_value = company if scope_type == "COMPANY" else None
        company_group_value = company.company_group if scope_type != "GLOBAL" else None

        report = serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
            company=company_value,
            company_group=company_group_value,
        )
        publish = report.status == "active"
        sync_report_metadata(report, user=self.request.user, publish=publish)

    def perform_update(self, serializer):
        report = serializer.save(updated_by=self.request.user)
        if report.scope_type == "COMPANY" and report.company:
            if report.company_group_id != report.company.company_group_id:
                report.company_group = report.company.company_group
                report.save(update_fields=["company_group", "updated_at"])
        elif report.scope_type == "GROUP":
            if report.company_id:
                report.company = None
                report.save(update_fields=["company", "updated_at"])
        else:  # GLOBAL
            updated_fields = []
            if report.company_id:
                report.company = None
                updated_fields.append("company")
            if report.company_group_id:
                report.company_group = None
                updated_fields.append("company_group")
            if updated_fields:
                updated_fields.append("updated_at")
                report.save(update_fields=updated_fields)
        publish = report.status == "active"
        sync_report_metadata(report, user=self.request.user, publish=publish)

    @action(detail=False, methods=["get"], url_path="datasets")
    def datasets(self, request):
        company = getattr(request, "company", None)
        if not company:
            raise ValidationError({"detail": "Active company context is required."})
        datasets = get_available_datasets(request.user, company)
        return Response({"results": datasets})

    @action(detail=True, methods=["post"], url_path="preview")
    def preview(self, request, pk=None):
        company = getattr(request, "company", None)
        if not company:
            raise ValidationError({"detail": "Active company context is required."})

        serializer = ReportPreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report = self.get_object()

        engine = ReportQueryEngine(report=report, company=company, user=request.user)
        result = engine.run_preview(limit=serializer.validated_data.get("limit"))

        payload = {
            "rows": result.rows,
            "fields": result.fields,
            "meta": {
                "total_available": result.total_available,
                "limit": result.limit,
                "dataset": {
                    "type": result.dataset.type,
                    "key": result.dataset.key,
                    "label": result.dataset.label,
                },
            },
        }
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        company = getattr(request, "company", None)
        if not company:
            raise ValidationError({"detail": "Active company context is required."})

        report = self.get_object()
        report.status = "active"
        report.updated_by = request.user
        report.save(update_fields=["status", "updated_by", "updated_at"])
        sync_report_metadata(report, user=request.user, publish=True)
        serializer = self.get_serializer(report)
        return Response(serializer.data, status=status.HTTP_200_OK)
