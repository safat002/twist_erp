# Product-to-Item Refactoring - Quick Summary

**Last Updated**: November 5, 2025

---

## What Changes?

### 1. Product vs Item Separation

#### CURRENT (Before)
```
inventory.Product
└── Used for EVERYTHING:
    ├── Raw materials
    ├── Finished goods for sale
    ├── Consumables
    ├── Fixed assets
    └── Components
```

#### NEW (After)
```
sales.Product                          inventory.Item
├── Saleable items                     ├── Raw materials
├── Trading goods                      ├── Consumables
├── Services sold to customers         ├── Components
└── Has selling_price                  ├── Fixed assets
    ├── Used in: Sales Orders          ├── Semi-finished goods
    ├── Used in: Quotations            └── Has cost_price
    └── Used in: Revenue Budgets           ├── Used in: Purchase Orders
                                           ├── Used in: Production (BOM)
                                           ├── Used in: Stock Movements
                                           └── Used in: Expense/CAPEX Budgets

Optional Link: Product.linked_item → Item
(For products that need inventory tracking)
```

### 2. Budget Classification

As per your clarification:

| Budget Type | Uses | Example |
|-------------|------|---------|
| **Revenue Budget** | `sales.Product` | "Budget to sell 1000 units of Product ABC at $50 each" |
| **Expense Budget** | `inventory.Item` | "Budget for 500 kg of Raw Material XYZ at $10/kg" |
| **CAPEX Budget** | `inventory.Item` | "Budget for 1 Machine (Fixed Asset) at $50,000" |
| **Production Budget** | `inventory.Item` | "Budget for 10,000 units of Component PQR" |

**File to Update**: `backend/apps/budgeting/models.py`

```python
class BudgetLine(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE)
    line_number = models.IntegerField()

    # NEW: Split into two fields
    product = models.ForeignKey(
        'sales.Product',
        on_delete=models.PROTECT,
        null=True, blank=True,
        help_text="For revenue budgets only"
    )
    item = models.ForeignKey(
        'inventory.Item',
        on_delete=models.PROTECT,
        null=True, blank=True,
        help_text="For expense/capex/production budgets"
    )

    # Validation: One and only one must be set
    def clean(self):
        if (self.product and self.item) or (not self.product and not self.item):
            raise ValidationError("Must specify either product OR item, not both")
```

---

## Default Master Data Implementation

### What Gets Pre-Populated?

When a **new company is created**, the system automatically creates:

#### 1. Chart of Accounts (50+ accounts)
```
1000 - ASSETS
  1100 - Current Assets
    1110 - Cash & Bank
      1111 - Cash in Hand
      1112 - Bank Account
    1120 - Accounts Receivable
    1130 - Inventory
      1131 - Raw Materials
      1132 - WIP
      1133 - Finished Goods
  1200 - Fixed Assets
    ...
2000 - LIABILITIES
    ...
3000 - EQUITY
    ...
4000 - REVENUE
    ...
5000 - EXPENSES
    ...
```

#### 2. Item Categories (15+ categories)
```
RM - Raw Materials
  RM-MTL - Metals
  RM-CHM - Chemicals
COMP - Components
  COMP-ELC - Electronics
CONS - Consumables
  CONS-OFF - Office Supplies
FA - Fixed Assets
  FA-MCH - Machinery
```

#### 3. Product Categories (10+ categories)
```
GOODS - Trading Goods
  GOODS-ELC - Electronics
  GOODS-APP - Appliances
SERV - Services
  SERV-CNS - Consulting
```

#### 4. Departments (10 departments)
```
EXEC - Executive Management
FIN - Finance & Accounting
HR - Human Resources
SALES - Sales & Marketing
OPS - Operations
PROD - Production
...
```

#### 5. Cost Centers (6 cost centers)
```
CC-ADMIN - Administration
CC-PROD - Production
CC-SALES - Sales & Marketing
CC-RND - Research & Development
...
```

### How Admin Can Customize?

**Via Django Admin Panel**:
1. Navigate to `/admin/`
2. Select the master data type (e.g., Accounts, Item Categories)
3. Filter by `is_default_template = True` to see defaults
4. **Edit**: Change name, code, or properties
5. **Delete**: Remove if not needed
6. **Add New**: Create custom entries

**All default data is fully editable and deletable** - it's just a starting template.

---

## Key Implementation Files

### New Models (3 files)
1. `backend/apps/inventory/models/item.py` - NEW
2. `backend/apps/sales/models/product.py` - NEW
3. `backend/apps/sales/models/product_category.py` - NEW

### Default Data Service (1 file)
4. `backend/apps/metadata/services/default_data_service.py` - NEW

### Fixture Files (5 JSON files)
5. `backend/apps/finance/fixtures/default_chart_of_accounts.json`
6. `backend/apps/inventory/fixtures/default_item_categories.json`
7. `backend/apps/sales/fixtures/default_product_categories.json`
8. `backend/apps/companies/fixtures/default_departments.json`
9. `backend/apps/budgeting/fixtures/default_cost_centers.json`

### Models to Update (10+ files)
- All models with `ForeignKey('inventory.Product')` → Update to `Item` or `sales.Product`
- Key modules: budgeting, production, procurement, inventory, sales

### Views & Serializers to Update (20+ files)
- Inventory views → Use `Item`
- Sales views → Use `Product`
- Budget views → Support both `Product` and `Item`

### Frontend Components to Update (15+ files)
- Rename Product components → Item components
- Create new Product components for sales module
- Update all API calls

---

## Migration Sequence

### Step 1: Add `is_default_template` Flag
```python
# All master data models get this field
is_default_template = models.BooleanField(
    default=False,
    help_text="System default that can be customized"
)
```

**Models Updated**:
- Account
- ItemCategory
- ProductCategory
- Department
- CostCenter
- UnitOfMeasure

### Step 2: Create New Models
- Create `Item` model
- Create `sales.Product` model
- Create `sales.ProductCategory` model

### Step 3: Data Migration
- Copy all existing `inventory.Product` → `inventory.Item`
- Create `sales.Product` for items used in sales orders
- Link Product to Item via `linked_item` FK

### Step 4: Update Foreign Keys
- Update all modules to reference correct model
- BudgetLine gets both `product` and `item` FKs

### Step 5: Populate Defaults
- When new company created, auto-populate all defaults
- Signal: `post_save` on Company model

---

## Testing Checklist

### Data Migration Testing
- [ ] All old products migrated to items
- [ ] Saleable products also created in sales.Product
- [ ] No data loss
- [ ] Foreign key integrity maintained

### Module Testing
- [ ] Purchase Orders use Items
- [ ] Sales Orders use Products
- [ ] Production (BOM) uses Items
- [ ] Stock Movements use Items
- [ ] Revenue Budgets use Products
- [ ] Expense Budgets use Items
- [ ] Valuation services work with Items

### Default Data Testing
- [ ] New company gets all defaults
- [ ] Can edit default accounts
- [ ] Can delete default categories
- [ ] Can add custom master data
- [ ] Defaults don't affect existing companies

### Frontend Testing
- [ ] Item selector works in inventory screens
- [ ] Product selector works in sales screens
- [ ] Budget screen shows correct selector based on type
- [ ] Stock reports use Items
- [ ] Sales reports use Products

---

## Rollback Plan

If critical issues found:

```bash
# 1. Restore database backup
pg_restore -d twist_erp backup_before_migration.dump

# 2. Revert code
git revert <commit-hash>

# 3. Restart services
systemctl restart gunicorn
```

---

## Timeline

| Phase | Duration | Activities |
|-------|----------|------------|
| **Phase 1: Models** | 2 days | Create Item, Product, ProductCategory models |
| **Phase 2: Migration** | 2 days | Write data migration scripts |
| **Phase 3: Backend** | 3 days | Update views, serializers, services |
| **Phase 4: Defaults** | 2 days | Create fixtures, implement default service |
| **Phase 5: Frontend** | 3 days | Update React components |
| **Phase 6: Testing** | 3 days | Unit, integration, E2E tests |
| **Phase 7: Deployment** | 2 days | Staging → Production |

**Total: 17 days (3.5 weeks)**

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Data migration fails | Low | HIGH | Multiple backups, staging testing |
| Foreign key errors | Medium | HIGH | Comprehensive testing, validation |
| User confusion | Medium | Low | Documentation, training |
| Performance issues | Low | Medium | Proper indexing, monitoring |

---

## Questions to Resolve

1. **Industry-Specific Defaults**: Should we create multiple default templates for different industries (Manufacturing, Trading, Services)?

2. **Multi-Currency**: Should default Chart of Accounts support multi-currency from start?

3. **Existing Data**: For existing companies, do we:
   - Auto-migrate to new structure?
   - Let them opt-in to migration?
   - Keep both models (with deprecation notice)?

4. **Product-Item Linking**: Should we:
   - Automatically link Product to Item with same code?
   - Force manual linking?
   - Make linking optional?

5. **Default Data Language**: Should defaults be:
   - English only?
   - Multi-language?
   - Configurable by company?

---

## Next Steps

1. **Review** this summary and detailed plan
2. **Decide** on questions above
3. **Approve** to proceed
4. **Start** with Phase 1 (Model creation)

---

## Files Created

1. ✅ `PRODUCT_TO_ITEM_REFACTORING_PLAN.md` - Detailed 50-page plan
2. ✅ `IMPLEMENTATION_SUMMARY.md` - This quick summary

**Ready to proceed when you approve!**
