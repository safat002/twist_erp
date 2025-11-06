# Continue Implementation Guide
**Product-to-Item Refactoring & Financial Statements**

**Created**: November 5, 2025
**Status**: Phase 1 Partially Complete

---

## ✅ COMPLETED IN THIS SESSION

### Models Created
1. ✅ **`backend/apps/inventory/models/item.py`** - Item model with all fields
2. ✅ **`backend/apps/inventory/models/item.py`** - ItemCategory with hierarchy support
3. ✅ **`backend/apps/sales/models/product.py`** - Product model for saleable items
4. ✅ **`backend/apps/sales/models/product.py`** - ProductCategory with hierarchy
5. ✅ **`backend/apps/sales/models/product.py`** - TaxCategory model

### Documentation Created
1. ✅ `PRODUCT_TO_ITEM_REFACTORING_PLAN.md` - Detailed 50-page implementation plan
2. ✅ `IMPLEMENTATION_SUMMARY.md` - Quick reference guide
3. ✅ `ENHANCED_IMPLEMENTATION_PLAN.md` - Enhanced plan with all features
4. ✅ `CONTINUE_IMPLEMENTATION_GUIDE.md` - This document

---

## 🔄 REMAINING WORK

### Phase 1 Remaining (Critical Foundation)
- [ ] Update `backend/apps/inventory/models/__init__.py` to import new models
- [ ] Update `backend/apps/sales/models/__init__.py` to import new models
- [ ] Add multi-currency fields to Account model
- [ ] Create Currency and ExchangeRate models
- [ ] Add industry_category field to Company model
- [ ] Update BudgetLine model to support Product and Item with sub-categories

### Phase 2 (Industry Defaults) - 15 JSON files to create
- [ ] Create fixtures for all 15 industries
- [ ] Implement DefaultDataService
- [ ] Add company creation signal

### Phase 3 (Financial Statements) - 3 major services
- [ ] FinancialStatementService (3 statement types)
- [ ] FinancialStatementExportService (Excel, PDF)
- [ ] FinancialStatementViewSet API

### Phase 4 (Data Migration) - Critical!
- [ ] Create migration to split Product → Item + Product
- [ ] Update all ForeignKey references
- [ ] Migrate existing data

### Phase 5 (Testing & Deployment)
- [ ] Run all migrations
- [ ] Test thoroughly
- [ ] Deploy

---

## 📝 STEP-BY-STEP CONTINUATION INSTRUCTIONS

### STEP 1: Update Model __init__ Files

**File**: `backend/apps/inventory/models/__init__.py`

Add these imports:
```python
from .item import Item, ItemCategory

# Keep existing imports, add:
__all__ = [
    'Item',
    'ItemCategory',
    # ... existing exports
]
```

**File**: `backend/apps/sales/models/__init__.py`

Replace entire file:
```python
from .customer import Customer
from .sales_order import SalesOrder, SalesOrderLine
from .product import Product, ProductCategory, TaxCategory

__all__ = [
    'Customer',
    'SalesOrder',
    'SalesOrderLine',
    'Product',
    'ProductCategory',
    'TaxCategory',
]
```

### STEP 2: Add Multi-Currency to Account Model

**File**: `backend/apps/finance/models.py`

Find the `Account` model and add these fields BEFORE `class Meta`:

```python
    # NEW: Multi-currency fields
    currency = models.CharField(
        max_length=3,
        default='BDT',
        help_text="Primary currency for this account"
    )

    is_multi_currency = models.BooleanField(
        default=False,
        help_text="If True, can have transactions in multiple currencies"
    )

    # Currency-specific balances (JSON)
    currency_balances = models.JSONField(
        default=dict,
        blank=True,
        help_text="Balances by currency: {'USD': 1000.00, 'EUR': 500.00}"
    )

    # NEW: Default template flag
    is_default_template = models.BooleanField(
        default=False,
        help_text="System default account that can be customized"
    )
```

###  STEP 3: Create Currency Models

**File**: `backend/apps/finance/models/currency.py` (CREATE NEW)

```python
"""
Currency and Exchange Rate models for multi-currency support
"""
from decimal import Decimal
from django.conf import settings
from django.db import models


class Currency(models.Model):
    """Currency master data with ISO codes"""
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        help_text="Company this record belongs to"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    code = models.CharField(
        max_length=3,
        help_text="ISO 4217 currency code: USD, EUR, BDT, etc."
    )
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    decimal_places = models.IntegerField(
        default=2,
        help_text="Number of decimal places for this currency"
    )

    is_active = models.BooleanField(default=True)
    is_base_currency = models.BooleanField(
        default=False,
        help_text="Is this the base currency for this company?"
    )

    class Meta:
        db_table = 'finance_currency'
        unique_together = ('company', 'code')
        verbose_name_plural = 'Currencies'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class ExchangeRate(models.Model):
    """Exchange rates between currencies with date effectivity"""
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        help_text="Company this record belongs to"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    from_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='rates_from',
        help_text="Source currency"
    )
    to_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='rates_to',
        help_text="Target currency"
    )

    rate = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        help_text="Exchange rate (1 from_currency = rate * to_currency)"
    )

    effective_date = models.DateField(
        db_index=True,
        help_text="Date from which this rate is effective"
    )

    # Optional validity period
    valid_until = models.DateField(
        null=True,
        blank=True,
        help_text="Last date this rate is valid (null = indefinite)"
    )

    class Meta:
        db_table = 'finance_exchange_rate'
        unique_together = ('company', 'from_currency', 'to_currency', 'effective_date')
        ordering = ['-effective_date']
        indexes = [
            models.Index(fields=['company', 'from_currency', 'to_currency', '-effective_date']),
        ]

    def __str__(self):
        return f"{self.from_currency.code} → {self.to_currency.code}: {self.rate} ({self.effective_date})"

    @classmethod
    def get_rate(cls, company, from_currency, to_currency, as_of_date):
        """
        Get exchange rate for a specific date

        Args:
            company: Company instance
            from_currency: Currency code (string) or Currency instance
            to_currency: Currency code (string) or Currency instance
            as_of_date: Date to get rate for

        Returns:
            Decimal: Exchange rate, or None if not found
        """
        from datetime import date

        if isinstance(from_currency, str):
            from_currency = Currency.objects.get(company=company, code=from_currency)
        if isinstance(to_currency, str):
            to_currency = Currency.objects.get(company=company, code=to_currency)

        # Same currency = 1.0
        if from_currency.code == to_currency.code:
            return Decimal('1.0')

        # Find rate effective on or before as_of_date
        rate_obj = cls.objects.filter(
            company=company,
            from_currency=from_currency,
            to_currency=to_currency,
            effective_date__lte=as_of_date
        ).order_by('-effective_date').first()

        if rate_obj:
            # Check if still valid
            if rate_obj.valid_until and rate_obj.valid_until < as_of_date:
                return None
            return rate_obj.rate

        return None


class CurrencyConversionService:
    """Service for currency conversion"""

    @staticmethod
    def convert(amount, from_currency, to_currency, company, as_of_date=None):
        """
        Convert amount from one currency to another

        Args:
            amount: Decimal amount to convert
            from_currency: Source currency code or instance
            to_currency: Target currency code or instance
            company: Company instance
            as_of_date: Date for exchange rate (defaults to today)

        Returns:
            Decimal: Converted amount

        Raises:
            ValueError: If exchange rate not found
        """
        from datetime import date

        if as_of_date is None:
            as_of_date = date.today()

        # Get rate
        rate = ExchangeRate.get_rate(company, from_currency, to_currency, as_of_date)

        if rate is None:
            from_code = from_currency.code if hasattr(from_currency, 'code') else from_currency
            to_code = to_currency.code if hasattr(to_currency, 'code') else to_currency
            raise ValueError(
                f"No exchange rate found for {from_code} → {to_code} "
                f"as of {as_of_date}"
            )

        return amount * rate
```

Now update `backend/apps/finance/models/__init__.py`:

```python
from .currency import Currency, ExchangeRate, CurrencyConversionService

# Add to __all__:
__all__ = [
    # ... existing ...
    'Currency',
    'ExchangeRate',
    'CurrencyConversionService',
]
```

### STEP 4: Add Industry Category to Company

**File**: `backend/apps/companies/models.py`

Find the `Company` model and add these fields:

```python
class CompanyCategory(models.TextChoices):
    MANUFACTURING = 'MANUFACTURING', 'Manufacturing'
    TRADING = 'TRADING', 'Trading/Wholesale'
    RETAIL = 'RETAIL', 'Retail'
    SERVICE = 'SERVICE', 'Service Provider'
    CONSTRUCTION = 'CONSTRUCTION', 'Construction'
    HEALTHCARE = 'HEALTHCARE', 'Healthcare'
    EDUCATION = 'EDUCATION', 'Education'
    NGO = 'NGO', 'Non-Profit/NGO'
    AGRICULTURE = 'AGRICULTURE', 'Agriculture'
    TECHNOLOGY = 'TECHNOLOGY', 'Technology/Software'
    HOSPITALITY = 'HOSPITALITY', 'Hospitality'
    TRANSPORT = 'TRANSPORT', 'Transportation/Logistics'
    REAL_ESTATE = 'REAL_ESTATE', 'Real Estate'
    FINANCIAL = 'FINANCIAL', 'Financial Services'
    OTHER = 'OTHER', 'Other'

class Company(models.Model):
    # ... existing fields ...

    # NEW: Industry category (add after existing fields)
    industry_category = models.CharField(
        max_length=50,
        choices=CompanyCategory.choices,
        default=CompanyCategory.OTHER,
        help_text="Company industry category - determines default master data"
    )

    # NEW: Currency settings
    base_currency = models.CharField(
        max_length=3,
        default='BDT',
        help_text="Base currency for this company"
    )

    secondary_currencies = models.JSONField(
        default=list,
        blank=True,
        help_text="List of additional currencies used: ['USD', 'EUR', 'GBP']"
    )

    enable_multi_currency = models.BooleanField(
        default=False,
        help_text="Enable multi-currency transactions"
    )
```

### STEP 5: Update BudgetLine Model to Support Product and Item

**File**: `backend/apps/budgeting/models.py`

Find `BudgetLine` model and modify:

```python
class BudgetLine(models.Model):
    # ... existing fields ...

    # CHANGE: Split product field into two
    # REMOVE: product = models.ForeignKey('inventory.Product', ...)

    # ADD: Separate fields for product vs item
    product = models.ForeignKey(
        'sales.Product',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='budget_lines',
        help_text="For revenue budgets only"
    )

    item = models.ForeignKey(
        'inventory.Item',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='budget_lines',
        help_text="For expense/capex/production budgets"
    )

    # ADD: Sub-category support (hierarchical)
    sub_category = models.ForeignKey(
        'ItemCategory',  # or BudgetSubCategory if you want separate model
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Sub-category for budget classification"
    )

    # ... rest of fields ...

    def clean(self):
        """Validation: Either product OR item must be set, not both"""
        from django.core.exceptions import ValidationError

        if self.product and self.item:
            raise ValidationError("Cannot specify both product and item. Choose one.")

        if not self.product and not self.item:
            raise ValidationError("Must specify either product (for revenue) or item (for expenses).")

        # Validate sub-category belongs to item's category
        if self.item and self.sub_category:
            if self.sub_category.parent_category != self.item.category:
                raise ValidationError("Sub-category must belong to item's category")
```

###  STEP 6: Create Migrations

Run these commands in sequence:

```bash
# 1. Create migrations for new models
python manage.py makemigrations inventory --name create_item_and_category_models
python manage.py makemigrations sales --name create_product_models
python manage.py makemigrations finance --name add_currency_models
python manage.py makemigrations companies --name add_industry_category
python manage.py makemigrations budgeting --name update_budget_line_for_product_item

# 2. Review migration files before applying
# Check: backend/apps/inventory/migrations/*_create_item_and_category_models.py
# Check: backend/apps/sales/migrations/*_create_product_models.py

# 3. DO NOT APPLY YET - Need data migration first
```

### STEP 7: Create Data Migration Script

**File**: Create `backend/apps/inventory/migrations/XXXX_migrate_product_to_item.py`

This is CRITICAL - it splits existing Product data into Item and sales.Product:

```python
"""
Data migration to split Product → Item + sales.Product
"""
from django.db import migrations
from decimal import Decimal


def migrate_products_to_items_and_sales_products(apps, schema_editor):
    """
    Split existing inventory.Product records into:
    1. inventory.Item (all products become items)
    2. sales.Product (products with selling_price > 0 or used in sales)
    """
    # Get models
    OldProduct = apps.get_model('inventory', 'Product')
    Item = apps.get_model('inventory', 'Item')
    SalesProduct = apps.get_model('sales', 'Product')
    ItemCategory = apps.get_model('inventory', 'ItemCategory')
    ProductCategory = apps.get_model('sales', 'ProductCategory')
    SalesOrderLine = apps.get_model('sales', 'SalesOrderLine')

    print("\\n=== Starting Product Migration ===")

    # Track old product category → new item/product categories
    item_category_map = {}
    product_category_map = {}

    # Step 1: Migrate ProductCategory to ItemCategory and sales.ProductCategory
    OldProductCategory = apps.get_model('inventory', 'ProductCategory')

    for old_cat in OldProductCategory.objects.all():
        # Create ItemCategory
        item_cat = ItemCategory.objects.create(
            company=old_cat.company,
            code=old_cat.code,
            name=old_cat.name,
            parent_category=item_category_map.get(old_cat.parent_category_id),
            is_active=old_cat.is_active,
            is_default_template=False,
        )
        item_category_map[old_cat.id] = item_cat

        # Create ProductCategory (sales)
        prod_cat = ProductCategory.objects.create(
            company=old_cat.company,
            code=old_cat.code,
            name=old_cat.name,
            parent_category=product_category_map.get(old_cat.parent_category_id),
            is_active=old_cat.is_active,
            is_default_template=False,
        )
        product_category_map[old_cat.id] = prod_cat

    print(f"Migrated {len(item_category_map)} categories")

    # Step 2: Find products used in sales
    products_in_sales = set(
        SalesOrderLine.objects.values_list('product_id', flat=True).distinct()
    )

    print(f"Found {len(products_in_sales)} products used in sales")

    # Step 3: Migrate all products
    item_map = {}  # old_product_id → new_item
    product_map = {}  # old_product_id → new_sales_product

    for old_product in OldProduct.objects.all():
        # Always create Item
        item = Item.objects.create(
            company=old_product.company,
            code=old_product.code,
            name=old_product.name,
            description=old_product.description,
            item_type='RAW_MATERIAL',  # Default, adjust manually later
            is_tradable=(old_product.id in products_in_sales),
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
            inventory_account=old_product.inventory_account,
            expense_account=old_product.expense_account,
            category=item_category_map[old_product.category_id],
            uom=old_product.uom,
            is_active=old_product.is_active,
            legacy_product_id=old_product.id,
        )
        item_map[old_product.id] = item

        # Create sales.Product if used in sales or has selling price
        if old_product.id in products_in_sales or old_product.selling_price > 0:
            sales_product = SalesProduct.objects.create(
                company=old_product.company,
                code=old_product.code,
                name=old_product.name,
                description=old_product.description,
                product_type='GOODS' if old_product.product_type == 'GOODS' else 'SERVICE',
                linked_item=item,
                selling_price=old_product.selling_price,
                cost_price=old_product.cost_price,
                sales_account=old_product.income_account,
                revenue_account=old_product.income_account,
                category=product_category_map[old_product.category_id],
                uom=old_product.uom,
                is_active=old_product.is_active,
                is_published=False,
                legacy_product_id=old_product.id,
            )
            product_map[old_product.id] = sales_product

    print(f"Created {len(item_map)} items")
    print(f"Created {len(product_map)} sales products")

    # Step 4: Update ForeignKey references
    print("\\nUpdating ForeignKey references...")

    # Update StockMovementLine
    StockMovementLine = apps.get_model('inventory', 'StockMovementLine')
    for line in StockMovementLine.objects.all():
        line.item = item_map.get(line.product_id)
        line.save(update_fields=['item'])

    # Update StockLevel
    StockLevel = apps.get_model('inventory', 'StockLevel')
    for level in StockLevel.objects.all():
        level.item = item_map.get(level.product_id)
        level.save(update_fields=['item'])

    # Update CostLayer
    CostLayer = apps.get_model('inventory', 'CostLayer')
    for layer in CostLayer.objects.all():
        layer.item = item_map.get(layer.product_id)
        layer.save(update_fields=['item'])

    # Update GoodsReceiptLine
    GoodsReceiptLine = apps.get_model('inventory', 'GoodsReceiptLine')
    for line in GoodsReceiptLine.objects.all():
        line.item = item_map.get(line.product_id)
        line.save(update_fields=['item'])

    # Update DeliveryOrderLine - uses sales.Product
    DeliveryOrderLine = apps.get_model('inventory', 'DeliveryOrderLine')
    for line in DeliveryOrderLine.objects.all():
        line.product = product_map.get(line.product_id)
        line.save(update_fields=['product'])

    # Update SalesOrderLine - uses sales.Product
    for line in SalesOrderLine.objects.all():
        line.product = product_map.get(line.product_id)
        line.save(update_fields=['product'])

    # Update PurchaseOrderLine - uses Item
    PurchaseOrderLine = apps.get_model('procurement', 'PurchaseOrderLine')
    for line in PurchaseOrderLine.objects.all():
        line.item = item_map.get(line.product_id)
        line.save(update_fields=['item'])

    # Update BudgetLine - split into product/item
    BudgetLine = apps.get_model('budgeting', 'BudgetLine')
    for line in BudgetLine.objects.all():
        old_product_id = line.product_id
        if old_product_id in product_map:
            # Has sales product - use it for revenue budgets
            line.product = product_map[old_product_id]
            line.item = None
        else:
            # No sales product - use item for expense budgets
            line.product = None
            line.item = item_map.get(old_product_id)
        line.save(update_fields=['product', 'item'])

    print("\\n=== Migration Complete ===\\n")


def reverse_migration(apps, schema_editor):
    """Reverse is complex - recommend database restore instead"""
    print("WARNING: Reverse migration not implemented. Restore from backup if needed.")
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('inventory', 'XXXX_create_item_and_category_models'),  # Update with actual migration
        ('sales', 'XXXX_create_product_models'),  # Update with actual migration
        ('budgeting', 'XXXX_update_budget_line_for_product_item'),  # Update with actual migration
    ]

    operations = [
        migrations.RunPython(
            migrate_products_to_items_and_sales_products,
            reverse_code=reverse_migration
        ),
    ]
```

### STEP 8: Update All Model ForeignKeys

After data migration, need to update model definitions to reference Item instead of Product:

**Files to Update** (search for `ForeignKey('Product'` or `ForeignKey(Product`):

1. `backend/apps/inventory/models.py`:
```python
# Change:
product = models.ForeignKey(Product, ...)

# To:
item = models.ForeignKey(Item, ...)
```

Update these models in `inventory/models.py`:
- StockMovementLine
- StockLevel
- StockLedger
- GoodsReceiptLine
- ItemValuationMethod
- CostLayer
- ValuationMethodChange

2. `backend/apps/procurement/models.py`:
```python
# PurchaseOrderLine
item = models.ForeignKey('inventory.Item', on_delete=models.PROTECT)
```

3. `backend/apps/production/models.py`:
```python
# BOM
item = models.ForeignKey('inventory.Item', on_delete=models.PROTECT, related_name='boms')

# BOMLine
component = models.ForeignKey('inventory.Item', on_delete=models.PROTECT, related_name='bom_components')

# WorkOrder
item = models.ForeignKey('inventory.Item', on_delete=models.PROTECT, related_name='work_orders')
```

4. `backend/apps/sales/models/sales_order.py`:
```python
# SalesOrderLine
product = models.ForeignKey('sales.Product', on_delete=models.PROTECT, related_name='sales_order_lines')
```

### STEP 9: Apply Migrations

```bash
# 1. Backup database first!
pg_dump twist_erp > backup_before_migration_$(date +%Y%m%d).sql

# 2. Apply migrations
python manage.py migrate inventory
python manage.py migrate sales
python manage.py migrate finance
python manage.py migrate companies
python manage.py migrate budgeting
python manage.py migrate procurement
python manage.py migrate production

# 3. Verify data
python manage.py shell
>>> from apps.inventory.models import Item
>>> from apps.sales.models import Product
>>> Item.objects.count()
>>> Product.objects.count()
```

---

## 🏗️ PHASE 2: Industry-Specific Defaults

This is in `ENHANCED_IMPLEMENTATION_PLAN.md` starting at line 200.

Key files to create (15 JSON files):
1. `backend/apps/metadata/fixtures/defaults/manufacturing/chart_of_accounts.json`
2. `backend/apps/metadata/fixtures/defaults/trading/chart_of_accounts.json`
3. ... and 13 more

Plus:
- `backend/apps/metadata/services/default_data_service.py`
- Signal in `backend/apps/companies/signals.py`

---

## 📊 PHASE 3: Financial Statements

Full implementation in `ENHANCED_IMPLEMENTATION_PLAN.md` starting at line 800.

Key files:
1. `backend/apps/finance/services/financial_statement_service.py` (~600 lines)
2. `backend/apps/finance/services/financial_statement_export_service.py` (~400 lines)
3. `backend/apps/finance/views/financial_statement_views.py` (~300 lines)

---

## ⚠️ CRITICAL NOTES

1. **Database Backup**: MUST backup before applying migrations
2. **Test in Staging**: Run on staging environment first
3. **Rollback Plan**: Keep backup for rollback if issues occur
4. **Data Validation**: After migration, verify:
   - All items created correctly
   - Sales products linked to items
   - No orphaned records
   - ForeignKey integrity maintained

---

## 📈 Progress Tracking

### Phase 1: Foundation (2 days)
- [x] Create Item model
- [x] Create ItemCategory with hierarchy
- [x] Create Product model (sales)
- [x] Create ProductCategory with hierarchy
- [x] Create TaxCategory model
- [ ] Add multi-currency to Account
- [ ] Create Currency/ExchangeRate models
- [ ] Add industry_category to Company
- [ ] Update BudgetLine model
- [ ] Create and apply migrations
- [ ] Create data migration script
- [ ] Update all ForeignKey references

### Phase 2: Industry Defaults (3 days)
- [ ] Create 15 industry-specific fixture files
- [ ] Implement DefaultDataService
- [ ] Add company creation signal
- [ ] Test default data population

### Phase 3: Financial Statements (5 days)
- [ ] Implement FinancialStatementService
- [ ] Implement export services
- [ ] Create API views
- [ ] Test statement generation

### Phase 4: Testing & Deployment (2 days)
- [ ] Unit tests
- [ ] Integration tests
- [ ] Staging deployment
- [ ] Production deployment

---

## 🚀 QUICK START FOR NEXT SESSION

**To continue implementation**:

1. Complete STEP 2-9 above (Multi-currency, Currency models, Industry category, BudgetLine, Migrations)
2. Then move to Phase 2 (Industry Defaults) using `ENHANCED_IMPLEMENTATION_PLAN.md`
3. Then Phase 3 (Financial Statements) using `ENHANCED_IMPLEMENTATION_PLAN.md`

**Estimated time remaining**: 15-20 days

---

## 📞 Support

If you encounter issues:
1. Check `ENHANCED_IMPLEMENTATION_PLAN.md` for detailed code examples
2. Check migration file dependencies
3. Verify all model imports are correct
4. Test incrementally after each step

**Last Updated**: November 5, 2025
**Status**: Phase 1 Partially Complete (20% overall)
