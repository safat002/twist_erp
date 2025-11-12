# Unified Item Migration Status

## ✅ Phase 1: Schema Updates - COMPLETE

### Models Updated (14 models)
All models now use `budget_item` FK instead of `item`/`product`:

1. ✅ StockMovementLine - uses budget_item
2. ✅ InTransitShipmentLine - uses budget_item
3. ✅ StockLedger - uses budget_item
4. ✅ StockLevel - uses budget_item
5. ✅ GoodsReceiptLine - uses budget_item
6. ✅ ItemValuationMethod - uses budget_item
7. ✅ CostLayer - uses budget_item
8. ✅ ValuationChange - uses budget_item
9. ✅ StandardCostVariance - uses budget_item
10. ✅ PurchasePriceVariance - uses budget_item
11. ✅ LandedCostComponent - uses budget_item
12. ✅ LandedCostVoucher (line) - uses budget_item
13. ✅ ReturnToVendorLine - uses budget_item
14. ✅ MovementEvent - uses budget_item
15. ✅ ItemOperationalExtension - uses budget_item (removed item FK)

### Admin Updates - COMPLETE
- ✅ All list_display fields updated
- ✅ All search_fields updated (product__code → budget_item__code)
- ✅ All autocomplete_fields updated
- ✅ Duplicate fieldsets fixed

## ⚠️ Phase 2: Migration Creation - IN PROGRESS

### Issue
Migration creation is blocked because:
- Adding non-nullable FK `budget_item` to tables with existing data
- Django requires either a default value or manual data migration

### Solution Options

**Option A: Make Fields Nullable (Quick Fix for Dev)**
- Add all new budget_item fields as nullable initially
- Suitable for development/testing environment
- Allows migrations to proceed without data migration logic

**Option B: Create Data Migration (Production-Ready)**
- Step 1: Add budget_item as nullable
- Step 2: RunPython to copy item_id → budget_item_id
- Step 3: Make budget_item non-nullable
- Step 4: Remove old item/product field
- Proper production migration strategy

### Affected Models Needing Nullable FKs
If going with Option A, these fields need `null=True, blank=True`:
- CostLayer.budget_item
- ItemValuationMethod.budget_item
- ValuationChange.budget_item
- StandardCostVariance.budget_item
- PurchasePriceVariance.budget_item
- LandedCostComponent.budget_item
- LandedCostVoucher line.budget_item
- ReturnToVendorLine.budget_item
- MovementEvent.budget_item
- StockMovementLine.budget_item
- InTransitShipmentLine.budget_item
- StockLedger.budget_item
- StockLevel.budget_item
- GoodsReceiptLine.budget_item

## 📋 Phase 3: Remaining Tasks

### Backend
- [ ] Complete migrations (choose Option A or B above)
- [ ] Update BudgetLine model to use budget_item
- [ ] Update inventory services
- [ ] Update budgeting serializers
- [ ] Update inventory serializers/viewsets

### Frontend
- [ ] Update item selectors to use BudgetItemCode
- [ ] Update Material Issue UI
- [ ] Update GRN UI
- [ ] Update Stock Movement UI
- [ ] Update Internal Requisition UI

### Testing
- [ ] IR → PO → GRN flow
- [ ] Material Issue flow
- [ ] Stock Movement flow
- [ ] GL posting verification

## 🎯 Recommendation

For development speed, proceed with **Option A** (nullable fields). This allows:
1. Rapid development and testing
2. No complex data migration logic needed yet
3. Easy to add proper data migration later for production

Command to proceed:
```bash
# Make all budget_item fields nullable in models.py
# Then run: python manage.py makemigrations inventory
# Then run: python manage.py migrate
```
