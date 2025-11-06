from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0002_deliveryorder_goodsreceipt_stocklevel_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="unitofmeasure",
            name="short_name",
            field=models.CharField(max_length=20, blank=True, default=""),
        ),
    ]

