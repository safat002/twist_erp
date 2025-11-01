import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import TaskItem, TaskStatus, TaskPriority
from apps.notifications.models import Notification, NotificationSeverity

logger = logging.getLogger(__name__)


@shared_task(name="apps.tasks.check_overdue_tasks")
def check_overdue_tasks():
    """Create notifications for overdue high/critical tasks.

    Escalation policies can be integrated with Workflow Studio later.
    """
    now = timezone.now()
    overdue = TaskItem.objects.filter(
        due_date__lt=now,
        status__in=[TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED],
        priority__in=[TaskPriority.HIGH, TaskPriority.CRITICAL],
    )
    created = 0
    for task in overdue:
        exists = Notification.objects.filter(
            user=task.assigned_to,
            company=task.company,
            group_key="task_overdue",
            entity_type="TASK",
            entity_id=str(task.id),
        ).exists()
        if exists:
            continue
        severity = NotificationSeverity.CRITICAL if task.priority == TaskPriority.CRITICAL else NotificationSeverity.WARNING
        Notification.objects.create(
            company=task.company,
            company_group=task.company_group,
            created_by=task.assigned_by,
            user=task.assigned_to,
            title=f"Overdue task: {task.title}",
            body="This task is overdue. Please update status or reschedule.",
            severity=severity,
            group_key="task_overdue",
            entity_type="TASK",
            entity_id=str(task.id),
        )
        created += 1
    logger.info("Overdue task notifications created: %s", created)
    return {"created": created}

