import logging
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from shared.models import CompanyAwareModel
from .enums import MigrationJobStatus, MigrationFileStatus

logger = logging.getLogger(__name__)


class MigrationJob(CompanyAwareModel):
    """
    Core migration job lifecycle tracker.
    Represents a batch import attempt for a single entity & company.
    """

    migration_job_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    entity_name_guess = models.CharField(
        max_length=100,
        help_text="Initial entity guess supplied by uploader or detector",
        blank=True,
    )
    target_model = models.CharField(
        max_length=150,
        help_text="Django model label (app_label.ModelName) resolved for this job",
        blank=True,
    )
    status = models.CharField(
        max_length=32,
        choices=MigrationJobStatus.choices,
        default=MigrationJobStatus.UPLOADED,
    )
    submitted_for_approval_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="approved_migration_jobs",
        on_delete=models.SET_NULL,
    )
    committed_at = models.DateTimeField(null=True, blank=True)
    committed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="committed_migration_jobs",
        on_delete=models.SET_NULL,
    )
    rollback_parent_job = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="rollback_children",
        on_delete=models.SET_NULL,
    )
    meta = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "target_model"]),
        ]

    def mark_status(self, new_status: str, *, by_user=None, notes: str | None = None):
        """Utility to safely transition status and persist audit timestamps."""
        if new_status not in MigrationJobStatus.values:
            raise ValueError(f"Invalid migration job status: {new_status}")

        timestamp = timezone.now()

        if new_status == MigrationJobStatus.AWAITING_APPROVAL:
            self.submitted_for_approval_at = timestamp
        elif new_status == MigrationJobStatus.APPROVED:
            self.approved_at = timestamp
            if by_user:
                self.approved_by = by_user
        elif new_status == MigrationJobStatus.COMMITTED:
            self.committed_at = timestamp
            if by_user:
                self.committed_by = by_user
        elif new_status == MigrationJobStatus.ROLLED_BACK:
            # Mark for traceability; actual rollback metadata handled separately
            self.meta.setdefault("rollbacks", []).append(
                {"timestamp": timestamp.isoformat(), "user_id": getattr(by_user, "id", None)}
            )

        if notes:
            self.notes = (self.notes or "") + f"\n[{timestamp.isoformat()}] {notes}"

        self.status = new_status
        self.save(update_fields=[
            "status",
            "submitted_for_approval_at",
            "approved_at",
            "approved_by",
            "committed_at",
            "committed_by",
            "notes",
            "meta",
            "updated_at",
        ])
        try:
            from apps.ai_companion.services.telemetry import TelemetryService  # noqa: WPS433

            TelemetryService().record_event(
                event_type=f"data_migration.job_status.{new_status}",
                user=by_user or getattr(self, "created_by", None),
                company=self.company,
                payload={
                    "job_id": self.id,
                    "migration_job_id": str(self.migration_job_id),
                    "status": new_status,
                    "target": self.target_model or self.entity_name_guess,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Telemetry event failed for MigrationJob %s: %s", self.id, exc)
        return self


class MigrationFile(models.Model):
    """
    Stores uploaded source files participating in a migration job.
    """

    FILE_UPLOAD_DIR = "migration_uploads/%Y/%m/%d"

    migration_job = models.ForeignKey(
        MigrationJob,
        related_name="files",
        on_delete=models.CASCADE,
    )
    original_filename = models.CharField(max_length=255)
    uploaded_file = models.FileField(upload_to=FILE_UPLOAD_DIR, blank=True, null=True)
    stored_path = models.CharField(
        max_length=512,
        blank=True,
        help_text="Physical storage reference (filesystem path, S3 key, etc.)",
    )
    file_hash = models.CharField(max_length=128, blank=True)
    status = models.CharField(
        max_length=16,
        choices=MigrationFileStatus.choices,
        default=MigrationFileStatus.UPLOADED,
    )
    row_count_detected = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    parsed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["uploaded_at"]
        indexes = [
            models.Index(fields=["migration_job", "status"]),
            models.Index(fields=["file_hash"]),
        ]

    def mark_parsed(self, *, row_count: int, stored_path: str | None = None):
        self.status = MigrationFileStatus.PARSED
        self.row_count_detected = row_count
        self.parsed_at = timezone.now()
        if stored_path:
            self.stored_path = stored_path
        self.save(update_fields=["status", "row_count_detected", "parsed_at", "stored_path"])

    def mark_error(self, message: str):
        self.status = MigrationFileStatus.ERROR
        self.error_message = message
        self.save(update_fields=["status", "error_message"])
        return self
