from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0011_costlayer_stock_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="goodsreceiptline",
            name="batch_no",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="goodsreceiptline",
            name="expiry_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]

