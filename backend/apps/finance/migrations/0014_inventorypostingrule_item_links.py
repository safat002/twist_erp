from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '10018_event_linkages'),
        ('budgeting', '0028_line_workflow_backfill'),
        ('finance', '0013_journalentry_cost_center_journalentry_project'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventorypostingrule',
            name='budget_item',
            field=models.ForeignKey(blank=True, help_text='Specific budget item for this posting rule', null=True, on_delete=models.PROTECT, related_name='inventory_posting_rules', to='budgeting.budgetitemcode'),
        ),
        migrations.AddField(
            model_name='inventorypostingrule',
            name='item',
            field=models.ForeignKey(blank=True, help_text='Legacy item reference (deprecated, prefer budget item)', null=True, on_delete=models.PROTECT, related_name='inventory_posting_rules', to='inventory.item'),
        ),
    ]
