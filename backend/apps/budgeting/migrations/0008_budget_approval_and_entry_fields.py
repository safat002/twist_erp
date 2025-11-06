from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("budgeting", "0007_rename_budgeting_b_company_code_idx_budgeting_b_company_fc7191_idx_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="budget",
            name="entry_start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="budget",
            name="entry_end_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="budget",
            name="budget_active_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="budget",
            name="budget_expire_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="budgetline",
            name="product",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="budget_lines", to="inventory.product"),
        ),
        migrations.CreateModel(
            name="BudgetApproval",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("approver_type", models.CharField(choices=[("cost_center_owner", "Cost Center Owner"), ("budget_module_owner", "Budget Module Owner")], max_length=32)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("sent_back", "Sent Back for Review")], default="pending", max_length=20)),
                ("decision_date", models.DateTimeField(auto_now_add=True)),
                ("comments", models.TextField(blank=True)),
                ("modifications_made", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("approver", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="budget_approvals", to=settings.AUTH_USER_MODEL)),
                ("budget", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="approvals", to="budgeting.budget")),
                ("cost_center", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="budget_approvals", to="budgeting.costcenter")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="budgetapproval",
            index=models.Index(fields=["budget", "approver_type", "status"], name="budget_appr_budget_ap_3b31b3_idx"),
        ),
        migrations.AddIndex(
            model_name="budgetapproval",
            index=models.Index(fields=["approver", "status"], name="budget_appr_approver__b4307b_idx"),
        ),
    ]

