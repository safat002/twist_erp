from django.core.management.base import BaseCommand
from django.db import transaction

from apps.budgeting.models import Budget, BudgetApproval


class Command(BaseCommand):
    help = "Align existing budgets with new name-approval policy (Draft -> Approved)."

    def handle(self, *args, **options):
        updated_pending = 0
        updated_entry_open = 0

        with transaction.atomic():
            # 1) Registry budgets stuck in pending_name_approval -> move to DRAFT
            qs_pending = Budget.objects.filter(cost_center__isnull=True, status=getattr(Budget, 'STATUS_PENDING_NAME_APPROVAL', 'pending_name_approval'))
            updated_pending = qs_pending.update(status=Budget.STATUS_DRAFT)

            # 2) Registry budgets in ENTRY_OPEN with approved name-approval -> mark as APPROVED
            qs_entry_open = Budget.objects.filter(cost_center__isnull=True, status=getattr(Budget, 'STATUS_ENTRY_OPEN', 'ENTRY_OPEN'))
            for b in qs_entry_open:
                has_approved = BudgetApproval.objects.filter(
                    budget=b,
                    approver_type=BudgetApproval.ApproverType.BUDGET_NAME_APPROVER,
                    status=BudgetApproval.Status.APPROVED,
                ).exists()
                if has_approved:
                    b.status = Budget.STATUS_APPROVED
                    b.save(update_fields=["status", "updated_at"])
                    updated_entry_open += 1

        self.stdout.write(self.style.SUCCESS(
            f"Updated {updated_pending} registry budgets to DRAFT and {updated_entry_open} to APPROVED."
        ))

