from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0003_remove_customer_company_group_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="customer_type",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("local", "Local"),
                    ("export", "Export"),
                    ("intercompany", "Intercompany"),
                ],
                default="local",
            ),
        ),
    ]

