from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0013_costlayer_expiry_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockmovementline",
            name="expiry_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]

