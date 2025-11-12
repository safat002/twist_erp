Unified Item Strategy (BudgetItemCode as the Master Record)
Budgeting → Inventory alignment without cloning master data.

———

1. High-Level Goal
   All modules (Budgeting, Inventory, Procurement, Material Issue, QC, Finance) will treat
   budgeting.BudgetItemCode as the canonical item. Inventory still needs physical metadata (valuation,
   serial/batch flags, stock UOM), so we’ll extend the budget item with those operational attributes
   instead of keeping a separate inventory.Item model. This keeps every activity on the same ID while
   preserving module-specific concerns via field groups or linked profiles.

———

2. Schema Changes

- BudgetItemCode (Inventory-aware master)
  - Keep existing fields (code, name, category, uom, standard_price).
  - Add new operational columns (nullable where not immediately used):
    - stock_uom (FK to inventory.UnitOfMeasure) – which UOM stock is tracked in.
    - valuation_rate / standard_cost – for MaterialIssue cost calculations.
    - is_batch_tracked, is_serial_tracked (booleans).
    - requires_fefo, is_service, item_type (Goods / Service / Tax / Consumption).
    - Optional inventory_account / expense_account (FK to finance) for GL posting.
  - Add lifecycle metadata: status (PLANNING, ACTIVE, OBSOLETE), created_by, department, etc.
- Optional Profiles (if you want separation)
  - BudgetItemInventoryProfile (1:1) for purely inventory-specific data (bins, valuation method).
  - BudgetItemFinanceProfile for GL/cost-center defaults.
  - These remain tied to the budget item ID but encapsulate different responsibilities (Inventory
    team edits the inventory profile; Finance edits the finance profile).
- Item Groups (Budget families)
  - Table budget_item_group with a many-to-many linking table to budget items.
  - Use these when a single budget line funds multiple SKUs (e.g., packaging material across
    warehouses).
  - Requisitions and GL rules can reference a group; Inventory transactions still operate on the
    concrete budget item.
- Inventory-specific tables
  - Drop or repurpose inventory.Item; any remaining operational data lives either on the budget item
    or dedicated profiles.
  - Stock movement lines, Material Issue lines, GRN lines point to budget_item_id (possibly via FK
    to the new expanded budget item).

———

3. API & Service Layer

- Budgeting APIs
  - /api/v1/budgets/item-codes/ remains but now includes the new inventory metadata and lifecycle
    fields.
  - Add query params to filter by item_type (Goods/Service), status, etc.
  - Include nested inventory_profile / finance_profile JSON if we use separate tables.
- Inventory APIs
  - /api/v1/inventory/items/ can become a thin wrapper that returns stock data aggregated by
    budget_item_id.
  - Material Issue, Stock Movement, GRN endpoints load “items” via budget_item_code data.
- Services
  - Material Issue service cost calculations read valuation_rate from budget item.
  - Internal Requisitions store lines with { budget_item_id, quantity, uom } so the flow is budget-
    item-centric.
  - GL posting rules reference budget_item_id (no new table).

———

4. Frontend Alignment

- Use a single item selector (budget item dropdown) everywhere inventory data is needed.
  - Display both budgeting info (code/name/GL) and inventory info (stock UOM, batch flag).
  - Warn when required inventory metadata is missing (e.g., no valuation rate).
- Material Issue drawer, GRN line editor, Purchase Requisition, and Budgeting screens all pull from /
  api/v1/budgets/item-codes/?item_type=GOODS.
- Provide filters for services (item_type=SERVICE for taxes, rent, etc.) so the same catalog handles
  everything.
- When Material Issue needs a serialized item, the new flags (is_serial_tracked) inform the UI to show
  serial inputs.

———

5. Governance & Lifecycle

- Status field controls readiness:
  - PLANNING: Budgeting can prepare GL/meters but Inventory doesn’t issue stock.
  - APPROVED: Inventory can start issuing/receiving.
  - OBSOLETE: Item still referenced historically but can’t be used for new documents.
- Permissions:
  - Budgeting team can edit budget/finance fields.
  - Inventory team edits stock/valuation flags.
  - Implement serializers/forms that expose only relevant sections per role (via nested serializers
    or UI tabs).

———

6. Migration Strategy

- Since you’re starting fresh, no historical data migration is needed.
- Drop or mark as deprecated any references to inventory.Item.
- Update every FK/serializer to point to budget_item_id.
- Provide compatibility shims if other modules still expect /inventory/items/ responses (just proxy
  the budget item metadata plus stock data).

———

7. Rollout Plan

1. Extend BudgetItemCode schema + optional profiles with inventory fields.
1. Update Inventory models/services to use budget_item_id.
1. Adjust all APIs/serializers accordingly.
1. Replace frontend dropdowns/flows with the unified budget-item selector.
1. Run regression for IR → PO → GRN → Material Issue → Stock Movement flows.
