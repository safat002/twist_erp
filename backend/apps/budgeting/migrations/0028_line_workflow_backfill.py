from django.db import migrations
from django.db.models import Q


def backfill_workflow(apps, schema_editor):
    BudgetLine = apps.get_model('budgeting', 'BudgetLine')
    BudgetApproval = apps.get_model('budgeting', 'BudgetApproval')
    BudgetApprovalLine = apps.get_model('budgeting', 'BudgetApprovalLine')

    # 1. Backfill BudgetLine workflow fields from legacy metadata
    for line in BudgetLine.objects.all().iterator():
        meta = getattr(line, 'metadata', {}) or {}
        updates = []
        new_cc = 'APPROVED' if meta.get('approved') else 'SENT_BACK' if (getattr(line, 'sent_back_for_review', False) or meta.get('rejected')) else 'PENDING'
        if line.cc_decision != new_cc:
            line.cc_decision = new_cc
            updates.append('cc_decision')
        new_final = 'APPROVED' if meta.get('final_approved') else 'REJECTED' if meta.get('final_rejected') else 'PENDING'
        if line.final_decision != new_final:
            line.final_decision = new_final
            updates.append('final_decision')
        if getattr(line, 'moderator_remarks', None) and str(line.moderator_remarks).strip():
            new_mod = 'REMARKED'
        elif getattr(line, 'is_held_for_review', False):
            new_mod = 'HELD'
        elif getattr(line, 'sent_back_for_review', False):
            new_mod = 'SENT_BACK'
        else:
            new_mod = 'NONE'
        if line.moderator_state != new_mod:
            line.moderator_state = new_mod
            updates.append('moderator_state')
        if updates:
            line.save(update_fields=updates)

    # 2. Populate BudgetApprovalLine scopes for existing approvals
    APPROVER_CC = 'cost_center_owner'
    APPROVER_FINAL = 'budget_module_owner'
    APPROVER_NAME = 'budget_name_approver'

    for approval in BudgetApproval.objects.select_related('budget', 'cost_center').all():
        if approval.approver_type == APPROVER_NAME:
            continue
        budget = approval.budget
        if not budget:
            continue
        if approval.approver_type == APPROVER_CC:
            stage = 'CC_APPROVAL'
            cc_id = approval.cost_center_id or getattr(budget, 'cost_center_id', None)
            lines_qs = BudgetLine.objects.filter(budget_id=budget.id)
            if cc_id:
                lines_qs = lines_qs.filter(Q(metadata__cost_center_id=cc_id) | Q(budget__cost_center_id=cc_id))
            lines = list(lines_qs)
        else:
            stage = 'FINAL_APPROVAL'
            lines = []
            for line in BudgetLine.objects.filter(budget_id=budget.id).iterator():
                meta = getattr(line, 'metadata', {}) or {}
                has_final_flag = meta.get('final_approved') or meta.get('final_rejected')
                remarked = bool((getattr(line, 'moderator_remarks', None) or '').strip())
                auto_forwarded = meta.get('not_reviewed')
                if has_final_flag or remarked or auto_forwarded:
                    lines.append(line)
        for line in lines:
            if stage == 'CC_APPROVAL':
                if line.cc_decision == 'APPROVED':
                    status = 'APPROVED'
                elif line.cc_decision == 'SENT_BACK':
                    status = 'SENT_BACK'
                else:
                    status = 'PENDING'
            else:
                if line.final_decision == 'APPROVED':
                    status = 'APPROVED'
                elif line.final_decision == 'REJECTED':
                    status = 'REJECTED'
                else:
                    status = 'PENDING'

            defaults = {
                'stage': stage,
                'status': status,
            }
            bal, created = BudgetApprovalLine.objects.get_or_create(
                approval=approval,
                line=line,
                defaults=defaults,
            )
            if not created:
                update_status = defaults['status']
                if bal.status != update_status:
                    bal.status = update_status
                    bal.stage = stage
                    bal.save(update_fields=['status', 'stage', 'updated_at'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('budgeting', '0027_budgetline_cc_decision_budgetline_cc_decision_at_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_workflow, noop),
    ]

