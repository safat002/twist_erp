# Product to Item Refactoring & Default Master Data Implementation Plan

**Date**: November 5, 2025
**Version**: 1.0
**Status**: Awaiting Approval

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Part 1: Product vs Item Separation](#part-1-product-vs-item-separation)
3. [Part 2: Default Master Data](#part-2-default-master-data)
4. [Implementation Steps](#implementation-steps)
5. [Database Migration Strategy](#database-migration-strategy)
6. [Testing Strategy](#testing-strategy)
7. [Rollback Plan](#rollback-plan)

---

## Overview

### Current State
- **Product model** in `inventory` app is used for EVERYTHING (raw materials, finished goods, services, consumables, fixed assets, etc.)
- No default master data - each company starts from scratch
- Manual setup required for Chart of Accounts, Item Categories, Departments, Cost Centers

### Target State
- **Product model** moves to `sales/crm` module - ONLY for saleable/trading items
- **Item model** in `inventory` app - for raw materials, consumables, components, fixed assets, etc.
- Default master data templates pre-populated for new companies
- Admin can customize/delete defaults via admin module

### Benefits
1. **Clear Separation of Concerns**: Sales products vs operational items
2. **Better Pricing Control**: Sales products have customer pricing, items have cost tracking
3. **Simplified Onboarding**: New companies get industry-standard defaults
4. **Compliance Ready**: Pre-configured chart of accounts follows accounting standards

---

## Part 1: Product vs Item Separation

### 1.1 New Data Model Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    SALES/CRM MODULE                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Product (Saleable Items)                           │   │
│  │  - code, name, description                          │   │
│  │  - selling_price, mrp, discount_rules               │   │
│  │  - customer_pricing_matrix                          │   │
│  │  - sales_account, revenue_account                   │   │
│  │  - product_type: ['GOODS', 'SERVICE']               │   │
│  │  - is_tradable: True (always)                       │   │
│  │  - linked_item (FK to inventory.Item) - optional    │   │
│  │  - tax_category, hsn_code                           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ optional link
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   INVENTORY MODULE                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Item (Non-Saleable Items)                          │   │
│  │  - code, name, description                          │   │
│  │  - cost_price, standard_cost                        │   │
│  │  - item_type: ['RAW_MATERIAL', 'CONSUMABLE',        │   │
│  │                'COMPONENT', 'FIXED_ASSET',          │   │
│  │                'SERVICE', 'SEMI_FINISHED']          │   │
│  │  - is_tradable: False (default)                     │   │
│  │  - track_inventory, track_serial, track_batch       │   │
│  │  - valuation_method (FIFO/LIFO/WAV/STD)            │   │
│  │  - inventory_account, expense_account               │   │
│  │  - reorder_level, reorder_quantity                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Key Differences: Product vs Item

| Aspect | Product (Sales) | Item (Inventory) |
|--------|----------------|------------------|
| **Purpose** | Sell to customers | Use in operations |
| **Pricing** | Selling price, MRP, discounts | Cost price, standard cost |
| **Module** | Sales/CRM | Inventory |
| **Can Sell?** | Yes (always) | No (unless linked to Product) |
| **Can Purchase?** | Depends on linked_item | Yes |
| **Stock Tracking** | Via linked_item | Yes (direct) |
| **Valuation** | N/A | FIFO/LIFO/WAV/STD |
| **Used In** | Sales Orders, Quotations, Invoices | Purchase Orders, Production, Stock Movements |
| **Accounts** | Sales, Revenue | Inventory, Expense, COGS |

### 1.3 Migration Strategy

#### Option A: Big Bang Migration (Recommended)
**Approach**: Create new structure, migrate all data in one go

**Steps**:
1. Create `Item` model in `inventory` app
2. Create new `Product` model in `sales` app
3. Migration script to split existing `Product` records:
   - Records with `selling_price > 0` or used in sales orders → `sales.Product`
   - All records → `inventory.Item` (for backward compatibility)
   - Create links between them
4. Update all ForeignKey references
5. Run comprehensive tests
6. Deploy with maintenance window

**Pros**:
- Clean break, clear separation
- No intermediate state
- Easier to reason about

**Cons**:
- Requires downtime (1-2 hours)
- Higher risk if issues found

**Estimated Effort**: 5-7 days

---

#### Option B: Gradual Migration (Safer)
**Approach**: Introduce Item model, keep Product, gradually migrate

**Steps**:
1. Create `Item` model in `inventory` app
2. Add `legacy_product` FK to Item (pointing to old Product)
3. Add `migrated_to_item` FK to Product (pointing to new Item)
4. Create sync mechanism (signals/services)
5. Gradually move modules to use Item instead of Product
6. After all modules migrated, create sales.Product
7. Final cleanup and remove old Product

**Pros**:
- Zero downtime
- Can rollback easily
- Incremental testing

**Cons**:
- Complex intermediate state
- Takes longer (2-3 weeks)
- Two sources of truth temporarily

**Estimated Effort**: 10-12 days

---

### 1.4 Affected Modules & Code Changes

#### Files Requiring Updates:

##### **1. Core Models**

**NEW FILE: `backend/apps/inventory/models/item.py`**
```python
class Item(models.Model):
    """
    Items are non-saleable inventory components used in operations:
    - Raw materials
    - Consumables
    - Components
    - Fixed assets
    - Semi-finished goods
    """
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    item_type = models.CharField(max_length=20, choices=[
        ('RAW_MATERIAL', 'Raw Material'),
        ('CONSUMABLE', 'Consumable'),
        ('COMPONENT', 'Component'),
        ('FIXED_ASSET', 'Fixed Asset'),
        ('SERVICE', 'Service'),
        ('SEMI_FINISHED', 'Semi-Finished Good'),
        ('PACKING_MATERIAL', 'Packing Material'),
    ], default='RAW_MATERIAL')

    is_tradable = models.BooleanField(default=False,
        help_text="If True, can be linked to a saleable Product")

    # Inventory tracking
    track_inventory = models.BooleanField(default=True)
    track_serial = models.BooleanField(default=False)
    track_batch = models.BooleanField(default=False)
    prevent_expired_issuance = models.BooleanField(default=True)
    expiry_warning_days = models.PositiveIntegerField(default=0)

    # Costing
    cost_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    standard_cost = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    valuation_method = models.CharField(max_length=20, choices=[
        ('FIFO', 'First In, First Out'),
        ('LIFO', 'Last In, First Out'),
        ('WEIGHTED_AVG', 'Weighted Average'),
        ('STANDARD_COST', 'Standard Cost'),
    ], default='FIFO')

    # Reordering
    reorder_level = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    reorder_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    lead_time_days = models.IntegerField(default=0)

    # Accounting
    inventory_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT,
        related_name='inventory_items', null=True, blank=True)
    expense_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT,
        related_name='expense_items', null=True, blank=True)

    # Master data
    category = models.ForeignKey('ItemCategory', on_delete=models.PROTECT)
    uom = models.ForeignKey('UnitOfMeasure', on_delete=models.PROTECT)

    # Status
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('company', 'code')
        indexes = [
            models.Index(fields=['company', 'category']),
            models.Index(fields=['company', 'item_type']),
            models.Index(fields=['company', 'is_active']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"
```

**NEW FILE: `backend/apps/sales/models/product.py`**
```python
class Product(models.Model):
    """
    Products are saleable items sold to customers.
    Can optionally link to an Item for inventory tracking.
    """
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    product_type = models.CharField(max_length=20, choices=[
        ('GOODS', 'Goods'),
        ('SERVICE', 'Service'),
    ], default='GOODS')

    # Link to inventory (optional)
    linked_item = models.ForeignKey('inventory.Item', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='products',
        help_text="Link to inventory item if this product needs stock tracking")

    # Pricing
    selling_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    mrp = models.DecimalField(max_digits=20, decimal_places=2, default=0,
        help_text="Maximum Retail Price")
    cost_price = models.DecimalField(max_digits=20, decimal_places=2, default=0,
        help_text="Reference cost for margin calculation")

    # Taxation
    tax_category = models.ForeignKey('sales.TaxCategory', on_delete=models.PROTECT,
        null=True, blank=True)
    hsn_code = models.CharField(max_length=20, blank=True,
        help_text="Harmonized System Nomenclature")

    # Accounting
    sales_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT,
        related_name='sales_products')
    revenue_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT,
        related_name='revenue_products', null=True, blank=True)

    # Master data
    category = models.ForeignKey('ProductCategory', on_delete=models.PROTECT)
    uom = models.ForeignKey('inventory.UnitOfMeasure', on_delete=models.PROTECT)

    # Status
    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False,
        help_text="Visible in customer portal/e-commerce")

    class Meta:
        unique_together = ('company', 'code')
        indexes = [
            models.Index(fields=['company', 'category']),
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['company', 'is_published']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def available_quantity(self):
        """Get available stock from linked item"""
        if self.linked_item:
            return self.linked_item.get_available_stock()
        return 0
```

##### **2. Rename ProductCategory → ItemCategory**

**File: `backend/apps/inventory/models.py`**
```python
# RENAME: ProductCategory → ItemCategory
class ItemCategory(models.Model):
    """Categories for inventory items"""
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    parent_category = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True)

    # NEW: Default flag for templates
    is_default_template = models.BooleanField(default=False,
        help_text="System default category that can be customized")

    class Meta:
        unique_together = ('company', 'code')
        verbose_name_plural = 'Item Categories'
```

**NEW FILE: `backend/apps/sales/models/product_category.py`**
```python
class ProductCategory(models.Model):
    """Categories for saleable products"""
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    parent_category = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True)

    # Sales-specific fields
    display_order = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)

    is_default_template = models.BooleanField(default=False)

    class Meta:
        unique_together = ('company', 'code')
        verbose_name_plural = 'Product Categories'
```

##### **3. Update All ForeignKey References**

**Modules with Product ForeignKey** (need updates):
1. ✅ `apps.budgeting.models` - BudgetLine.product → item
2. ✅ `apps.inventory.models` - StockMovementLine.product → item
3. ✅ `apps.inventory.models` - StockLevel.product → item
4. ✅ `apps.inventory.models` - CostLayer.product → item
5. ✅ `apps.production.models` - BOM.product → item (finished good)
6. ✅ `apps.production.models` - BOMLine.component → item
7. ✅ `apps.production.models` - WorkOrder.product → item
8. ✅ `apps.procurement.models` - PurchaseOrderLine.product → item
9. ✅ `apps.sales.models` - SalesOrderLine.product → product (stays as is!)
10. ✅ `apps.finance.models` - (Keep ItemCategory FK reference)

##### **4. Update Views, Serializers, Services**

**Files to Update** (16 files):
- `apps/inventory/views.py` - Update to use Item model
- `apps/inventory/serializers.py` - ItemSerializer
- `apps/inventory/services/*.py` - Update all product references
- `apps/sales/views/*.py` - Use new Product model
- `apps/sales/serializers/*.py` - ProductSerializer
- `apps/production/views.py` - Use Item for BOM
- `apps/procurement/views.py` - Use Item for PO
- `apps/budgeting/views.py` - Use Item for budgets
- All service files referencing Product

##### **5. Frontend Updates**

**React Components** (estimated 15-20 files):
- `frontend/src/pages/Inventory/Products.jsx` → `Items.jsx`
- `frontend/src/pages/Sales/Products.jsx` - NEW
- `frontend/src/components/ProductSelector.jsx` → `ItemSelector.jsx`
- `frontend/src/components/ProductForm.jsx` → `ItemForm.jsx`
- All imports and references

---

## Part 2: Default Master Data

### 2.1 Master Data to Provide Defaults

#### A. Chart of Accounts
**File**: `backend/apps/finance/fixtures/default_chart_of_accounts.json`

Standard 5-level Chart of Accounts:
```json
{
  "accounts": [
    // ASSETS
    {"code": "1000", "name": "ASSETS", "type": "ASSET", "level": 0},
    {"code": "1100", "name": "Current Assets", "type": "ASSET", "level": 1, "parent": "1000"},
    {"code": "1110", "name": "Cash & Bank", "type": "ASSET", "level": 2, "parent": "1100"},
    {"code": "1111", "name": "Cash in Hand", "type": "ASSET", "level": 3, "parent": "1110"},
    {"code": "1112", "name": "Bank Account - Operations", "type": "ASSET", "level": 3, "parent": "1110"},
    {"code": "1120", "name": "Accounts Receivable", "type": "ASSET", "level": 2, "parent": "1100"},
    {"code": "1121", "name": "Trade Debtors", "type": "ASSET", "level": 3, "parent": "1120"},
    {"code": "1130", "name": "Inventory", "type": "ASSET", "level": 2, "parent": "1100"},
    {"code": "1131", "name": "Raw Materials", "type": "ASSET", "level": 3, "parent": "1130"},
    {"code": "1132", "name": "Work in Progress", "type": "ASSET", "level": 3, "parent": "1130"},
    {"code": "1133", "name": "Finished Goods", "type": "ASSET", "level": 3, "parent": "1130"},

    {"code": "1200", "name": "Fixed Assets", "type": "ASSET", "level": 1, "parent": "1000"},
    {"code": "1210", "name": "Property, Plant & Equipment", "type": "ASSET", "level": 2, "parent": "1200"},
    {"code": "1211", "name": "Land & Building", "type": "ASSET", "level": 3, "parent": "1210"},
    {"code": "1212", "name": "Machinery & Equipment", "type": "ASSET", "level": 3, "parent": "1210"},
    {"code": "1213", "name": "Vehicles", "type": "ASSET", "level": 3, "parent": "1210"},
    {"code": "1214", "name": "Furniture & Fixtures", "type": "ASSET", "level": 3, "parent": "1210"},
    {"code": "1220", "name": "Accumulated Depreciation", "type": "ASSET", "level": 2, "parent": "1200"},

    // LIABILITIES
    {"code": "2000", "name": "LIABILITIES", "type": "LIABILITY", "level": 0},
    {"code": "2100", "name": "Current Liabilities", "type": "LIABILITY", "level": 1, "parent": "2000"},
    {"code": "2110", "name": "Accounts Payable", "type": "LIABILITY", "level": 2, "parent": "2100"},
    {"code": "2111", "name": "Trade Creditors", "type": "LIABILITY", "level": 3, "parent": "2110"},
    {"code": "2120", "name": "Accrued Expenses", "type": "LIABILITY", "level": 2, "parent": "2100"},
    {"code": "2121", "name": "Salaries Payable", "type": "LIABILITY", "level": 3, "parent": "2120"},
    {"code": "2122", "name": "Tax Payable", "type": "LIABILITY", "level": 3, "parent": "2120"},

    {"code": "2200", "name": "Long-term Liabilities", "type": "LIABILITY", "level": 1, "parent": "2000"},
    {"code": "2210", "name": "Loans Payable", "type": "LIABILITY", "level": 2, "parent": "2200"},

    // EQUITY
    {"code": "3000", "name": "EQUITY", "type": "EQUITY", "level": 0},
    {"code": "3100", "name": "Owner's Equity", "type": "EQUITY", "level": 1, "parent": "3000"},
    {"code": "3110", "name": "Share Capital", "type": "EQUITY", "level": 2, "parent": "3100"},
    {"code": "3120", "name": "Retained Earnings", "type": "EQUITY", "level": 2, "parent": "3100"},

    // REVENUE
    {"code": "4000", "name": "REVENUE", "type": "REVENUE", "level": 0},
    {"code": "4100", "name": "Sales Revenue", "type": "REVENUE", "level": 1, "parent": "4000"},
    {"code": "4110", "name": "Product Sales", "type": "REVENUE", "level": 2, "parent": "4100"},
    {"code": "4120", "name": "Service Revenue", "type": "REVENUE", "level": 2, "parent": "4100"},
    {"code": "4200", "name": "Other Income", "type": "REVENUE", "level": 1, "parent": "4000"},

    // EXPENSES
    {"code": "5000", "name": "EXPENSES", "type": "EXPENSE", "level": 0},
    {"code": "5100", "name": "Cost of Goods Sold", "type": "EXPENSE", "level": 1, "parent": "5000"},
    {"code": "5110", "name": "Direct Materials", "type": "EXPENSE", "level": 2, "parent": "5100"},
    {"code": "5120", "name": "Direct Labor", "type": "EXPENSE", "level": 2, "parent": "5100"},
    {"code": "5130", "name": "Manufacturing Overhead", "type": "EXPENSE", "level": 2, "parent": "5100"},

    {"code": "5200", "name": "Operating Expenses", "type": "EXPENSE", "level": 1, "parent": "5000"},
    {"code": "5210", "name": "Selling Expenses", "type": "EXPENSE", "level": 2, "parent": "5200"},
    {"code": "5211", "name": "Sales Salaries", "type": "EXPENSE", "level": 3, "parent": "5210"},
    {"code": "5212", "name": "Marketing & Advertising", "type": "EXPENSE", "level": 3, "parent": "5210"},
    {"code": "5213", "name": "Freight & Delivery", "type": "EXPENSE", "level": 3, "parent": "5210"},

    {"code": "5220", "name": "Administrative Expenses", "type": "EXPENSE", "level": 2, "parent": "5200"},
    {"code": "5221", "name": "Office Salaries", "type": "EXPENSE", "level": 3, "parent": "5220"},
    {"code": "5222", "name": "Rent", "type": "EXPENSE", "level": 3, "parent": "5220"},
    {"code": "5223", "name": "Utilities", "type": "EXPENSE", "level": 3, "parent": "5220"},
    {"code": "5224", "name": "Office Supplies", "type": "EXPENSE", "level": 3, "parent": "5220"},
    {"code": "5225", "name": "Depreciation", "type": "EXPENSE", "level": 3, "parent": "5220"},
    {"code": "5226", "name": "Insurance", "type": "EXPENSE", "level": 3, "parent": "5220"}
  ]
}
```

#### B. Item Categories
**File**: `backend/apps/inventory/fixtures/default_item_categories.json`

```json
{
  "categories": [
    {"code": "RM", "name": "Raw Materials", "parent": null},
    {"code": "RM-MTL", "name": "Metals", "parent": "RM"},
    {"code": "RM-CHM", "name": "Chemicals", "parent": "RM"},
    {"code": "RM-TXT", "name": "Textiles", "parent": "RM"},

    {"code": "COMP", "name": "Components", "parent": null},
    {"code": "COMP-ELC", "name": "Electronics", "parent": "COMP"},
    {"code": "COMP-MCH", "name": "Mechanical", "parent": "COMP"},

    {"code": "CONS", "name": "Consumables", "parent": null},
    {"code": "CONS-OFF", "name": "Office Supplies", "parent": "CONS"},
    {"code": "CONS-CLN", "name": "Cleaning Supplies", "parent": "CONS"},
    {"code": "CONS-PKG", "name": "Packaging Materials", "parent": "CONS"},

    {"code": "SF", "name": "Semi-Finished Goods", "parent": null},
    {"code": "FG", "name": "Finished Goods", "parent": null},

    {"code": "FA", "name": "Fixed Assets", "parent": null},
    {"code": "FA-MCH", "name": "Machinery", "parent": "FA"},
    {"code": "FA-FUR", "name": "Furniture", "parent": "FA"},
    {"code": "FA-VEH", "name": "Vehicles", "parent": "FA"}
  ]
}
```

#### C. Product Categories
**File**: `backend/apps/sales/fixtures/default_product_categories.json`

```json
{
  "categories": [
    {"code": "GOODS", "name": "Trading Goods", "parent": null},
    {"code": "GOODS-ELC", "name": "Electronics", "parent": "GOODS"},
    {"code": "GOODS-APP", "name": "Appliances", "parent": "GOODS"},
    {"code": "GOODS-TEX", "name": "Textiles", "parent": "GOODS"},

    {"code": "SERV", "name": "Services", "parent": null},
    {"code": "SERV-CNS", "name": "Consulting", "parent": "SERV"},
    {"code": "SERV-MNT", "name": "Maintenance", "parent": "SERV"},
    {"code": "SERV-INS", "name": "Installation", "parent": "SERV"}
  ]
}
```

#### D. Departments
**File**: `backend/apps/companies/fixtures/default_departments.json`

```json
{
  "departments": [
    {"code": "EXEC", "name": "Executive Management"},
    {"code": "FIN", "name": "Finance & Accounting"},
    {"code": "HR", "name": "Human Resources"},
    {"code": "SALES", "name": "Sales & Marketing"},
    {"code": "OPS", "name": "Operations"},
    {"code": "PROD", "name": "Production"},
    {"code": "PROC", "name": "Procurement"},
    {"code": "IT", "name": "Information Technology"},
    {"code": "QA", "name": "Quality Assurance"},
    {"code": "LOG", "name": "Logistics & Warehouse"}
  ]
}
```

#### E. Cost Centers
**File**: `backend/apps/budgeting/fixtures/default_cost_centers.json`

```json
{
  "cost_centers": [
    {"code": "CC-ADMIN", "name": "Administration", "type": "ADMIN"},
    {"code": "CC-PROD", "name": "Production", "type": "PRODUCTION"},
    {"code": "CC-SALES", "name": "Sales & Marketing", "type": "SALES"},
    {"code": "CC-RND", "name": "Research & Development", "type": "OVERHEAD"},
    {"code": "CC-LOG", "name": "Logistics", "type": "OVERHEAD"},
    {"code": "CC-QC", "name": "Quality Control", "type": "OVERHEAD"}
  ]
}
```

### 2.2 Default Data Service

**NEW FILE: `backend/apps/metadata/services/default_data_service.py`**

```python
"""
Service to populate default master data for new companies
"""
from django.db import transaction
from apps.finance.models import Account
from apps.inventory.models import ItemCategory
from apps.sales.models import ProductCategory
from apps.companies.models import Department
from apps.budgeting.models import CostCenter
import json
import os

class DefaultDataService:

    @staticmethod
    @transaction.atomic
    def populate_defaults_for_company(company, data_types=None):
        """
        Populate default master data for a new company

        Args:
            company: Company instance
            data_types: List of data types to populate.
                       If None, populates all.
                       Options: ['accounts', 'item_categories',
                                'product_categories', 'departments',
                                'cost_centers']

        Returns:
            dict: Summary of created records
        """
        if data_types is None:
            data_types = [
                'accounts',
                'item_categories',
                'product_categories',
                'departments',
                'cost_centers'
            ]

        summary = {}

        if 'accounts' in data_types:
            summary['accounts'] = DefaultDataService._create_default_accounts(company)

        if 'item_categories' in data_types:
            summary['item_categories'] = DefaultDataService._create_default_item_categories(company)

        if 'product_categories' in data_types:
            summary['product_categories'] = DefaultDataService._create_default_product_categories(company)

        if 'departments' in data_types:
            summary['departments'] = DefaultDataService._create_default_departments(company)

        if 'cost_centers' in data_types:
            summary['cost_centers'] = DefaultDataService._create_default_cost_centers(company)

        return summary

    @staticmethod
    def _create_default_accounts(company):
        """Create default chart of accounts"""
        fixture_path = os.path.join(
            os.path.dirname(__file__),
            '../fixtures/default_chart_of_accounts.json'
        )

        with open(fixture_path, 'r') as f:
            data = json.load(f)

        account_map = {}  # code -> Account instance
        created_count = 0

        # Create in order (level 0, then 1, then 2, etc.)
        for level in range(5):
            for acc_data in data['accounts']:
                if acc_data.get('level') == level:
                    parent = None
                    if acc_data.get('parent'):
                        parent = account_map.get(acc_data['parent'])

                    account = Account.objects.create(
                        company_group=company.company_group,
                        company=company,
                        code=acc_data['code'],
                        name=acc_data['name'],
                        account_type=acc_data['type'],
                        parent_account=parent,
                        is_active=True,
                        is_default_template=True  # Mark as default
                    )
                    account_map[acc_data['code']] = account
                    created_count += 1

        return created_count

    @staticmethod
    def _create_default_item_categories(company):
        """Create default item categories"""
        fixture_path = os.path.join(
            os.path.dirname(__file__),
            '../fixtures/default_item_categories.json'
        )

        with open(fixture_path, 'r') as f:
            data = json.load(f)

        category_map = {}
        created_count = 0

        # Create parents first
        for cat_data in data['categories']:
            if not cat_data.get('parent'):
                category = ItemCategory.objects.create(
                    company=company,
                    code=cat_data['code'],
                    name=cat_data['name'],
                    is_active=True,
                    is_default_template=True
                )
                category_map[cat_data['code']] = category
                created_count += 1

        # Create children
        for cat_data in data['categories']:
            if cat_data.get('parent'):
                parent = category_map.get(cat_data['parent'])
                category = ItemCategory.objects.create(
                    company=company,
                    code=cat_data['code'],
                    name=cat_data['name'],
                    parent_category=parent,
                    is_active=True,
                    is_default_template=True
                )
                category_map[cat_data['code']] = category
                created_count += 1

        return created_count

    @staticmethod
    def _create_default_product_categories(company):
        """Create default product categories"""
        # Similar to item categories
        # ... implementation ...
        pass

    @staticmethod
    def _create_default_departments(company):
        """Create default departments"""
        # ... implementation ...
        pass

    @staticmethod
    def _create_default_cost_centers(company):
        """Create default cost centers"""
        # ... implementation ...
        pass
```

### 2.3 Integration Points

#### A. Company Creation Signal

**File: `backend/apps/companies/signals.py`**

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Company
from apps.metadata.services.default_data_service import DefaultDataService

@receiver(post_save, sender=Company)
def populate_default_master_data(sender, instance, created, **kwargs):
    """
    Automatically populate default master data when a new company is created
    """
    if created:
        DefaultDataService.populate_defaults_for_company(instance)
```

#### B. Admin Interface for Managing Defaults

**File: `backend/apps/finance/admin.py`**

```python
from django.contrib import admin
from .models import Account

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'account_type', 'company', 'is_default_template', 'is_active']
    list_filter = ['company', 'account_type', 'is_default_template', 'is_active']
    search_fields = ['code', 'name']

    # Allow admin to delete defaults
    def has_delete_permission(self, request, obj=None):
        return True

    # Show which are defaults
    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        return list_display + ['is_default_template']
```

---

## Implementation Steps

### Phase 1: Preparation (Day 1-2)

#### Day 1: Analysis & Design
- [ ] Final review of this implementation plan
- [ ] Stakeholder approval
- [ ] Create test database backup
- [ ] Set up development branch: `feature/product-item-separation`

#### Day 2: Model Creation
- [ ] Create `Item` model in inventory app
- [ ] Create new `Product` model in sales app
- [ ] Create `ItemCategory` model
- [ ] Create `ProductCategory` model in sales
- [ ] Add `is_default_template` flags to all master data models
- [ ] Run `makemigrations` - review migration files
- [ ] **DO NOT APPLY YET**

### Phase 2: Migration Script (Day 3-4)

#### Day 3: Data Migration
Create custom migration: `backend/apps/inventory/migrations/XXXX_split_product_to_item.py`

```python
from django.db import migrations

def split_products(apps, schema_editor):
    """
    Split existing Product records into Item (inventory) and Product (sales)
    """
    OldProduct = apps.get_model('inventory', 'Product')
    Item = apps.get_model('inventory', 'Item')
    NewProduct = apps.get_model('sales', 'Product')
    SalesOrderLine = apps.get_model('sales', 'SalesOrderLine')

    # Get all products used in sales orders
    products_in_sales = SalesOrderLine.objects.values_list('product_id', flat=True).distinct()

    for old_product in OldProduct.objects.all():
        # 1. Always create Item (for backward compatibility)
        item = Item.objects.create(
            company=old_product.company,
            code=old_product.code,
            name=old_product.name,
            description=old_product.description,
            item_type='RAW_MATERIAL',  # Default, can be changed later
            track_inventory=old_product.track_inventory,
            track_serial=old_product.track_serial,
            track_batch=old_product.track_batch,
            cost_price=old_product.cost_price,
            valuation_method=old_product.valuation_method,
            standard_cost=old_product.standard_cost,
            reorder_level=old_product.reorder_level,
            reorder_quantity=old_product.reorder_quantity,
            inventory_account=old_product.inventory_account,
            expense_account=old_product.expense_account,
            category=old_product.category,  # Will need mapping
            uom=old_product.uom,
            is_active=old_product.is_active,
        )

        # 2. If used in sales, also create Product
        if old_product.id in products_in_sales or old_product.selling_price > 0:
            product = NewProduct.objects.create(
                company=old_product.company,
                code=old_product.code,
                name=old_product.name,
                description=old_product.description,
                product_type=old_product.product_type,
                linked_item=item,
                selling_price=old_product.selling_price,
                cost_price=old_product.cost_price,
                sales_account=old_product.income_account,
                category=old_product.category,  # Will need mapping
                uom=old_product.uom,
                is_active=old_product.is_active,
            )

class Migration(migrations.Migration):
    dependencies = [
        ('inventory', 'XXXX_create_item_model'),
        ('sales', 'XXXX_create_product_model'),
    ]

    operations = [
        migrations.RunPython(split_products, reverse_code=migrations.RunPython.noop),
    ]
```

#### Day 4: Foreign Key Updates
Create migrations to update all ForeignKey references:

```python
# Update StockMovementLine
migrations.AlterField(
    model_name='stockmovementline',
    name='product',
    field=models.ForeignKey('inventory.Item', on_delete=models.PROTECT),
)

# Update CostLayer
migrations.AlterField(
    model_name='costlayer',
    name='product',
    field=models.ForeignKey('inventory.Item', on_delete=models.PROTECT),
)

# ... repeat for all models
```

### Phase 3: Code Updates (Day 5-6)

#### Day 5: Backend Code
- [ ] Update all views to use Item instead of Product
- [ ] Update all serializers
- [ ] Update all services
- [ ] Update URL patterns if needed
- [ ] Update admin.py files

#### Day 6: Frontend Code
- [ ] Rename Product components to Item
- [ ] Create new Product components for sales
- [ ] Update all imports
- [ ] Update API calls

### Phase 4: Default Data (Day 7-8)

#### Day 7: Fixtures & Service
- [ ] Create all fixture JSON files
- [ ] Implement `DefaultDataService`
- [ ] Create admin interfaces for managing defaults
- [ ] Add company creation signal

#### Day 8: Testing Defaults
- [ ] Test default data creation for new company
- [ ] Test admin can edit defaults
- [ ] Test admin can delete defaults
- [ ] Test defaults don't affect existing companies

### Phase 5: Testing (Day 9-10)

#### Day 9: Unit & Integration Tests
- [ ] Write tests for Item model
- [ ] Write tests for new Product model
- [ ] Write tests for DefaultDataService
- [ ] Write tests for data migration

#### Day 10: E2E Testing
- [ ] Test complete purchase flow (item-based)
- [ ] Test complete sales flow (product-based)
- [ ] Test inventory movements
- [ ] Test production (BOM with items)
- [ ] Test budgeting

### Phase 6: Deployment (Day 11-12)

#### Day 11: Staging Deployment
- [ ] Deploy to staging environment
- [ ] Run migrations on staging database
- [ ] Perform smoke tests
- [ ] Performance testing

#### Day 12: Production Deployment
- [ ] Schedule maintenance window (2-3 hours)
- [ ] Backup production database
- [ ] Deploy to production
- [ ] Run migrations
- [ ] Verify all modules working
- [ ] Monitor for 24 hours

---

## Database Migration Strategy

### Migration Files Order

```
1. inventory/migrations/XXXX_add_default_template_flags.py
   - Add is_default_template to ItemCategory, UOM

2. companies/migrations/XXXX_add_default_template_flags.py
   - Add is_default_template to Department

3. budgeting/migrations/XXXX_add_default_template_flags.py
   - Add is_default_template to CostCenter

4. finance/migrations/XXXX_add_default_template_flags.py
   - Add is_default_template to Account

5. inventory/migrations/XXXX_rename_product_category_to_item_category.py
   - Rename ProductCategory model

6. inventory/migrations/XXXX_create_item_model.py
   - Create Item model

7. sales/migrations/XXXX_create_product_category_model.py
   - Create ProductCategory in sales

8. sales/migrations/XXXX_create_product_model.py
   - Create Product model in sales

9. inventory/migrations/XXXX_split_product_data.py
   - Data migration: Split Product → Item + Product

10. inventory/migrations/XXXX_update_foreignkeys_to_item.py
    - Update all ForeignKeys from Product to Item

11. inventory/migrations/XXXX_remove_old_product_model.py
    - Remove old Product model (optional, for cleanup)
```

### Rollback Strategy

If issues occur during migration:

```bash
# Restore database from backup
psql -U postgres -d twist_erp < backup_before_migration.sql

# Or rollback migrations one by one
python manage.py migrate inventory XXXX_previous_migration
python manage.py migrate sales XXXX_previous_migration
```

---

## Testing Strategy

### Test Categories

#### 1. Unit Tests
```python
# tests/test_item_model.py
def test_item_creation()
def test_item_valuation_methods()
def test_item_category_hierarchy()

# tests/test_product_model.py
def test_product_creation()
def test_product_item_linking()
def test_product_available_quantity()

# tests/test_default_data_service.py
def test_populate_chart_of_accounts()
def test_populate_item_categories()
def test_defaults_for_new_company()
```

#### 2. Integration Tests
```python
# tests/test_purchase_flow.py
def test_purchase_order_with_items()
def test_goods_receipt_creates_cost_layers()

# tests/test_sales_flow.py
def test_sales_order_with_products()
def test_product_stock_deduction_via_linked_item()

# tests/test_production_flow.py
def test_bom_with_items()
def test_work_order_consumes_items()
```

#### 3. Data Migration Tests
```python
# tests/test_data_migration.py
def test_products_split_correctly()
def test_sales_products_created()
def test_foreign_keys_updated()
def test_no_data_loss()
```

### Test Data Preparation

```sql
-- Before migration: Create test products
INSERT INTO inventory_product (...) VALUES (...);

-- After migration: Verify split
SELECT COUNT(*) FROM inventory_item; -- Should equal product count
SELECT COUNT(*) FROM sales_product; -- Should equal saleable products
```

---

## Rollback Plan

### If Issues Found in Staging

```bash
# 1. Restore database
psql twist_erp_staging < backup_staging.sql

# 2. Rollback code
git checkout main

# 3. Fix issues
# ... make corrections ...

# 4. Retry
```

### If Issues Found in Production (Critical)

```bash
# Emergency Rollback Procedure

# 1. IMMEDIATELY restore database from backup
pg_restore -d twist_erp backup_before_migration.dump

# 2. Deploy previous code version
git revert <commit-hash>
git push production main

# 3. Restart services
systemctl restart gunicorn
systemctl restart celery

# 4. Verify system operational
curl https://erp.company.com/api/health

# 5. Notify stakeholders
# 6. Schedule post-mortem meeting
```

---

## Summary of Changes

### Files to Create (17 files)
1. `backend/apps/inventory/models/item.py`
2. `backend/apps/sales/models/product.py`
3. `backend/apps/sales/models/product_category.py`
4. `backend/apps/metadata/services/default_data_service.py`
5. `backend/apps/finance/fixtures/default_chart_of_accounts.json`
6. `backend/apps/inventory/fixtures/default_item_categories.json`
7. `backend/apps/sales/fixtures/default_product_categories.json`
8. `backend/apps/companies/fixtures/default_departments.json`
9. `backend/apps/budgeting/fixtures/default_cost_centers.json`
10-17. Various migration files

### Files to Modify (30+ files)
1. All models with Product ForeignKey (10 files)
2. All views using Product (8 files)
3. All serializers using Product (8 files)
4. All services using Product (6 files)
5. Admin files (4 files)
6. Signals (2 files)

### Frontend Files (15-20 files)
- All Product-related components need updates

### Database Tables Affected
- `inventory_product` → Split into `inventory_item` + `sales_product`
- `inventory_productcategory` → `inventory_itemcategory`
- New: `sales_productcategory`
- Updated: All tables with product_id foreign key

---

## Estimated Effort

### Development Time
- **Backend Development**: 8-10 days
- **Frontend Development**: 3-4 days
- **Testing**: 2-3 days
- **Documentation**: 1-2 days

**Total**: 14-19 days (3-4 weeks)

### Team Requirements
- 1 Senior Backend Developer
- 1 Frontend Developer
- 1 QA Engineer
- 1 DevOps Engineer (for deployment)

### Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data migration fails | HIGH | Thorough testing in staging, database backups |
| Foreign key integrity issues | HIGH | Careful migration script, validation checks |
| Performance degradation | MEDIUM | Add proper indexes, monitor query performance |
| Frontend breaking changes | MEDIUM | Gradual rollout, feature flags |
| User confusion | LOW | Clear documentation, training sessions |

---

## Approval Required

- [ ] **Technical Lead**: Code architecture approved
- [ ] **Product Owner**: Feature scope approved
- [ ] **Database Admin**: Migration strategy approved
- [ ] **DevOps**: Deployment plan approved
- [ ] **QA Lead**: Testing strategy approved

---

## Next Steps

1. **Review this document** with all stakeholders
2. **Get approvals** from technical leads
3. **Create development branch**
4. **Begin Phase 1** (Model creation)

---

**Document Version**: 1.0
**Last Updated**: November 5, 2025
**Author**: Claude (AI Assistant)
**Review Status**: Pending Approval
