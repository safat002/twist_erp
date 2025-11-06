# Fix WorkOrderComponent and MaterialIssueLine to reference inventory.Item
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "10002_migrate_product_to_item_and_sales_product"),
        ("production", "0002_alter_product_fk_to_item"),
    ]

    operations = [
        # Fix WorkOrderComponent.component to have proper related_name
        migrations.AlterField(
            model_name="workordercomponent",
            name="component",
            field=models.ForeignKey(
                to="inventory.item",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="work_order_components",
                help_text="Component item required for production"
            ),
        ),

        # Rename MaterialIssueLine.product to item
        migrations.RenameField(
            model_name="materialissueline",
            old_name="product",
            new_name="item",
        ),

        # Update the ForeignKey definition for MaterialIssueLine.item
        migrations.AlterField(
            model_name="materialissueline",
            name="item",
            field=models.ForeignKey(
                to="inventory.item",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="material_issue_lines",
                help_text="Item being issued for production"
            ),
        ),
    ]
