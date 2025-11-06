from django.db import migrations, connection


def drop_fk_constraints(cursor, table_name: str, column_name: str, ref_table: str):
    sql = (
        "SELECT conname FROM pg_constraint c "
        "JOIN pg_class r ON r.oid = c.conrelid "
        "JOIN pg_attribute a ON a.attrelid = r.oid AND a.attnum = ANY(c.conkey) "
        "JOIN pg_class fr ON fr.oid = c.confrelid "
        "WHERE r.relname = %s AND a.attname = %s AND fr.relname = %s AND c.contype = 'f'"
    )
    cursor.execute(sql, [table_name, column_name, ref_table])
    rows = cursor.fetchall()
    for (conname,) in rows:
        cursor.execute(f'ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {conname}')


def map_costlayer_product_to_item(apps, schema_editor):
    # Drop existing FKs to inventory_product so we can rewrite ids safely
    with connection.cursor() as cursor:
        drop_fk_constraints(cursor, 'inventory_costlayer', 'product_id', 'inventory_product')
        drop_fk_constraints(cursor, 'inventory_valuationchangelog', 'product_id', 'inventory_product')
        drop_fk_constraints(cursor, 'inventory_itemvaluationmethod', 'product_id', 'inventory_product')

    Item = apps.get_model('inventory', 'Item')
    CostLayer = apps.get_model('inventory', 'CostLayer')
    ValuationChangeLog = apps.get_model('inventory', 'ValuationChangeLog')
    ItemValuationMethod = apps.get_model('inventory', 'ItemValuationMethod')

    # Build mapping: legacy_product_id -> new Item.id
    legacy_to_item = {}
    for item in Item.objects.exclude(legacy_product_id__isnull=True).only('id', 'legacy_product_id'):
        legacy_to_item[item.legacy_product_id] = item.id

    # Remap CostLayer.product_id where possible
    for cl in CostLayer.objects.all().only('id', 'product_id'):
        new_id = legacy_to_item.get(cl.product_id)
        if new_id:
            CostLayer.objects.filter(pk=cl.pk).update(product_id=new_id)

    # Remap ValuationChangeLog.product_id
    for vcl in ValuationChangeLog.objects.all().only('id', 'product_id'):
        new_id = legacy_to_item.get(vcl.product_id)
        if new_id:
            ValuationChangeLog.objects.filter(pk=vcl.pk).update(product_id=new_id)

    # Remap ItemValuationMethod.product_id
    for ivm in ItemValuationMethod.objects.all().only('id', 'product_id'):
        new_id = legacy_to_item.get(ivm.product_id)
        if new_id:
            ItemValuationMethod.objects.filter(pk=ivm.pk).update(product_id=new_id)


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "10002_migrate_product_to_item_and_sales_product"),
    ]

    operations = [
        migrations.RunPython(map_costlayer_product_to_item, migrations.RunPython.noop),
    ]
