from django.apps import apps
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import MigrationJob, MigrationFieldMapping, migration_enums
from ..serializers.job_serializers import (
    MigrationFileUploadSerializer,
    MigrationJobCreateSerializer,
    MigrationJobSerializer,
    MappingUpdateSerializer,
    MigrationFieldMappingSerializer,
)
from ..services import MigrationPipeline
from ..tasks.migration_tasks import (
    profile_migration_job,
    stage_migration_job,
    validate_migration_job,
    commit_migration_job,
    rollback_migration_job,
)


def _user_has_permission(user, company, perm_code: str) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or getattr(user, "is_system_admin", False):
        return True

    UserCompanyRole = apps.get_model("users.UserCompanyRole")
    roles = (
        UserCompanyRole.objects.filter(user=user, company=company, is_active=True)
        .select_related("role")
        .prefetch_related("role__permissions")
    )
    for role_assignment in roles:
        if role_assignment.role.permissions.filter(code=perm_code).exists():
            return True
    return False


class MigrationJobViewSet(viewsets.ModelViewSet):
    queryset = MigrationJob.objects.select_related("company", "company_group").prefetch_related(
        "files", "column_profiles", "field_mappings", "staging_rows", "validation_errors"
    )
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return MigrationJobCreateSerializer
        if self.action == "upload_file":
            return MigrationFileUploadSerializer
        if self.action == "update_mapping":
            return MappingUpdateSerializer
        return MigrationJobSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_system_admin", False):
            return queryset

        accessible_company_ids = apps.get_model("users.UserCompanyRole").objects.filter(
            user=user,
            is_active=True,
        ).values_list("company_id", flat=True)
        return queryset.filter(company_id__in=accessible_company_ids)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save()
        output = MigrationJobSerializer(job, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    def _require_permission(self, job: MigrationJob, perm_code: str):
        if not _user_has_permission(self.request.user, job.company, perm_code):
            raise PermissionDenied(f"This action requires the '{perm_code}' permission.")

    @action(methods=["post"], detail=True, url_path="upload-file")
    def upload_file(self, request, pk=None):
        job = self.get_object()
        self._require_permission(job, "data_migration.importer")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pipeline = MigrationPipeline(job)
        pipeline.add_file(
            uploaded_by=request.user,
            file_name=serializer.validated_data["file"].name,
            file_content=serializer.validated_data["file"],
        )
        job.refresh_from_db()
        return Response(MigrationJobSerializer(job, context=self.get_serializer_context()).data)

    @action(methods=["post"], detail=True)
    def profile(self, request, pk=None):
        job = self.get_object()
        self._require_permission(job, "data_migration.importer")
        if request.query_params.get("async") == "true":
            task = profile_migration_job.delay(job.id)
            return Response({"task_id": task.id, "status": job.status})
        pipeline = MigrationPipeline(job)
        pipeline.profile_files()
        pipeline.generate_field_mappings()
        job.refresh_from_db()
        return Response(MigrationJobSerializer(job, context=self.get_serializer_context()).data)

    @action(methods=["post"], detail=True)
    def stage(self, request, pk=None):
        job = self.get_object()
        self._require_permission(job, "data_migration.importer")
        if request.query_params.get("async") == "true":
            task = stage_migration_job.delay(job.id)
            return Response({"task_id": task.id, "status": job.status})
        pipeline = MigrationPipeline(job)
        pipeline.stage_rows(user=request.user)
        job.refresh_from_db()
        return Response(
            {
                "staged_rows": job.staging_rows.count(),
                "status": job.status,
            }
        )

    @action(methods=["post"], detail=True)
    def validate(self, request, pk=None):
        job = self.get_object()
        self._require_permission(job, "data_migration.importer")
        if request.query_params.get("async") == "true":
            task = validate_migration_job.delay(job.id)
            return Response({"task_id": task.id, "status": job.status})
        pipeline = MigrationPipeline(job)
        summary = pipeline.validate(user=request.user)
        return Response({"summary": summary, "status": job.status})

    @action(methods=["post"], detail=True, url_path="submit")
    def submit_for_approval(self, request, pk=None):
        job = self.get_object()
        self._require_permission(job, "data_migration.importer")
        pipeline = MigrationPipeline(job)
        pipeline.submit_for_approval(user=request.user)
        return Response({"status": job.status})

    @action(methods=["post"], detail=True)
    def approve(self, request, pk=None):
        job = self.get_object()
        self._require_permission(job, "data_migration.approver")
        notes = request.data.get("notes")
        pipeline = MigrationPipeline(job)
        pipeline.approve(approver=request.user, notes=notes)
        return Response({"status": job.status})

    @action(methods=["post"], detail=True)
    def reject(self, request, pk=None):
        job = self.get_object()
        self._require_permission(job, "data_migration.approver")
        notes = request.data.get("notes")
        pipeline = MigrationPipeline(job)
        pipeline.reject(approver=request.user, notes=notes)
        return Response({"status": job.status})

    @action(methods=["post"], detail=True)
    def commit(self, request, pk=None):
        job = self.get_object()
        self._require_permission(job, "data_migration.approver")
        if request.query_params.get("async") == "true":
            task = commit_migration_job.delay(job.id, request.user.id)
            return Response({"task_id": task.id, "status": job.status})
        pipeline = MigrationPipeline(job)
        pipeline.apply_schema_extensions(approver=request.user)
        commit_log = pipeline.commit(user=request.user)
        return Response({"status": job.status, "summary": commit_log.summary})

    @action(methods=["post"], detail=True)
    def rollback(self, request, pk=None):
        job = self.get_object()
        self._require_permission(job, "data_migration.approver")
        if request.query_params.get("async") == "true":
            task = rollback_migration_job.delay(job.id, request.user.id)
            return Response({"task_id": task.id, "status": job.status})
        pipeline = MigrationPipeline(job)
        deleted = pipeline.rollback(user=request.user)
        return Response({"status": job.status, "deleted": deleted})

    @action(methods=["patch"], detail=True, url_path="mappings/(?P<mapping_id>[^/.]+)")
    def update_mapping(self, request, pk=None, mapping_id=None):
        job = self.get_object()
        self._require_permission(job, "data_migration.importer")
        try:
            mapping = job.field_mappings.get(pk=mapping_id)
        except MigrationFieldMapping.DoesNotExist:
            return Response({"detail": "Mapping not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance=mapping, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MigrationFieldMappingSerializer(mapping).data)
