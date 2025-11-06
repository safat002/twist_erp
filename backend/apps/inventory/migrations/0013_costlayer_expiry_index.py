from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0012_goodsreceiptline_batch_expiry"),
    ]

    operations = [
        migrations.AddField(
            model_name="costlayer",
            name="expiry_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="costlayer",
            index=models.Index(fields=["expiry_date"], name="inv_costlayer_expiry_idx"),
        ),
    ]

