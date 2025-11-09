from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budgeting', '0023_budgetitemcode_created_at_budgetitemcode_is_active_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='budgetline',
            name='budget_item',
            field=models.ForeignKey(
                to='budgeting.budgetitemcode',
                null=True,
                blank=True,
                on_delete=models.SET_NULL,
                related_name='budget_lines',
            ),
        ),
    ]
