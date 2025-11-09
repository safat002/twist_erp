from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("budgeting", "0024_add_budgetline_budget_item"),
    ]

    operations = [
        migrations.AddField(
            model_name="budget",
            name="name_status",
            field=models.CharField(
                choices=[("DRAFT", "Draft"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")],
                default="DRAFT",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="budget",
            name="name_approved_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="name_approved_budgets", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="budget",
            name="name_approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="budget",
            name="auto_activate",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="budget",
            name="applicable_cost_centers",
            field=models.ManyToManyField(blank=True, related_name="applicable_budgets", to="budgeting.costcenter"),
        ),
    ]
