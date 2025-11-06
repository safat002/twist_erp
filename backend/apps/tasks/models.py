from __future__ import annotations

from django.conf import settings
from django.db import models

from shared.models import CompanyAwareModel


class TaskType(models.TextChoices):
    SYSTEM = "system", "System"
    PERSONAL = "personal", "Personal"


class TaskPriority(models.TextChoices):
    LOW = "low", "Low"
    NORMAL = "normal", "Normal"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class TaskStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not Started"
    IN_PROGRESS = "in_progress", "In Progress"
    BLOCKED = "blocked", "Blocked"
    DONE = "done", "Done"


class TaskVisibility(models.TextChoices):
    PRIVATE = "private", "Private"
    MANAGER_VISIBLE = "manager_visible", "Manager Visible"
    TEAM_VISIBLE = "team_visible", "Team Visible"
    EXEC_VISIBLE = "exec_visible", "Executive Visible"


class TaskItem(CompanyAwareModel):
    task_type = models.CharField(max_length=20, choices=TaskType.choices, default=TaskType.PERSONAL)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_tasks")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="delegated_tasks")
    due_date = models.DateTimeField(null=True, blank=True)
    priority = models.CharField(max_length=12, choices=TaskPriority.choices, default=TaskPriority.NORMAL)
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.NOT_STARTED)
    linked_entity_type = models.CharField(max_length=120, blank=True)
    linked_entity_id = models.CharField(max_length=120, blank=True)
    visibility_scope = models.CharField(max_length=20, choices=TaskVisibility.choices, default=TaskVisibility.PRIVATE)

    # Calendar sync integration placeholders
    calendar_event_id = models.CharField(max_length=255, blank=True)
    calendar_sync_status = models.CharField(max_length=20, blank=True)

    class Recurrence(models.TextChoices):
        NONE = "none", "None"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"

    recurrence = models.CharField(max_length=12, choices=Recurrence.choices, default=Recurrence.NONE)
    recurrence_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-priority", "due_date", "-id"]
        indexes = [
            models.Index(fields=["company", "assigned_to", "status"]),
            models.Index(fields=["company", "assigned_by"]),
            models.Index(fields=["company", "due_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.title}"


class CalendarProvider(models.TextChoices):
    GOOGLE = "google", "Google"
    OUTLOOK = "outlook", "Outlook"


class UserCalendarLink(CompanyAwareModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calendar_links")
    provider = models.CharField(max_length=20, choices=CalendarProvider.choices, default=CalendarProvider.GOOGLE)
    email = models.EmailField(blank=True)
    is_enabled = models.BooleanField(default=False)
    # Private token for ICS feed subscription
    ics_token = models.CharField(max_length=64, unique=True)

    class Meta:
        unique_together = ("company", "user", "provider")

    def __str__(self) -> str:
        return f"{self.user_id}:{self.provider}:{'on' if self.is_enabled else 'off'}"


class UserCalendarCredential(CompanyAwareModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calendar_credentials")
    provider = models.CharField(max_length=20, choices=CalendarProvider.choices, default=CalendarProvider.OUTLOOK)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()
    scope = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("company", "user", "provider")

    def __str__(self) -> str:
        return f"{self.user_id}:{self.provider} cred"
