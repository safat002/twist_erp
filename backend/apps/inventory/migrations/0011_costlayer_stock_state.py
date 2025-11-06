from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0010_stockledger_layer_consumed_detail_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="costlayer",
            name="stock_state",
            field=models.CharField(
                choices=[
                    ("QUARANTINE", "Quarantine"),
                    ("ON_HOLD", "On Hold"),
                    ("RELEASED", "Released"),
                ],
                default="QUARANTINE",
                help_text="Stock availability state; only RELEASED layers are issuable",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="costlayer",
            index=models.Index(
                fields=["company", "product", "warehouse", "stock_state"], name="inv_costlayer_state_idx"
            ),
        ),
    ]

