# Fix DeliveryOrderLine to reference sales.Product instead of inventory.Item
from django.db import migrations, models
import django.db.models.deletion


def migrate_deliveryorderline_to_sales_product(apps, schema_editor):
    """
    Update DeliveryOrderLine to reference sales.Product instead of inventory.Item.
    Map existing inventory.Item references to corresponding sales.Product.
    """
    DeliveryOrderLine = apps.get_model('inventory', 'DeliveryOrderLine')
    SalesProduct = apps.get_model('sales', 'Product')
    Item = apps.get_model('inventory', 'Item')

    print("\n" + "="*60)
    print("Migrating DeliveryOrderLine references from Item to sales.Product")
    print("="*60)

    lines_updated = 0
    lines_skipped = 0

    for line in DeliveryOrderLine.objects.select_related('product').all():
        # Current product field points to inventory.Item
        item = line.product

        # Find the corresponding sales.Product via legacy_product_id
        if hasattr(item, 'legacy_product_id') and item.legacy_product_id:
            sales_product = SalesProduct.objects.filter(
                legacy_product_id=item.legacy_product_id
            ).first()

            if sales_product:
                # Update to reference sales.Product
                line.product_id = sales_product.id
                line.save(update_fields=['product_id'])
                lines_updated += 1
            else:
                print(f"  WARNING: No sales.Product found for Item {item.code} (legacy_id: {item.legacy_product_id})")
                lines_skipped += 1
        else:
            print(f"  WARNING: Item {item.code} has no legacy_product_id")
            lines_skipped += 1

    print(f"\nMigration Summary:")
    print(f"  Lines updated: {lines_updated}")
    print(f"  Lines skipped: {lines_skipped}")
    print("="*60 + "\n")


def reverse_migration(apps, schema_editor):
    """Reverse: Map sales.Product back to inventory.Item"""
    DeliveryOrderLine = apps.get_model('inventory', 'DeliveryOrderLine')
    SalesProduct = apps.get_model('sales', 'Product')

    for line in DeliveryOrderLine.objects.select_related('product').all():
        sales_product = line.product
        if sales_product.linked_item_id:
            line.product_id = sales_product.linked_item_id
            line.save(update_fields=['product_id'])


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "10003_remove_stockledger_inventory_s_company_394f5b_idx_and_more"),
        ("sales", "0005_taxcategory_productcategory_product_and_more"),
    ]

    operations = [
        # Step 1: Run data migration to map Item IDs to sales.Product IDs
        migrations.RunPython(
            migrate_deliveryorderline_to_sales_product,
            reverse_migration
        ),

        # Step 2: Alter the ForeignKey to point to sales.Product
        migrations.AlterField(
            model_name="deliveryorderline",
            name="product",
            field=models.ForeignKey(
                to="sales.product",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="delivery_order_lines",
                help_text="Saleable product being delivered to customer"
            ),
        ),
    ]
