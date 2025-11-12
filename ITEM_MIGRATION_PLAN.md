# Item Ownership Change - Migration Plan

## Summary
Consolidating `inventory.Item` into `budgeting.BudgetItemCode` as the master item record for all modules.

## Status: PARTIALLY IMPLEMENTED

### Completed
- ✅ Extended `BudgetItemCode` with all inventory fields (valuation_method, reorder levels, tracking flags, lifecycle status)
- ✅ Created `BudgetItemInventoryProfile` (optional, for inventory-specific settings)
- ✅ Created `BudgetItemFinanceProfile` (optional, for GL/finance settings)

### Models with BOTH item & budget_item (transitional state)
These models already have both FKs and sync logic:
1. `StockHold` - has both item & budget_item FKs (lines 2400-2401)
2. `BatchLot` - has both item & budget_item FKs (lines 2531-2532)
3. `SerialNumber` - has both item & budget_item FKs (lines 2598-2599)
4. `StockMovement` - has budget_item FK (line 63)

### Models with ONLY item FK (need migration)
These need to be updated to use budget_item instead:
1. `StockMovementLine` - item FK (line 181)
2. `WarehouseBin` - item FK (line 203)
3. `StockLedgerEntry` - item FK (line 242)
4. `StockLevel` - item FK (line 476)
5. `GoodsReceiptLine` - item FK (line 531)
6. `ItemValuationMethod` - product FK to Item (line 586)
7. `ItemCostLayer` - product FK to Item (line 636)
8. `ValuationChange` - product FK to Item (line 778)
9. `StandardCostVariance` - product FK to Item (line 866)
10. `PurchasePriceVariance` - product FK to Item (line 952)
11. `LandedCostComponent` - product FK to Item (line 1135)
12. `LandedCostVoucher` - product FK to Item (line 1329)
13. `ReturnToVendorLine` - product FK to Item (line 1584)
14. `MovementEvent` - item FK (line 2175)

Note: Many models use `product` as the field name but it's FK to Item, not sales.Product

### Models referencing Item in other apps
1. `BudgetLine` (budgeting/models.py) - has item FK (line 627) for expense/capex budgets
2. Production models (apps/production/models.py) - need to check
3. Sales models (apps/sales/models.py) - need to check

## Migration Steps

### Phase 1: Model Updates ⏳
1. ~~Add new fields to BudgetItemCode~~ ✅
2. ~~Create profile models~~ ✅
3. Remove `item` FK from models that have both (StockHold, BatchLot, SerialNumber)
4. Replace `item` FK with `budget_item` FK in remaining models
5. Mark `inventory.Item` model as deprecated (add warning in docstring)

### Phase 2: Service Layer Updates
1. Update `stock_service.py` to use budget_item
2. Update `valuation_service.py` to use budget_item
3. Update `material_issue_service.py` to use budget_item
4. Update `landed_cost_service.py` to use budget_item
5. Update `rtv_service.py` to use budget_item
6. Update `qc_service.py` to use budget_item

### Phase 3: API & Serializer Updates
1. Update budgeting serializers to expose inventory metadata
2. Create ItemSerializer that wraps BudgetItemCode with inventory profile
3. Update inventory viewsets to use budget_item
4. Add filter `/api/v1/budgets/item-codes/?item_type=GOODS&status=ACTIVE`

### Phase 4: Frontend Updates
1. Replace all Item dropdowns with BudgetItemCode selector
2. Update Material Issue UI to use budget items
3. Update GRN UI to use budget items
4. Update Stock Movement UI to use budget items
5. Update Internal Requisition UI to use budget items

### Phase 5: Migration & Testing
1. Create Django migration for new fields
2. Data migration: sync existing Item data to BudgetItemCode (if needed)
3. Run full workflow test: IR → PO → GRN → Material Issue → Stock Movement
4. Verify GL postings work correctly

## Key Architectural Changes

### Before
```
BudgetLine → inventory.Item (separate record)
StockMovement → inventory.Item
GRN → inventory.Item
```

### After
```
BudgetLine → BudgetItemCode (master)
StockMovement → BudgetItemCode
GRN → BudgetItemCode
```

## Backward Compatibility

- Keep `inventory.Item` model temporarily as deprecated
- Add OneToOne link from Item → BudgetItemCode (already exists)
- Gradually phase out Item references over time
- Eventually remove Item model in future version

## Governance

- `status` field on BudgetItemCode controls lifecycle:
  - `PLANNING`: Budget preparation only, no inventory ops
  - `ACTIVE`: Full inventory operations enabled
  - `OBSOLETE`: Historical reference only, no new transactions

- Permissions:
  - Budgeting team: edit budget/pricing fields
  - Inventory team: edit inventory profile
  - Finance team: edit finance profile

## Notes

- Many models use `product` as field name but reference `Item`, not `sales.Product`
- This naming inconsistency should be fixed during migration
- Some models have sync code (lines 1987-2000 etc.) to keep item/budget_item aligned - remove after migration
