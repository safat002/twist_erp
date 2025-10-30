from django.db import models

class MigrationLog(models.Model):
    """
    Detailed log of migration operations
    """
    session = models.ForeignKey(
        'MigrationSession',
        on_delete=models.CASCADE,
        related_name='logs'
    )
    log_level = models.CharField(
        max_length=10,
        choices=[
            ('INFO', 'Info'),
            ('WARNING', 'Warning'),
            ('ERROR', 'Error'),
        ]
    )
    message = models.TextField()
    row_number = models.IntegerField(null=True, blank=True)
    details = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'log_level']),
        ]

class MigrationError(models.Model):
    """
    Track errors during migration
    """
    session = models.ForeignKey(
        'MigrationSession',
        on_delete=models.CASCADE,
        related_name='errors'
    )
    row_number = models.IntegerField()
    source_data = models.JSONField()
    error_type = models.CharField(max_length=50)
    error_message = models.TextField()
    field_name = models.CharField(max_length=100, blank=True)
    can_retry = models.BooleanField(default=True)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['session', 'is_resolved']),
        ]

class MigrationRecord(models.Model):
    """
    Tracks imported records for rollback
    """
    session = models.ForeignKey(
        'MigrationSession',
        on_delete=models.CASCADE,
        related_name='records'
    )
    target_model = models.CharField(max_length=50)
    target_id = models.IntegerField()
    source_row_number = models.IntegerField()
    source_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['session', 'target_model']),
        ]