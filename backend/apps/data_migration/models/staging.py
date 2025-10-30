from django.conf import settings
from django.db import models
from django.utils import timezone

from .enums import StagingRowStatus, ValidationSeverity
from .job import MigrationJob
from .mapping import MigrationFieldMapping


class MigrationStagingRow(models.Model):
    """
    Normalized row staged for validation prior to commit.
    """

    migration_job = models.ForeignKey(
        MigrationJob,
        related_name="staging_rows",
        on_delete=models.CASCADE,
    )
    source_file_name = models.CharField(max_length=255, blank=True)
    row_index_in_file = models.IntegerField()
    clean_payload_json = models.JSONField()
    status = models.CharField(
        max_length=24,
        choices=StagingRowStatus.choices,
        default=StagingRowStatus.PENDING_VALIDATION,
    )
    validation_summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["migration_job", "status"]),
        ]
        ordering = ["row_index_in_file"]

    def mark_valid(self):
        self.status = StagingRowStatus.VALID
        self.validation_summary = {}
        self.save(update_fields=["status", "validation_summary", "updated_at"])
        return self

    def mark_invalid(self, summary: dict):
        self.status = StagingRowStatus.INVALID
        self.validation_summary = summary
        self.save(update_fields=["status", "validation_summary", "updated_at"])
        return self

    def mark_skipped(self):
        self.status = StagingRowStatus.SKIPPED
        self.save(update_fields=["status", "updated_at"])
        return self


class MigrationValidationError(models.Model):
    """
    Individual validation errors associated with staging rows.
    """

    migration_job = models.ForeignKey(
        MigrationJob,
        related_name="validation_errors",
        on_delete=models.CASCADE,
    )
    staging_row = models.ForeignKey(
        MigrationStagingRow,
        related_name="errors",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    field_mapping = models.ForeignKey(
        MigrationFieldMapping,
        related_name="validation_errors",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    error_code = models.CharField(max_length=100)
    error_message = models.TextField()
    severity = models.CharField(
        max_length=8,
        choices=ValidationSeverity.choices,
        default=ValidationSeverity.HARD,
    )
    suggested_fix = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["migration_job", "severity"]),
        ]


class MigrationCommitLog(models.Model):
    """
    Records the commit execution details for audit & rollback.
    """

    migration_job = models.OneToOneField(
        MigrationJob,
        related_name="commit_log",
        on_delete=models.CASCADE,
    )
    committed_at = models.DateTimeField(default=timezone.now)
    committed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="migration_commit_logs",
    )
    summary = models.JSONField(
        default=dict,
        help_text="Counts, totals, and other diagnostics for the commit.",
    )
    created_records = models.JSONField(
        default=list,
        help_text="List of dicts describing created record identifiers for rollback.",
    )
    gl_entries = models.JSONField(
        default=list,
        help_text="Journal vouchers or GL impacts produced during commit.",
        blank=True,
    )
    extra_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-committed_at"]
