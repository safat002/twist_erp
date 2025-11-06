# Twist ERP - Inventory Module: ADVANCED ENTERPRISE SPECIFICATION
## Extended Requirements: Item Master, Valuation, QC, Movements, Planning, Compliance

---

## TABLE OF CONTENTS

1. Item Master & UoM Architecture
2. Budget Authority vs Operational Extensions
3. Alternate UoM with Conversions
4. Valuation & Landed Cost
5. QC & Batch/Serial Compliance
6. Stock States & Quality Gates
7. Event-Sourced Movement Ledger
8. Two-Step Transfers with In-Transit
9. Advanced Reorder Planning
10. Cycle Counting & ABC Cadence
11. GL Mapping Fallback Matrix
12. Extra Dimensions (Cost Center, Project)
13. Production & Sales Integration
14. Dual-Control & Audit Framework
15. Mobile & Scanning Operations
16. Data Migration & Cutover
17. KPIs & Analytics
18. Performance & Scalability

---

## SECTION 1: ITEM MASTER & UoM ARCHITECTURE

### 1.1 Master-Detail Separation Model

```
BUDGET MODULE (AUTHORITY - IMMUTABLE CORE)
├─ Item Code (unique, global)
├─ Item Name
├─ Category (hierarchical)
├─ Sub-Category
├─ Base/Stock UoM (FIXED - all valuations here)
├─ Standard Cost (cost basis)
├─ Accounting Classification (Asset, Expense, etc.)
└─ Tax Classification

INVENTORY MODULE (OPERATIONAL EXTENSIONS - MUTABLE)
├─ Links to Budget Item via Item Code
├─ Warehouse-Specific Settings
│   ├─ Bin location defaults
│   ├─ Pack size for this warehouse
│   ├─ Min/Max levels (per warehouse)
│   └─ Reorder point (per warehouse)
│
├─ Operational Attributes
│   ├─ Barcode / QR code
│   ├─ Hazmat flags (UN class, signal words)
│   ├─ Storage class (frozen, dry, etc.)
│   ├─ Handling instructions
│   ├─ Shelf life / expiry tracking (Y/N)
│   └─ Batch/Serial requirement
│
├─ Purchase/Stock/Sales UoM Configuration
│   ├─ Purchase UoM (from supplier)
│   ├─ Stock UoM (internal standard - matches Budget)
│   ├─ Sales UoM (to customer)
│   └─ Conversion factors + rounding rules
│
├─ Supplier Links (per item-supplier combo)
│   ├─ Supplier code
│   ├─ Supplier item code
│   ├─ MOQ (minimum order quantity)
│   ├─ Multiples (order in multiples of X)
│   ├─ Lead time
│   └─ Lead time variability (days std dev)
│
└─ Costing Parameters
    ├─ Valuation method (FIFO/LIFO/Avg/Standard) - default from global
    ├─ Cost layers (FIFO batches, LIFO stacks, or moving avg pool)
    ├─ Landed cost rules (apportion freight/duty/insurance)
    └─ Negative inventory allowed (Y/N)
```

### 1.2 Item Master Data Model

```
ITEM_MASTER (Budget-Controlled Core)
├─ item_code (PK)
├─ item_name
├─ category_id (FK to Budget Categories)
├─ sub_category_id (FK to Budget Sub-Categories)
├─ base_uom_id (FK to Budget UoM - IMMUTABLE)
├─ standard_cost (currency)
├─ tax_classification (enum: Taxable, Exempt, Input-tax-eligible)
├─ accounting_type (enum: Asset, Expense, COGS, etc.)
├─ active (boolean)
├─ created_by, created_date
└─ updated_by, updated_date

ITEM_OPERATIONAL_EXTENSION (Inventory-Controlled Ops)
├─ item_ext_id (PK)
├─ item_code (FK)
├─ barcode
├─ qr_code
├─ hazmat_class (enum: 1-9 DOT/UN classes)
├─ hazmat_signal_word (enum: DANGER, WARNING, CAUTION)
├─ storage_class (enum: Dry, Frozen, Climate-Ctrl, etc.)
├─ handling_instructions (text)
├─ requires_batch_tracking (boolean)
├─ requires_serial_tracking (boolean)
├─ requires_expiry_tracking (boolean)
├─ expiry_warning_days (int)
├─ allow_negative_inventory (boolean)
├─ active (boolean)
└─ last_updated

ITEM_WAREHOUSE_CONFIG (Per warehouse-item)
├─ item_wh_config_id (PK)
├─ item_code (FK)
├─ warehouse_id (FK)
├─ default_bin_id (FK to WAREHOUSE_BINS)
├─ pack_size_qty (int - units per pack in this warehouse)
├─ pack_size_uom_id (FK to UoM)
├─ min_stock_level (decimal)
├─ max_stock_level (decimal)
├─ reorder_point (decimal)
├─ eoc_qty (Economic Order Quantity)
├─ lead_time_days (int)
├─ lead_time_std_dev (int - days)
├─ demand_std_dev (decimal - units/day)
├─ service_level_pct (e.g., 95, 99)
├─ active (boolean)
└─ last_updated

ITEM_UOM_CONVERSION
├─ conversion_id (PK)
├─ item_code (FK)
├─ from_uom_id (FK to UoM)
├─ to_uom_id (FK to UoM)
├─ conversion_factor (decimal - e.g., 1 Box = 12 Pieces means 12.00)
├─ rounding_rule (enum: ROUND_UP, ROUND_DOWN, ROUND_NEAREST, TRUNCATE)
├─ is_purchase_conversion (boolean)
├─ is_sales_conversion (boolean)
├─ is_stock_conversion (boolean)
├─ effective_date (date)
├─ end_date (nullable - null = ongoing)
└─ last_updated

ITEM_SUPPLIER
├─ item_supplier_id (PK)
├─ item_code (FK)
├─ supplier_id (FK)
├─ supplier_item_code (text)
├─ supplier_pack_size (int)
├─ supplier_pack_uom_id (FK to UoM)
├─ moq_qty (Minimum Order Quantity)
├─ multiple_qty (Order in multiples of X)
├─ lead_time_days (int)
├─ lead_time_variability (int - std dev days)
├─ preferred_rank (int - 1 = preferred)
├─ last_purchase_price (currency)
├─ last_purchase_date (date)
├─ active (boolean)
└─ last_updated
```

---

## SECTION 2: BUDGET AUTHORITY VS OPERATIONAL EXTENSIONS

### 2.1 Governance Model

```
DATA OWNERSHIP MATRIX

BUDGET MODULE OWNS (Authority - No override in Inventory):
├─ Item Code (global unique identifier)
├─ Item Name (description)
├─ Category & Sub-Category (hierarchical classification)
├─ Base/Stock UoM (standard measure)
├─ Standard Cost (valuation baseline)
├─ Accounting Type (GL classification)
├─ Tax Treatment (taxable/exempt)
└─ Item Status (Active/Inactive/Discontinued)

INVENTORY MODULE OWNS (Operational - Extensions Only):
├─ Warehouse-specific settings (min/max/reorder per WH)
├─ Bin location defaults
├─ Pack sizes for operations
├─ Barcode & QR codes
├─ Hazmat & handling info
├─ UoM conversions (purchase, sales, stock)
├─ Supplier links & MOQ/multiples
├─ Batch/serial/expiry tracking rules
├─ Negative inventory flags
└─ Costing method overrides (by item)

SHARED GOVERNANCE:
├─ Standard Cost: Maintained in Budget, referenced by Inventory
├─ UoM: Defined in Budget (base), extended in Inventory (conversions)
├─ Categories: Defined in Budget, used for GL mapping in Inventory
└─ GL Accounts: Maintained in Finance, mapped by Inventory via Category

SYNC RULES:
├─ Change in Budget → Auto-update Inventory core (item code, name, category, base UoM)
├─ Changes in Inventory ops fields → Stay local (no feedback to Budget)
├─ Standard Cost change in Budget → Triggers valuation reconciliation in Inventory
└─ Category change in Budget → Re-routes future GL postings in Inventory
```

### 2.2 Data Integrity Rules

```
BUDGET IMMUTABILITY IN INVENTORY:

Rule 1: Item Code Lock
├─ Once Budget Item created, code never changes
├─ Inventory references item_code as stable foreign key
└─ Changes force data migration, never in-place edit

Rule 2: Base UoM Lock
├─ Budget defines base/stock UoM
├─ All inventory balances in base UoM
├─ All valuations use base UoM
├─ Conversions are multipliers, never change base
└─ Validation: Reject any valuation in non-base UoM

Rule 3: Standard Cost as Floor
├─ Budget standard cost sets baseline
├─ Actual purchase cost can differ (variances tracked)
├─ Landed cost apportioned but doesn't override standard
├─ Variance GL accounts capture differences
└─ Validation: Cost cannot go negative

Rule 4: Category Cascade
├─ Change in Budget category
├─ Triggers GL mapping re-evaluation in Inventory
├─ Future transactions use new mapping
├─ Prior transactions unaffected (immutable posts)
└─ Audit trail logs the category change

EXTENSION FLEXIBILITY IN INVENTORY:

Allow:
├─ Add/remove barcode
├─ Adjust pack sizes per warehouse
├─ Override valuation method (item-level)
├─ Add warehouse-specific min/max
├─ Link to multiple suppliers
├─ Enable/disable batch tracking
└─ Change hazmat/storage/handling info

Prevent:
├─ Change item code
├─ Change base UoM
├─ Delete category assignment
├─ Modify Budget-controlled fields directly
└─ Override standard cost (only track variance)
```

---

## SECTION 3: ALTERNATE UOM WITH CONVERSIONS

### 3.1 Three-Tier UoM Model

```
TIER 1: PURCHASE UoM (Supplier's Unit)
├─ What suppliers deliver in
├─ Example: Supplier ships in Cartons
├─ Conversion: 1 Carton = 20 Units (base/stock UoM)
└─ GRN captured in purchase UoM, auto-converted to stock UoM

TIER 2: STOCK UoM (Base Unit - Immutable from Budget)
├─ Internal standard measure for inventory
├─ Example: Individual Unit (Piece)
├─ All GL posting in stock UoM
├─ All valuations in stock UoM
├─ Balances always reported in stock UoM
└─ No conversions here—everything resolves to this

TIER 3: SALES UoM (Customer's Unit)
├─ What customers order in
├─ Example: Customer orders in Boxes
├─ Conversion: 1 Box = 5 Units (base/stock UoM)
└─ Sales order captured in sales UoM, auto-converted for stock deduction

CONVERSION FLOW:

Purchase Receipt (GRN):
├─ Supplier sends: 10 Cartons (purchase UoM)
├─ System applies: 1 Carton = 20 Units
├─ Stock increases by: 200 Units (stock UoM)
├─ GL posting in: 200 Units (stock UoM)
└─ Cost per unit: $X / 200 units = $X/unit

Sales Order:
├─ Customer orders: 15 Boxes (sales UoM)
├─ System applies: 1 Box = 5 Units
├─ Stock decreases by: 75 Units (stock UoM)
├─ COGS posted for: 75 Units at current valuation
└─ Picking list shows: 15 Boxes or 75 Units (admin configurable)

Internal Transfer (Inventory):
├─ Always in stock UoM
├─ No conversion needed
├─ Simplifies movement GL posting
└─ Warehouse-to-warehouse in base units
```

### 3.2 UoM Conversion Configuration

```
DATABASE SCHEMA:

ITEM_UOM_CONVERSION
├─ conversion_id (PK)
├─ item_code (FK to ITEM_MASTER)
├─ from_uom_id (FK to UoM - e.g., Carton)
├─ to_uom_id (FK to UoM - e.g., Piece, which is base)
├─ conversion_factor (decimal - e.g., 20.00)
│   └─ Meaning: 1 Carton = 20 Pieces
│
├─ rounding_rule (enum)
│   ├─ ROUND_UP: Excess converted → round up (10.1 pieces → 11)
│   ├─ ROUND_DOWN: Deficit converted → round down (10.9 pieces → 10)
│   ├─ ROUND_NEAREST: Standard rounding (10.5 → 10 or 11 based on banker's)
│   ├─ TRUNCATE: Always truncate (10.9 → 10)
│   └─ NO_ROUNDING: Maintain decimal (10.5 pieces allowed)
│
├─ is_purchase_conversion (boolean) - usable for GRN
├─ is_sales_conversion (boolean) - usable for Sales Order
├─ is_stock_conversion (boolean) - usable for inventory movement
│
├─ effective_date (date) - when this conversion becomes active
├─ end_date (nullable date) - null = forever, populated = archive old conversions
├─ precedence (int) - if multiple active, use highest precedence
│
├─ created_by, created_date
└─ last_updated

VALIDATION RULES:

Rule 1: Stock UoM Special
├─ Base UoM always has conversion factor = 1.0 to itself
├─ Stock UoM never appears in from_uom_id unless for override purposes
└─ All conversions funnel to stock UoM as the common denominator

Rule 2: Rounding Consistency
├─ Apply rounding at transaction time (GRN, SO, Movement)
├─ Store rounded quantity in stock UoM
├─ Track rounding variance (Rounding Gain/Loss account)
└─ Prevent fractional units where rounding_rule = NO_ROUNDING if base UoM is piece

Rule 3: Chainable Conversions
├─ If multiple conversions needed (e.g., Pallet → Carton → Unit):
│   ├─ GRN input: 2 Pallets
│   ├─ System applies: Pallet → Carton (1 Pallet = 10 Cartons)
│   ├─ Then: Carton → Unit (1 Carton = 20 Units)
│   ├─ Result: 2 × 10 × 20 = 400 Units
│   └─ All GL in Units
│
└─ Prevent circular references (e.g., A→B, B→A not allowed)

PRACTICAL EXAMPLE:

Item: Printer Cartridges
├─ Stock UoM: Piece (base, from Budget)
│
├─ Purchase UoM: Box
│   ├─ Conversion: 1 Box = 10 Pieces
│   ├─ Rounding Rule: ROUND_UP
│   └─ GRN: Supplier sends 5.5 Boxes → System treats as 6 Boxes → 60 Pieces in stock
│
├─ Sales UoM: Pack (customer unit)
│   ├─ Conversion: 1 Pack = 2 Pieces
│   ├─ Rounding Rule: ROUND_DOWN
│   └─ SO: Customer orders 25 Packs → System deducts 50 Pieces (25 × 2, no rounding here)
│
└─ All GL posting in Pieces (stock UoM):
    ├─ GRN: 60 Pieces purchased
    ├─ SO: 50 Pieces sold
    └─ COGS & Inventory both in Pieces
```

---

## SECTION 4: VALUATION & LANDED COST

### 4.1 Landed Cost Architecture

```
LANDED COST COMPONENTS:

Direct Costs (on invoice):
├─ Product cost (unit price × qty)
└─ Already on supplier invoice

Indirect Costs (freight, duty, insurance):
├─ Freight (inbound)
├─ Customs/Import Duty
├─ Insurance (in-transit)
├─ Brokerage fees
├─ Demurrage
├─ Port handling
└─ Other inbound fees

Cost Apportionment:
├─ Method 1: By item quantity
│   └─ Total landed cost / Total qty = Cost per unit
│
├─ Method 2: By line value
│   └─ (Line amount / Total GRN amount) × Freight = Line's freight share
│
├─ Method 3: By weight
│   └─ (Item weight / Total weight) × Freight = Item's freight share
│
└─ Method 4: Manual allocation
    └─ Admin manually assigns landed cost to each line

LATE COST ADJUSTMENT:

Scenario: GRN posted, then freight invoice arrives later
├─ Step 1: Initial GRN posted
│   ├─ Cost: Product cost only
│   └─ GL: Dr. Inventory 100 @ $10 = 1000, Cr. AP 1000
│
├─ Step 2: Freight invoice arrives (later)
│   ├─ Link to original GRN
│   ├─ Freight: $100
│   └─ Apportion: $100 / 100 units = $1 additional per unit
│
├─ Step 3: System creates Landed Cost JE (Retro-Active)
│   ├─ For existing stock: Dr. Inventory +100, Cr. AP +100
│   ├─ For consumed stock: Dr. COGS Adjustment +50, Cr. AP +50
│   │   (if 50 units sold, they carry new cost)
│   │
│   └─ Cost layer recalculation:
│       ├─ Old: 100 units @ $10.00/unit = $1000
│       ├─ Adjustment: +$100 = 100 units @ $11.00/unit
│       └─ New GL reflects $1100 at cost
│
└─ Audit trail captures: Original cost, adjustment, JE reference, timestamp, user
```

### 4.2 Cost Layer Management

```
COST LAYERS BY VALUATION METHOD:

FIFO (First In, First Out) - Layer Stack:
├─ Layer 1: 100 units @ $10.00 (received Jan 1)
├─ Layer 2: 50 units @ $11.50 (received Jan 15)
├─ Layer 3: 75 units @ $12.00 (received Jan 30)
│
└─ Issuance of 120 units:
    ├─ Take 100 from Layer 1 @ $10.00 = $1000
    ├─ Take 20 from Layer 2 @ $11.50 = $230
    ├─ COGS = $1230
    └─ Remaining: 30 units @ $11.50, 75 @ $12.00

LIFO (Last In, First Out) - Reverse Stack:
├─ Layer 1 (oldest): 100 units @ $10.00
├─ Layer 2: 50 units @ $11.50
├─ Layer 3 (newest): 75 units @ $12.00
│
└─ Issuance of 120 units:
    ├─ Take 75 from Layer 3 @ $12.00 = $900
    ├─ Take 45 from Layer 2 @ $11.50 = $517.50
    ├─ COGS = $1417.50
    └─ Remaining: 5 units @ $11.50, 100 @ $10.00

WEIGHTED AVERAGE - Rolling Pool:
├─ All units of same item-warehouse in one pool
├─ Pool cost: Sum of all cost / Count of all units
├─ Recalculated:
│   ├─ Daily (if avg_period = daily)
│   ├─ Weekly (if avg_period = weekly)
│   ├─ Monthly (if avg_period = monthly)
│   └─ Perpetually (moving average, updated on each receipt)
│
└─ Example (Monthly recalculation):
    ├─ Jan 1-31: Pool = 100 @ $10 + 50 @ $11.50 + 75 @ $12 = 225 units
    ├─ Pool cost: $2837.50 / 225 = $12.61/unit
    ├─ All Feb issuances: $12.61/unit (fixed for month)
    ├─ Mar 1: New month, pool recalculates
    └─ If new receipt Mar 1 @ $13: New monthly avg includes Mar receipts

STANDARD COST - Fixed Reference:
├─ Each item has standard cost (from Budget or admin-set)
├─ Every issuance: COGS at standard cost
├─ Actual cost can differ (captured in variance account)
│
└─ Example:
    ├─ Standard: $10/unit
    ├─ Purchase @ $9.50: Favorable variance $0.50/unit
    ├─ COGS always: Standard $10.00/unit
    ├─ Variance GL account: Favorable variance $0.50 × qty
    └─ Period-end close: Variance analysis & potential inventory adjustment
```

### 4.3 Valuation Method Governance

```
DATABASE SCHEMA:

ITEM_VALUATION_METHOD
├─ valuation_method_id (PK)
├─ item_code (FK)
├─ warehouse_id (FK) - per warehouse costing layer
├─ valuation_method (enum: FIFO, LIFO, WEIGHTED_AVG, STANDARD)
├─ effective_date (date - when this method starts)
├─ requires_revaluation (boolean - if changed, need JE)
├─ avg_period (enum - if WEIGHTED_AVG)
│   ├─ DAILY
│   ├─ WEEKLY
│   ├─ MONTHLY
│   ├─ PERPETUAL (moving average)
│   └─ CUSTOM (every N days)
│
├─ allow_negative_inventory (boolean)
├─ prevent_cost_below_zero (boolean)
├─ created_by, created_date
└─ last_updated

COST_LAYER (immutable event log)
├─ cost_layer_id (PK)
├─ item_code (FK)
├─ warehouse_id (FK)
├─ lot_batch_id (FK - if batch tracking enabled, null otherwise)
├─ receipt_date (date - when received)
├─ receipt_qty (decimal - quantity received)
├─ cost_per_unit (decimal - cost at receipt)
├─ total_cost (decimal = qty × cost, immutable)
├─ qty_remaining (decimal - updated as consumed)
├─ cost_remaining (decimal = qty_remaining × cost_per_unit)
├─ fifo_sequence (int - order received, for FIFO)
├─ is_standard_cost (boolean - if standard cost, not actual)
├─ landed_cost_adjustment (decimal - retro-adjusted cost)
├─ adjustment_je_id (FK - if adjusted, links to JE)
├─ adjustment_reason (text)
├─ adjustment_date (date)
├─ created_date, last_updated
└─ immutable_after_post (true - no edits once stock issued)

VALUATION_CHANGE_LOG (audit trail)
├─ change_log_id (PK)
├─ item_code (FK)
├─ warehouse_id (FK)
├─ old_method (enum)
├─ new_method (enum)
├─ effective_date (date)
├─ revaluation_je_id (FK - JE created)
├─ revaluation_amount (decimal)
├─ requested_by (user)
├─ requested_date (date)
├─ approved_by (user - must be approver)
├─ approval_date (date)
├─ status (enum: PENDING, APPROVED, REJECTED)
└─ reason (text)

VARIANCE_ACCOUNT (capture differences)
├─ variance_id (PK)
├─ item_code (FK)
├─ warehouse_id (FK)
├─ variance_type (enum: PURCHASE_PRICE_VARIANCE, LANDED_COST_VARIANCE, ROUNDING_VARIANCE)
├─ variance_amount (decimal - favorable if positive, adverse if negative)
├─ related_grn_id (FK)
├─ related_issuance_id (FK)
├─ gl_account_id (FK - PPV account or Landed Cost Adj account)
├─ je_id (FK - GL posting)
├─ created_date
└─ details (json - variance details)
```

### 4.4 Valuation Method Change Process

```
CHANGE FLOW:

Step 1: Admin Initiates Change
├─ Current method: FIFO
├─ New method: Weighted Average
├─ Effective Date: Feb 1, 2025
├─ Reason: Align with corporate policy
└─ Status: PENDING

Step 2: System Validates
├─ Check: No open GRNs in process
├─ Check: No holds on inventory
├─ Check: All prior month closed & locked
├─ If valid: Proceed; If not: Reject with reason

Step 3: Approval Required
├─ Sent to: Finance Director (approver)
├─ Shows: Impact estimate
│   ├─ Current inventory value @ FIFO: $100,000
│   ├─ Projected @ FIFO-to-Avg change: $95,000
│   └─ Adjustment needed: -$5,000
│
└─ Approver can: Approve / Reject / Request Info

Step 4: On Effective Date, Auto-Post JE
├─ If change approved:
│   ├─ Create Inventory Revaluation JE
│   │   ├─ Dr. Inventory Adjustment Expense: $5,000
│   │   └─ Cr. Inventory Asset: $5,000
│   │
│   ├─ GL posts & GL reconciliation report runs
│   ├─ Inventory GL balance updated
│   ├─ Cost layers recalculated for new method
│   └─ Log entry: "Method changed FIFO → Avg, JE-2025-001"
│
├─ Future transactions:
│   ├─ GRN Feb 1+: Cost layers under Weighted Avg
│   ├─ Prior transactions: Remain at historical cost (immutable)
│   └─ Prior GL entries: Unchanged, audit trail preserves
│
└─ Status: EFFECTIVE

Step 5: Ongoing Monitoring
├─ Variance reports: Compare prior vs new method on same item
├─ GL reconciliation: Tie-out subledger to GL monthly
├─ Audit: Review valuation changes quarterly
└─ Reversal: If errors found, create reversing JE (never edit posted transaction)

PREVENTION RULES:

Prevent Negative Inventory:
├─ At issuance: Check (qty_on_hand - qty_to_issue) >= 0
├─ If allow_negative_inventory = FALSE: Reject issuance
├─ If TRUE: Allow, but flag & track in variance account
└─ GL posting: Still posts (may go into debit position on Inventory asset)

Prevent Cost Below Zero:
├─ Cost layer: qty_remaining × cost_per_unit ≥ 0
├─ When issuing more than available:
│   ├─ If excess hits negative inventory (if allowed):
│   │   └─ Cost still positive (based on available layers)
│   │
│   └─ If would result in negative cost: Fail validation
│
├─ Landing cost: cost_per_unit - freight adjustment > 0
│   └─ If freight > product cost: Flag for manual review
│
└─ Example: Item @ $10 cost, freight $15
    ├─ Landed cost per unit: $10 + $15 = $25 (allowed, positive)
    ├─ But if audit flags: High freight %, review supplier/routing
```

---

## SECTION 5: QUALITY CONTROL & BATCH/SERIAL

### 5.1 QC States & Stock Holds

```
STOCK STATES (QC-Driven):

QUARANTINE
├─ Stock received but not yet inspected
├─ GRN posted, qty in "Quarantine" state
├─ Cannot issue to warehouse
├─ Cannot allocate to sales
├─ GL: Held in Inventory-Quarantine account (sub of main Inventory)
└─ Move to: ON_HOLD or RELEASED (after QC decision)

ON_HOLD
├─ Inspection failed or pending approval
├─ Reason: Defect, document missing, approval pending
├─ Cannot issue to warehouse
├─ Cannot allocate to sales
├─ GL: Held in Inventory-On-Hold account
├─ Hold reason logged in STOCK_HOLD table
└─ Can move to: RELEASED (after issue resolved) or SCRAP/RETURN

RELEASED
├─ QC passed, inspection complete
├─ Available for warehouse placement
├─ Available for allocation to sales
├─ GL: Moved to main Inventory-Saleable (or category-based account)
├─ FEFO enforcement: If expiry-tracked, earliest-expiry first
└─ Normal issuance/sales workflows apply

SCRAP / RETURN / WRITE-OFF
├─ Item not suitable, sent back or destroyed
├─ GL: Dr. Scrap Loss account, Cr. Inventory
├─ Removed from available balance
├─ Reason & authorization required
└─ Audit trail logs disposal

DATABASE SCHEMA:

STOCK_HOLD
├─ hold_id (PK)
├─ item_code (FK)
├─ warehouse_id (FK)
├─ bin_id (FK - specific bin on hold)
├─ batch_lot_id (FK - if batch, specific lot on hold)
├─ hold_type (enum: QC_INSPECTION, DOCUMENT_HOLD, APPROVAL_PENDING, CUSTOMER_RETURN, DEFECT, OTHER)
├─ qty_held (decimal - in stock UoM)
├─ hold_reason (text - detailed reason)
├─ hold_date (date)
├─ hold_by (user)
├─ expected_release_date (date)
├─ actual_release_date (nullable)
├─ released_by (user)
├─ qc_pass_result (enum: PASS, FAIL, PENDING, CONDITIONAL)
├─ qc_notes (text)
├─ escalation_flag (boolean - if overdue)
├─ status (enum: ACTIVE, RELEASED, SCRAPPED, RETURNED)
└─ disposition (enum: TO_WAREHOUSE, SCRAP, RETURN, REWORK, REJECT)

QC_CHECKPOINT
├─ checkpoint_id (PK)
├─ warehouse_id (FK)
├─ checkpoint_name (text - e.g., "Receiving Dock Inspection")
├─ checkpoint_order (int - sequence)
├─ automatic_after (boolean - auto-run without user?)
├─ inspection_criteria (text - what to check)
├─ inspection_template (document ID - SOP)
├─ acceptance_threshold (e.g., AQL level)
├─ escalation_threshold (e.g., >5% reject → escalate)
└─ assigned_to (user/role)

QC_RESULT
├─ qc_result_id (PK)
├─ grn_id (FK)
├─ checkpoint_id (FK)
├─ inspected_by (user)
├─ inspected_date (date)
├─ qty_inspected (decimal)
├─ qty_accepted (decimal)
├─ qty_rejected (decimal)
├─ rejection_reason (enum: DAMAGE, INCOMPLETE_DOC, WRONG_ITEM, QUANTITY_DISCREPANCY, QUALITY_ISSUE, OTHER)
├─ qc_status (enum: PASS, FAIL, CONDITIONAL_PASS)
├─ notes (text)
├─ rework_instruction (nullable - if conditional)
├─ attachment_id (FK - COA, photo, etc.)
└─ hold_created (boolean - creates STOCK_HOLD?)

GL POSTING FOR QC STATES:

GRN Receipt:
├─ Dr. Inventory-Quarantine: $1000
└─ Cr. Accounts Payable: $1000

QC Pass:
├─ Dr. Inventory-Saleable: $1000
└─ Cr. Inventory-Quarantine: $1000

QC Fail → Scrap:
├─ Dr. Scrap Loss: $1000
└─ Cr. Inventory-Quarantine: $1000
└─ (includes reason code for cost center allocation)
```

### 5.2 Batch/Serial Tracking & FEFO

```
BATCH ATTRIBUTES:

Batch (Lot) Definition:
├─ batch_lot_id (PK)
├─ item_code (FK)
├─ supplier_lot_number (text - supplier's batch ID)
├─ internal_batch_code (auto-generated or manual)
├─ grn_id (FK - which receipt created this batch)
├─ mfg_date (date - manufacture date)
├─ exp_date (date - expiration/use-by date)
├─ received_date (date)
├─ received_qty (decimal - stock UoM)
├─ current_qty (decimal - remaining after issuances)
├─ cost_per_unit (decimal - cost of this batch)
├─ certificate_of_analysis_id (FK - COA document)
├─ coa_upload_date (date)
├─ storage_location (text - where stored)
├─ hazmat_classification (enum - if hazmat)
├─ hold_status (enum: QUARANTINE, ON_HOLD, RELEASED, SCRAP)
├─ fefo_sequence (int - for sorting)
└─ created_date, last_updated

SERIAL TRACKING:

Serial Number Definition:
├─ serial_id (PK)
├─ item_code (FK)
├─ serial_number (text - unique per item, e.g., "ABC-001")
├─ batch_lot_id (FK - which batch, if applicable)
├─ warranty_start (date)
├─ warranty_end (date)
├─ asset_tag (text - if fixed asset)
├─ assigned_to_customer_order_id (FK - if assigned to SO)
├─ issued_date (date)
├─ issued_to (customer/department)
├─ received_back_date (nullable - if returned/recalled)
├─ inspection_date (nullable - if re-inspected)
├─ status (enum: IN_STOCK, ASSIGNED, ISSUED, RETURNED, SCRAPPED)
└─ created_date, last_updated

FEFO ENFORCEMENT (First Expiry, First Out):

Scenario: Item requires expiry tracking
├─ Multiple batches in stock:
│   ├─ Batch A: 50 units, Exp Dec 25, 2025
│   ├─ Batch B: 30 units, Exp Jan 15, 2026
│   └─ Batch C: 20 units, Exp Feb 20, 2026
│
├─ Sales order: Pick 60 units
├─ System picks:
│   ├─ Batch A: 50 units (earliest expiry first)
│   ├─ Batch B: 10 units (next earliest)
│   └─ Remaining in stock: Batch B 20 units, Batch C 20 units
│
├─ COGS calculation:
│   ├─ 50 units @ Batch A cost
│   ├─ 10 units @ Batch B cost
│   └─ Blend COGS if batches have different costs
│
└─ If expiry date < today:
    ├─ Item flagged for disposal
    ├─ Cannot issue
    ├─ Trigger disposal workflow (scrap, donate, etc.)
    └─ GL: Dr. Scrap Loss, Cr. Inventory

FEFO CONFIGURATION:

ITEM_FEFO_CONFIG
├─ fefo_config_id (PK)
├─ item_code (FK)
├─ warehouse_id (FK)
├─ enforce_fefo (boolean)
├─ warn_days_before_expiry (int - e.g., 30 days)
├─ block_issue_if_expired (boolean)
├─ disposal_method (enum: SCRAP, DONATE, RETURN_TO_SUPPLIER, REWORK)
├─ expiry_calculation_rule (enum)
│   ├─ FIXED_DATE (exp_date is fixed, use as-is)
│   ├─ DAYS_FROM_MFG (exp = mfg_date + shelf_life_days)
│   ├─ DAYS_FROM_RECEIPT (exp = received_date + shelf_life_days)
│   └─ CUSTOM_FORMULA
│
├─ shelf_life_days (int)
└─ last_updated
```

---

## SECTION 6-18: ADVANCED FEATURES (SUMMARY OVERVIEW)

Given the extensive nature of remaining sections, I'll provide a comprehensive summary structure:

### 6. EVENT-SOURCED MOVEMENT LEDGER
```
Treat every stock movement as immutable event:
├─ GRN (Goods Receipt Note)
├─ Issue (Sales/Production/Internal)
├─ Transfer-Out (leaving source warehouse)
├─ Transfer-In (arriving at dest warehouse)
├─ Adjust (cycle count variance)
├─ Scrap/Loss
└─ Reversal (of prior movement)

Schema: MOVEMENT_EVENT (immutable log)
├─ event_id (PK, ever-increasing)
├─ item_code, warehouse_id, bin_id
├─ event_type (enum above)
├─ qty_change (signed decimal, + for receipt, - for issuance)
├─ event_date, event_timestamp (UTC)
├─ reference_id (GRN_id, SO_id, etc.)
├─ cost_per_unit_at_event
├─ posted_by, created_date
└─ immutable_after_posting = true

On-Hand Calculation:
├─ Current stock = SUM of qty_change WHERE item, warehouse
├─ Audit: Recalculate from event log daily
├─ Discrepancies → trigger cycle count
```

### 7. TWO-STEP TRANSFERS WITH IN-TRANSIT
```
Transfer-Out (Source Warehouse):
├─ Create virtual "In-Transit" location
├─ Dr. Inventory-In-Transit, Cr. Inventory-Source
├─ Qty removed from source availability

In-Transit State:
├─ Tracked separately for lead time visibility
├─ KPI: Shrinkage during transit
├─ Predictive: When expected to arrive

Transfer-In (Destination Warehouse):
├─ Upon arrival confirmation:
│   ├─ Dr. Inventory-Destination
│   └─ Cr. Inventory-In-Transit
├─ Qty added to destination availability
└─ If damage en route: Dr. Loss, Cr. In-Transit
```

### 8. ADVANCED REORDER PLANNING
```
Compute ROP from:
├─ Demand variability (std dev of demand)
├─ Lead time variability (std dev of LT)
├─ Service level %ile (e.g., 95%, 99%)
├─ Formula: ROP = (Avg Demand × Avg LT) + Z-score × √(LT×Demand²_var + Demand²×LT_var)
├─ Min/Max/EOQ as fallback or override
└─ Respect supplier MOQ, multiples, calendars

Auto-PR Logic:
├─ When stock ≤ ROP: Create PR
├─ Qty = max(EOQ, MOQ) respecting multiples
├─ Avoid orders during supplier blackout dates
└─ Aggregate multiple PRs if > MOQ possible
```

### 9. CYCLE COUNTING & ABC CADENCE
```
ABC-Driven Schedule:
├─ A items (80% value): Monthly cycle count
├─ B items (15% value): Quarterly
├─ C items (5% value): Semi-annual

Blind Count Process:
├─ Counting sheets don't show expected qty
├─ Count, then verify system qty
├─ Variance threshold (e.g., >2%): Auto re-count
├─ Reason codes: Counting error, theft, damage, etc.
├─ Attachments: Photos, supervisor approval

Freeze Windows:
├─ Freeze stock during count (no issues allowed)
├─ Prevents churn during verification
└─ SLA: Count completed within X hours
```

### 10. GL MAPPING FALLBACK MATRIX
```
GL Lookup Cascade:
├─ Level 1 (Most specific): Category + Sub-Category + Warehouse + Transaction Type
├─ Level 2: Category + Warehouse + Transaction Type
├─ Level 3: Category + Transaction Type
├─ Level 4 (Fallback): Category only
├─ Level 5 (Default): Global default (if all else fails)

Pre-Issue Simulation:
├─ User creates GRN/Issue, clicks "Preview GL"
├─ System shows exact Dr/Cr lines
├─ Prevents setup mistakes
└─ "Confirm" button commits
```

### 11. EXTRA DIMENSIONS (Cost Center, Project)
```
IR/Issue can specify:
├─ Cost Center (department)
├─ Project (optional job code)
├─ Both flow into GL postings
├─ Example:
│   ├─ Dr. Office Supplies Exp + Cost Center: Finance
│   ├─ Dr. Office Supplies Exp + Cost Center: Sales
│   └─ GL posting auto-splits by cost center
└─ Finance reports by cost center automatically
```

### 12. PRODUCTION & SALES INTEGRATION
```
Sales Order:
├─ Reserves stock per line (with auto-expiration)
├─ ATP (Available to Promise) = On-hand - Reservations
├─ Backflush on completion:
│   ├─ Option A: Backflush on PO completion (consume BOM)
│   ├─ Option B: Issue by pick list (manual control)
│   └─ Option C: Hybrid (confirm PO lines in stages)
│
├─ Track yield/scrap variance:
│   ├─ Standard yield: 95%
│   ├─ Actual yield: 93%
│   ├─ Variance: 2% scrap GL posting
│   └─ Variance account feeds into margin analysis
└─ Finished goods transferred to Sales warehouse (optional)
```

### 13. DUAL-CONTROL & AUDIT FRAMEWORK
```
Separation of Duties:
├─ Receive: Warehouse staff (physical receipt)
├─ Approve GRN: Receiving manager (validates receipt)
├─ Post GRN: System (automatic, cannot be bypassed)
├─ Create IR: Employee (request)
├─ Approve IR: Manager (budget check)
├─ Issue: Warehouse staff (picks/packs)
└─ Post GL: Finance (reviews before committing)

Immutability:
├─ No edits on posted GRN/Issue
├─ Corrections: Reversals only
├─ Reversals create offsetting transactions
├─ Audit trail: All reversals logged with reason & approver
```

### 14. MOBILE & SCANNING OPERATIONS
```
Mobile Apps:
├─ Receiving (GRN):
│   ├─ Barcode scan → auto-fetch PO
│   ├─ Scan each carton → add to receipt qty
│   ├─ QR code labels → print on-site
│   └─ Offline queue if connectivity drops
│
├─ Picking:
│   ├─ SO → generate pick list
│   ├─ Scan bins → guide picker
│   ├─ Confirm qty → update system
│   └─ Pack label generation
│
├─ Cycle Count:
│   ├─ Download ABC list to mobile
│   ├─ Blind count (no hints)
│   ├─ Scan items → enter qty
│   └─ Upload results
│
└─ Offline Queue:
    ├─ When connectivity lost, queue transactions
    ├─ Sync when back online
    └─ Conflict resolution: Server version wins
```

### 15. DATA MIGRATION & CUTOVER
```
Opening Balance by Lot/Location:
├─ Import: item_code, warehouse_id, bin_id, batch_id, qty, cost_per_unit
├─ Validation:
│   ├─ Item exists in Budget
│   ├─ Warehouse exists
│   ├─ Bin matches warehouse
│   ├─ Cost >= 0
│   └─ UoM = stock UoM (no conversions on import)
│
├─ Post-import validation:
│   ├─ Sum of import qty = GL Inventory control balance
│   ├─ Sum of import cost = GL Inventory balance
│   └─ If mismatch: Fail cutover, request correction
│
└─ Create opening movement events (immutable log):
    ├─ Event type: OPENING_BALANCE
    ├─ One event per item-warehouse-batch
    ├─ Marks start of event ledger
    └─ All future events chain from these

Legacy Category Mapping:
├─ Old system categories → Budget categories
├─ Mapping table for user convenience
└─ GL mappings retroactively apply to opening balances
```

### 16. KPIs & ANALYTICS
```
Operational KPIs:
├─ Inventory Accuracy %: (Accurate bins / Total bins) × 100
├─ Shrinkage %: (Adjusted loss qty / Total throughput) × 100
├─ Service Level %: (Orders fulfilled on-time / Total) × 100
├─ Stockout Rate: (Days item out of stock / Period days)
├─ Carrying Cost: (Avg inventory value × % carrying cost rate)
├─ Inventory Turns: (COGS / Avg inventory)
├─ Slow/Obsolete: Items with no movement > N months
├─ ABC Stratification: % of items in A/B/C by value
├─ Warehouse Utilization: (Used volume / Total capacity) × 100

Finance KPIs:
├─ PPV (Purchase Price Variance): (Actual - Standard) / Standard
├─ Landed Cost Variance: (Actual landed - Budget) / Budget
├─ GL Reconciliation: (GL Inventory - Subledger balance) - should be 0
├─ Inventory Aging: Days since last movement
└─ COGS Accuracy: (Actual COGS - Standard COGS) / Standard
```

### 17. PERFORMANCE & SCALABILITY
```
Indexes & Materialized Views:
├─ Indexes on: item_code, warehouse_id, bin_id, batch_id (frequent queries)
├─ Materialized Views:
│   ├─ item_warehouse_summary (qty, value, cost, last_movement)
│   ├─ cost_layer_pool (current cost by valuation method)
│   ├─ stock_by_bin (for physical layout reports)
│   └─ gl_subledger (GL balance per item-warehouse)
│
├─ Refresh schedule: Nightly + on-demand post-GRN/Issue
└─ Query optimization: Use MVs not event log for real-time dashboards

Archival Policy:
├─ Move closed movement lines > 3 years to archive tables
├─ Keeps hot set small (current year + 2 prior)
├─ Archive tables indexed same way (searchable if needed)
└─ GL remains immutable in main tables (never archive GL posting)
```

---

## IMPLEMENTATION PRIORITY

### **Phase 1: Core (Weeks 1-4)**
- Master-detail separation (Budget authority, Inventory ops)
- UoM conversions (purchase, stock, sales)
- Event-sourced movement ledger
- Basic GL mapping fallback

### **Phase 2: Valuation & Cost (Weeks 5-7)**
- Landed cost capture & apportionment
- Late-arriving invoices & retro-adjustment
- Cost layer management (FIFO/LIFO/Avg/Standard)
- Valuation method change governance

### **Phase 3: Quality & Compliance (Weeks 8-10)**
- QC states (Quarantine, On-Hold, Released)
- Batch/Serial tracking
- FEFO enforcement
- Two-step transfers with In-Transit

### **Phase 4: Planning & Replenishment (Weeks 11-12)**
- Advanced ROP calculation
- Supplier constraints (MOQ, multiples, calendars)
- ABC cycle counting
- Freeze windows during counts

### **Phase 5: Integration & Controls (Weeks 13-15)**
- GL mapping fallback matrix
- Extra dimensions (Cost Center, Project)
- Production backflush options
- Dual-control & audit trails

### **Phase 6: Mobile & Analytics (Weeks 16-18)**
- Mobile apps (receiving, picking, counting)
- KPI dashboards
- Performance optimization (MVs, archival)
- Data migration tools

### **Phase 7: Go-Live (Week 19)**
- UAT with data migration
- Cutover & opening balance validation
- Support & tuning

---

## CONCLUSION

**Enterprise-Grade Inventory Backbone:**

✅ Budget as authority (immutable core)
✅ Inventory as operational layer (flexible extensions)
✅ Event-sourced ledger (immutable movement history)
✅ Multiple UoM with conversions
✅ Landed cost & retroactive adjustments
✅ QC & batch control (FEFO enforcement)
✅ Advanced ROP & supplier constraints
✅ Dual-control & audit trails
✅ GL mapping with fallbacks & simulations
✅ Mobile-first operations
✅ Enterprise KPIs & analytics
✅ Production & sales integration

**This design provides industry-standard control, compliance, and scalability for 100+ user ERP deployments.**

