from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "10001_item_itemcategory_alter_productcategory_options_and_more"),
        ("sales", "0005_taxcategory_productcategory_product_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="salesorderline",
            name="product",
            field=models.ForeignKey(to="inventory.item", on_delete=django.db.models.deletion.PROTECT),
        ),
    ]

