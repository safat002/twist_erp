from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0001_initial"),
        ("budgeting", "0012_merge_20251103_1645"),
    ]

    operations = [
        migrations.AddField(
            model_name="budget",
            name="parent_declared",
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name="cc_budgets", to="budgeting.budget"),
        ),
        migrations.AddField(
            model_name="budget",
            name="revision_no",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="budgetline",
            name="manual_unit_price",
            field=models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True),
        ),
        # Remove prior broad unique constraint if present
        migrations.RemoveConstraint(
            model_name="budget",
            name="unique_company_period_per_type",
        ),
        # Add partial uniques for declared and CC budgets
        migrations.AddConstraint(
            model_name="budget",
            constraint=models.UniqueConstraint(
                fields=["company", "budget_type", "period_start", "period_end"],
                condition=Q(cost_center__isnull=True),
                name="uniq_declared_company_type_period",
            ),
        ),
        migrations.AddConstraint(
            model_name="budget",
            constraint=models.UniqueConstraint(
                fields=["company", "budget_type", "period_start", "period_end", "cost_center", "revision_no"],
                condition=Q(cost_center__isnull=False),
                name="uniq_cc_company_type_period_revision",
            ),
        ),
        migrations.CreateModel(
            name="BudgetPricePolicy",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("primary_source", models.CharField(max_length=20, choices=[("standard", "Standard"), ("last_po", "Last PO"), ("avg", "Average"), ("manual_only", "Manual Only")], default="standard")),
                ("secondary_source", models.CharField(max_length=20, choices=[("standard", "Standard"), ("last_po", "Last PO"), ("avg", "Average"), ("manual_only", "Manual Only")], default="last_po")),
                ("tertiary_source", models.CharField(max_length=20, choices=[("standard", "Standard"), ("last_po", "Last PO"), ("avg", "Average"), ("manual_only", "Manual Only")], default="avg")),
                ("avg_lookback_days", models.IntegerField(default=365)),
                ("fallback_on_zero", models.BooleanField(default=True)),
                ("company", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="budget_price_policy", to="companies.company")),
            ],
            options={
                "ordering": ["company_id"],
            },
        ),
    ]

