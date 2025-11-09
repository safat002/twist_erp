from django.core.management.base import BaseCommand

from apps.budgeting.models import Budget, BudgetApproval


class Command(BaseCommand):
    help = "Re-run CC approvals: reset prematurely approved CC approval tasks to PENDING when not all items are cleared, and fix budget workflow back to PENDING_CC_APPROVAL."

    def handle(self, *args, **options):
        reset_tasks = 0
        budgets_touched = set()

        cc_approvals = BudgetApproval.objects.select_related("budget", "cost_center").filter(
            approver_type=BudgetApproval.ApproverType.COST_CENTER_OWNER,
            status=BudgetApproval.Status.APPROVED,
        )

        for appr in cc_approvals:
            budget = appr.budget
            cc = appr.cost_center or getattr(budget, 'cost_center', None)
            try:
                lines = list(budget.lines.all())
                if cc:
                    cc_lines = [
                        bl for bl in lines
                        if (getattr(bl, 'metadata', {}) or {}).get('cost_center_id') == cc.id
                        or getattr(budget, 'cost_center_id', None) == cc.id
                    ]
                else:
                    cc_lines = lines
                if not cc_lines:
                    continue
                total = len(cc_lines)
                cleared = 0
                for bl in cc_lines:
                    meta = getattr(bl, 'metadata', {}) or {}
                    if meta.get('approved') is True or getattr(bl, 'sent_back_for_review', False):
                        cleared += 1
                if cleared < total:
                    # Reset to pending
                    appr.status = BudgetApproval.Status.PENDING
                    appr.decision_date = None
                    appr.save(update_fields=["status", "decision_date"])
                    reset_tasks += 1
                    budgets_touched.add(budget.id)
            except Exception:
                continue

        # Fix budgets back to PENDING_CC_APPROVAL when there are still pending CC tasks
        for bid in budgets_touched:
            try:
                b = Budget.objects.get(pk=bid)
                has_pending = b.approvals.filter(
                    approver_type=BudgetApproval.ApproverType.COST_CENTER_OWNER,
                    status=BudgetApproval.Status.PENDING,
                ).exists()
                if has_pending and getattr(b, 'status', None) != Budget.STATUS_PENDING_CC_APPROVAL:
                    b.status = Budget.STATUS_PENDING_CC_APPROVAL
                    b.save(update_fields=["status", "updated_at"])
            except Budget.DoesNotExist:
                continue

        self.stdout.write(self.style.SUCCESS(f"Reset {reset_tasks} CC approval task(s). Budgets touched: {len(budgets_touched)}."))

