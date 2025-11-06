from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.budgeting.models import Budget
from apps.budgeting.services import BudgetNotificationService


class Command(BaseCommand):
    help = "Send notifications for entry period start/ending/ended for budgets."

    def handle(self, *args, **options):
        today = timezone.now().date()
        soon = today + timedelta(days=1)

        # Starting today
        for b in Budget.objects.filter(entry_start_date=today):
            BudgetNotificationService.notify_entry_period_started(b)

        # Ending tomorrow
        for b in Budget.objects.filter(entry_end_date=soon):
            BudgetNotificationService.notify_entry_period_ending(b, 1)

        # Ended today
        for b in Budget.objects.filter(entry_end_date=today):
            BudgetNotificationService.notify_entry_period_ended(b)

        self.stdout.write(self.style.SUCCESS("Entry period notifications processed."))

