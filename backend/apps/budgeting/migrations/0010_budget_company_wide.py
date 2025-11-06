from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("budgeting", "0009_alter_budget_status_length"),
    ]

    operations = [
        migrations.AlterField(
            model_name="budget",
            name="cost_center",
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name="budgets", to="budgeting.costcenter"),
        ),
        migrations.RemoveConstraint(
            model_name="budget",
            name="unique_budget_period_per_type",
        ),
        migrations.AddConstraint(
            model_name="budget",
            constraint=models.UniqueConstraint(
                fields=["company", "budget_type", "period_start", "period_end"], name="unique_company_period_per_type"
            ),
        ),
    ]
