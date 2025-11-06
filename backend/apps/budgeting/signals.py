from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Budget
from .services import BudgetNotificationService


@receiver(post_save, sender=Budget)
def budget_status_notifications(sender, instance: Budget, created: bool, **kwargs):
    if created:
        return
    # Simple notifications on key transitions
    if instance.status == Budget.STATUS_APPROVED:
        try:
            BudgetNotificationService.notify_budget_active(instance)
        except Exception:
            pass
