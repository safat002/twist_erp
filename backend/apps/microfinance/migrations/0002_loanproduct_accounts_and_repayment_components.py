from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0001_initial"),
        ("microfinance", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="loanproduct",
            name="portfolio_account",
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name="loan_products_portfolio", to="finance.account"),
        ),
        migrations.AddField(
            model_name="loanproduct",
            name="interest_income_account",
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name="loan_products_interest", to="finance.account"),
        ),
        migrations.AddField(
            model_name="loanproduct",
            name="cash_account",
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name="loan_products_cash", to="finance.account"),
        ),
        migrations.AddField(
            model_name="loanrepayment",
            name="principal_component",
            field=models.DecimalField(max_digits=20, decimal_places=2, default=0),
        ),
        migrations.AddField(
            model_name="loanrepayment",
            name="interest_component",
            field=models.DecimalField(max_digits=20, decimal_places=2, default=0),
        ),
    ]

