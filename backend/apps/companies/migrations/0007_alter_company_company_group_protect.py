from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0006_company_default_data_loaded_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="company",
            name="company_group",
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name="companies",
                help_text="Parent group (optional for standalone companies)",
                to="companies.companygroup",
            ),
        ),
    ]

