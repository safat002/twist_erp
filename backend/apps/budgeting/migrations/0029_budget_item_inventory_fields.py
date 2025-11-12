from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('budgeting', '0028_line_workflow_backfill'),
        ('inventory', '10025_materialissue_materialissueline_and_more'),
        ('finance', '0015_inventorypostingrule_finance_inv_company_344372_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='budgetitemcode',
            name='stock_uom',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='+',
                to='inventory.unitofmeasure',
            ),
        ),
        migrations.AddField(
            model_name='budgetitemcode',
            name='valuation_rate',
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='budgetitemcode',
            name='is_batch_tracked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='budgetitemcode',
            name='is_serial_tracked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='budgetitemcode',
            name='requires_fefo',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='budgetitemcode',
            name='item_type',
            field=models.CharField(
                choices=[
                    ('GOODS', 'Goods'),
                    ('SERVICE', 'Service'),
                    ('TAX', 'Tax'),
                    ('OTHER', 'Other'),
                ],
                default='GOODS',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='budgetitemcode',
            name='inventory_account',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='+',
                to='finance.account',
            ),
        ),
        migrations.AddField(
            model_name='budgetitemcode',
            name='expense_account',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='+',
                to='finance.account',
            ),
        ),
    ]
