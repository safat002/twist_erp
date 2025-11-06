from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("companies", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Borrower",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=30)),
                ("name", models.CharField(max_length=255)),
                ("mobile", models.CharField(blank=True, max_length=32)),
                ("nid", models.CharField(blank=True, max_length=50)),
                ("address", models.TextField(blank=True)),
                ("group_name", models.CharField(blank=True, max_length=100)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="borrowers", to="companies.company")),
            ],
            options={"ordering": ["name"], "unique_together": {("company", "code")}},
        ),
        migrations.CreateModel(
            name="LoanProduct",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=30)),
                ("name", models.CharField(max_length=255)),
                ("interest_rate_annual", models.DecimalField(decimal_places=4, max_digits=7)),
                ("term_months", models.PositiveIntegerField()),
                ("repayment_frequency", models.CharField(choices=[("weekly", "Weekly"), ("biweekly", "Bi-Weekly"), ("monthly", "Monthly")], default="monthly", max_length=20)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="loan_products", to="companies.company")),
            ],
            options={"unique_together": {("company", "code")}},
        ),
        migrations.CreateModel(
            name="Loan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("number", models.CharField(blank=True, max_length=40)),
                ("principal", models.DecimalField(decimal_places=2, max_digits=20)),
                ("interest_rate_annual", models.DecimalField(decimal_places=4, max_digits=7)),
                ("term_months", models.PositiveIntegerField()),
                ("repayment_frequency", models.CharField(choices=[("weekly", "Weekly"), ("biweekly", "Bi-Weekly"), ("monthly", "Monthly")], default="monthly", max_length=20)),
                ("disburse_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[
                    ("applied", "Applied"),
                    ("approved", "Approved"),
                    ("disbursed", "Disbursed"),
                    ("active", "Active"),
                    ("closed", "Closed"),
                    ("written_off", "Written Off")
                ], default="applied", max_length=20)),
                ("outstanding_amount", models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ("borrower", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="loans", to="microfinance.borrower")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="loans", to="companies.company")),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="loans", to="microfinance.loanproduct")),
            ],
            options={"unique_together": {("company", "number")}},
        ),
        migrations.CreateModel(
            name="LoanRepaymentSchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("installment_number", models.PositiveIntegerField()),
                ("due_date", models.DateField()),
                ("principal_due", models.DecimalField(decimal_places=2, max_digits=20)),
                ("interest_due", models.DecimalField(decimal_places=2, max_digits=20)),
                ("total_due", models.DecimalField(decimal_places=2, max_digits=20)),
                ("paid_amount", models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("paid", "Paid"), ("overdue", "Overdue")], default="pending", max_length=20)),
                ("loan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="schedule", to="microfinance.loan")),
            ],
            options={"ordering": ["loan", "installment_number"]},
        ),
        migrations.CreateModel(
            name="LoanRepayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payment_date", models.DateField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=20)),
                ("receipt_number", models.CharField(blank=True, max_length=40)),
                ("loan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="repayments", to="microfinance.loan")),
                ("schedule", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="repayments", to="microfinance.loanrepaymentschedule")),
            ],
        ),
    ]

