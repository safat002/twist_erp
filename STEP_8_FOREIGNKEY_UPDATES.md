# Step 8: Update ForeignKey References

## Overview
After the Product→Item migration completes, we need to update ForeignKey references in various models to point to the correct model:
- **Item** for operational/expense items (procurement, production, inventory)
- **sales.Product** for saleable items (sales orders, revenue)

---

## ⚠️ CRITICAL: Apply Migrations First

Before making these changes:
```bash
cd backend
python manage.py migrate
```

This will:
1. Create the new tables (Item, ItemCategory, sales.Product, etc.)
2. Run the data migration to split Product → Item + sales.Product
3. Populate the new tables with migrated data

**ONLY THEN** proceed with the ForeignKey updates below.

---

## Models That Need Updates

### 1. 🟢 COMPLETED: BudgetLine
**File:** `backend/apps/budgeting/models.py`
**Status:** ✅ Already updated in this session

```python
# Already has both fields:
product = models.ForeignKey('sales.Product', ...)  # For revenue budgets
item = models.ForeignKey('inventory.Item', ...)     # For expense budgets
```

---

### 2. ❌ TODO: PurchaseOrderLine
**File:** `backend/apps/procurement/models.py`
**Current:** References `inventory.Product`
**Should be:** `inventory.Item`

**Changes needed:**
```python
# FIND this line:
product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, ...)

# REPLACE with:
item = models.ForeignKey(
    'inventory.Item',
    on_delete=models.PROTECT,
    related_name='purchase_order_lines',
    help_text="Inventory item being purchased"
)

# Also update any references to self.product in methods to self.item
```

**Affected methods to update:**
- Any method that accesses `self.product` should use `self.item`
- Update related serializers in `procurement/serializers.py`
- Update views in `procurement/views.py`

---

### 3. ❌ TODO: BOM (Bill of Materials)
**File:** `backend/apps/production/models.py`
**Current:** References `inventory.Product`
**Should be:** `inventory.Item`

**Changes needed:**
```python
# In BOM model:
# FIND:
product = models.ForeignKey('inventory.Product', ...)

# REPLACE with:
finished_item = models.ForeignKey(
    'inventory.Item',
    on_delete=models.PROTECT,
    related_name='bom_as_finished_good',
    help_text="Finished item produced by this BOM"
)

# In BOMLine model:
# FIND:
component = models.ForeignKey('inventory.Product', ...)

# REPLACE with:
component_item = models.ForeignKey(
    'inventory.Item',
    on_delete=models.PROTECT,
    related_name='bom_lines_as_component',
    help_text="Component item used in this BOM"
)
```

---

### 4. ❌ TODO: WorkOrder
**File:** `backend/apps/production/models.py`
**Current:** References `inventory.Product`
**Should be:** `inventory.Item`

**Changes needed:**
```python
# FIND:
product = models.ForeignKey('inventory.Product', ...)

# REPLACE with:
item = models.ForeignKey(
    'inventory.Item',
    on_delete=models.PROTECT,
    related_name='work_orders',
    help_text="Item to be produced"
)
```

---

### 5. ⚠️ SPECIAL CASE: SalesOrderLine
**File:** `backend/apps/sales/models/sales_order_line.py`
**Current:** References `inventory.Product`
**Should be:** `sales.Product`

**Changes needed:**
```python
# FIND:
product = models.ForeignKey('inventory.Product', ...)

# REPLACE with:
product = models.ForeignKey(
    'sales.Product',
    on_delete=models.PROTECT,
    related_name='sales_order_lines',
    help_text="Saleable product"
)
```

**Important:** SalesOrderLine should reference `sales.Product` (saleable items), NOT `inventory.Item`.

---

### 6. ❌ TODO: GoodsReceiptLine
**File:** `backend/apps/inventory/models.py`
**Current:** References legacy `inventory.Product`
**Should be:** `inventory.Item`

**Changes needed:**
```python
# FIND:
product = models.ForeignKey(Product, on_delete=models.PROTECT, ...)

# REPLACE with:
item = models.ForeignKey(
    Item,
    on_delete=models.PROTECT,
    related_name='goods_receipt_lines',
    help_text="Item being received"
)
```

---

### 7. ❌ TODO: DeliveryOrderLine
**File:** `backend/apps/inventory/models.py`
**Current:** References legacy `inventory.Product`
**Should be:** `sales.Product` (since this is for delivered sales items)

**Changes needed:**
```python
# FIND:
product = models.ForeignKey(Product, on_delete=models.PROTECT, ...)

# REPLACE with:
product = models.ForeignKey(
    'sales.Product',
    on_delete=models.PROTECT,
    related_name='delivery_order_lines',
    help_text="Saleable product being delivered"
)
```

---

### 8. ❌ TODO: StockMovementLine
**File:** `backend/apps/inventory/models.py`
**Current:** References legacy `Product`
**Should be:** `inventory.Item`

**Changes needed:**
```python
# FIND:
product = models.ForeignKey(Product, on_delete=models.PROTECT)

# REPLACE with:
item = models.ForeignKey(
    Item,
    on_delete=models.PROTECT,
    related_name='stock_movement_lines',
    help_text="Item being moved"
)
```

---

### 9. ❌ TODO: StockLedger
**File:** `backend/apps/inventory/models.py`
**Current:** References legacy `Product`
**Should be:** `inventory.Item`

**Changes needed:**
```python
# FIND:
product = models.ForeignKey(Product, on_delete=models.PROTECT)

# REPLACE with:
item = models.ForeignKey(
    Item,
    on_delete=models.PROTECT,
    related_name='stock_ledger_entries',
    help_text="Item for stock tracking"
)
```

---

### 10. ❌ TODO: StockLevel
**File:** `backend/apps/inventory/models.py`
**Current:** References legacy `Product`
**Should be:** `inventory.Item`

**Changes needed:**
```python
# FIND:
product = models.ForeignKey(Product, on_delete=models.PROTECT)

# REPLACE with:
item = models.ForeignKey(
    Item,
    on_delete=models.PROTECT,
    related_name='stock_levels',
    help_text="Item with stock level"
)
```

---

### 11. ❌ TODO: CostLayer
**File:** `backend/apps/inventory/models.py`
**Current:** References legacy `Product`
**Should be:** `inventory.Item`

**Changes needed:**
```python
# FIND:
product = models.ForeignKey(Product, on_delete=models.PROTECT, ...)

# REPLACE with:
item = models.ForeignKey(
    Item,
    on_delete=models.PROTECT,
    related_name='cost_layers',
    help_text="Item for cost layer tracking"
)
```

---

### 12. ❌ TODO: ItemValuationMethod
**File:** `backend/apps/inventory/models.py`
**Current:** References legacy `Product`
**Should be:** `inventory.Item`

**Changes needed:**
```python
# FIND:
product = models.ForeignKey(Product, on_delete=models.PROTECT, ...)

# REPLACE with:
item = models.ForeignKey(
    Item,
    on_delete=models.PROTECT,
    related_name='valuation_methods',
    help_text="Item with valuation method"
)
```

---

### 13. ❌ TODO: ValuationChangeLog
**File:** `backend/apps/inventory/models.py`
**Current:** References legacy `Product`
**Should be:** `inventory.Item`

**Changes needed:**
```python
# FIND:
product = models.ForeignKey(Product, on_delete=models.PROTECT, ...)

# REPLACE with:
item = models.ForeignKey(
    Item,
    on_delete=models.PROTECT,
    related_name='valuation_changes',
    help_text="Item with valuation change"
)
```

---

## Step-by-Step Implementation Process

### Phase A: Update Model Files (2-3 hours)

1. **Start with inventory models** (same file, easier):
   ```bash
   # File: backend/apps/inventory/models.py
   # Update: StockMovementLine, StockLedger, StockLevel, GoodsReceiptLine,
   #         CostLayer, ItemValuationMethod, ValuationChangeLog
   ```

2. **Update sales models**:
   ```bash
   # File: backend/apps/sales/models/sales_order_line.py
   # Update: product field to reference sales.Product

   # File: backend/apps/inventory/models.py
   # Update: DeliveryOrderLine to reference sales.Product
   ```

3. **Update procurement models**:
   ```bash
   # File: backend/apps/procurement/models.py
   # Update: PurchaseOrderLine.product → PurchaseOrderLine.item
   ```

4. **Update production models**:
   ```bash
   # File: backend/apps/production/models.py
   # Update: BOM, BOMLine, WorkOrder
   ```

### Phase B: Create Migrations (30 minutes)

After updating all models:
```bash
cd backend
python manage.py makemigrations inventory
python manage.py makemigrations sales
python manage.py makemigrations procurement
python manage.py makemigrations production
```

### Phase C: Review Generated Migrations (30 minutes)

**CRITICAL:** Review each generated migration carefully. Django should detect:
- Field renames (`product` → `item`)
- ForeignKey target changes (`inventory.Product` → `inventory.Item`)

**Verify migrations don't:**
- Delete and recreate fields (should be RenameField or AlterField)
- Lose data
- Break constraints

### Phase D: Create Data Migration to Update References (1 hour)

You may need a data migration to update existing ForeignKey values:

```python
# Example migration to update references
def update_foreignkey_references(apps, schema_editor):
    """Update ForeignKey references from old Product to new Item"""

    # Get models
    Item = apps.get_model('inventory', 'Item')
    StockMovementLine = apps.get_model('inventory', 'StockMovementLine')

    # For each StockMovementLine, find the matching Item
    for line in StockMovementLine.objects.all():
        # Find Item that was created from the old product
        item = Item.objects.filter(legacy_product_id=line.product_id).first()
        if item:
            line.item_id = item.id
            line.save(update_fields=['item_id'])
```

### Phase E: Apply Migrations (15 minutes)

```bash
cd backend

# Backup database first!
pg_dump twist_erp > backup_before_fk_updates.sql

# Apply migrations
python manage.py migrate inventory
python manage.py migrate sales
python manage.py migrate procurement
python manage.py migrate production
```

### Phase F: Update Services and Views (2-3 hours)

Update any code that references the old field names:

1. **Serializers:**
   - `procurement/serializers.py`: Update `product` → `item`
   - `production/serializers.py`: Update `product` → `item`
   - `sales/serializers.py`: Ensure references `sales.Product`

2. **Views:**
   - Any views that filter/query by `product` need updating

3. **Services:**
   - `inventory/services/stock_service.py`: Update all `product` references
   - `procurement/services/`: Update references
   - `production/services/`: Update references

---

## Testing Checklist

After applying all changes:

- [ ] Server starts without errors
- [ ] No import errors
- [ ] Django admin shows all models correctly
- [ ] Can create new PurchaseOrder with Items
- [ ] Can create new SalesOrder with sales.Products
- [ ] Can create new WorkOrder with Items
- [ ] Stock movements work with Items
- [ ] Cost layers track Items correctly
- [ ] No broken ForeignKey relationships (check with admin)

---

## Rollback Plan

If issues arise:

```bash
# Restore database backup
psql twist_erp < backup_before_fk_updates.sql

# Revert migrations
python manage.py migrate inventory 10001  # Before FK updates
python manage.py migrate sales 0004       # Before FK updates
```

---

## Estimated Time

- **Model Updates:** 2-3 hours
- **Migration Creation & Review:** 1 hour
- **Migration Application:** 15 minutes
- **Service/View Updates:** 2-3 hours
- **Testing:** 1-2 hours

**Total:** 6-10 hours

---

## Next Steps After Completion

Once Step 8 is complete:
1. **Step 9:** Validate all data integrity
2. **Phase 2:** Begin industry-specific default data implementation
3. **Phase 3:** Implement Financial Statements service

---

**Status:** 📝 Documentation complete - Ready for implementation
**Last Updated:** November 5, 2025
