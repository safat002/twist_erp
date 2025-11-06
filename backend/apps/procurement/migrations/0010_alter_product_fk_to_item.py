from django.db import migrations, models
import django.db.models.deletion

def nullify_all_products(apps, schema_editor):
    Item = apps.get_model('inventory', 'Item')
    POL = apps.get_model('procurement', 'PurchaseOrderLine')
    PRL = apps.get_model('procurement', 'PurchaseRequisitionLine')
    # For safety in mixed databases, set all existing product references to NULL before FK change
    POL.objects.exclude(product_id__isnull=True).update(product_id=None)
    PRL.objects.exclude(product_id__isnull=True).update(product_id=None)
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "10001_item_itemcategory_alter_productcategory_options_and_more"),
        ("procurement", "0009_rename_proc_pr_draft_compan_bf18f3_idx_procurement_company_cda163_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(nullify_all_products, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="purchaserequisitionline",
            name="product",
            field=models.ForeignKey(
                to="inventory.item",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="purchase_requisition_lines",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="purchaseorderline",
            name="product",
            field=models.ForeignKey(
                to="inventory.item",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="purchase_order_lines",
                null=True,
                blank=True,
            ),
        ),
    ]
