from django.apps import apps
from rest_framework import serializers

from ..models import (
    MigrationFile,
    MigrationJob,
    MigrationFieldMapping,
    MigrationColumnProfile,
    MigrationStagingRow,
    MigrationValidationError,
    migration_enums,
)
from ..services import MigrationPipeline


class MigrationFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MigrationFile
        fields = [
            "id",
            "original_filename",
            "status",
            "row_count_detected",
            "uploaded_at",
            "parsed_at",
            "file_hash",
        ]
        read_only_fields = fields


class MigrationColumnProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MigrationColumnProfile
        fields = [
            "column_name_in_file",
            "detected_data_type",
            "inferred_field_name",
            "sample_values",
            "stats",
            "confidence_score",
        ]
        read_only_fields = fields


class MigrationFieldMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MigrationFieldMapping
        fields = [
            "id",
            "column_name_in_file",
            "target_entity_field",
            "target_storage_mode",
            "new_field_definition_json",
            "is_required_match",
            "confidence_score",
            "approved_at",
            "approved_by",
        ]
        read_only_fields = ["id", "confidence_score", "approved_at", "approved_by"]


class MigrationStagingRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = MigrationStagingRow
        fields = [
            "id",
            "row_index_in_file",
            "source_file_name",
            "status",
            "clean_payload_json",
            "validation_summary",
        ]
        read_only_fields = fields


class MigrationValidationErrorSerializer(serializers.ModelSerializer):
    field_name = serializers.SerializerMethodField()

    class Meta:
        model = MigrationValidationError
        fields = ["id", "error_code", "error_message", "severity", "field_name", "created_at"]
        read_only_fields = fields

    def get_field_name(self, obj):
        if obj.field_mapping:
            return obj.field_mapping.target_entity_field
        if obj.staging_row:
            return obj.staging_row.validation_summary.get("field") if obj.staging_row.validation_summary else None
        return None


class MigrationJobSerializer(serializers.ModelSerializer):
    files = MigrationFileSerializer(many=True, read_only=True)
    field_mappings = MigrationFieldMappingSerializer(many=True, read_only=True)
    column_profiles = MigrationColumnProfileSerializer(many=True, read_only=True)
    staging_rows = MigrationStagingRowSerializer(many=True, read_only=True)
    validation_errors = MigrationValidationErrorSerializer(many=True, read_only=True)
    company_id = serializers.IntegerField(source="company.id", read_only=True)
    company_name = serializers.CharField(source="company.legal_name", read_only=True)
    staging_summary = serializers.SerializerMethodField()
    validation_summary = serializers.SerializerMethodField()

    class Meta:
        model = MigrationJob
        fields = [
            "id",
            "migration_job_id",
            "company_id",
            "company_name",
            "target_model",
            "entity_name_guess",
            "status",
            "created_at",
            "updated_at",
            "submitted_for_approval_at",
            "approved_at",
            "committed_at",
            "meta",
            "notes",
            "files",
            "column_profiles",
            "field_mappings",
            "staging_rows",
            "validation_errors",
            "staging_summary",
            "validation_summary",
        ]
        read_only_fields = [
            "id",
            "migration_job_id",
            "status",
            "created_at",
            "updated_at",
            "submitted_for_approval_at",
            "approved_at",
            "committed_at",
            "files",
            "column_profiles",
            "field_mappings",
            "staging_rows",
            "validation_errors",
            "staging_summary",
            "validation_summary",
        ]

    def get_staging_summary(self, obj: MigrationJob):
        return {
            status: obj.staging_rows.filter(status=status).count()
            for status in migration_enums.StagingRowStatus.values
        }

    def get_validation_summary(self, obj: MigrationJob):
        return obj.meta.get("validation", {}).get("summary", {})


class MigrationJobCreateSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    entity_name_guess = serializers.CharField(required=False, allow_blank=True)
    target_model = serializers.CharField(required=False, allow_blank=True)
    meta = serializers.JSONField(required=False)

    def create(self, validated_data):
        company = apps.get_model("companies.Company").objects.get(pk=validated_data["company_id"])
        request = self.context["request"]
        job = MigrationPipeline.create_job(
            company=company,
            created_by=request.user,
            entity_name_guess=validated_data.get("entity_name_guess"),
            target_model=validated_data.get("target_model"),
            meta=validated_data.get("meta"),
        )
        return job


class MigrationFileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, file_obj):
        filename = file_obj.name
        if not any(filename.lower().endswith(ext) for ext in [".csv", ".xlsx", ".xls"]):
            raise serializers.ValidationError("Only CSV and Excel files are supported.")
        return file_obj


class MappingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MigrationFieldMapping
        fields = ["target_entity_field", "target_storage_mode", "new_field_definition_json", "is_required_match"]
