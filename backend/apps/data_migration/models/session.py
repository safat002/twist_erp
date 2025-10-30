from django.db import models
from shared.models import CompanyAwareModel
import json

class MigrationSession(CompanyAwareModel):
    """
    Tracks complete data migration session
    """

    # Allow historical sessions to omit company_group; newer pipeline uses MigrationJob
    company_group = models.ForeignKey(
        'companies.CompanyGroup',
        on_delete=models.PROTECT,
        db_index=True,
        help_text="Company group this record belongs to",
        null=True,
        blank=True,
    )
    session_id = models.UUIDField(unique=True, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    # Source info
    source_type = models.CharField(
        max_length=20,
        choices=[
            ('EXCEL', 'Excel File'),
            ('CSV', 'CSV File'),
            ('DATABASE', 'Database'),
            ('API', 'API Import'),
        ]
    )
    source_file = models.FileField(
        upload_to='migrations/%Y/%m/',
        null=True,
        blank=True
    )
    source_connection = models.JSONField(
        null=True,
        blank=True,
        help_text="Database connection info"
    )
    # Target
    target_module = models.CharField(max_length=50)
    target_model = models.CharField(max_length=50)
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('UPLOADED', 'File Uploaded'),
            ('PROFILED', 'Data Profiled'),
            ('MAPPED', 'Fields Mapped'),
            ('VALIDATED', 'Validation Complete'),
            ('IMPORTING', 'Import in Progress'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
            ('ROLLED_BACK', 'Rolled Back'),
        ],
        default='UPLOADED'
    )
    # Statistics
    total_rows = models.IntegerField(default=0)
    processed_rows = models.IntegerField(default=0)
    success_rows = models.IntegerField(default=0)
    error_rows = models.IntegerField(default=0)
    skipped_rows = models.IntegerField(default=0)
    # Configuration
    mapping_config = models.JSONField(default=dict)
    validation_rules = models.JSONField(default=dict)
    transformation_rules = models.JSONField(default=dict)
    # Template
    template = models.ForeignKey(
        'MigrationTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    save_as_template = models.BooleanField(default=False)
    # Audit
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'target_module']),
        ]

class MigrationTemplate(CompanyAwareModel):
    """
    Reusable migration templates
    """

    company_group = models.ForeignKey(
        'companies.CompanyGroup',
        on_delete=models.PROTECT,
        db_index=True,
        help_text="Company group this record belongs to",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    target_module = models.CharField(max_length=50)
    target_model = models.CharField(max_length=50)
    # Template configuration
    field_mappings = models.JSONField(default=dict)
    validation_rules = models.JSONField(default=dict)
    transformation_rules = models.JSONField(default=dict)
    default_values = models.JSONField(default=dict)
    # Usage stats
    usage_count = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    is_public = models.BooleanField(
        default=False,
        help_text="Available to all users in company"
    )

    class Meta:
        unique_together = [['company', 'name', 'target_model']]

class DataProfile(models.Model):
    """
    Source data profiling results
    """
    session = models.OneToOneField(
        MigrationSession,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    # Column analysis
    columns = models.JSONField(default=list)
    column_types = models.JSONField(default=dict)
    column_stats = models.JSONField(default=dict)
    # Data quality
    null_counts = models.JSONField(default=dict)
    unique_counts = models.JSONField(default=dict)
    duplicate_rows = models.IntegerField(default=0)
    # Sample data
    sample_rows = models.JSONField(default=list)
    profiled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'migration_data_profiles'
