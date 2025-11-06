from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "10001_item_itemcategory_alter_productcategory_options_and_more"),
        ("production", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="billofmaterial",
            name="product",
            field=models.ForeignKey(to="inventory.item", on_delete=django.db.models.deletion.PROTECT, related_name="boms"),
        ),
        migrations.AlterField(
            model_name="billofmaterialcomponent",
            name="component",
            field=models.ForeignKey(to="inventory.item", on_delete=django.db.models.deletion.PROTECT, related_name="bom_components"),
        ),
        migrations.AlterField(
            model_name="workorder",
            name="product",
            field=models.ForeignKey(to="inventory.item", on_delete=django.db.models.deletion.PROTECT, related_name="work_orders"),
        ),
    ]

