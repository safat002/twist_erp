# Product → Item Refactoring Plan (Phase 1 follow‑up)

Goal: converge on a single operational entity “Item” owned by the Inventory app and update all references currently pointing to `inventory.Product`. Sales keeps its own `sales.Product` for sellable catalog; it optionally links to Inventory via `linked_item`.

This plan finishes Phase 1 by updating all ForeignKey references in models and application code without breaking existing data or APIs.

## High‑Level Approach
- Step 0 (already in repo): inventory Product is the operational entity used by stock, valuation, and procurement. Sales has a separate `sales.Product` that may link to inventory via `linked_item`.
- Step 1: Introduce `inventory.Item` as the canonical name (initially as a thin alias to the same DB table used by `inventory.Product`).
- Step 2: Migrate code references (models, serializers, services, tests, admin, views, frontends) from `inventory.Product` to `inventory.Item` in a controlled sequence.
- Step 3: Provide a temporary compatibility shim so existing imports referencing `inventory.Product` keep working during rollout (proxy model or import alias).
- Step 4: Once all FKs and code paths are switched to `Item`, deprecate the old `Product` symbol and remove after a stabilization window.

## Migration Strategy (Django)
Two safe options — choose based on tolerance for intermediate shims:

1) Rename model using migrations.RenameModel
- State migration: `RenameModel('Product','Item')` in inventory.
- Add a temporary proxy class `class Product(Item): class Meta: proxy = True` to keep dotted path `apps.inventory.models.Product` importable while code is being updated.
- Follow‑up migrations adjust constraints/index names if needed.

2) Dual‑class alias (no DB rename), then cut‑over
- Create `class Item(models.Model): Meta: db_table = 'inventory_product'` with identical fields; set `managed = False` if desired, or regular managed model if schema ownership remains.
- Incrementally change FKs/code to point to `Item`.
- Remove or proxy `Product` once references are updated.

Recommendation: Use Option 1 (RenameModel) if test coverage is available; use Option 2 if you prefer a gradual switch.

## ForeignKey Update Checklist (inventory.Product → inventory.Item)
Below is a non‑exhaustive but practical list derived from code search. Replace FK target from `inventory.Product` to `inventory.Item` and re‑run migrations.

Back‑end model references to update:
- Procurement
  - `backend/apps/procurement/models.py:205` (PurchaseRequisitionLine.product)
  - `backend/apps/procurement/models.py:483` (PurchaseOrderLine.product)
- Production
  - `backend/apps/production/models.py:47` (BOM.product)
  - `backend/apps/production/models.py:104` (WorkOrder.product)
  - `backend/apps/production/models.py:416` (Consumption.product / as applicable)
- Budgeting
  - `backend/apps/budgeting/models.py:556` (BudgetLine.product optional link)
- Sales
  - `backend/apps/sales/models.py:83` (Legacy sales line to inventory product)
  - `backend/apps/sales/models/sales_order_line.py:14` (SalesOrderLine.product)
- Inventory
  - `backend/apps/inventory/models.py:116` (StockMovementLine.product)
  - `backend/apps/inventory/models.py:430` (GoodsReceiptLine.product)
  - `backend/apps/inventory/models.py:441` (DeliveryOrderLine.product)
  - `backend/apps/inventory/models.py:492` (ItemValuationMethod.product)
  - `backend/apps/inventory/models.py:542` (CostLayer.product)
  - `backend/apps/inventory/models.py:684` (ValuationChangeLog.product)

Notes:
- Several related_name values currently carry a "legacy_*" prefix in Inventory. Align related_name to `items`, `item_*` consistently once the switch is complete.
- Sales has its own `sales.Product` (catalog) and keeps `linked_item = ForeignKey('inventory.Item', ...)` — no changes needed there other than ensuring the Inventory side is `Item`.

## Code Paths to Review After FK Update
- Services
  - Inventory: `backend/apps/inventory/services/stock_service.py` (layer consumption, postings)
  - Valuation: `backend/apps/inventory/services/valuation_service.py`
  - Finance event handlers: `backend/apps/finance/event_handlers.py` (account resolution uses `product.inventory_account` etc.)
- Serializers & Views
  - Inventory serializers for product→item field names
  - Procurement serializers & views exposing product fields
  - Sales order line serializers
- Admin
  - Inventory admin Product screens — rename to Item and verify filters/search
- Frontend
  - Any components that depend on `product` field names for inventory entities (lists, selectors). Replace labels and API payloads as needed (e.g., `item` or `item_id`).

## Step‑By‑Step Execution Plan
1. Introduce Item model in Inventory
   - Option A (rename): migration `RenameModel('Product','Item')`.
   - Option B (alias): new `Item` class with same fields (db_table preserved).
   - Add proxy `Product` to keep imports working temporarily.

2. Update FKs incrementally
   - Start with leaf modules (Production, Budgeting), proceed to Procurement, then Sales lines, then Inventory internals.
   - For each module update:
     - Change FK target to `inventory.Item`.
     - Create and apply migrations.
     - Run checks and smoke test affected APIs.

3. Update services/serializers/admin
   - Replace attribute names (`product` → `item`) where appropriate, or preserve external API fields while backend maps to Item for a transition period.

4. Update frontend payloads and UIs
   - Replace form fields and table columns to use `item`/`item_name`.
   - Provide compatibility mapping in API services (e.g., accept both `product_id` and `item_id` for a deprecation window).

5. Remove proxy and clean up
   - After all references and tests pass, drop proxy `Product` and any legacy related_names.
   - Regenerate OpenAPI docs if applicable.

## Data Migration & Backfill
- If using rename, data remains intact. Validate constraints and indexes transferred.
- If using alias, no data copy is needed (same db_table). If restructuring tables, use `RunPython` to copy rows and remap FKs.
- Validate count parity before/after and foreign key integrity with a simple SQL sanity check.

## Testing Plan
- Unit tests:
  - Valuation/issuance use `Item` end‑to‑end (FEFO/expiry cases).
  - Finance posting handlers still resolve accounts via item links and posting rules.
  - Procurement flow: PR → PO → GRN, budget usage and stock layers created referencing Item.
- API/Integration tests:
  - Ensure serializers emit and accept `item` fields; optionally accept `product` for a deprecation window.
- Frontend smoke tests:
  - Stock movements/GRN/DO creation with item picker.

## Rollout & Risk Mitigation
- Use feature branch and end‑to‑end CI before merge.
- Enable dual‑field acceptance (product_id and item_id) temporarily to avoid client breakage.
- Keep proxy `Product(Item)` for at least one release, then remove.
- Communicate deprecation timeline to app teams.

## Deliverables & Checklist
- [ ] Add `inventory.Item` model (rename or alias)
- [ ] Update FKs listed above to reference Item
- [ ] Update serializers/services/admin to Item
- [ ] Frontend substitutions and API compatibility
- [ ] Proxy removal and cleanup
- [ ] Docs update and release notes

