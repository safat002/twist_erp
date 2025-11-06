from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("budgeting", "0010_budget_company_wide"),
    ]

    operations = [
        migrations.AlterField(
            model_name="budget",
            name="amount",
            field=models.DecimalField(max_digits=16, decimal_places=2, default="0.00"),
        ),
    ]

