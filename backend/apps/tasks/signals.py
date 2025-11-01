from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.models import Notification, NotificationSeverity
from .models import TaskItem, TaskType, TaskPriority


@receiver(post_save, sender=TaskItem)
def create_task_notification(sender, instance: TaskItem, created: bool, **kwargs):
    if not created:
        return
    # Only notify for system tasks assigned to others
    if instance.task_type != TaskType.SYSTEM:
        return
    severity = NotificationSeverity.INFO
    if instance.priority in {TaskPriority.HIGH, TaskPriority.CRITICAL}:
        severity = NotificationSeverity.CRITICAL if instance.priority == TaskPriority.CRITICAL else NotificationSeverity.WARNING
    Notification.objects.create(
        company=instance.company,
        company_group=instance.company_group,
        created_by=instance.assigned_by,
        user=instance.assigned_to,
        title=f"New task assigned: {instance.title}",
        body=(instance.description or ""),
        severity=severity,
        group_key="task_assigned",
        entity_type=instance.linked_entity_type or "TASK",
        entity_id=str(instance.id),
    )

