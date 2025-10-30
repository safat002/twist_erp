from django.db.models import Q
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import DynamicEntity, FormSubmission, FormTemplate
from .serializers import (
    DynamicEntitySerializer,
    FormSubmissionSerializer,
    FormTemplateSerializer,
)
from .services.dynamic_entities import load_runtime_entity
from apps.permissions.drf_permissions import HasPermission


class FormTemplateListCreateView(generics.ListCreateAPIView):
    serializer_class = FormTemplateSerializer
    permission_classes = [IsAuthenticated, HasPermission]
    permission_code = "can_design_forms"

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = FormTemplate.objects.all().select_related("metadata").prefetch_related("entity")
        if company:
            qs = qs.filter(
                Q(scope_type="GLOBAL")
                | Q(scope_type="GROUP", company_group=company.company_group)
                | Q(scope_type="COMPANY", company=company)
            )
        return qs


class FormSubmissionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            template = FormTemplate.objects.get(pk=pk)
        except FormTemplate.DoesNotExist:
            return Response({"detail": "Form template not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = FormSubmissionSerializer(data={"template": template.id, **request.data}, context={"request": request})
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()
        return Response(FormSubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)


class DynamicEntityListView(generics.ListAPIView):
    serializer_class = DynamicEntitySerializer
    permission_classes = [IsAuthenticated, HasPermission]
    permission_code = "can_build_modules"

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = DynamicEntity.objects.filter(is_active=True).select_related("metadata")
        if company:
            qs = qs.filter(
                Q(scope_type="GLOBAL")
                | Q(scope_type="GROUP", company_group=company.company_group)
                | Q(scope_type="COMPANY", company=company)
            )
        return qs.order_by('-created_at')


class DynamicEntitySchemaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        company = getattr(request, "company", None)
        if not company:
            raise ValidationError({"detail": "Active company is required."})
        try:
            runtime = load_runtime_entity(slug, company)
        except DynamicEntity.DoesNotExist as exc:
            raise NotFound(str(exc)) from exc

        serializer = DynamicEntitySerializer(runtime.entity)
        payload = serializer.data
        payload["runtime"] = {
            "model": runtime.model.__name__,
            "fields": runtime.field_names,
        }
        return Response(payload)


class DynamicEntityMixin:
    permission_classes = [IsAuthenticated]
    runtime = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        company = getattr(request, "company", None)
        if not company:
            raise ValidationError({"detail": "Active company is required."})
        slug = kwargs.get("slug")
        if not slug:
            raise ValidationError({"detail": "Entity slug not provided."})
        try:
            self.runtime = load_runtime_entity(slug, company)
        except DynamicEntity.DoesNotExist as exc:
            raise NotFound(str(exc)) from exc

    def get_serializer_class(self):
        return self.runtime.serializer_class

    def get_queryset(self):
        return self.runtime.model.objects.filter(company=self.request.company).order_by('-created_at')


class DynamicEntityRecordsView(DynamicEntityMixin, generics.ListCreateAPIView):
    def perform_create(self, serializer):
        serializer.save(company=self.request.company, created_by=self.request.user)


class DynamicEntityRecordDetailView(DynamicEntityMixin, generics.RetrieveUpdateDestroyAPIView):
    def get_object(self):
        instance = super().get_object()
        if instance.company != self.request.company:
            raise NotFound("Record not found for this company.")
        return instance

    def perform_update(self, serializer):
        serializer.save(company=self.request.company, created_by=self.request.user)
