going to treat this as a platform feature, not a one-off, so you can keep adding modules (microfinance, NGO, Manufacturing, Budget, etc.) and they all get IDs/codes the same way.

---

# Twist ERP – Automatic ID & Code Generation (Final Plan)

## 0. Goals

1. **No manual ID/codes** — devs and users should not invent permission codes, menu keys, or API paths.
2. **Deterministic** — the same model always produces the same IDs.
3. **Tenant-aware** — document numbers and sequences must be per company/tenant.
4. **Cross-layer aligned** — backend, frontend, BI, and the visual data model all reference the _same_ IDs.
5. **Regenerable** — when codegen is re-run, it updates IDs, not duplicate them.

---

## 1. ID / Code Taxonomy

We define 6 kinds of IDs:

1. **System Codes** – for permissions, routes, menus

   - string-based
   - deterministic
   - global
   - e.g. `finance_create_journal_voucher`

2. **API Paths** – for REST endpoints

   - deterministic from app + model
   - e.g. `/api/finance/journal-vouchers/`

3. **UI Keys** – for menus & route registry

   - e.g. `finance-journal-vouchers`

4. **Metadata IDs** – for visual data model (tables, columns, relationships)

   - e.g. `fin_journal_voucher`, `fin_journal_voucher_line`

5. **Business Document Numbers** – human-facing doc numbers

   - e.g. `JV-25-000123`, `PO-25-000887`
   - **per company** and **per doc type**

6. **Ad-hoc / User-Added Field IDs** – created during imports / schema auto-extend

   - e.g. `fld_fin_journal_voucher_extra_color_code`

Everything we generate must fall into one of these buckets.

---

## 2. Core Components to Build

We will build 4 small platform services/utilities:

1. **Code/Name Factory** (`core.id_factory`)
2. **Permission Sync & Generator** (`security.sync_permissions`)
3. **Document Numbering Service** (`core.doc_sequence`)
4. **Metadata Registration Service** (for visual DM & BI) (`metadata.register_model(...)`)

These 4 will be called by:

- code generator
- Django apps on startup
- import/migration engine
- UI module builder

---

## 3. Component 1: Code / Name Factory

**File:** `core/id_factory.py`

**Responsibilities:**

1. Make permission codes

   ```python
   def make_permission_codes(app_label: str, model_name: str) -> dict:
       base = model_name.lower().replace(" ", "_")
       return {
           "view": f"{app_label}_view_{base}",
           "create": f"{app_label}_create_{base}",
           "update": f"{app_label}_update_{base}",
           "delete": f"{app_label}_delete_{base}",
       }
   ```

   Optional extra:

   ```python
   def make_extra_permission(app_label, model_name, action):
       base = model_name.lower().replace(" ", "_")
       return f"{app_label}_{action}_{base}"
   ```

2. Make API paths

   ```python
   def make_api_path(app_label: str, model_name: str) -> str:
       return f"/api/{app_label}/{model_name.replace('_', '-').lower()}s/"
   ```

3. Make menu keys

   ```python
   def make_menu_key(app_label: str, model_name: str) -> str:
       return f"{app_label}-{model_name.replace('_', '-').lower()}s"
   ```

4. Make metadata table names

   ```python
   def make_table_name(app_label: str, model_name: str) -> str:
       # finance + journal_voucher -> fin_journal_voucher
       prefix = app_label[:3]  # fin, pro, inv
       return f"{prefix}_{model_name.lower()}"
   ```

**Rule:** every generator must call this; no hard-coded strings in features.

---

## 4. Component 2: Permission Sync & Generator

**File:** `security/management/commands/sync_permissions.py`

**What it does:**

1. Reads **all apps’** `permissions.py` if present.
2. If an app **doesn’t** have `permissions.py`, it auto-derives permission codes from its models (via `id_factory`).
3. Upserts into `sec_permission` table.

**Table:** `sec_permission`

- `id` (PK)
- `code` (unique) → e.g. `finance_create_journal_voucher`
- `description`
- `category`
- `scope_required` (bool)
- `is_assignable` (bool)
- `created_at`, `updated_at`

**Why:** This turns your auto-generated strings into real, assignable permissions for roles/groups/users.

---

## 5. Component 3: Document Numbering Service

**Goal:** business documents (JV, PO, GRN, Bill, Payment, Asset Reg, Loan Disbursement) must have **human-readable** auto numbers, per company.

**Table:** `core_doc_sequence`

Columns:

- `id`
- `company_id`
- `doc_type` (e.g. `JV`, `PO`, `GRN`, `PAY`)
- `fiscal_year`
- `current_no` (int)
- `updated_at`

**Service:** `core/doc_numbers.py`

```python
def get_next_doc_no(company_id, doc_type, fiscal_year=None):
    # 1. get (company_id, doc_type, fy) row
    # 2. lock/update
    # 3. return formatted number e.g. "JV-25-000123"
```

**Pattern:**

- `JV-<fy>-<seq>`
- padding configurable (4 / 5 / 6 digits)

**Usage in codegen:**

- When generator creates a new _document_ model (has `is_document = True` in spec), it also:

  - mixes in a `DocumentNumberMixin`
  - sets `doc_type`
  - in `create()`, it calls `get_next_doc_no(...)` to fill `voucher_no` / `po_no` / `grn_no`

So users never type the number.

---

## 6. Component 4: Metadata Registration (Visual DM + BI)

**File:** `metadata/registry.py`

```python
def register_model(app_label: str, model_cls):
    # 1. get table name from model or id_factory
    # 2. write to dm_table if not exists
    # 3. read model._meta.fields and write to dm_column
```

**Tables:**

1. `dm_table`

   - `id`
   - `schema_name`
   - `table_name`
   - `display_name`
   - `module`
   - `tenant_cluster_id` (nullable)
   - `company_id` (nullable)

2. `dm_column`

   - `id`
   - `table_id`
   - `column_name`
   - `display_name`
   - `data_type`
   - `is_pk`
   - `is_fk`

3. `dm_relationship`

   - `id`
   - `left_table_id`
   - `right_table_id`
   - `left_column`
   - `right_column`
   - `cardinality` (1-1, 1-N, N-1, N-N)
   - `is_system`
   - `tenant_cluster_id` (nullable)

**Why:** when you generate `JournalVoucher`, it **immediately** appears in the visual data model → dashboards can use it → and if a relation is missing, dashboard can ask for manual joins.

---

## 7. Codegen Flow (end-to-end)

When you (or the system) creates a new feature/module (say, “Journal Voucher”), this is what happens:

1. **Input spec** received (YAML/JSON) → `finance + JournalVoucher + fields`
2. **Backend generator**:

   - creates model
   - creates serializer
   - creates viewset
   - creates urls
   - calls `id_factory` to generate:

     - permission codes
     - API path
     - menu key
     - table name

   - writes app’s `permissions.py` (append into marked block)

3. **Run** `python manage.py sync_permissions`
   → writes those permission codes into DB
4. **Frontend generator**:

   - uses same `id_factory` outputs to create:

     - list/form pages
     - route entries
     - menu entries
     - permission-aware buttons

5. **Metadata registration**:

   - call `metadata.register_model("finance", JournalVoucher)`
     → adds `fin_journal_voucher`

6. **If document**:

   - model’s `create()` uses `doc_number` service to auto-generate business number

**Result:** nobody hand-wrote an ID.

---

## 8. Handling User-Created / Migrated Fields

When a user uploads a file and you auto-create a column:

1. Migration/import service normalizes header:

   - `Extra Color Code` → `extra_color_code`

2. Check if exists in real table

   - If no → ALTER TABLE add column

3. Generate metadata ID:

   - table name (from id_factory): `fin_journal_voucher`
   - field ID: `fld_fin_journal_voucher_extra_color_code`

4. Insert into `dm_column`
5. (optional) Log to an “auto-extensions” table so admin can attach business meaning later.

This keeps schema, metadata, and BI in sync.

---

## 9. Multi-Company / Tenant Considerations

- **Permissions**: global strings (same for all companies)
- **Document numbers**: per company
- **Metadata (DM)**: global by default, but allow `company_id` override if a company has a custom table/column
- **Sequences**: must be locked per (company, doc_type, fy)

So in DB, you must **index**:

```sql
UNIQUE (company_id, doc_type, fiscal_year)
```

in `core_doc_sequence`.

---

## 10. Validation & Enforcement

To make sure people don’t sneak in hand-made IDs:

1. **Django check** (system check): scan models at startup

   - if model is marked `is_document = True` but has no `business_no` field → raise warning
   - if model has API but no permission in `permissions.py` → raise warning

2. **CI job**:

   - run `sync_permissions --dry-run` and compare with committed `permissions.py`
   - if diff → fail the pipeline (“You added a model but didn’t generate permissions”)

3. **Frontend lint**:

   - ensure every menu item has `permission:` property
   - ensure route path matches pattern from generator

---

## 11. Migration of Existing Modules

You already have some modules (report builder, data model, dashboards). To bring them under this auto-ID regime:

1. **Scan existing Django apps** → list models
2. For each model:

   - generate permission codes and insert if missing
   - generate API path and register if missing
   - generate menu key (for UI auto-nav)
   - register in `dm_table` / `dm_column`

3. For existing documents (PO, GRN, JV if you had it manually):

   - create `core_doc_sequence` entries per company
   - next time they create, it will auto-number

This is a **one-time** normalization.

---

## 12. Testing Strategy

1. **Unit tests** for `id_factory`:

   - `finance` + `JournalVoucher` → `finance_view_journal_voucher` etc.
   - pluralization
   - kebab/snake-case conversions

2. **Integration tests** for `sync_permissions`:

   - create fake app with `permissions.py`
   - run command
   - check DB

3. **API tests**:

   - create JV → assert `voucher_no` auto-filled
   - create JV for another company → sequence starts from 1 again

4. **Metadata tests**:

   - create model → hit `/api/data-model/tables/` → must include generated table

---

## 13. Developer Rules (to write in your handbook)

- Do **not** hard-code permission strings — always use helper/generator.
- Do **not** create API routes manually — use router registration with generated basename.
- Do **not** add menu keys freehand — use generated key.
- Do **not** add DB columns during migration without calling metadata registration.

If they break the rule → CI should fail.

---

## 14. Future Extensions

- **Human-readable override**: allow admin to rename (“Journal Vouchers” → “JV Register”) while keeping internal ID same.
- **ID shortener**: for mobile/UI, show short code but store full code.
- **Audit**: store generator version and source spec for every auto-generated thing.

---

## 15. Final Outcome

After this is implemented:

- You say: **“Create module: Fixed Asset Register”**
- Generator creates:

  - model: `FixedAsset`
  - table: `fin_fixed_asset`
  - permissions:

    - `finance_view_fixed_asset`
    - `finance_create_fixed_asset`
    - `finance_update_fixed_asset`
    - `finance_delete_fixed_asset`

  - API: `/api/finance/fixed-assets/`
  - menu: `finance-fixed-assets`
  - metadata: table + columns
  - if it’s a document (asset add) → doc no: `FA-25-000001`

- You don’t type any of those IDs.

That’s your full & final implementation plan.
