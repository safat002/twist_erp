from __future__ import annotations

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Donor, Program, ComplianceRequirement, ComplianceSubmission
from .serializers import (
    DonorSerializer,
    ProgramSerializer,
    ComplianceRequirementSerializer,
    ComplianceSubmissionSerializer,
)
from apps.permissions.permissions import has_permission


class CompanyScopedQuerysetMixin:
    permission_classes = [IsAuthenticated]

    def get_company(self):
        return getattr(self.request, 'company', None)

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset()
        company = self.get_company()
        if company and hasattr(qs.model, 'company_id'):
            qs = qs.filter(company=company)
        return qs

    def get_serializer_context(self):  # type: ignore[override]
        ctx = super().get_serializer_context()
        ctx.setdefault('request', self.request)
        return ctx


class DonorViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Donor.objects.all().order_by('name')
    serializer_class = DonorSerializer

    def _require(self, code: str):
        company = self.get_company()
        if not has_permission(self.request.user, code, company):
            return Response({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)
        return None

    def perform_create(self, serializer):
        denied = self._require("ngo.create_donor")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        serializer.save()

    def perform_update(self, serializer):
        denied = self._require("ngo.update_donor")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        serializer.save()

    def perform_destroy(self, instance):
        denied = self._require("ngo.delete_donor")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        instance.delete()


class ProgramViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Program.objects.all().select_related('donor').order_by('-created_at')
    serializer_class = ProgramSerializer

    def _require(self, code: str):
        company = self.get_company()
        if not has_permission(self.request.user, code, company):
            return Response({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)
        return None

    def perform_create(self, serializer):
        denied = self._require("ngo.create_program")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        serializer.save()

    def perform_update(self, serializer):
        denied = self._require("ngo.update_program")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        serializer.save()

    def perform_destroy(self, instance):
        denied = self._require("ngo.delete_program")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        instance.delete()

    @action(detail=False, methods=["get"], url_path="overview")
    def overview(self, request):
        from django.utils import timezone
        from django.db.models import Count, Q, Min
        from datetime import timedelta
        company = self.get_company()
        programs = Program.objects.filter(company=company)
        total_programs = programs.count()
        active_programs = programs.filter(status=Program.Status.ACTIVE).count()
        closed_programs = programs.filter(status=Program.Status.CLOSED).count()
        reqs = ComplianceRequirement.objects.filter(program__company=company, status=ComplianceRequirement.Status.ACTIVE)
        total_requirements = reqs.count()
        # Apply optional range filters
        qs_from = request.query_params.get('from')
        qs_to = request.query_params.get('to')
        today = timezone.now().date()
        base = reqs
        if qs_from:
            base = base.filter(next_due_date__gte=qs_from)
        if qs_to:
            base = base.filter(next_due_date__lte=qs_to)
        due_30 = reqs.filter(next_due_date__gte=today, next_due_date__lte=today + timedelta(days=30)).count()
        overdue = base.filter(next_due_date__lt=today).count()
        per_program = (
            programs
            .annotate(
                requirements_count=Count('requirements', filter=Q(requirements__status=ComplianceRequirement.Status.ACTIVE)),
                overdue_count=Count('requirements', filter=Q(requirements__next_due_date__lt=today, requirements__status=ComplianceRequirement.Status.ACTIVE)),
                next_due=Min('requirements__next_due_date'),
            )
            .values('id', 'code', 'title', 'status', 'requirements_count', 'overdue_count', 'next_due')
            .order_by('title')
        )
        data = {
            'totals': {
                'total_programs': total_programs,
                'active_programs': active_programs,
                'closed_programs': closed_programs,
                'total_requirements': total_requirements,
                'requirements_due_30': due_30,
                'requirements_overdue': overdue,
            },
            'programs': list(per_program),
        }
        return Response(data)


class ComplianceRequirementViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ComplianceRequirement.objects.all().select_related('program')
    serializer_class = ComplianceRequirementSerializer

    def _require(self, code: str):
        company = self.get_company()
        if not has_permission(self.request.user, code, company):
            return Response({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)
        return None

    def perform_create(self, serializer):
        denied = self._require("ngo.create_requirement")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        serializer.save()

    def perform_update(self, serializer):
        denied = self._require("ngo.update_requirement")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        serializer.save()

    def perform_destroy(self, instance):
        denied = self._require("ngo.delete_requirement")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        instance.delete()


class ComplianceSubmissionViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ComplianceSubmission.objects.all().select_related('requirement')
    serializer_class = ComplianceSubmissionSerializer

    def _require(self, code: str):
        company = self.get_company()
        if not has_permission(self.request.user, code, company):
            return Response({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)
        return None

    def perform_create(self, serializer):
        denied = self._require("ngo.create_submission")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        serializer.save()

    def perform_update(self, serializer):
        denied = self._require("ngo.update_submission")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        serializer.save()

    def perform_destroy(self, instance):
        denied = self._require("ngo.delete_submission")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        instance.delete()
    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset()
        program_id = self.request.query_params.get('program')
        if program_id:
            try:
                qs = qs.filter(program_id=int(program_id))
            except (TypeError, ValueError):
                pass
        return qs
    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset()
        req_id = self.request.query_params.get('requirement')
        if req_id:
            try:
                qs = qs.filter(requirement_id=int(req_id))
            except (TypeError, ValueError):
                pass
        return qs
