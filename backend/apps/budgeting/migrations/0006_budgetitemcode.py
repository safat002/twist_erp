from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("budgeting", "0005_alter_budgetusage_usage_type"),
        ("inventory", "0005_goodsreceipt_hold_reason_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="BudgetItemCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=64)),
                ("name", models.CharField(max_length=255)),
                ("category", models.CharField(blank=True, max_length=120)),
                ("standard_price", models.DecimalField(decimal_places=2, default="0.00", max_digits=20)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="budget_item_codes", to="companies.company")),
                ("uom", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="budget_item_codes", to="inventory.unitofmeasure")),
            ],
            options={
                "ordering": ["code"],
                "unique_together": {("company", "code")},
            },
        ),
        migrations.AddIndex(
            model_name="budgetitemcode",
            index=models.Index(fields=["company", "code"], name="budgeting_b_company_code_idx"),
        ),
        migrations.AddIndex(
            model_name="budgetitemcode",
            index=models.Index(fields=["company", "is_active"], name="budgeting_b_company_active_idx"),
        ),
    ]

