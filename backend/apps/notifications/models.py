from __future__ import annotations

from django.conf import settings
from django.db import models

from shared.models import CompanyAwareModel


class NotificationSeverity(models.TextChoices):
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    CRITICAL = "critical", "Critical"


class NotificationStatus(models.TextChoices):
    UNREAD = "unread", "Unread"
    READ = "read", "Read"
    CLEARED = "cleared", "Cleared"


class Notification(CompanyAwareModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    severity = models.CharField(max_length=10, choices=NotificationSeverity.choices, default=NotificationSeverity.INFO)
    status = models.CharField(max_length=10, choices=NotificationStatus.choices, default=NotificationStatus.UNREAD)
    group_key = models.CharField(max_length=100, blank=True, help_text="Key to group similar notifications")
    entity_type = models.CharField(max_length=100, blank=True)
    entity_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "user", "status"]),
            models.Index(fields=["company", "user", "severity"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.title}"


class EmailAwarenessState(CompanyAwareModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_awareness")
    unread_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("company", "user")

