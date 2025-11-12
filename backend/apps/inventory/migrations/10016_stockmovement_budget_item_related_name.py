from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '10015_budget_item_constraints'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockmovement',
            name='budget_item',
            field=models.ForeignKey(
                blank=True,
                help_text='Budget master item reference',
                null=True,
                on_delete=models.PROTECT,
                related_name='stock_movements',
                to='budgeting.budgetitemcode',
            ),
        ),
    ]
