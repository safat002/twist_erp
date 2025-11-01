from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0003_rename_assets_asset_company_ae4bee_idx_assets_asse_company_5ef9ed_idx_and_more"),
        ("finance", "0001_initial"),
        ("companies", "0004_intercompanylink_groupaccountmap"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="depreciation_expense_account",
            field=models.ForeignKey(
                blank=True,
                help_text="Expense account to debit for monthly depreciation",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="depreciation_assets",
                to="finance.account",
            ),
        ),
        migrations.AddField(
            model_name="asset",
            name="accumulated_depreciation_account",
            field=models.ForeignKey(
                blank=True,
                help_text="Balance sheet account to credit (accumulated depreciation)",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="accumulated_depreciation_assets",
                to="finance.account",
            ),
        ),
        migrations.CreateModel(
            name="DepreciationRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period", models.CharField(help_text="YYYY-MM", max_length=7)),
                ("total_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "company",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="asset_depreciation_runs", to="companies.company"),
                ),
                (
                    "voucher",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="finance.journalvoucher"),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AlterUniqueTogether(name="depreciationrun", unique_together={("company", "period")}),
        migrations.CreateModel(
            name="DowntimeLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.CharField(max_length=255)),
                ("started_at", models.DateTimeField()),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("impact_percent", models.PositiveIntegerField(default=0, help_text="Estimated productivity impact 0-100%")),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "asset",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="downtimes", to="assets.asset"),
                ),
                (
                    "company",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="asset_downtimes", to="companies.company"),
                ),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.AddIndex(
            model_name="downtimelog",
            index=models.Index(fields=["company", "started_at"], name="assets_down_company_ae0b2a_idx"),
        ),
        migrations.AddIndex(
            model_name="downtimelog",
            index=models.Index(fields=["company", "asset"], name="assets_down_company_4b5b7f_idx"),
        ),
    ]

