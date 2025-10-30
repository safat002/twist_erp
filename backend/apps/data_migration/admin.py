from django.contrib import admin
from .models import (
    MigrationSession,
    MigrationTemplate,
    DataProfile,
    MigrationLog,
    MigrationError,
    MigrationRecord,
    MigrationJob,
    MigrationFile,
    MigrationColumnProfile,
    MigrationFieldMapping,
    MigrationSchemaExtension,
    MigrationStagingRow,
    MigrationValidationError,
    MigrationCommitLog,
)


class MigrationLogInline(admin.TabularInline):
    model = MigrationLog
    extra = 0
    readonly_fields = ["log_level", "message", "row_number", "details", "created_at"]


class MigrationErrorInline(admin.TabularInline):
    model = MigrationError
    extra = 0
    readonly_fields = [
        "row_number",
        "source_data",
        "error_type",
        "error_message",
        "field_name",
        "can_retry",
        "is_resolved",
        "created_at",
    ]


class MigrationRecordInline(admin.TabularInline):
    model = MigrationRecord
    extra = 0
    readonly_fields = ["target_model", "target_id", "source_row_number", "source_data", "created_at"]


@admin.register(MigrationSession)
class MigrationSessionAdmin(admin.ModelAdmin):
    list_display = [
        "session_id",
        "name",
        "status",
        "target_module",
        "target_model",
        "company",
        "started_at",
        "completed_at",
    ]
    list_filter = ["company", "status", "target_module"]
    search_fields = ["name", "session_id", "target_model"]
    inlines = [MigrationLogInline, MigrationErrorInline, MigrationRecordInline]


@admin.register(MigrationTemplate)
class MigrationTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "target_module", "target_model", "company", "usage_count", "is_public"]
    list_filter = ["company", "target_module", "is_public"]
    search_fields = ["name", "target_model"]


@admin.register(DataProfile)
class DataProfileAdmin(admin.ModelAdmin):
    list_display = ["session", "profiled_at"]
    search_fields = ["session__name", "session__session_id"]
    readonly_fields = ["profiled_at"]


@admin.register(MigrationLog)
class MigrationLogAdmin(admin.ModelAdmin):
    list_display = ["session", "log_level", "row_number", "created_at"]
    list_filter = ["log_level", "created_at"]
    search_fields = ["message"]


@admin.register(MigrationError)
class MigrationErrorAdmin(admin.ModelAdmin):
    list_display = ["session", "row_number", "error_type", "is_resolved", "created_at"]
    list_filter = ["is_resolved", "error_type"]
    search_fields = ["error_message", "field_name"]


@admin.register(MigrationRecord)
class MigrationRecordAdmin(admin.ModelAdmin):
    list_display = ["session", "target_model", "target_id", "source_row_number", "created_at"]
    list_filter = ["target_model"]
    search_fields = ["target_model", "target_id"]


class MigrationFileInline(admin.TabularInline):
    model = MigrationFile
    extra = 0
    readonly_fields = [
        "original_filename",
        "status",
        "row_count_detected",
        "uploaded_at",
        "parsed_at",
        "file_hash",
    ]


class MigrationFieldMappingInline(admin.TabularInline):
    model = MigrationFieldMapping
    extra = 0
    readonly_fields = [
        "column_name_in_file",
        "target_entity_field",
        "target_storage_mode",
        "confidence_score",
        "is_required_match",
        "approved_at",
    ]


class MigrationSchemaExtensionInline(admin.TabularInline):
    model = MigrationSchemaExtension
    extra = 0
    readonly_fields = [
        "field_name",
        "metadata_layer",
        "status",
        "decision_at",
        "decided_by",
    ]


@admin.register(MigrationJob)
class MigrationJobAdmin(admin.ModelAdmin):
    list_display = [
        "migration_job_id",
        "company",
        "target_model",
        "status",
        "created_at",
        "approved_at",
        "committed_at",
    ]
    list_filter = ["company", "status", "target_model"]
    search_fields = ["migration_job_id", "target_model", "entity_name_guess"]
    readonly_fields = [
        "migration_job_id",
        "created_at",
        "updated_at",
        "submitted_for_approval_at",
        "approved_at",
        "approved_by",
        "committed_at",
        "committed_by",
        "notes",
    ]
    inlines = [MigrationFileInline, MigrationFieldMappingInline, MigrationSchemaExtensionInline]


@admin.register(MigrationColumnProfile)
class MigrationColumnProfileAdmin(admin.ModelAdmin):
    list_display = ["migration_job", "column_name_in_file", "detected_data_type", "confidence_score"]
    list_filter = ["detected_data_type"]
    search_fields = ["column_name_in_file"]
    readonly_fields = ["stats", "sample_values"]


@admin.register(MigrationStagingRow)
class MigrationStagingRowAdmin(admin.ModelAdmin):
    list_display = ["migration_job", "row_index_in_file", "status"]
    list_filter = ["status"]
    search_fields = ["migration_job__migration_job_id", "source_file_name"]
    readonly_fields = ["clean_payload_json", "validation_summary"]


@admin.register(MigrationValidationError)
class MigrationValidationErrorAdmin(admin.ModelAdmin):
    list_display = ["migration_job", "error_code", "severity", "created_at"]
    list_filter = ["severity"]
    search_fields = ["error_code", "error_message"]
    readonly_fields = ["error_message", "suggested_fix"]


@admin.register(MigrationCommitLog)
class MigrationCommitLogAdmin(admin.ModelAdmin):
    list_display = ["migration_job", "committed_at", "committed_by"]
    search_fields = ["migration_job__migration_job_id"]
    readonly_fields = ["summary", "created_records", "gl_entries", "extra_metadata"]
