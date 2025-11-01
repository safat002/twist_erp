from decimal import Decimal

from django.db import migrations, models
from django.conf import settings
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0004_add_finance_and_additional_models"),
        ("finance", "0001_initial"),
        ("companies", "0004_intercompanylink_groupaccountmap"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssetDisposal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("method", models.CharField(choices=[("SALE", "Sale"), ("SCRAP", "Scrap"), ("WRITE_OFF", "Write Off")], max_length=20)),
                ("disposal_date", models.DateField()),
                ("reason", models.TextField(blank=True)),
                ("proceeds_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=16)),
                ("nbv_at_disposal", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=16)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("POSTED", "Posted")], default="DRAFT", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="disposals", to="assets.asset")),
                ("asset_cost_account", models.ForeignKey(blank=True, help_text="Fixed asset cost account to credit on disposal", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="finance.account")),
                ("accumulated_dep_account", models.ForeignKey(blank=True, help_text="Accumulated depreciation account to debit on disposal", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="finance.account")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="asset_disposals", to="companies.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("gain_loss_account", models.ForeignKey(blank=True, help_text="Gain/Loss on disposal account", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="finance.account")),
                ("proceeds_account", models.ForeignKey(blank=True, help_text="Cash/Bank or Receivable account to debit for proceeds", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="finance.account")),
                ("voucher", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="finance.journalvoucher")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
