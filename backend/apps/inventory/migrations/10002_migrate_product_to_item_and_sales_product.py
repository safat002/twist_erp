# Generated manually for Product-to-Item refactoring

from django.db import migrations
from decimal import Decimal


def migrate_products_to_items_and_sales_products(apps, schema_editor):
    """
    Split existing inventory.Product records into:
    1. inventory.Item (for all products - operational items)
    2. sales.Product (only for saleable products)

    Strategy:
    - Every old Product becomes a new Item
    - If Product has selling_price > 0 OR is used in sales, also create sales.Product
    - Link sales.Product to Item via linked_item field
    """

    # Get model references
    OldProduct = apps.get_model('inventory', 'Product')
    Item = apps.get_model('inventory', 'Item')
    ItemCategory = apps.get_model('inventory', 'ItemCategory')
    SalesProduct = apps.get_model('sales', 'Product')
    SalesProductCategory = apps.get_model('sales', 'ProductCategory')

    # Get references to check which products are used in sales
    SalesOrderLine = apps.get_model('sales', 'SalesOrderLine')

    # Get all products that have been used in sales orders
    products_in_sales = set(
        SalesOrderLine.objects.values_list('product_id', flat=True).distinct()
    )

    print(f"\n{'='*60}")
    print(f"PRODUCT-TO-ITEM DATA MIGRATION")
    print(f"{'='*60}")
    print(f"Total products to migrate: {OldProduct.objects.count()}")
    print(f"Products used in sales orders: {len(products_in_sales)}")

    # Step 1: Create ItemCategory records from ProductCategory
    print(f"\n--- Step 1: Migrating ProductCategories to ItemCategories ---")
    OldProductCategory = apps.get_model('inventory', 'ProductCategory')
    category_mapping = {}  # Maps old ProductCategory.id -> new ItemCategory.id

    for old_category in OldProductCategory.objects.all():
        # Check if ItemCategory already exists with same code
        existing = ItemCategory.objects.filter(
            company=old_category.company,
            code=old_category.code
        ).first()

        if existing:
            category_mapping[old_category.id] = existing.id
            print(f"  Reusing ItemCategory: {old_category.code}")
        else:
            item_category = ItemCategory.objects.create(
                company=old_category.company,
                code=old_category.code,
                name=old_category.name,
                is_active=old_category.is_active,
                created_by=old_category.created_by,
                created_at=old_category.created_at,
                updated_at=old_category.updated_at,
            )
            category_mapping[old_category.id] = item_category.id
            print(f"  Created ItemCategory: {old_category.code}")

    print(f"Created/mapped {len(category_mapping)} item categories")

    # Step 2: Create SalesProductCategory records from ProductCategory (for saleable products)
    print(f"\n--- Step 2: Creating SalesProductCategories ---")
    sales_category_mapping = {}  # Maps old ProductCategory.id -> new sales.ProductCategory.id

    for old_category in OldProductCategory.objects.all():
        # Check if already exists
        existing = SalesProductCategory.objects.filter(
            company=old_category.company,
            code=old_category.code
        ).first()

        if existing:
            sales_category_mapping[old_category.id] = existing.id
            print(f"  Reusing SalesProductCategory: {old_category.code}")
        else:
            sales_category = SalesProductCategory.objects.create(
                company=old_category.company,
                code=old_category.code,
                name=old_category.name,
                description="",
                is_active=old_category.is_active,
                created_by=old_category.created_by,
                created_at=old_category.created_at,
                updated_at=old_category.updated_at,
            )
            sales_category_mapping[old_category.id] = sales_category.id
            print(f"  Created SalesProductCategory: {old_category.code}")

    print(f"Created {len(sales_category_mapping)} sales categories")

    # Step 3: Migrate Products to Items and sales.Products
    print(f"\n--- Step 3: Migrating Products to Items + sales.Products ---")

    items_created = 0
    sales_products_created = 0
    product_mapping = {}  # Maps old Product.id -> new Item.id
    sales_product_mapping = {}  # Maps old Product.id -> new sales.Product.id

    for old_product in OldProduct.objects.select_related('category', 'uom').all():
        # Determine item type based on old product_type
        item_type_map = {
            'GOODS': 'RAW_MATERIAL',
            'SERVICE': 'SERVICE',
            'CONSUMABLE': 'CONSUMABLE',
        }
        item_type = item_type_map.get(old_product.product_type, 'RAW_MATERIAL')

        # Get mapped category
        item_category_id = category_mapping.get(old_product.category_id)
        if not item_category_id:
            print(f"  WARNING: No category mapping for product {old_product.code}, skipping...")
            continue

        # ALWAYS create Item for every product
        item = Item.objects.create(
            company=old_product.company,
            created_by=old_product.created_by,
            created_at=old_product.created_at,
            updated_at=old_product.updated_at,
            code=old_product.code,
            name=old_product.name,
            description=old_product.description,
            item_type=item_type,
            is_tradable=(old_product.selling_price > 0),  # Tradable if has selling price
            track_inventory=old_product.track_inventory,
            track_serial=old_product.track_serial,
            track_batch=old_product.track_batch,
            prevent_expired_issuance=old_product.prevent_expired_issuance,
            expiry_warning_days=old_product.expiry_warning_days,
            cost_price=old_product.cost_price,
            standard_cost=old_product.standard_cost,
            valuation_method=old_product.valuation_method,
            reorder_level=old_product.reorder_level,
            reorder_quantity=old_product.reorder_quantity,
            inventory_account_id=old_product.inventory_account_id,
            expense_account_id=old_product.expense_account_id,
            category_id=item_category_id,
            uom_id=old_product.uom_id,
            is_active=old_product.is_active,
            legacy_product_id=old_product.id,
        )
        product_mapping[old_product.id] = item.id
        items_created += 1

        # Create sales.Product if:
        # 1. Has selling_price > 0, OR
        # 2. Is used in sales orders
        should_create_sales_product = (
            old_product.selling_price > 0 or
            old_product.id in products_in_sales
        )

        if should_create_sales_product:
            sales_category_id = sales_category_mapping.get(old_product.category_id)

            sales_product = SalesProduct.objects.create(
                company=old_product.company,
                created_by=old_product.created_by,
                created_at=old_product.created_at,
                updated_at=old_product.updated_at,
                code=old_product.code,
                name=old_product.name,
                description=old_product.description,
                product_type='GOODS' if old_product.product_type != 'SERVICE' else 'SERVICE',
                linked_item=item,  # Link to the Item we just created
                selling_price=old_product.selling_price,
                mrp=old_product.selling_price,  # Use selling_price as MRP if no MRP field exists
                cost_price=old_product.cost_price,
                allow_discount=True,
                max_discount_percent=Decimal('0'),
                sales_account_id=old_product.income_account_id,
                revenue_account_id=old_product.income_account_id,
                category_id=sales_category_id,
                uom_id=old_product.uom_id,
                is_active=old_product.is_active,
                is_published=False,
                display_order=0,
                legacy_product_id=old_product.id,
            )
            sales_product_mapping[old_product.id] = sales_product.id
            sales_products_created += 1
            print(f"  ✓ {old_product.code}: Item + SalesProduct created")
        else:
            print(f"  ✓ {old_product.code}: Item only (not saleable)")

    print(f"\n{'='*60}")
    print(f"MIGRATION SUMMARY")
    print(f"{'='*60}")
    print(f"Items created: {items_created}")
    print(f"Sales Products created: {sales_products_created}")
    print(f"Total: {items_created} items, {sales_products_created} saleable products")
    print(f"\nNext step: Update ForeignKey references in other models")
    print(f"{'='*60}\n")


def reverse_migration(apps, schema_editor):
    """
    Reverse migration: Delete all Item and sales.Product records
    WARNING: This will lose the split. Only use if no transactions have been created.
    """
    Item = apps.get_model('inventory', 'Item')
    SalesProduct = apps.get_model('sales', 'Product')
    ItemCategory = apps.get_model('inventory', 'ItemCategory')
    SalesProductCategory = apps.get_model('sales', 'ProductCategory')

    print("\nReversing Product-to-Item migration...")
    print(f"Deleting {SalesProduct.objects.count()} sales products...")
    SalesProduct.objects.all().delete()

    print(f"Deleting {Item.objects.count()} items...")
    Item.objects.all().delete()

    # Only delete ItemCategories that were created during migration
    print(f"Deleting migrated item categories...")
    ItemCategory.objects.filter(created_at__isnull=False).delete()

    print(f"Deleting migrated sales product categories...")
    SalesProductCategory.objects.filter(created_at__isnull=False).delete()

    print("Reverse migration complete.")


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '10001_item_itemcategory_alter_productcategory_options_and_more'),
        ('sales', '0005_taxcategory_productcategory_product_and_more'),
    ]

    operations = [
        migrations.RunPython(
            migrate_products_to_items_and_sales_products,
            reverse_migration
        ),
    ]
