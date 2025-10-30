from django.conf import settings
from django.db import models
from django.utils import timezone

from .enums import TargetStorageMode, SchemaExtensionStatus
from .job import MigrationJob, MigrationFile


class MigrationColumnProfile(models.Model):
    """
    Column-level profiling metadata produced during detection phase.
    """

    migration_job = models.ForeignKey(
        MigrationJob,
        related_name="column_profiles",
        on_delete=models.CASCADE,
    )
    migration_file = models.ForeignKey(
        MigrationFile,
        related_name="column_profiles",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    column_name_in_file = models.CharField(max_length=255)
    detected_data_type = models.CharField(max_length=50)
    inferred_field_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Best-guess normalized field name (snake_case)",
    )
    sample_values = models.JSONField(default=list, blank=True)
    stats = models.JSONField(default=dict, blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["column_name_in_file"]
        unique_together = [["migration_job", "column_name_in_file"]]


class MigrationFieldMapping(models.Model):
    """
    Stores the mapping decisions between source columns and target entity fields.
    """

    migration_job = models.ForeignKey(
        MigrationJob,
        related_name="field_mappings",
        on_delete=models.CASCADE,
    )
    column_name_in_file = models.CharField(max_length=255)
    target_entity_field = models.CharField(max_length=255, blank=True)
    target_storage_mode = models.CharField(
        max_length=32,
        choices=TargetStorageMode.choices,
        default=TargetStorageMode.EXISTING_COLUMN,
    )
    new_field_definition_json = models.JSONField(blank=True, null=True)
    is_required_match = models.BooleanField(default=False)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_field_mappings",
    )

    class Meta:
        ordering = ["column_name_in_file"]
        unique_together = [["migration_job", "column_name_in_file"]]

    @property
    def requires_schema_extension(self) -> bool:
        return self.target_storage_mode == TargetStorageMode.NEW_FIELD


class MigrationSchemaExtension(models.Model):
    """
    Tracks proposed metadata changes (new fields) arising from a migration.
    """

    migration_job = models.ForeignKey(
        MigrationJob,
        related_name="schema_extensions",
        on_delete=models.CASCADE,
    )
    field_name = models.CharField(max_length=255)
    proposed_definition = models.JSONField()
    metadata_layer = models.CharField(
        max_length=50,
        help_text="Which metadata layer to apply the change to (e.g. COMPANY_OVERRIDE)",
    )
    status = models.CharField(
        max_length=16,
        choices=SchemaExtensionStatus.choices,
        default=SchemaExtensionStatus.PENDING,
    )
    decision_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="metadata_extension_decisions",
        on_delete=models.SET_NULL,
    )
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [["migration_job", "field_name"]]
        indexes = [
            models.Index(fields=["migration_job", "status"]),
        ]

    def approve(self, user=None, notes: str | None = None):
        self.status = SchemaExtensionStatus.APPROVED
        self.decision_at = timezone.now()
        if user:
            self.decided_by = user
        if notes:
            self.notes = notes
        self.save(update_fields=["status", "decision_at", "decided_by", "notes"])
        return self

    def reject(self, user=None, notes: str | None = None):
        self.status = SchemaExtensionStatus.REJECTED
        self.decision_at = timezone.now()
        if user:
            self.decided_by = user
        if notes:
            self.notes = notes
        self.save(update_fields=["status", "decision_at", "decided_by", "notes"])
        return self
