# Twist ERP Platform - Phase 0 & 1 Blueprint

This document provides the engineering blueprint for Phase 0 (Multi-Company Architecture) and Phase 1 (Platform Foundation) of the Twist ERP platform. It translates product intent into concrete technical deliverables, guardrails, and acceptance criteria so that implementation teams can execute without ambiguity.

---

## 1. Guiding Outcomes

- Single-machine installation that bootstraps an embedded PostgreSQL instance and provisions tenant databases without manual DBA work.
- CompanyGroup tenancy model that isolates unrelated businesses while enabling real-time inter-company flows inside each group.
- Metadata-first platform foundation (schema, workflows, permissions) that Phase 2 functional modules can rely on immediately.
- Audit, backup, and observability hooks in place from the outset to keep later phases stable.

---

## 2. Phase 0 - Multi-Company Architecture Skeleton

### 2.1 Objectives

- Stand up the embedded database runtime and provisioning flow.
- Define and persist CompanyGroup tenancy, company context, and inter-company plumbing.
- Establish metadata layering and audit logging foundations.
- Ship minimal admin tooling (CLI or scripts acceptable) for backup and basic health checks.

### 2.2 Embedded PostgreSQL Runtime

**Scope**

- Bundle PostgreSQL binaries for supported platforms and install a managed instance on first run.
- Initialize a dedicated data directory (default port `5433`, `listen_addresses = 'localhost'`).
- Create the global system database `twist_system` and, when requested, additional CompanyGroup databases (for example `cg_<slug>`).

**Security and Access**

- Generate a superuser credential during install and store it encrypted (machine keystore or sealed secrets file).
- Application services authenticate with least-privilege roles per database.
- Only the provisioning or migration service can use elevated credentials to create databases or apply schema migrations.

**Operations**

- Provide a CLI or admin endpoint for:
  - `db status` - verify instance is running and reachable.
  - `db backup` - create dumps of `twist_system` and all CompanyGroup databases as a single artifact.
  - `db start` / `db stop` - manage the managed Postgres service (optional in Phase 0 but recommended if effort allows).
- Emit structured logs for lifecycle events (initialization, start, stop, backup success or failure).

### 2.3 CompanyGroup (Tenant Cluster) Model

**Concept**

- CompanyGroup is the tenancy boundary. Companies inside the same group share a database and can transact with one another; companies in different groups remain fully isolated.

**Persistence**

- `twist_system.company_groups` table fields:
  - `company_group_id` (UUID primary key)
  - `group_name`
  - `db_name` (physical Postgres database identifier)
  - `industry_pack_type` (manufacturing, NGO, trading, service, ...)
  - `supports_intercompany` (boolean)
  - `status`
  - `created_at`, `updated_at`
- `twist_system.company_group_settings` for shared configuration (timezone, base currency, reporting calendar, and similar items).

**Provisioning Flow**

1. Request to create a CompanyGroup arrives (wizard or CLI).
2. System database stores the metadata row (status = `creating`).
3. Provisioning service creates the physical Postgres database, runs baseline migrations, seeds industry-pack metadata.
4. Default admin role and service accounts are created for the group.
5. Status flips to `active`; audit entry recorded.

### 2.4 Company Model and Context

- `cg_<slug>.companies` table with:
  - `company_id` (UUID primary key)
  - `company_group_id` (foreign key back to system database)
  - `legal_name`, `short_code`, `currency`, `timezone`, `is_active`, timestamps.
- Every transactional table inside a CompanyGroup database includes `company_id` and `company_group_id`.
- Runtime context middleware resolves for every request:
  - Authenticated user.
  - Active CompanyGroup and Company (from headers or token claims).
  - Optional cross-company visibility flag (for group-level roles).

### 2.5 Inter-Company Transaction Framework

- Introduce `inter_company_txn_id` to link mirrored AR/AP or inventory movements.
- Create `cg_<slug>.inter_company_links` with:
  - `link_id` (UUID primary key)
  - `initiating_company_id`
  - `counterparty_company_id`
  - `source_entity` (invoice, stock_transfer, ...)
  - `source_record_id`
  - `status` (pending, confirmed, canceled)
  - timestamps
- Add group-level GL mapping table `cg_<slug>.group_account_map` to tie local accounts to a consolidated chart and flag inter-company accounts used for eliminations.

### 2.6 Metadata Layering Strategy

- Four-layer model:
  1. Core system (ships with codebase).
  2. Industry pack baseline (selected per CompanyGroup).
  3. Group customization (applies to all companies in the group).
  4. Company override (final adjustments per company).
- Store metadata definitions using versioned JSON (entity definitions, field schemas, form layouts, workflow templates).
- Provide merge logic that produces an effective definition per request context and records the version used for audit.

### 2.7 Security, Permissions, and Audit Baseline

- Adopt custom `users.User` model with:
  - `is_system_admin`, `is_staff`, `is_active`.
  - Many-to-many `companies` via `user_company_roles` containing `role_id`.
- Enforce access by:
  - Checking a user has an active role for the target company.
  - Allowing group-level roles to operate across companies where permitted (`can_view_all_companies`).
- Audit logging requirements:
  - Record user, company, company group, entity, action, before/after (where feasible), correlation identifiers.
  - Minimum storage: append-only table `cg_<slug>.audit_log`.

### 2.8 Observability and Guardrails

- Application-level health endpoint should confirm:
  - Database connectivity for system database and current CompanyGroup.
  - Background services (workflow engine, job runner) heartbeat (stubbed if not yet implemented).
- Metrics hooks (even if only counters) for database provisioning time, backup duration, failed authentication attempts.

### 2.9 Phase 0 Exit Criteria

- Embedded Postgres service can be installed, started, stopped, and backed up without manual DBA steps.
- CompanyGroup provisioning creates both metadata and physical database with baseline schema.
- Multi-company session context enforced across the API stack.
- Metadata layering persists and can render an effective definition sample (API or CLI).
- Audit log captures authentication and provisioning events.
- Documentation and runbook for installation, backup, and troubleshooting delivered.

---

## 3. Phase 1 - Platform Foundation

### 3.1 Objectives

- Deliver onboarding experience that provisions CompanyGroups, companies, and the first administrators end-to-end.
- Provide tooling for schema customization, workflow orchestration, and role-based access control.
- Implement runtime metadata merge and hybrid storage model to support future module extensibility.
- Surface an internal admin console for operating the platform day to day.

### 3.2 Core Workstreams

#### 3.2.1 Onboarding Wizard

- **Flows**
  1. Select or create CompanyGroup; choose industry pack.
  2. Name the primary company and set default currency and timezone.
  3. Create first admin user (credentials and optional MFA bootstrap).
  4. Review summary and provision.
- **Backend responsibilities**
  - Trigger CompanyGroup provisioning pipeline; either block UI until complete or provide progress feedback.
  - Assign admin user to group and company with superuser-equivalent role.
  - Seed demo data where relevant (chart of accounts, approval workflows).
- **Deliverables**
  - REST endpoints with idempotency controls.
  - Frontend wizard with validation and failure recovery.
  - Audit trail entry capturing wizard actions.

#### 3.2.2 Metadata-Driven Schema Designer (MVP)

- Service and lightweight UI to list entities and fields drawn from merged metadata.
- Support CRUD on custom fields:
  - Field name, label, datatype, default, required flag, display rules.
  - Persist definition at appropriate layer (group versus company).
- Newly created fields stored initially in `extra_data` JSONB on transactional tables.
- Emit events when metadata changes for downstream cache invalidation.

#### 3.2.3 Hybrid Storage and Promotion Path

- Standard structure for core tables:
  - Base columns defined in migrations.
  - `extra_data` JSONB column for flexible attributes.
- Implement backend job to promote a JSONB field into a real column:
  - Validate data type and nullability.
  - Run `ALTER TABLE` within maintenance window.
  - Backfill existing data.
  - Update metadata to mark field as `storage_mode = column`.
  - Provide rollback guidance if migration fails.

#### 3.2.4 Workflow Engine Core

- Metadata models:
  - `workflow_definitions` (graph of states, transitions, conditions).
  - `workflow_versions` (immutable snapshots).
  - `workflow_assignments` (map workflows to entities or companies).
- Runtime service responsibilities:
  - Subscribe to domain events (`PR.CREATED`, `INVOICE.POSTED`, and similar).
  - Evaluate rules, escalate approvals, notify participants.
  - Persist workflow instances and action logs with audit context.
- Provide admin UI to view workflow graph and current instances (read-only acceptable for Phase 1).

#### 3.2.5 Permission Matrix and Role Management

- Define `role_definitions` per CompanyGroup with modules, actions, and field-level permissions.
- Extend `user_company_roles` with attributes:
  - `role_id`, `company_id`, `is_active`, `assigned_at`.
  - Flags such as `can_switch_company`, `can_manage_metadata`.
- Build admin screens and APIs to:
  - Assign users to roles and companies.
  - Clone roles across companies.
  - Preview effective permissions for a user.
- Enforce permissions inside API endpoints and workflow engine hooks.

#### 3.2.6 Runtime Metadata Merge Service

- Implement deterministic merge order (Core -> Industry Pack -> Group Custom -> Company Override).
- Cache effective definitions per entity and company (invalidate on changes).
- Provide API to fetch effective schema, form layout, and workflow selection.
- Include version hash so clients can detect changes and refresh UI automatically.

#### 3.2.7 Admin Console (MVP)

- Web-based internal tool (can live inside existing frontend workspace) with modules:
  - Dashboard: system status, database health, pending provisioning tasks.
  - Tenancy: list CompanyGroups and companies, create or disable entities.
  - Users and Roles: manage assignments, reset passwords, view audit trail.
  - Metadata: view definitions, create custom fields, trigger promotions.
  - Workflows: list definitions, inspect running instances.
  - Maintenance: trigger backups, download support bundles.
- Authentication restricted to system admins and group-level admins.

### 3.3 Supporting Infrastructure

- **Background workers**: Celery or equivalent with Redis to run provisioning, workflow, and promotion tasks asynchronously.
- **Event bus**: Define minimum set of domain events (for example `company.created`, `user.invited`, `metadata.updated`) and message contracts.
- **Testing and QA**:
  - Fixture data for integration tests across multiple companies within a group.
  - Automated test harness for metadata merge scenarios.
  - Load test scripts for onboarding wizard to validate provisioning concurrency.

### 3.4 Phase 1 Exit Criteria

- Onboarding wizard provisions a new CompanyGroup, company, admin user, and baseline metadata entirely through UI or API.
- Schema designer supports creating and editing custom fields stored in JSONB.
- Promotion workflow can move a custom field from JSONB to native column with audit trail.
- Workflow engine executes approval flows and stores state transitions.
- Permission matrix enforces module or action level security and supports cross-company roles.
- Runtime metadata merge returns correct effective definitions; cache invalidation works.
- Admin console exposes tenancy, user management, metadata, workflow, and maintenance views.
- Backup command integrates with admin console (or exposed API) and is documented.

---

## 4. Implementation Milestones

| Milestone                  | Duration | Key Deliverables                                         |
| -------------------------- | -------- | -------------------------------------------------------- |
| Phase 0 Kickoff            | Week 0   | Environment setup, embedded Postgres packaging plan      |
| Embedded DB GA             | Week 2   | Automated init, start, backup scripts, health checks     |
| CompanyGroup MVP           | Week 4   | System database schema, provisioning flow, audit logging |
| Phase 0 Exit               | Week 6   | Sign-off on tenancy, metadata skeleton, runbook          |
| Phase 1 Kickoff            | Week 6   | Cross-team alignment, backlog finalization               |
| Onboarding Wizard Alpha    | Week 8   | UI flow, provisioning pipeline integration               |
| Metadata and Workflow Beta | Week 10  | Schema designer, workflow runtime                        |
| Admin Console Beta         | Week 11  | Core admin features, permission guardrails               |
| Phase 1 Exit               | Week 12  | All exit criteria met, docs and testing complete         |

---

## 5. Risks and Mitigations

- **Embedded Postgres packaging complexity** - Prototype installer early; document OS-specific steps; provide fallback Docker compose for development.
- **Schema promotion downtime** - Enforce maintenance windows, wrap migrations in transactions, maintain backup before promotion.
- **Metadata merge correctness** - Build comprehensive unit tests and deterministic ordering; log merge decisions for debugging.
- **Workflow engine scalability** - Start with synchronous path but design queue-friendly architecture; benchmark before Phase 2 load increases.
- **Role explosion** - Establish naming convention and role templates; admin console must support cloning and diffing roles.

---

## 6. Deliverables Checklist

- Installation runbook covering embedded database lifecycle.
- API and CLI documentation for provisioning, metadata, workflow, permissions.
- Seed data for industry packs and default roles.
- Automated test suite results and coverage summary.
- Architecture decision records for key choices (embedded DB, metadata merge, promotion flow).
- Operational handoff notes: backup restore drill, audit log retention, monitoring setup.

---

## 7. Next Steps After Phase 1

- Kick off Phase 2 module implementation (Finance, Procurement, Sales, Inventory) using metadata, workflow, and RBAC foundations.
- Expand observability (metrics dashboard, alerting) based on Phase 1 instrumentation.
- Plan Phase 3 data migration tooling using backup and export capabilities built in Phases 0 and 1.

---

**Version**: 1.0  
**Last Updated**: October 2025  
**Owners**: Platform Architecture, Core Engineering, DevOps

Awesome. Phase 2 is where Twist ERP stops being just a platform and actually starts behaving like a working ERP.

By the end of Phase 2:

- A company in a CompanyGroup can buy something, receive it, stock it, sell it, invoice it, collect money, and have everything post to ledgers with audit and approvals enforced.
- Group finance (CFO role) can see live status across companies in that group.
- All of this runs on the architecture we already locked in (Postgres per CompanyGroup, metadata-driven forms/workflows, RBAC, audit).

I’ll break Phase 2 into the major deliverables you listed and define: scope, data model, workflows, role/security, posting logic, and integration points for each.

## Phase 2 Modules

- 2.1 Finance (GL / AP / AR)
- 2.2 Procurement (PR → PO → GRN → Bill → Payment)
- 2.3 Sales / Order-to-Cash (Quotation → Sales Order → Delivery → Invoice → Receipt)
- 2.4 Inventory & Warehouse
- 2.5 Group dashboards + Cross-module audit visibility

We’re implementing all of these inside each CompanyGroup database (`cg_*`), using:

- `company_id` on all transactional records
- Workflow Engine from Phase 1
- RoleDefinition permissions from Phase 1
- AuditLog from Phase 1

---

## 2.1 Finance Module (GL / AP / AR)

### 2.1.1 Scope

Finance in Phase 2 must support:

- Chart of Accounts (CoA) per company, mapped to GroupAccountMap for consolidation.
- General Ledger postings.
- Accounts Payable:

  - Supplier Bills
  - Payables aging
  - Payment posting

- Accounts Receivable:

  - Customer Invoices
  - Receivables aging
  - Collection/receipt posting

- Audit trail: who approved, who posted.
- Inter-company tagging (for elimination later).

### 2.1.2 Core data tables in `cg_*` DB

**ChartOfAccounts**

- `account_id` UUID PK
- `company_id`
- `account_code` text
- `account_name` text
- `account_type` text (Asset, Liability, Equity, Income, Expense)
- `is_intercompany` bool
- `group_account_code` text (for consolidation / elimination)
- `status`
- timestamps

**GLEntry**

- `gl_entry_id` UUID PK
- `company_id`
- `posting_date`
- `account_id`
- `debit_amount` numeric(18,2)
- `credit_amount` numeric(18,2)
- `currency`
- `reference_type` (e.g. "AP_BILL", "AR_INVOICE", "JOURNAL")
- `reference_id`
- `inter_company_txn_id` (nullable, link if inter-company)
- `created_by_user_id`
- `created_at`
- `extra_data` jsonb

All postings result in rows in GLEntry.

**APBill (Supplier Invoice)**

- `ap_bill_id` UUID PK
- `company_id`
- `supplier_id`
- `bill_date`
- `due_date`
- `currency`
- `status` ("draft", "approved", "posted", "paid")
- `total_amount`
- `extra_data` jsonb
- timestamps
- link to GRN/PO lines if originated from procurement

**APPayment**

- `ap_payment_id` UUID PK
- `company_id`
- `ap_bill_id`
- `paid_amount`
- `payment_date`
- `payment_method` (bank/cash)
- timestamps

**ARInvoice (Customer Invoice)**

- `ar_invoice_id` UUID PK
- `company_id`
- `customer_id`
- `invoice_date`
- `due_date`
- `currency`
- `status` ("draft","approved","posted","collected","writeoff_pending")
- `total_amount`
- `inter_company_txn_id` (if selling to sister company)
- `extra_data` jsonb
- timestamps

**ARReceipt**

- `ar_receipt_id` UUID PK
- `company_id`
- `ar_invoice_id`
- `received_amount`
- `receipt_date`
- `payment_method`
- timestamps

You’ll also have master data:

- `supplier` table (similar to `customer`)
- `bank_account` / `cash_account` reference
- tax tables if needed

### 2.1.3 Posting rules

For each “financial event” we generate GLEntry rows:

- APBill posted:

  - Debit Expense or Inventory
  - Credit AP Control account

- APPayment posted:

  - Debit AP Control
  - Credit Bank/Cash

- ARInvoice posted:

  - Debit AR Control
  - Credit Revenue

- ARReceipt posted:

  - Debit Bank/Cash
  - Credit AR Control

- Inventory movement (from Inventory module) posts to stock/COGS accounts

These posting mappings must be configurable by company:

- In metadata, define Posting Rules per document type.
  Example: `posting_rules_json` in metadata for `APBill`:

  ```json
  {
  	"lines": [
  		{
  			"dr": "inventory_account_id",
  			"cr": "ap_control_account_id",
  			"basis": "line_amount"
  		}
  	]
  }
  ```

Phase 2 must:

- Read posting rules from metadata (Company Override layer can change accounts).
- Generate balanced debit/credit GLEntry rows.
- Log the fact that posting happened (AuditLog entry with action_type="POST_GL").

### 2.1.4 Approvals & workflow

AP Bills, AR Invoices, and Manual Journals must pass through Workflow Engine from Phase 1:

- When APBill is submitted:

  - Fire event `APBILL.SUBMITTED`.
  - WorkflowDefinition for APBill decides:

    - If amount > threshold, require CFO approval.
    - If supplier is “new vendor”, require Compliance approval.

  - Store state in workflow instance (pending approvals).
  - When fully approved, mark `status="approved"`.
  - Only approved bills can be posted to GL.

Same for ARInvoice and for manual Journals.

All approval steps write to AuditLog.

### 2.1.5 Aging and basic finance reports

Phase 2 must generate:

- AP aging (per supplier, total outstanding by aging bucket).
- AR aging (per customer).
- Trial balance (sum of GLEntry per account for a date range).
- P&L and Balance Sheet per company:

  - Summarize accounts by `account_type`.

- Group trial balance (for Group CFO role across companies in same CompanyGroup):

  - Summarize per company_id, map to `group_account_code`, include `is_intercompany`.
  - This sets you up for consolidation/elimination reports.

These queries stay within the same `cg_*` DB.

---

## 2.2 Procurement (PR → PO → GRN → Bill → Payment)

### 2.2.1 Scope

Procurement flow inside one company:

1. Purchase Requisition (PR) – request to buy
2. Purchase Order (PO) – approved order to supplier
3. Goods Receipt Note (GRN) – items physically received into stock
4. Supplier Bill (APBill) – invoice from supplier
5. Payment (APPayment)

This must integrate Inventory (stock levels, valuation) and Finance (AP).

Also supports inter-company if supplier is actually another company in the same CompanyGroup.

### 2.2.2 Core tables in `cg_*` DB

**PurchaseRequisition**

- `pr_id` UUID PK
- `company_id`
- `requested_by_user_id`
- `request_date`
- `status` ("draft","submitted","approved","rejected","converted_to_po")
- `total_estimated_amount`
- `extra_data` jsonb
- timestamps

**PurchaseOrder**

- `po_id` UUID PK
- `company_id`
- `supplier_id` (or sister company’s company_id if inter-company)
- `po_date`
- `status` ("draft","approved","sent","partially_received","closed")
- `currency`
- `total_amount`
- `inter_company_txn_id` (nullable)
- `extra_data` jsonb
- timestamps

**PurchaseOrderLine**

- `po_line_id` UUID PK
- `po_id` FK
- `item_id`
- `description`
- `qty_ordered`
- `price`
- `uom`
- `expected_delivery_date`
- `company_id`
- timestamps
- `extra_data` jsonb

**GoodsReceiptNote (GRN)**

- `grn_id` UUID PK
- `company_id`
- `po_id`
- `received_date`
- `status` ("draft","posted")
- timestamps

**GRNLine**

- `grn_line_id` UUID PK
- `grn_id`
- `po_line_id`
- `item_id`
- `qty_received`
- `warehouse_id`
- `company_id`
- timestamps
- `extra_data` jsonb

Flow:

- PR creates/requests items or services.
- Approved PR → PO.
- Received items create GRN lines → update Inventory.
- Supplier sends invoice → APBill linked to PO/GRN.
- Payment → APPayment.

### 2.2.3 Workflow & approvals

- PR approval routing:

  - Use WorkflowEngine. Rules can be like:

    - If total > X → Dept Head approval
    - If CapEx category → CFO approval

  - Only approved PR can become PO.

- PO approval routing:

  - Separate WorkflowDefinition for `PurchaseOrder`.
  - After approval, mark `status="approved"` and “PO sent”.

- GRN posting:

  - When GRN is posted, Inventory increases. See Inventory module section below.

- AP Bill:

  - APBill generated from PO/GRN.
  - APBill approval uses Finance workflow (CFO/etc).
  - When posted, it hits the GL (AP credit, Inventory or Expense debit).

### 2.2.4 Inter-company procurement

If `supplier_id` represents another company in the same CompanyGroup:

- Creating PO in Company B should:

  - generate a mirror Sales Order in Company A (Sales module) and set a shared `inter_company_txn_id`.

- Receiving GRN in Company B should:

  - decrement stock in Company A (Delivery from A),
  - increment stock in Company B,
  - prepare ARInvoice in Company A / APBill in Company B.

This uses the `InterCompanyLink` table we defined in Phase 0.
That link must be filled in Phase 2 when PR→PO→GRN happens across companies.

---

## 2.3 Sales / Order-to-Cash

### 2.3.1 Scope

Sales flow inside one company:

1. Quotation / Offer
2. Sales Order (SO)
3. Delivery / Dispatch (ships goods, reduces Inventory)
4. Customer Invoice (ARInvoice)
5. Receipt / Collection (ARReceipt)

Also drives AR and revenue in Finance.

### 2.3.2 Core tables in `cg_*` DB

**SalesQuotation**

- `quote_id` UUID PK
- `company_id`
- `customer_id`
- `quote_date`
- `status` ("draft","sent","accepted","rejected","expired")
- `total_amount`
- `currency`
- `extra_data` jsonb
- timestamps

**SalesOrder**

- `so_id` UUID PK
- `company_id`
- `customer_id`
- `so_date`
- `status` ("draft","approved","partially_delivered","closed")
- `currency`
- `total_amount`
- `inter_company_txn_id` (nullable, if customer is sister company)
- `extra_data` jsonb
- timestamps

**SalesOrderLine**

- `so_line_id` UUID PK
- `so_id`
- `item_id`
- `description`
- `qty_ordered`
- `price`
- `uom`
- `company_id`
- timestamps
- `extra_data` jsonb

**DeliveryNote / Shipment**

- `delivery_id` UUID PK
- `company_id`
- `so_id`
- `delivered_date`
- `status` ("draft","posted")
- timestamps

**DeliveryLine**

- `delivery_line_id` UUID PK
- `delivery_id`
- `so_line_id`
- `item_id`
- `qty_delivered`
- `warehouse_id`
- `company_id`
- timestamps
- `extra_data` jsonb

**ARInvoice** (already defined in Finance)

- Will now be linked to the Sales Order / DeliveryNote

**ARReceipt** (already defined in Finance)

### 2.3.3 Workflow & approvals

- Sales Order approval:

  - WorkflowDefinition for `SalesOrder` can enforce:

    - Credit check (Customer credit_limit vs outstanding AR)
    - Discount approval if margin below threshold

  - Only approved SO can generate Delivery.

- Delivery posting:

  - When DeliveryNote is posted:

    - Inventory goes down for that warehouse (Inventory module).
    - COGS and stock ledger posting is prepared for Finance.

- Invoice:

  - ARInvoice is generated from delivered quantities.
  - ARInvoice approval follows Finance workflow.
  - Posting creates GLEntry (Debit AR / Credit Revenue).

- Receipt:

  - Receiving money (ARReceipt) posts (Debit Bank / Credit AR).

### 2.3.4 Inter-company sales

If `customer_id` actually represents another company in the same CompanyGroup:

- Creating Sales Order in Company A should:

  - create mirror Purchase Order in Company B and link both via `inter_company_txn_id`.

- Delivery in Company A:

  - triggers GRN in Company B.

- ARInvoice in A:

  - becomes APBill in B.

All linked through `InterCompanyLink`.
Finance will tag those postings as inter-company for consolidation elimination later.

---

## 2.4 Inventory & Warehouse

### 2.4.1 Scope

Inventory module must support:

- Item master
- Warehouse / location master
- Stock ledger
- On-hand quantity per item per warehouse
- Valuation posting to Finance
- Notifications / alerts (low stock, aging stock)

This module sits between Procurement and Sales.

### 2.4.2 Core tables in `cg_*` DB

**Item**

- `item_id` UUID PK
- `company_id`
- `item_code`
- `item_name`
- `uom`
- `item_type` ("raw", "finished", "service", etc.)
- `valuation_method` ("FIFO", "MovingAvg", etc.)
- `status`
- `extra_data` jsonb (for industry-specific fields like GSM/shade for textile, batch/lot for pharma/food)
- timestamps

**Warehouse**

- `warehouse_id` UUID PK
- `company_id`
- `warehouse_name`
- `location_code`
- `status`
- timestamps

**StockLedgerEntry**

- `sle_id` UUID PK
- `company_id`
- `item_id`
- `warehouse_id`
- `txn_type` ("GRN_POST", "DELIVERY_POST", "ADJUSTMENT", etc.)
- `txn_reference_type` ("GRN","DELIVERY","MANUAL_ADJ", etc.)
- `txn_reference_id`
- `posting_time`
- `qty_in`
- `qty_out`
- `balance_qty_after_txn`
- `unit_cost`
- `total_cost`
- timestamps
- `extra_data` jsonb

StockLedgerEntry is the atomic movement record:

- GRN posting creates `qty_in`.
- Delivery posting creates `qty_out`.
- Adjustments create in/out as needed.

**StockBalanceSnapshot** (optional optimization)

- `company_id`
- `item_id`
- `warehouse_id`
- `on_hand_qty`
- `on_hand_value`
- updated whenever we post stock moves.

### 2.4.3 Integration with Procurement

When a GRN is posted:

- For each `GRNLine`:

  - Create StockLedgerEntry with `qty_in`.
  - Update StockBalanceSnapshot.
  - Calculate cost (from PO price or valuation rules).

- If item is stock-controlled, post to Finance:

  - Debit Inventory Account
  - Credit GRN Clearing / AP Accrual (depending on config)
    This uses the posting rules in Finance.

### 2.4.4 Integration with Sales

When a DeliveryNote is posted:

- For each DeliveryLine:

  - Create StockLedgerEntry with `qty_out`.
  - Update StockBalanceSnapshot.
  - Compute cost of goods sold (COGS).

- Post to Finance:

  - Debit COGS
  - Credit Inventory

### 2.4.5 Alerts / dashboards

Inventory module in Phase 2 must generate:

- Low stock alert (compare `on_hand_qty` vs `reorder_level` in Item metadata).
- Slow-moving / aging stock report.
- GRN pending QC / blocked stock (if we later add QC/Inspection in advanced phases).

These alerts can show up in a basic dashboard for Store/Warehouse roles.

---

## 2.5 Group Dashboards & Cross-Module Audit

### 2.5.1 Group-level snapshots

Phase 2 must produce dashboards for:

- CFO / Finance Controller (role may have `can_view_multiple_companies_in_group = true`):

  - Cash position per company (sum of bank/cash accounts from GL).
  - AP aging summary per company.
  - AR aging summary per company.
  - Top overdue receivables.
  - Stock valuation by item category (if valuation method allows it).
  - Purchase commitments (open POs not yet received).
  - Sales pipeline / open SO value.
  - High-risk workflow blocks (PRs or Bills waiting > X days for approval).

All of this is computed inside the same CompanyGroup DB (single source) and filtered by `company_id` according to role.

### 2.5.2 Cross-module audit timeline

We already log actions in `AuditLog`. In Phase 2 we extend it so you can reconstruct process history:

For any document (PO, GRN, APBill, ARInvoice, DeliveryNote, etc.), you must be able to pull:

- Who created it (user_id, role, timestamp)
- Who approved it (workflow steps from Workflow Engine)
- When it was posted to GL
- When inventory moved
- If inter-company: the linked company/doc via `inter_company_txn_id`

This is not just “for security.” This is very important for disputes:

- “Warehouse says they never received it.”
- “Finance says invoice was already approved.”
- “Subsidiary B says price was wrong from Subsidiary A.”

So in Phase 2:

- Every critical state change must write an AuditLog row:

  - `action_type` = "CREATE", "APPROVE", "POST_GL", "POST_STOCK", "CLOSE", etc.

- Every AuditLog row must include:

  - `company_id`
  - `entity_name` ("PurchaseOrder", "GRN", etc.)
  - `record_pk` (the PO ID, GRN ID, etc.)
  - `user_id`
  - snapshot of role(s) from session at that time in `metadata`

This gives you a full trace across Procurement → Inventory → Finance.
This also satisfies future UAT / audit readiness in Phase 7.

---

## Phase 2 Deliverables (What engineering must build)

This is the output of Phase 2. When Phase 2 is “done,” Twist ERP must have:

### 1. Finance Core

- Tables in each CompanyGroup DB for:

  - ChartOfAccounts, GLEntry, APBill, APPayment, ARInvoice, ARReceipt.

- Posting rules metadata per document type (e.g. APBill, ARInvoice) stored in metadata so it’s configurable.
- Posting service that:

  - Generates balanced GL entries.
  - Tags inter-company transactions.

- AP aging, AR aging, Trial Balance, P&L, Balance Sheet queries.
- Workflow approval (via Workflow Engine) for APBill, ARInvoice, manual Journals.
- AuditLog entries for approval, posting.

### 2. Procurement Flow

- Entities/tables for PurchaseRequisition, PurchaseOrder (+ lines), GRN (+ lines).
- Workflow approvals for PR and PO.
- GRN posting that:

  - Updates Inventory (StockLedgerEntry, StockBalanceSnapshot).
  - Can create APBill draft.

- Link to Finance:

  - APBill for supplier invoices.
  - APPayment posting.

- Inter-company: PO / GRN in Company B creates mirror Sales / Delivery in Company A via `inter_company_txn_id`.

### 3. Sales / Order-to-Cash

- Entities/tables for SalesQuotation, SalesOrder (+ lines), DeliveryNote (+ lines).
- Workflow approvals for SalesOrder (credit/discount check).
- Delivery posting:

  - Reduces Inventory.
  - Computes COGS.

- ARInvoice generation from deliveries.
- ARReceipt posting.
- Inter-company: Sales in Company A mirrors Purchase in Company B.

### 4. Inventory

- Item master, Warehouse master.
- StockLedgerEntry table and logic.
- StockBalanceSnapshot updates on every inbound (GRN) / outbound (Delivery).
- Valuation (Moving Avg or FIFO baseline to start).
- Integration with Finance for inventory/COGS postings.
- Low stock / slow-moving stock alerts.

### 5. Group Dashboards

- Summary queries for CFO role across all companies in the same CompanyGroup DB:

  - Cash, AP aging, AR aging, stock value, open POs, open SOs, overdue approvals.

- Respect role permissions:

  - If role can view multiple companies, show aggregated.
  - If not, filter by their `company_id`.

### 6. Cross-Module Audit Trail

- Every key state change (CREATE / APPROVE / POST_STOCK / POST_GL / CLOSE) logged in `AuditLog`.
- `AuditLog` must include `user_id`, `company_id`, `entity_name`, `record_pk`, timestamp, and role context.
- Must be possible to reconstruct end-to-end chain:

  - PR → PO → GRN → APBill → APPayment
  - SO → Delivery → ARInvoice → ARReceipt
  - Inventory and GL postings along the way

---

## How Phase 2 sits on Phases 0 + 1

- From Phase 0:

  - You already have embedded Postgres per CompanyGroup.
  - You already have Company / CompanyGroup / User / Role / Access.
  - You already have inter-company linking concept and group-level account mapping.
  - You already have audit plumbing and session scoping by `company_id`.
  - You already have RBAC and field-level visibility.

- From Phase 1:

  - You already have Schema Designer metadata (entity + fields).
  - You already have `extra_data` JSONB fields and field promotion path for custom fields.
  - You already have WorkflowDefinition + Workflow Engine runtime.
  - You already have onboarding wizard to create a new CompanyGroup and seed Industry Pack.

- Phase 2 now plugs in the first business workflows (Finance, Procurement, Sales, Inventory) directly on top of those foundations.

At the end of Phase 2, Twist ERP is no longer just “a platform.” It’s an actually usable ERP core for a multi-company group: buy → stock → sell → invoice → collect → post → report.

Phase 3 is the Data Migration Engine.

After Phase 3, Twist ERP should be able to pull in legacy data (Excel, CSV, old ERP exports) into any company inside any CompanyGroup — cleanly, safely, with minimal manual data entry, and without needing a developer/DBA.

Below is the full specification of Phase 3: entities, pipeline, workflow, permissions, rollback, metadata interaction, and deliverables.

---

## 3.0 Phase 3 Outcome

By the end of Phase 3, Twist ERP can:

1. Let an authorized user upload legacy data files (customers, suppliers, items, stock balances, opening AR/AP, etc.).
2. Detect the structure of the file and map its columns to Twist ERP entities/fields.
3. Suggest new fields that don't exist yet — and safely extend metadata to handle them.
4. Clean/normalize/validate rows (types, duplicates, referential links, required fields).
5. Stage the data inside the CompanyGroup DB without touching live tables yet.
6. Show the user exactly what will be imported and what will fail, with error queues they can fix.
7. Require approval to commit.
8. Commit atomically → write to the real tables (Customer, Supplier, Item, ARInvoice, etc.) and create GL/opening entries when applicable.
9. Be able to roll back an import batch.

All of this must respect:

- company_id scoping,
- RBAC/permissions,
- audit logging,
- metadata layering (Industry Pack / Group Custom / Company Override).

---

## 3.1 Migration Personas / Roles

We define two roles that matter in Phase 3:

### 1. **Data Importer**

- Usually someone inside the company (e.g. finance lead, inventory controller).
- Can start/import/stage data for _their_ company only.
- Can fix validation errors and resubmit.
- Cannot commit to live tables without approval.

This is a Company-level permission.

### 2. **Migration Approver**

- Usually Company Admin / Finance Controller / Group IT for that CompanyGroup.
- Has permission to approve and finalize imports.
- Can trigger commit of staged data into live tables.
- Can authorize schema extension (new fields).

This role may have `can_view_multiple_companies_in_group = true` (like Group CFO or HQ IT), but we still log company_id for every import.

Both roles must be definable in `RoleDefinition.permissions` in the CompanyGroup DB.

---

## 3.2 The Migration Pipeline (Lifecycle)

The migration process in Phase 3 is a pipeline with explicit stages. The engine must enforce that a batch moves in order, not skip steps.

### Step 1. Upload

User uploads one or more source files for a specific company:

- Allowed formats in Phase 3: CSV, XLSX.
- Example use cases:

  - Legacy Customer Master
  - Supplier/Vendor Master
  - Item Master
  - Opening Stock by warehouse
  - Opening AR (unpaid invoices)
  - Opening AP (unpaid bills)
  - Opening GL balances (optional if you allow cutover at trial balance level)

At upload time, user must choose:

- Target company (must match active_company_id in session).
- Target entity type they _think_ this is (e.g. “Customer”, “Item”, “Opening AR”, etc.) — OR “Unknown / Detect”.

We save the physical file (store reference in the CompanyGroup DB as metadata, not as raw blob if you want file system for size; store path + hash in DB).

**Tables (in CompanyGroup DB):**

- `migration_job`

  - `migration_job_id` UUID PK
  - `company_id`
  - `entity_name_guess` ("customer", "item", "opening_ar", etc.)
  - `status` ("uploaded","mapped","validated","approved","committed","rolled_back","error")
  - `created_by_user_id`
  - `created_at`
  - `approved_by_user_id` (nullable)
  - `approved_at` (nullable)
  - `committed_at` (nullable)
  - `rollback_parent_job_id` (nullable if this is a rollback attempt)
  - `meta` jsonb (free-form job notes)

- `migration_file`

  - `file_id` UUID PK
  - `migration_job_id`
  - `original_filename`
  - `stored_path` or reference
  - `file_hash`
  - `status` ("uploaded","parsed","error")
  - `row_count_detected`
  - timestamps

All uploads log to AuditLog (`action_type="IMPORT_UPLOAD"` with job & file IDs).

---

### Step 2. Detect & Parse

System inspects the uploaded file(s):

- Parse headers.
- Guess delimiter (for CSV).
- Read first N rows.
- Infer data types per column (string, numeric, date, money).
- Try to guess which Twist ERP entity this corresponds to if not provided:

  - e.g. columns `Customer Name`, `Address`, `Credit Limit` → likely "customer".
  - columns `Item Code`, `UOM`, `Unit Cost`, `Warehouse` → likely "item" or "opening stock".

We store this parsed structure.

**Tables:**

- `migration_column_profile`

  - `column_profile_id` UUID PK
  - `migration_job_id`
  - `column_name_in_file` text
  - `detected_data_type` text ("text","number","date","money")
  - `sample_values` jsonb (first few unique samples)
  - `confidence_score` numeric
  - timestamps

Status of `migration_job` can move from `"uploaded"` → `"mapped"` after column mapping is prepared.

---

### Step 3. Field Mapping

Now we map file columns → Twist ERP entity fields.

This is where we integrate with metadata from Phase 1.

For the chosen entity (example: `Customer`):

- Load merged effective entity definition for that company:

  - Core + Industry Pack + Group Custom + Company Override.

- That definition includes:

  - Known field names
  - Data types
  - Required flags
  - Visibility rules
  - Whether a field is backed by a physical column or in `extra_data`.

The system should auto-suggest mappings:

- `Customer Name` → `customer_name`
- `CreditLimit` → `credit_limit`
- `RegionCode` → `region_code` (doesn’t exist yet? propose new field)

We store the mapping.

**Tables:**

- `migration_field_mapping`

  - `mapping_id` UUID PK
  - `migration_job_id`
  - `column_name_in_file`
  - `target_entity_field` text (e.g. `customer_name`, `credit_limit`, `region_code`)
  - `target_storage_mode` text ("column" | "extra_data_new_field" | "ignore")
  - `new_field_definition_json` jsonb (if this creates a new custom field)
  - `is_required_match` bool
  - timestamps

Details:

- `target_storage_mode="column"` means this will fill an existing known field.
- `target_storage_mode="extra_data_new_field"` means we'll create a new field in metadata and store it in `extra_data` initially.
- `"ignore"` means we won't import that column.

**Important:**
At this stage, the system can propose schema extension:

- If file has a column not in ERP (e.g. `RegionCode`), propose:

  - `new_field_definition_json` with:

    - `field_name`: "region_code"
    - data type
    - label
    - visibility defaults
    - which layer: company-level override

- The Migration Approver can accept that new field.
  When accepted:

  - We update metadata (`EntityDefinition`) for this company with that new field (Company Override layer).
  - That field will land in `extra_data` for now.

We must record this approval decision for audit (see 3.6).

---

### Step 4. Transform / Clean

Before staging, system normalizes values:

- Trim whitespace.
- Parse dates into ISO.
- Convert money to decimal.
- Normalize case where appropriate (e.g. uppercasing codes).
- Map known enums (e.g. “Active”, “ACTIVE”, “A” → `active`).
- Resolve foreign keys:

  - e.g. for `opening stock` rows, `WarehouseName` must match an existing Warehouse in that company.
  - for `AR open invoices`, `CustomerCode` must match an existing or newly-imported customer in the same job.

We create a staging table of clean rows.

**Tables:**

- `migration_staging_row`

  - `staging_row_id` UUID PK
  - `migration_job_id`
  - `row_index_in_file` int
  - `clean_payload_json` jsonb // keys = target fields after mapping/normalization
  - `status` ("pending_validation","valid","invalid","skipped")
  - timestamps

Note: `clean_payload_json` is how we store each row after mapping to entity fields.

---

### Step 5. Validate

Run validation rules on each staged row:

Validation types:

- **Required fields present?**
  (e.g. `customer_name` is required)
- **Data type valid?**
  (`credit_limit` is numeric, etc.)
- **Uniqueness / duplicates?**
  (duplicate `customer_name` or `item_code`?)
- **Referential integrity?**
  (warehouse exists? customer exists for opening AR invoice?)
- **Business rules?**
  (e.g. credit limit cannot be negative; opening stock qty cannot be negative; invoice total must match sum of lines)

Store validation results.

**Tables:**

- `migration_validation_error`

  - `validation_error_id` UUID PK
  - `migration_job_id`
  - `staging_row_id`
  - `error_code` text
  - `error_message` text
  - `severity` ("hard","soft")
  - `suggested_fix` jsonb (optional, e.g. “use Warehouse=Main Warehouse”)
  - timestamps

Row status gets updated:

- If no hard errors → `valid`.
- If hard errors → `invalid`.
- If row was intentionally skipped by user → `skipped`.

The UI must show a grid like:

- Valid rows: will import.
- Invalid rows: require fix or exclusion.
- Summary totals: “125 rows valid, 7 invalid, 3 skipped.”

User with Data Importer role can now:

- Edit values inline for invalid rows (fix typos, fix code mismatches).
- Re-run validation for just those rows.
- Mark certain rows `skipped`.

When all remaining rows are `valid` or `skipped`, job can move to approval step.

At this point `migration_job.status` changes from `"mapped"` → `"validated"`.

---

### Step 6. Approval

Before data touches live tables, require approval.

Workflow:

- Fire event `MIGRATION_JOB.SUBMITTED_FOR_APPROVAL`.
- Use the Workflow Engine (Phase 1) with a special workflow definition for import jobs.

  - Example rule: If entity is `ChartOfAccounts` or `Opening AR/AP`, require Finance Controller approval.
  - If entity is `Customer Master`, allow Company Admin to approve.
  - If job affects multiple companies (not allowed in Phase 3; one job = one company), block.

The approver (Migration Approver role) reviews:

- Summary totals (how many records will go in).
- New fields that will be created.
- Financial impact if applicable (e.g. opening AR totals, opening stock total value).
- Audit preview.

Approver can:

- Approve → job moves to `"approved"`.
- Reject → job goes back to `"validated"` with comments.

Approval action writes to:

- `migration_job.approved_by_user_id`
- `migration_job.approved_at`
- AuditLog with `action_type="IMPORT_APPROVED"`.

---

### Step 7. Commit to Live Tables

On approval, the system performs the final import.

For each `migration_job` where `status="approved"`:

1. Start a DB transaction (inside that CompanyGroup DB).

2. For each `migration_staging_row` with `status="valid"`:

   - Insert/Upsert into the target live table (e.g. `customer`, `item`, `ar_invoice`, etc.).

     - Map known fields to columns.
     - Write unknown/custom (approved) fields into `extra_data`.

   - Capture the new PK of the created/updated live record.

3. If the entity type triggers finance effects:

   - Opening AR:

     - For each imported unpaid invoice:

       - Create `ARInvoice` with `status="posted"`.
       - Create corresponding `GLEntry` rows:

         - Debit AR control account
         - Credit Opening Balances / Retained Earnings / Migration Equity (configurable)

   - Opening AP:

     - Same idea but mirrored (Debit Opening Balances, Credit AP control).

   - Opening Stock:

     - For each row with qty and cost:

       - Create `StockLedgerEntry` with `qty_in` and valuation.
       - Post inventory value to GL (Debit Inventory, Credit Migration Equity).

   - Opening GL balances (if you support trial balance import at go-live):

     - Directly insert balanced `GLEntry` rows dated “opening date.”

4. Mark `migration_job.status="committed"`.

5. Write `migration_commit_log` (see below).

6. Commit DB transaction.

**Tables:**

- `migration_commit_log`

  - `commit_id` UUID PK
  - `migration_job_id`
  - `committed_at` timestamptz
  - `committed_by_user_id`
  - `record_count_committed`
  - `gl_impact_summary_json` (totals per account if applicable)
  - `notes`
  - timestamps

Also write AuditLog entries per affected entity row:

- `action_type="IMPORT_COMMIT"`
- Include migration_job_id, record_pk, company_id, who committed.

---

### Step 8. Rollback

We need controlled rollback, but not casual undo.

Rollback is allowed for:

- Master data (customers, suppliers, items) inserted in this batch.
- Opening balances (AR/AP/Stock/GL) inserted in this batch.

Rules:

- Only Migration Approver (or higher) can request rollback.
- Rollback is “all or nothing” per job, not row-by-row.
- Rollback is only allowed if:

  - Those imported records have not been referenced by new transactions later.

    - e.g. customer imported, then already used in a SalesOrder → cannot safely delete.

  - Those GL entries are still isolated to this import batch.

Rollback process:

1. System checks referential usage.

2. If safe:

   - Start transaction.
   - Reverse all inserted master rows where possible (delete those customers/items/ar_invoices/etc.).
   - Reverse GL entries (post reversing journal or delete if allowed pre-go-live).

     - For AR/AP opening, reversing means credit AR/debit equity etc.
     - For stock opening, create outbound StockLedgerEntry to bring stock to zero and post reversing GL.

   - Mark `migration_job.status="rolled_back"`.
   - Create a new `migration_job` as rollback record with `rollback_parent_job_id` pointing to original.

3. Log to AuditLog with `action_type="IMPORT_ROLLBACK"`.

Rollback must be explicit and fully audited.

---

## 3.3 Integration With Metadata Layer

Phase 3 must integrate tightly with the metadata system from Phase 1:

### Auto-suggest new fields

When mapping file columns → entity fields:

- If column doesn't match any known field in that entity’s current merged definition:

  - Prepare a proposed `new_field_definition_json`:

    - `field_name` (machine key)
    - `label`
    - inferred data type
    - visibility defaults
    - optional validations (length, allowed values)
    - mark layer_scope = "company" (Company Override layer, not Group Custom, unless Migration Approver chooses group-wide)

The Migration Approver can:

- Approve this new field for this company only.
- Approve it at group level (applies to all companies in this CompanyGroup).
- Reject it (column gets ignored or must be mapped manually to an existing field).

When approved:

- Update `EntityDefinition` in the CompanyGroup DB:

  - Insert/modify definition_json for that entity to include this new field and mark it as `extra_data`-backed.

- Version bump:

  - `version = version + 1`
  - `changed_by_user_id`
  - `changed_at`
  - layer_scope = "company" or "group" accordingly

- Write AuditLog with `action_type="METADATA_CHANGE_FROM_IMPORT"`.

This means after migration, the UI/forms/workflows in Phase 2+ will _see_ those new fields without code change.

---

## 3.4 Validation Rules Library

Phase 3 must ship a validation layer with reusable rules, not hardcode in views.

Categories:

1. **Field-level rules**
   Required, type, length/format, enum membership.

2. **Cross-field rules**
   Example:

   - `due_date` must be >= `invoice_date`.
   - `credit_limit` must be >= 0.
   - For opening AR/AP, `total_amount` must match sum of line items (if you import line detail).

3. **Reference rules**

   - `warehouse_id` must exist in `Warehouse` table for that company.
   - `customer_id` in AR import must either match existing or be created in the same batch.
   - `chart_of_accounts.account_code` must not collide incorrectly with existing ones.

4. **Business rules (Phase 2 tie-in)**

   - For inventory start balances: cannot import negative stock unless explicitly allowed.
   - For AR/AP open items: cannot import already-paid invoices.

These validations should:

- Mark row as `invalid` with `hard` errors if must-block.
- Mark row as `valid` but attach `soft` warnings (like “currency mismatch, will convert to company base currency”).

The UI should let Data Importer fix invalid rows and rerun validation without re-uploading.

---

## 3.5 Audit & Compliance in Phase 3

Every important action must hit AuditLog in that CompanyGroup DB with `company_id` and `user_id`:

- Upload file → `IMPORT_UPLOAD`
- Column mapping saved → `IMPORT_MAP_SAVED`
- Metadata extension approved → `METADATA_CHANGE_FROM_IMPORT`
- Validation completed → `IMPORT_VALIDATED`
- Job submitted for approval → `IMPORT_SUBMIT_FOR_APPROVAL`
- Approval / rejection → `IMPORT_APPROVED` or `IMPORT_REJECTED`
- Commit → `IMPORT_COMMIT`
- Rollback → `IMPORT_ROLLBACK`

Each log entry should include:

- Which role was active (from session),
- Migration job ID,
- Counts (rows valid / invalid / committed),
- If GL postings were generated,
- If metadata was modified.

This gives you a clean audit for UAT, external auditors, or finance leadership.

---

## 3.6 Company / CompanyGroup Scope Rules

The Data Migration Engine must obey the isolation model:

1. **A migration_job belongs to exactly one `company_id`.**

   - You cannot import for multiple companies in a single job.
   - This keeps rollback simple and prevents cross-company leaks.

2. The migration runs inside the CompanyGroup DB that holds that company.

   - Staging tables, validation tables, commit logs all live in that CompanyGroup DB (e.g. `cg_garments`).
   - This keeps everything auditable and backed up together with that company’s operations data.

3. A Migration Approver with cross-company view (like Group CFO) may be able to approve imports for multiple companies in the same CompanyGroup, but:

   - Each company’s job is still isolated.
   - Each job’s GL postings and Inventory postings are posted to that specific `company_id`.

4. Inter-company data can be imported, but:

   - For inter-company opening balances, you still do one company at a time.
   - If you need to import the mirrored opening balances for sister company B, that’s a second migration_job targeted at B.

We are **not** doing “one giant spreadsheet that seeds all companies at once” in Phase 3. That’s too risky for rollback and audit.

---

## 3.7 What Phase 3 Does Not Need Yet

Phase 3 does **not** need to:

- Import historical transactional journals for years of history (nice-to-have later, but cutover is usually “all open balances as of go-live date,” not full history).
- Import historical workflow approvals.
- Automatically reconcile inter-company balances across companies. (You can do that manually by importing AR to A and AP to B in coordinated jobs.)
- Support PDF parsing / OCR / invoice scanning. That’s later, or AI phase.

Phase 3 is focused on:

- Masters,
- Opening states,
- Clean cutover,
- Schema extension.

---

## 3.8 Phase 3 Deliverables (Engineering Checklist)

When Phase 3 is complete, Twist ERP must ship all of the following:

### 1. Migration Job Engine (in each CompanyGroup DB)

- Tables:

  - `migration_job`
  - `migration_file`
  - `migration_column_profile`
  - `migration_field_mapping`
  - `migration_staging_row`
  - `migration_validation_error`
  - `migration_commit_log`

- CRUD + status transitions for these.

### 2. File ingestion + profiling

- Upload via UI/API.
- Store file reference + hash.
- Parse header and sample rows.
- Infer column types.
- Infer target entity (or confirm with user).

### 3. Mapping UI / API

- Let Data Importer map file columns to entity fields.
- Auto-suggest matches.
- Auto-suggest new fields (with proposed metadata JSON).
- Save mapping to `migration_field_mapping`.

### 4. Metadata extension hook

- Migration Approver can approve new fields.
- Engine updates `EntityDefinition` for that entity:

  - Adds new field to Company Override layer (or Group layer if chosen).

- Version bump and AuditLog entry with `METADATA_CHANGE_FROM_IMPORT`.

### 5. Staging + normalization

- Clean all rows into `migration_staging_row.clean_payload_json`.
- Normalize datatypes, trim, map enums, resolve FK targets.
- Mark each row `pending_validation`.

### 6. Validation runner

- Run validation rules.
- Populate `migration_validation_error`.
- Mark rows `valid` / `invalid` / `skipped`.
- Let Data Importer fix rows and re-run validation.
- When all remaining rows are valid or skipped, mark job as `"validated"`.

### 7. Approval workflow

- Submit job for approval.
- Trigger Workflow Engine with `MIGRATION_JOB.SUBMITTED_FOR_APPROVAL`.
- Migration Approver can approve or reject.
- Approval updates `migration_job.status="approved"` and logs in AuditLog.

### 8. Commit executor

- For `status="approved"`:

  - Perform transactional import into live tables (Customer, Item, AR/AP opening, StockLedgerEntry, GLEntry).
  - Apply posting rules for opening balances (Inventory, AR/AP, Equity).
  - Write `migration_commit_log`.
  - Mark job `status="committed"`.
  - Write AuditLog entries (`IMPORT_COMMIT` per impacted entity).

### 9. Rollback executor

- Allow rollback if safe:

  - Check referential usage.
  - Reverse or delete imported records.
  - Reverse GL / stock postings.
  - Update job `status="rolled_back"`.
  - Write AuditLog `IMPORT_ROLLBACK`.

### 10. Security & audit integration

- All actions require proper role (`Data Importer`, `Migration Approver`).
- All actions run in the authenticated `active_company_id` context.
- Every step writes an AuditLog entry into that CompanyGroup DB:

  - `IMPORT_UPLOAD`
  - `IMPORT_MAP_SAVED`
  - `IMPORT_VALIDATED`
  - `IMPORT_SUBMIT_FOR_APPROVAL`
  - `IMPORT_APPROVED` / `IMPORT_REJECTED`
  - `IMPORT_COMMIT`
  - `IMPORT_ROLLBACK`
  - `METADATA_CHANGE_FROM_IMPORT`

### 11. UI/UX (minimum Phase 3 requirements)

You must provide at least basic admin-facing screens for:

- Upload file(s) and start a migration job.
- Column mapping (with suggestions).
- Validation view (table of rows, with inline error list and inline edit).
- Approval screen summarizing impact (counts, totals, new fields, GL impact).
- Commit + Rollback status view.
- History of past jobs for audit.

It doesn’t have to be pretty, but it has to be usable without going to the database manually.

---

## Phase 3 in one line

Phase 3 turns Twist ERP into a self-service onboarding/migration machine:

- You take any company’s old data,
- The system learns its shape,
- It extends the ERP data model if needed,
- It validates, stages, and gets approval,
- It imports cleanly with GL/stock impact,
- It can roll back.

This makes Twist ERP “plug and play” for a new company, with almost zero developer involvement. This is what unlocks rollout at scale in Phases 8–10.

Love it. Phase 4 is where Twist ERP becomes “self-configurable.” After this phase, a power user (not a developer) should be able to:

- add/change screens,
- add/change data structures,
- add/change workflows/approvals/automations,
- build and share dashboards,

…without touching code, and without breaking audit, RBAC, or upgradeability.

This is how Twist ERP stops being “ERP with settings” and becomes “ERP platform.”

We’ll break Phase 4 into the four builders:

1. Form Builder
2. Custom Module Builder
3. Workflow Studio
4. Dashboard Builder

For each: what it must do, how it interacts with metadata, security, audit, and how it fits with earlier phases.

At the end you’ll get a Phase 4 Deliverables Checklist.

---

## Phase 4

## 4.1 Form Builder

### Goal

Let an authorized admin design or edit any data-entry screen (Customer form, Purchase Order form, etc.) without code:

- Add/remove fields
- Rearrange layout
- Set required rules / validation / visibility by role
- Persist those changes back into metadata so runtime uses it immediately

### Scope

Form Builder must work for:

- Core entities from Phase 2 (Customer, Supplier, Item, PurchaseOrder, SalesOrder, APBill, ARInvoice, etc.)
- Custom entities created in Phase 4 (see Custom Module Builder below)
- Company-level overrides (Company A can change its form layout without affecting Company B even if both are in the same CompanyGroup)

### How it works

1. Admin opens Form Builder and chooses:

   - Target entity (e.g. `PurchaseOrder`)
   - Target scope:

     - “Group default” (Group Custom Layer → affects all companies in the CompanyGroup)
     - or “Company override” (affects only this one company)

2. The Form Builder loads:

   - The merged effective entity definition from metadata (Core → Industry Pack → Group Custom → Company Override)
   - The current form layout (sections, tabs, field positions, labels, read-only flags)

3. Admin can do:

   - Drag fields into sections
   - Hide a field
   - Mark a field required / optional
   - Change label
   - Set read-only for certain roles
   - Add a new custom field (if not in metadata yet)

4. If a new field is added:

   - The Form Builder will call the metadata layer to create this field in the correct layer:

     - Company Override or Group Custom

   - The field initially lives in that entity’s `extra_data` (JSONB) unless already promoted to a column
   - Version of EntityDefinition increases
   - AuditLog writes `action_type="FORM_FIELD_ADDED"`

5. Save/Publish:

   - The final form layout is stored as metadata:

     - a `form_layout_json` attached to that entity definition for that scope (group/company)

   - Version bump recorded with who changed it and when
   - AuditLog writes `action_type="FORM_LAYOUT_CHANGED"`

### Technical details

- Need a `form_definition` structure in the CompanyGroup DB:

  - `form_id`
  - `entity_id`
  - `scope_layer` ("group" or "company")
  - `company_id` (nullable if scope=group)
  - `layout_json` (sections, fields, order, tabs, validation rules)
  - `version`
  - `changed_by_user_id`
  - `changed_at`

- Runtime UI (Phase 2 screens) should NOT be hardcoded; it should render forms based on `form_definition.layout_json`.

  - Which means by Phase 4 you replace any temporary hardcoded Django/React form layouts with metadata-driven rendering.

### Permissions and audit

- Only roles with “Form Designer” or “Configuration Admin” permission can edit.
- All changes log an AuditLog entry in that CompanyGroup DB with the acting `user_id`, `company_id` (if company-scoped), `entity_id`, and diff summary.

---

## 4.2 Custom Module Builder

### Goal

Let an admin create an entirely new business object (a “module”) — for example:

- “Vehicle Maintenance Request”
- “Donation Campaign”
- “Quality Inspection Report”
- “Project Task”
- “Field Visit Log”

— without writing backend code.

This module should:

- Generate its own data table shape (metadata first, JSONB-backed at start)
- Have a form (via Form Builder)
- Appear in navigation/menu
- Be securable via RoleDefinition
- Participate in workflow approvals
- Be available to Dashboard Builder for reporting

### Scope

Custom Module Builder must cover:

- Entity definition
- Fields
- Relationships to existing entities
- Basic list view / detail view / create form
- Role access

### How it works

1. Admin clicks “New Module.”

2. Wizard asks:

   - Module name (singular/plural labels)
   - Purpose/category (e.g. “Quality”, “Maintenance”, “Project”, etc.) just for navigation grouping
   - Visibility (group-wide vs company-only)
   - Which company (if company-only)

3. Add fields:

   - Field name, label, type (text, number, date, money, dropdown, user picker, company picker, file attachment ref, etc.)
   - Required or optional
   - Default value
   - Visibility/readonly rules by role
   - Validation rules (regex, min/max, etc.)
   - Whether it can be filtered/reported (include in analytics)

4. Add relationships:

   - Link to existing entities (e.g. link to `Item`, `Supplier`, `Project`, `Customer`)
   - Cardinality (1-to-1, 1-to-many, many-to-many)
   - For example: “Each Maintenance Request can reference exactly 1 Asset from Asset module” or “Each Donation Campaign has many Pledge records”

5. Save module:

   - System creates a new entry in metadata (`EntityDefinition`) with:

     - `entity_id` (e.g. `maintenance_request`)
     - `layer_scope` ("group" or "company")
     - `definition_json` describing all fields and relationships
     - initial `version`

   - System creates a default `form_definition` for that entity.
   - System creates list view metadata:

     - which columns appear in the table/grid, default filters, sort.

   - RoleDefinition is updated / extended:

     - Add new permissions like `can_view_maintenance_request`, `can_edit_maintenance_request`, etc.

   - AuditLog entry: `action_type="CUSTOM_MODULE_CREATED"`

6. Storage:

   - At runtime, records of this new module are stored in a generic table pattern:

     - A physical table, e.g. `custom_entity_records` or one table per custom entity.
       There are two patterns you can choose:
       **Pattern A: one generic universal table**

   - Columns:

     - `record_id` UUID
     - `entity_id` text
     - `company_id`
     - `core_fields_json` jsonb
     - `extra_data` jsonb
     - timestamps

   - Pros: zero migrations per new module.
   - Cons: slower querying for heavy analytics.

   **Pattern B: one new physical table per module**

   - When module is created, system runs `ALTER DATABASE` / `CREATE TABLE module_<entity_id>` with:

     - `record_id` UUID PK
     - `company_id`
     - `extra_data` jsonb
     - timestamps

   - Fields start in `extra_data`.
   - If admin “promotes” a field, system runs `ALTER TABLE module_<entity_id> ADD COLUMN ...`
   - Pros: better performance later, easier reporting, matches how core entities work.
   - Cons: needs migration logic at runtime (but we already support promotion in Phase 1/2 logic).

   We already have column promotion logic in Phase 1, so Pattern B fits nicely and keeps your story consistent. We’ll go with Pattern B.

### Navigation

- The new module must appear in the UI menu for users with permission.
- The module’s list view uses the list definition metadata.
- Clicking into a row opens the form layout (which admin can then refine using Form Builder).

### Workflow support

- Immediately after module creation, admin can attach an approval / workflow definition for that module using Workflow Studio (see 4.3).

### RBAC

- The moment the module is created:

  - System must generate new permission flags in `RoleDefinition.permissions` for that CompanyGroup:

    - view / create / edit / approve / delete / export for that entity

  - Admin can assign those to roles through the existing Role/Permission matrix UI.

### Audit

- Each create/update/delete of records in the custom module must still write to `AuditLog` with:

  - entity_name = that module’s entity_id
  - record_pk = record_id
  - action_type = "CREATE","UPDATE","DELETE","APPROVE"
  - company_id, user_id, timestamp, role context

---

## 4.3 Workflow Studio

You already have Workflow Engine from Phase 1 (metadata-based graph of steps, approvers, escalations). Phase 4 takes this engine and exposes a visual no-code designer for business users.

### Goal

Let an admin visually build and change approval flows and automations:

- “If PO > $10,000 → send to CFO”
- “If stock variance > 5% → alert QC Manager and block posting”
- “When donor grant spend hits 80%, notify Program Director”
- “If SLA ticket is not closed in 4 hours, escalate to Tier 2”

No developer intervention.

### Core capabilities

1. Visual editor (drag-and-drop nodes):

   - Start / Trigger node:

     - On Create
     - On Status Change
     - On Threshold condition (amount > X, overdue days > Y)
     - On Scheduled check (daily at 8pm)

   - Condition node:

     - Comparisons on fields (`total_amount`, `urgency`, `company_id`, etc.)
     - Role checks (`requested_by.role == 'StoreManager'`)

   - Approval node:

     - Assigns approver role(s)
     - Sets SLA (approve within X hours)
     - Defines escalation target role if no response

   - Action node:

     - Change status field (e.g. `po.status = 'approved'`)
     - Send notification / reminder
     - Block posting to GL / block posting to stock ledger
     - Trigger follow-up workflow (child workflow, e.g. create a CAPA task in Quality)

2. Versioning:

   - Every save creates a new `WorkflowDefinition.version`.
   - Old versions remain read-only (for audit).
   - You can mark a specific version as “active.”
   - All “in-flight” documents continue under the version that was active when they started.

3. Scope layer:

   - Group scope workflow (applies to all companies in that CompanyGroup)
   - Company override workflow (like “Company B needs an extra approval step for any supplier > 5k USD”)

4. Enforcement:

   - The runtime Workflow Engine (already built in Phase 1) must consume these definitions exactly.
   - When a user tries to post something (e.g. post APBill to GL, post GRN to stock), Workflow Studio’s definitions determine:

     - allowed/not allowed
     - who must approve first
     - escalation if blocked

5. Audit:

   - Editing a workflow writes to AuditLog:

     - `action_type="WORKFLOW_CHANGED"`
     - includes who changed it, new version, diff summary

   - Every workflow action (request approval, approval given, escalation triggered, block enforced) is also logged per document.

### Technical metadata

Extend `workflow_definition` table in CompanyGroup DB:

- Add fields:

  - `ui_graph_json` (designer-friendly layout info: node positions, labels, colors)
  - `active_flag` bool
  - `scope_layer` ("group" / "company")
  - `company_id` nullable

- Link each workflow_definition to an `entity_id` (like `PurchaseOrder`, `APBill`, `custom.myInspectionForm`).

Workflow Studio updates `workflow_definition` rows instead of requiring code changes.

---

## 4.4 Dashboard Builder

### Goal

Let a non-technical power user create dashboards with widgets sourced from live ERP data, and share them with roles/companies.

These are NOT full-blown BI cubes yet. They’re live operational dashboards:

- “Top 10 overdue payables”
- “Stock aging”
- “Sales today vs target”
- “POs waiting approval”
- “Cash position per company”
- “Donor fund utilization %”

### Scope

Dashboard Builder must allow admins to:

- Create a dashboard
- Add widgets
- Bind each widget to a data source
- Filter by company / date / status
- Control who can see the dashboard (role-based + company-based)
- Save and publish

### Widget types (Phase 4 scope)

- KPI tile (single number, like “Total AP Overdue >30d”)
- Table/grid (top N records with columns)
- Simple bar/line chart (trend over time, by status, by warehouse, etc.)
- Alert list (workflow bottlenecks, exceptions)

No advanced drill-down is required yet, but we should store configuration in metadata.

### Data source model

We provide built-in query templates per module:

- AP aging summary
- AR aging summary
- Cash-on-hand summary (bank + cash GL accounts)
- Inventory valuation by item group
- Open POs by supplier
- Open SOs by customer
- Workflow bottlenecks (documents pending approval > X hours)

A widget is created by:

1. Picking a template
2. Applying filters (e.g. `company_id=CurrentCompany` or “All companies I’m allowed to see”)
3. Choosing display type (tile/table/chart)
4. Setting thresholds/alerts (e.g. red if AP overdue > 10M)

We store this as metadata.

### Metadata storage

Add `dashboard_definition` table in CompanyGroup DB:

- `dashboard_id` UUID PK
- `dashboard_name`
- `scope_layer` ("group" or "company")
- `company_id` nullable
- `visibility_roles` jsonb (which roles can view)
- `layout_json` (positions and sizes of widgets)
- `version`
- timestamps
- `changed_by_user_id`

Add `dashboard_widget_definition`:

- `widget_id` UUID PK
- `dashboard_id` FK
- `widget_type` ("kpi","table","chart","alert_list")
- `data_source_template` ("AP_AGING", "STOCK_VALUATION", etc.)
- `filters_json` (company filter, date range, status filter)
- `display_config_json` (chart axes, columns to show, thresholds)
- `order_index`
- timestamps

Frontend:

- Reads `dashboard_definition` for the user’s active company/role.
- Renders widgets accordingly.

Security:

- Only users whose role is in `visibility_roles` should be able to open that dashboard.
- If role has multi-company access (e.g. Group CFO), data aggregation can span multiple companies in that CompanyGroup DB.
- Otherwise, filter to `company_id` = active company.

Audit:

- Creating/updating a dashboard logs `action_type="DASHBOARD_CHANGED"` in AuditLog.
- Viewing a dashboard doesn’t need row-level audit per widget, but viewing sensitive dashboards (like finance consolidation) can still log `action_type="DASHBOARD_VIEWED"` if you want traceability.

---

## 4.5 How Phase 4 Uses Previous Phases

**From Phase 1:**

- We already have metadata model: EntityDefinition, WorkflowDefinition, RoleDefinition.
- We have the merge layering logic: Core → Industry Pack → Group Custom → Company Override.
- We have RBAC and audit logging.
- We have Workflow Engine runtime.

**From Phase 2:**

- We now have real entities for Finance, Procurement, Sales, Inventory.
- We have posting logic, approval flows, inter-company flows.
- We have AuditLog of document state changes.
- We have operational KPIs (AP aging, stock, etc.) that dashboards can expose.

**Therefore:**

- Form Builder modifies entity form layouts that render Phase 2 screens.
- Custom Module Builder creates net-new entities that behave like first-class citizens (can have workflows, dashboards, approvals).
- Workflow Studio edits/creates the actual rules driving all approval + blocking behavior for Procurement, Finance, Sales, Inventory AND any new custom module.
- Dashboard Builder surfaces live operational data to decision-makers with RBAC.

At the end of Phase 4, Twist ERP is not just configurable. It is admin-programmable.

---

## 4.6 Phase 4 Deliverables (Engineering Checklist)

When Phase 4 is done, Twist ERP must include:

### 1. Form Builder

- UI to edit form layout of any entity (core or custom).
- Ability to add/hide/relabel/reorder fields, set required/readonly, and set role-based visibility.
- Ability to create new custom fields directly from the form UI.
- Save layout to `form_definition` metadata with versioning + audit.
- Runtime forms in the app must render from this metadata, not hardcoded templates.

### 2. Custom Module Builder

- Wizard to create a brand-new entity/module.
- Define fields (data type, required, validation, visibility).
- Define relationships to existing entities.
- Choose scope: group-wide module or company-specific module.
- Auto-generate:

  - new `EntityDefinition`
  - new physical table `module_<entity_id>` with `extra_data`
  - default `form_definition`
  - default list view definition
  - new permission flags in `RoleDefinition.permissions`
  - menu/nav entry

- Audit of `CUSTOM_MODULE_CREATED`.

### 3. Workflow Studio (visual workflow designer)

- Drag-and-drop workflow builder that writes to `workflow_definition`:

  - Triggers, conditions, approval nodes, escalations, actions (block posting / send alert / change status).

- Version management (multiple versions, activate/deactivate).
- Scope layer support (group-wide or company override).
- Audit log for workflow edits (`WORKFLOW_CHANGED`).
- Runtime Workflow Engine must execute exactly what’s defined here for:

  - PurchaseRequisition, PurchaseOrder, GRN, APBill, APPayment
  - SalesOrder, Delivery, ARInvoice, ARReceipt
  - Inventory adjustments
  - Any custom module entities

### 4. Dashboard Builder

- Define dashboards as metadata (`dashboard_definition` + `dashboard_widget_definition`).
- Widget types: KPI tile, table/grid, simple chart, alert list.
- Bind widgets to prebuilt data source templates (AP aging, AR aging, stock valuation, pending approvals, etc.).
- Set filters (company, date range, etc.).
- Set access control (which roles can view).
- Save dashboards with version and audit (`DASHBOARD_CHANGED`).
- Runtime dashboard page renders from metadata and respects RBAC:

  - Single-company users see only their company’s slice.
  - Group CFO roles can see multi-company aggregate.

### 5. Security / RBAC Integration

- New permissions needed:

  - `can_design_forms`
  - `can_build_modules`
  - `can_edit_workflows`
  - `can_build_dashboards`

- These must be stored in `RoleDefinition.permissions` so that admin can assign them per role per company.
- UI should allow assigning these capabilities via the existing Role/Permission matrix from Phase 1.

### 6. Audit Integration

Every configuration change must create an AuditLog entry in that CompanyGroup DB with:

- `user_id`
- `company_id` (if company-scoped) or null if group-scope
- `action_type`: one of

  - `FORM_LAYOUT_CHANGED`
  - `FORM_FIELD_ADDED`
  - `CUSTOM_MODULE_CREATED`
  - `WORKFLOW_CHANGED`
  - `DASHBOARD_CHANGED`

- timestamp
- summary metadata (what entity, how many fields, etc.)

This gives you traceability for governance, and is required for finance/compliance teams later in Phase 7 (UAT / auditability).

---

## After Phase 4

After Phase 4, Twist ERP can:

- Be onboarded (Phase 3),
- Run operations (Phase 2),
- And then be tailored by the customer themselves using Phase 4 builders without source code changes.

That means by the end of Phase 4 you’ll be in a position to:

- Hand this to a new multi-company client,
- Import their data,
- Configure their approval rules and dashboards,
- Add that one weird module they need,
- And go live — without a dev writing custom code per client.

That is exactly the point where Twist ERP becomes scalable as a product, not just a project.

## Phase 5

## 5.1 Conversational AI Assistant

### Goal

Give every user an assistant panel inside Twist ERP that they can just talk to:

- “Show me overdue supplier bills.”
- “What’s blocking PO #4481?”
- “Create a sales order for 100 units for X Customer.”
- “Why did cash drop this week?”
- “Remind me my low-stock SKUs every morning.”

This assistant:

- understands context from the ERP,
- respects permissions,
- remembers conversation within the session,
- optionally learns user preferences long-term.

### 5.1.1 Assistant Panel UI

We add an always-available “Ask Twist” panel that opens like a chat sidebar.

Capabilities:

- You type natural language.
- Assistant replies in natural language and also shows structured data cards (tables, KPIs, links to records).
- Assistant can offer actions:

  - Buttons like “Approve PO” / “Post Invoice” / “Open Item” / “View Dashboard.”
  - You confirm instead of manually navigating.

Session model:

- Each panel session keeps short-term memory for the context of that chat (last queries, selected docs).
- You can reset/clear session.

### 5.1.2 RBAC & scope

Critical rule: The assistant never has more access than the human user.

So:

- The assistant runs under the user’s session:

  - `user_id`
  - `active_company_id`
  - `active_company_group_id`
  - that user’s role(s)
  - that user’s field-level visibility rules

If the Warehouse Manager asks “Show employee salaries,” assistant must refuse.
If the Group CFO asks “Show consolidated cash across all companies in my group,” assistant can do it.

We already built:

- RoleDefinition with `can_view_multiple_companies_in_group`
- Field-level visibility (“salary” field only visible to HR/Finance roles)
  That exact logic is reused here.

### 5.1.3 Audit

For every response that contains sensitive data, and for every action the assistant performs:

- Write AuditLog in the CompanyGroup DB with:

  - `user_id`
  - `company_id`
  - `action_type` (e.g. "AI_QUERY_FINANCE", "AI_ACTION_APPROVAL")
  - summary of what was asked / done
  - timestamp
  - role snapshot

This keeps compliance clean. During audit you can prove who saw what and who approved what via AI.

### 5.1.4 Conversation context storage

We need two types of memory:

**(a) Session context (short-term memory)**

- Lives in memory / cache / temp table keyed by `session_id`.
- Stores:

  - the list of “active records” (like PO #4481 was shown),
  - derived filters (like “overdue AP >30 days”),
  - pronoun and reference resolution (when the user says “that PR,” “those two invoices”).

- Expires when chat is cleared.

**(b) User AI Preferences (long-term)**

- A table per CompanyGroup DB, e.g. `user_ai_preferences`:

  - `user_id`
  - `company_id`
  - `preference_key` (e.g. "default_currency_display", "default_warehouse")
  - `preference_value` (jsonb)
  - timestamps

Examples:

- “From now on show money in BDT.”
- “Assume warehouse ‘Main Dhaka’ unless I say otherwise.”
- “Focus dashboards on AR first, not AP.”

Rules:

- These preferences are private per user unless marked “company-wide default,” which only high roles can set.
- Setting a preference writes to AuditLog (`action_type="AI_PREF_SET"`).

No passwords, no “auto-approve everything” stored here. If the user tries to set something risky, assistant must refuse.

---

## 5.2 AI Task Execution (“Do it for me”)

### Goal

Let the user not just ask “what,” but say “do it.”

Examples:

- “Approve PO 4481.”
- “Create a purchase requisition for 500 kg Dyes from Supplier BengalChem, delivery next week.”
- “Post AP Invoice INV-0098 to GL.”
- “Record payment of 120,000 BDT to supplier DeltaFab.”

### 5.2.1 Execution model

Important: The AI never bypasses business logic.

Instead, the AI acts as an orchestrator that calls the same backend service functions your normal UI would call. That means:

1. Parse intent:

   - User says: “Approve PO 4481.”

2. Check permissions via Workflow Engine:

   - Is PO 4481 in a state that needs approval?
   - Is this user an allowed approver for that step?
   - Does any threshold require CFO, not this user?

3. If allowed:

   - Call your existing service: `approve_purchase_order(po_id, acting_user_id)`.

4. Log in AuditLog:

   - `action_type="WORKFLOW_APPROVE"`
   - include `via_ai: true`
   - include old_status → new_status

If not allowed:

- Assistant explains “You are not an approver for this PO” or “This PO exceeds your limit and needs CFO approval per workflow rules.”

### 5.2.2 Confirmation flow

Any action that has financial or inventory impact must require explicit confirmation:

- Approving high-value PO
- Posting GRN that moves stock into inventory
- Posting ARInvoice / APBill to ledger
- Recording payment or receipt (cash/bank movement)

Flow:

- Assistant drafts summary:

  - “You are about to approve PO 4481 for 1,250,000 BDT from Supplier BengalChem. This will release it to Procurement and unblock GRN.”

- User must confirm: “Confirm approval” or click a confirmation button in UI.
- Only then call the service.

This protects you from “accidental approvals.”

### 5.2.3 Generated draft transactions

For creation flows:

- User: “Create PR for 2,000m fabric roll blue, urgent, for Dyeing Unit.”
- AI:

  1. Resolves which company_id we are in (Dyeing Unit).
  2. Resolves items (matches “fabric roll blue” to Item master).
  3. Builds a draft `PurchaseRequisition` record in that company.
  4. Returns the draft to the user as a preview form.
  5. User says “Submit.”
  6. AI submits it → which triggers normal PR workflow.

This means you will expose a “draft-create” and “confirm-create” endpoint for key docs (PR, PO, SO, etc.) so AI can operate cleanly.

---

## 5.3 Predictive Alerts & Early Warnings

This is the “proactive brain” side of Phase 5.
The assistant shouldn’t just answer “what you ask,” it should also say “hey, look at this.”

### Goal

Twist ERP should automatically warn the right users about risk conditions **before** things go wrong:

- Budget overrun risk,
- Stockout risk,
- SLA breach risk,
- AR cash-collection risk.

### 5.3.1 Alert Engine

We need an internal Alert Engine service that runs checks on a schedule and writes alert events.

These are not random AI guesses. They are structured triggers defined in metadata (and later tunable in Workflow Studio).

Examples:

**Budget / cost center overrun warning**

- Condition:

  - `actual_spend` in a cost center (based on GLEntry totals for that cost center this period)
  - vs `budget_limit` from Budget module / Cost Center module (Phase 6)
  - If projected to exceed limit before period end → alert Finance Controller and Cost Center Owner.

**Stockout risk warning**

- Condition:

  - `on_hand_qty` in StockBalanceSnapshot for Item X < `reorder_level`
  - OR based on moving average demand from recent SalesOrders
  - Alert: “Item X will stock out in ~3 days at current burn rate.”
  - Notify Warehouse Manager + Procurement.

**SLA breach / ticket escalation**

- Condition:

  - Support tickets or service orders approaching SLA limit without status change.
  - Alert Service Manager: “Ticket #882 is 90% of SLA window, still unassigned.”

**AR collection risk**

- Condition:

  - Large ARInvoice overdue + high amount + customer historically slow.
  - Alert AR team: “Customer A might default soon; outstanding 3.2M BDT, 45 days overdue, no recent receipts.”

We define, per alert type:

- trigger logic,
- severity,
- target roles to notify,
- company scope.

### 5.3.2 Delivery of alerts

The assistant panel becomes a notification surface.

The user will see:

- proactive messages in the assistant like:
  “⚠ Stock risk: Item DYE-BLUE-220 is projected to run out in 2.5 days in Warehouse Main Dhaka. Want me to draft a Purchase Requisition?”

User can then say “Yes, draft it,” and we go into the draft-create flow described earlier.

Also:

- Alerts are stored in a table like `ai_alert_queue` in each CompanyGroup DB:

  - `alert_id`
  - `company_id`
  - `alert_type` ("stockout_risk","budget_overrun_risk","sla_risk","ar_risk")
  - `severity`
  - `payload_json` (item, warehouse, amounts, due dates, etc.)
  - `status` ("new","acknowledged","dismissed","acting")
  - timestamps
  - `notified_user_id` or `notified_role`

### 5.3.3 Who gets which alert?

Access is still RBAC:

- Warehouse Manager sees stockout alerts for their warehouse/company only.
- Finance Controller sees budget/cash alerts for their company.
- Group CFO can get cross-company alerts (because they have multi-company permission).
- Service Manager sees SLA alerts.
  This means Alert Engine must check roles/permissions the same way as assistant queries.

### 5.3.4 AI explanation

When the assistant surfaces an alert, it should also explain cause in plain language using ERP data. For example:

- “Purchase Order 7712 for this item is still pending approval and won’t arrive in time. Approval has been waiting on CFO for 3 days.”

That explanation uses:

- Workflow state from Workflow Studio,
- Procurement data (PO still blocked),
- Inventory balance,
- Sales demand forecast.

Now the AI is doing real operational coaching, not just static KPIs.

---

## 5.4 Learning Loop / Metadata Feedback

We don’t just want AI to help users. We also want the system to learn from how users interact with AI and use that to improve templates and packs.

This touches your Industry Packs.

### Goal

Use AI + usage signals to improve:

- Industry Packs,
- Company customizations,
- Field definitions,
- Approvals.

### 5.4.1 Field usage insights

Phase 3 / Phase 4 allow adding custom fields and custom modules. Over time:

- We can track which custom fields get referenced a lot in AI queries.
  Example:

  - Users keep asking: “Show me stock by GSM and Shade.”
  - GSM and Shade are custom textile fields in this CompanyGroup.

We log those references and rank them.
Then we can tell the Group Admin:

> “Everyone is querying ‘Shade’ across inventory dashboards and AI. Do you want to promote ‘Shade’ to a first-class field (indexed column, visible in default forms, part of the industry template for textile manufacturing)?”

That’s the feedback loop:

- AI observes usage → proposes to formalize it → admin clicks yes → we run promotion (ALTER TABLE) using the mechanism from Phase 1.

### 5.4.2 Workflow bottleneck insights

The assistant can analyze workflow logs:

- “PR approvals in Dyeing Unit are consistently waiting 2+ days at step ‘GM Approval’.”
- Suggest:

  - Add escalation,
  - Lower threshold for low-value PR to auto-approve,
  - Add backup approver role.

This is improving Workflow Studio definitions using data, not guesswork.

### 5.4.3 Dashboard suggestions

Assistant notices:

- User keeps asking the same AR aging question every morning.
  It can suggest:

> “Do you want a dashboard widget ‘AR Overdue Last 30 Days’ visible on your home screen and shared with AR team?”

If user accepts:

- Automatically creates a Dashboard Builder widget (Phase 4 feature),
- Adds it to their dashboard,
- Logs `DASHBOARD_CHANGED` audit entry.

### 5.4.4 Industry pack evolution (admin level)

For a super-admin role (you, the vendor / system integrator), you can review patterns across different customers (this is outside per-tenant, so this is only if/when you aggregate learnings across installs — depends on your product model).

Inside a single install:

- The AI can still suggest:
  “This NGO company created a ‘Donor Compliance Report’ module with fields X, Y, Z. Do you want to mark this as base template for all companies in this CompanyGroup so new entities auto-get these fields?”

This locks in repeatable best practices inside one CompanyGroup.
That’s huge for Phase 9+ rollout: you’re standardizing processes without writing code.

---

## 5.5 Phase 5 Deliverables (Engineering Checklist)

When Phase 5 is complete, Twist ERP must have:

### 1. Assistant Panel (Chat UI)

- A persistent “Ask Twist” chat sidebar in the app.
- Session memory for short-term context (references like “approve #2”).
- Ability to render:

  - natural language responses
  - structured results (tables of overdue AR, list of POs waiting approval, KPI tiles)
  - action buttons (“Approve”, “Create PR”, “Open record”)

- Ability to switch company context if the user has multi-company permission (e.g. Group CFO can say “Now show for Subsidiary B”).

### 2. RBAC-aware AI layer

- Every AI request runs under the user’s session (`user_id`, `company_id`, roles).
- Field-level masking (salary, bank account, donor-sensitive fields, etc.).
- If the user tries to access something they can’t see, assistant must refuse, not hallucinate.
- Every sensitive response logs an AuditLog entry with `action_type="AI_QUERY_*"`.

### 3. Action Execution via Assistant

- Natural language → structured intent.
- Assistant calls actual backend service functions (approve PO, post invoice, create PR draft, etc.).
- Hard actions require confirmation.
- After execution, we write standard audit entries:

  - e.g. workflow approval → `WORKFLOW_APPROVE` with `via_ai: true`
  - posting to GL → `POST_GL` with `via_ai: true`
  - stock posting → `POST_STOCK` with `via_ai: true`

No alternate bypass path. AI is just another frontend.

### 4. User AI Preferences store

- Table (per CompanyGroup DB) like `user_ai_preferences`:

  - `user_id`, `company_id`, `preference_key`, `preference_value`, timestamps.

- Assistant can set/query these preferences:

  - “Show currency in BDT”
  - “Default warehouse is Main Dhaka”
  - “Focus AR overdue first”

- Writing preferences logs `action_type="AI_PREF_SET"` in AuditLog.
- Dangerous preferences (like “auto-approve everything”) must be blocked or escalated to admin.

### 5. Alert Engine & Predictive Warnings

- Background alert checks for:

  - Budget/cost center overrun risk
  - Stockout risk (based on on-hand + demand trend)
  - SLA breach risk
  - High-risk receivables

- Writes alerts into `ai_alert_queue` with:

  - `company_id`, `alert_type`, severity, payload_json, timestamps.

- Maps alerts to roles/users based on RBAC:

  - Warehouse → stock alerts
  - Finance Controller → budget/AR/AP alerts
  - Service Manager → SLA alerts
  - Group CFO → cross-company alerts

- Assistant surfaces alerts proactively with explanations and next-step buttons (“Draft PR now?” “Escalate ticket?”).

## Phase 6

### 6. Workflow + Approval Explanation

- Assistant can explain WHY something is blocked:

  - Pulls workflow instance state, pending approver, SLA timer, etc.
  - “PO 4481 is waiting CFO approval because amount is above 10,000 USD. It’s been pending 3 days, SLA is 24h, escalation is next to CEO.”

- This uses Workflow Studio metadata and Workflow Engine runtime from Phase 4 / Phase 1.

### 7. Dashboard & Module Suggestions (Learning Loop)

- Track what the user repeatedly asks the AI.
- If repetitive, assistant can:

  - Offer to build a dashboard widget (using Dashboard Builder metadata).
  - Offer to promote a commonly referenced custom field to “first-class” (run the promotion pipeline to add column + index).
  - Offer workflow tweaks (e.g. escalation rules) based on bottleneck analysis.

- Accepting a suggestion triggers:

  - a metadata update in EntityDefinition / DashboardDefinition / WorkflowDefinition,
  - version bump,
  - AuditLog entry: `DASHBOARD_CHANGED`, `FORM_FIELD_PROMOTED`, or `WORKFLOW_CHANGED` with `via_ai: true`.

### 8. Compliance & Logging

- Every AI-driven read of sensitive financial/HR data and every AI-driven state change is logged in `AuditLog`, tied to:

  - `user_id`, `company_id`, timestamp, action_type, record_pk, and `via_ai: true`.

- This satisfies audit and UAT requirements later (Phase 7).

### 9. Performance / Rate limiting

- The AI layer must call your own query/metrics layer (the same layer Dashboard Builder uses).
  That reduces direct raw-SQL spam.
- Cache expensive summaries per user/session for a short window (e.g. AP aging across all suppliers for a company).
- Apply per-user rate limits so a single user can’t spam 100 complex cross-company “explain everything” queries.

---

## 5.6 What Phase 5 changes in Twist ERP overall

After Phase 5:

- Users can run Twist ERP mostly through conversation.
- The system actively warns them about risk, not just shows static dashboards.
- AI can explain “why” something is blocked, not just “what” is blocked.
- AI can actually do work (with confirmation and audit), not just show data.
- The platform can evolve itself:

  - adding fields,
  - adding dashboards,
  - tightening workflows,
  - tuning approval SLAs,
    driven by real usage patterns.

And critically:
All of it is still inside the guardrails you already built in Phases 0–4:

- RBAC and field visibility from Phase 0/1
- Workflow enforcement from Phase 1/4
- Finance / Inventory / Procurement / Sales posting logic from Phase 2 (service layer)
- Metadata / no-code builders / dashboards from Phase 4
- Migration and custom fields from Phase 3

So Phase 5 doesn’t sit “outside” Twist ERP.
Phase 5 _is Twist ERP’s brain_, plugged into the same audited, permissioned, multi-company-safe core.

# Twist ERP — Phase 6 Specification

**Phase 6: Advanced / Vertical Modules, Budget Governance, and Full Finance**

---

## 0. Phase 6 Mission

Phase 6 turns Twist ERP from “ERP with modules” into “an operational governance platform.”

By the end of Phase 6, Twist ERP will:

- Control how money is allowed to leave the organization.
- Control how physical stock is requested, issued, and replenished.
- Control how departments can create commitments (PR, PO, service spend, capex requests).
- Track who broke budget, who approved it, and penalize them in KPIs.
- Plan and execute manufacturing capacity based on material, machine and labor.
- Run donor-funded programs and microfinance field operations.
- Enforce quality, compliance, asset lifecycle, people cost/availability, and SLA obligations.
- Tie all of this back into Finance, which becomes a first-class, auditable financial core.

This phase includes:

1. Budget & Cost Control Module (governance of spend, KPI impact, bottom-up budgeting)
2. Procurement Governance + Store Integration + Price Tolerance Control
3. Finance Module (elevated as a core class module)
4. Production & Manufacturing with Planning (MPS / MRP / Capacity)
5. HR & Workforce Management (full lifecycle)
6. NGO & Microfinance
7. Project & Task Management
8. Asset Management
9. Policy & Document Control
10. Quality & Compliance
11. SLA / Service Management
12. Cross-cutting features: Workflow Studio integration, AuditLog, KPI dashboards, budget enforcement, and AI hooks (from Phase 5)

Everything here is assumed to run in a multi-company environment, with cost centers, workflow approvals, field-level role-based access, and audit.

---

## 1. Core Governance Concepts (Foundational to Phase 6)

### 1.1 Cost Center

A cost center represents a department, branch, production line, program, grant, or other spending “owner.”

Each cost center has:

- `cost_center_id`
- Linked `company_id`
- Owner (`cost_center_owner_user_id`) and backup approver
- Default currency/base of reporting
- KPI tracking for financial discipline

All spend is associated with a cost center.  
All budgets are assigned to cost centers.  
All KPI penalties are reported against cost centers.

---

### 1.2 Procurement Class

Every item / service / capex line in the system MUST belong to exactly one `procurement_class`:

- **`stock_item`**  
  Physical consumables or materials held in inventory (spares, bearings, chemicals, raw materials, stationery, packaging).  
  Controlled by Store. There is stock, GRN, and on-hand quantity.

- **`service_item`**  
  Intangible spend (consulting fees, marketing services, external audits, external lab tests, outsourced training, travel agency services).  
  No stock, no warehouse, no GRN. Department requests it directly, but only Procurement can buy it.

- **`capex_item`**  
  Capital acquisitions (machinery, vehicles, servers, generators, major tools).  
  Becomes an asset in Asset Management and is depreciated. Approval path is stricter (finance/top management).

`procurement_class` drives:

- Who is allowed to initiate the request.
- Which approval workflow applies.
- Whether Store is involved.
- How/when budget usage is consumed.
- Which KPIs are impacted.

---

### 1.3 Budget Types

Every approved budget is split into logical buckets. We support multiple parallel budget types:

- **Operational / Production Budget**  
  Day-to-day production / operations: consumables, spares, process chemicals, overtime labor, utilities.

- **Expenditure / OPEX Budget**  
  General departmental expenses: marketing, travel, training, consultancy, admin services.

- **Capex Budget**  
  One-time asset purchases that go to Asset Management and generate depreciation.

- **Revenue Budget / Target**  
  Forecasted income per business unit, grant program, branch, etc.  
  (This is tracked as performance, not “consumed” like cost.)

Budgets are defined for time periods (month, quarter, FY, or project period).

---

### 1.4 Budget Record and Budget Line

A **Budget Record** is a container for a cost center’s budget for a given period and type.

A **Budget Line** is the enforceable unit under that record.

**Budget Line fields:**

- `budget_line_id`
- `budget_id` (link to the parent Budget Record)
- `procurement_class` (`stock_item` | `service_item` | `capex_item`)
- For stock_item: `item_id` or `item_category_id`
- For service_item: `service_category_id`
- For capex_item: `capex_asset_category` or specific capex item
- `qty_limit` (max allowed quantity this period)
- `value_limit` (max allowed spend this period)
- `standard_price` (expected price per unit / per service)
- `tolerance_percent` (e.g. 5%)
- `period_start`, `period_end`
- `budget_owner_user_id` (person accountable for approving/controlling this budget line)

**Critical rule:**  
No request (internal requisition, purchase requisition, capex request) can reference an item/service/capex that does NOT exist as a budget_line, unless it goes through an explicit Out-of-Budget exception approval (see below).

---

### 1.5 Budget Usage Tracking

For each budget_line we will maintain actual consumption in real time:

- `qty_used` (how much of the item or service has been consumed)
- `value_used` (monetary value consumed)
- Breakdown by source:
  - store issue,
  - PO/GRN/AP Bill,
  - capex acquisition,
  - etc.

Budget usage is updated when:

- Store issues stock to a department (for `stock_item`)
- Procurement confirms and Finance posts AP Bill for a `service_item`
- Procurement finalizes capex PO and Store/Asset Management receives the capex item (for `capex_item`)

This enables “Remaining Budget” visibility at any moment.

---

### 1.6 Out-of-Budget / Override Spending

The system supports controlled “break the budget” events.

- A department / store / project / manager can request an item/service/capex _even if_:
  - it’s not in any budget_line, OR
  - the remaining qty/value is already exhausted, OR
  - it exceeds financial limits.

This goes into **Out-of-Budget Exception Workflow**:

1. The request is flagged “Out-of-Budget.”
2. It automatically routes to the `budget_owner_user_id` for that cost center/budget area.
3. That owner must explicitly approve or reject.
4. If approved:
   - The spend is allowed to continue (to Procurement, to Store issue, etc.).
   - The system marks this as an “Out-of-Budget Spend Event.”
   - This event is stored and penalizes that cost center’s KPI.
   - Finance can see this and leadership can escalate.

In other words: nothing is completely blocked forever — but any bypass creates a permanent trace and a KPI penalty.

---

### 1.7 KPI Tracking for Budget Discipline

For each cost center (and period), we will calculate KPI stats such as:

- `out_of_budget_spend_count`
- `out_of_budget_spend_value`
- `over_tolerance_approval_count`
- `emergency_purchase_count`
- `unplanned_capex_flag_count`

These KPI metrics become part of performance evaluation for departments, production lines, branches, grant owners, etc.  
Upper management and Finance will see which cost centers are behaving financially and which ones are constantly escalating.

---

### 1.8 Bottom-Up Budget Submission

Before a new period (new month/quarter/FY/project cycle), **each cost center owner MUST submit their proposed budget** in the system:

- They propose:

  - stock_item needs (quantities and expected prices),
  - service_item needs (training, marketing, contractors, audits),
  - capex_item plans (machines, vehicles),
  - optional revenue targets.

- They also propose `standard_price` assumptions and `tolerance_percent`.

- That “Proposed Budget” goes into a workflow:

  - Cost center owner → Department Head → Finance Controller → Top Management / CFO.

- Finance & Management can:

  - Accept or reduce quantities,
  - Adjust standard_price,
  - Adjust allowed tolerance,
  - Assign final `budget_owner_user_id` for that line,
  - Lock it.

- The final approved budget lines become “Active Budget Lines” for that period.  
  Those are then enforced by the system in all requisitions/PRs/POs/GRNs.

This ensures:

- Bottom-up forecasting captured inside Twist ERP (not Excel).
- Top-down control published as hard system rules.
- Traceability: “You requested 1.2M, we approved 900k, you spent 880k by mid period.”

---

## 2. Procurement Governance and Store Integration

### 2.1 Authority Separation

- **Departments / Users (Production, Maintenance, Marketing, etc.):**

  - They can REQUEST, but they CANNOT BUY.
  - They submit either Internal Requisition (for stock_item) or External Purchase Requisition (for service_item / capex_item).
  - They must choose cost center and budget line.

- **Store / Warehouse:**

  - Receives Internal Requisitions for `stock_item`.
  - Issues stock if available.
  - If stock is insufficient, Store raises a Purchase Requisition (PR) to Procurement to replenish.
  - Performs GRN (Goods Receipt Note) for physical deliveries.
  - Can quality-hold received items if suspicious.

- **Procurement:**

  - The ONLY team allowed to create Purchase Orders (PO) to suppliers.
  - Must perform budget validation and price tolerance validation.
  - Must follow Workflow Studio approvals.
  - Cannot bypass price/tolerance rules.
  - Cannot buy without a PR and without the required approvals.

- **Budget Owner / Cost Control Owner:**
  - Approves Out-of-Budget requests.
  - Approves over-tolerance price events.
  - Receives alerts for suspiciously cheap purchases.
  - Their approvals (or denials) affect KPI scoring.

---

### 2.2 Flows by Procurement Class

#### A. `stock_item` Flow

1. Department raises an **Internal Requisition** for stock_item.
2. System checks:
   - Budget line exists for that cost center and period?
   - Remaining qty/value available?
3. If within budget:
   - Requisition goes to Store.
4. If NOT within budget:
   - System triggers Out-of-Budget Exception Workflow → `budget_owner_user_id` must approve.
   - If approved, it’s recorded as Out-of-Budget (negative KPI).
5. Store action:
   - If stock in warehouse: Store issues material.
   - If no stock: Store creates PR to Procurement (Store still does NOT create PO).
6. Procurement receives PR from Store and:
   - Validates the budget line.
   - Checks price tolerance (see below).
   - Generates PO, sends to supplier.
7. Store performs GRN when goods arrive.
8. Store can mark “quality hold,” which can block AP Bill posting in Finance if material is questionable.

Consumption of budget is updated:

- On Store issue (internal consumption),
- On Procurement purchase if it represents replenishment tied to a known budget line.

#### B. `service_item` Flow

1. Department raises an **External Purchase Requisition (PR)** for a service_item (e.g. marketing agency, audit service, consultant).
2. System checks:
   - Budget line exists and has remaining value?
3. If yes:
   - PR goes to Procurement.
4. If NOT:
   - Out-of-Budget Exception Workflow triggers.
   - `budget_owner_user_id` must approve this overrun.
   - If approved, the spend is tagged Out-of-Budget (KPI negative).
5. Procurement:
   - Performs vendor selection/quotation.
   - Checks price vs `standard_price ± tolerance_percent`.
   - Creates PO only after approvals are satisfied.
6. The service is delivered.
7. Procurement / Finance records AP Bill against that PO.
8. Budget usage is updated when the AP Bill is posted.

No Store/GRN is involved because it's not physical stock.

#### C. `capex_item` Flow

1. Management / Engineering / Project raises a **Capex Purchase Requisition** for a capex_item.
2. System checks:
   - Is this item part of an approved Capex Budget Line?
3. If yes:
   - Goes to capex approval workflow (Finance controller, top management).
4. If NOT:
   - Triggers Out-of-Budget Exception Workflow AND flags `unplanned_capex_flag_count`.
   - Requires approval by budget_owner_user_id (often CFO/MD/Board level).
   - If approved, this is a KPI-negative event for that cost center or project.
5. Procurement:
   - After approvals, Procurement negotiates and creates PO.
   - Must respect price tolerance rules.
6. Store (or Asset Management) performs GRN for the physical asset.
7. Asset gets registered in Asset Management.
8. Finance starts depreciation.

---

### 2.3 Price Tolerance Enforcement

Each budget_line has:

- `standard_price`
- `tolerance_percent` (e.g. 5%)

When Procurement enters vendor pricing in the PO:

**Over-price case:**  
If `vendor_price > standard_price * (1 + tolerance_percent)`:

- System blocks automatic PO approval.
- Procurement must request an explicit approval from `budget_owner_user_id`.
- If they approve, this over-tolerance event is tagged.  
  KPI impact: Negative.
- All logged to AuditLog.

**Suspiciously cheap case:**  
If `vendor_price < standard_price * (1 - tolerance_percent)`:

- Procurement IS allowed to continue (you’re not blocking savings).
- System automatically alerts:
  - budget_owner_user_id,
  - Store/Quality (for `stock_item`),
  - Engineering (for `capex_item`).
- At GRN, Store can hold the item in “quality hold,” which:
  - prevents automatic AP Bill finalization,
  - triggers inspection / QC validation.
- KPI impact:
  - Not automatically negative.
  - But appears in dashboards as “review required: is quality compromised OR should we re-baseline standard_price?”

All tolerance checks and approvals are auditable and attached to final spend records.

---

### 2.4 Emergency Purchase Path

For true exceptional breakdowns:

- Users can raise “Emergency PR” (must flag EMERGENCY).
- Still routed through Procurement.
- Auto-alerted to budget_owner_user_id and Finance immediately.
- Automatically scored as an emergency event (tracked in KPI if repeatedly abused).
- Must be reconciled to budget and inventory after-the-fact.
- Cannot silently bypass Procurement.

---

## 3. Finance Module (First-Class Core Module)

The Finance module is now treated as a central pillar. It is the source of financial truth and is deeply integrated with Budget, Procurement, Manufacturing, HR, Microfinance, Capex, and Compliance.

### 3.1 General Ledger (GL)

- Multi-company chart of accounts.
- Journal / Journal Lines with:
  - account
  - amount
  - cost_center_id
  - project_id
  - grant_id/program_id (for NGO)
  - asset_id
- Period open/close, locking of historical periods.
- Multi-currency support.
- Intercompany tracking (for CompanyGroup-level operations).

### 3.2 Accounts Payable (AP)

- Supplier/Vendor master.
- AP Bills (Vendor Invoices), usually created from:
  - PO + GRN for stock_item/capex_item
  - PO + service delivery confirmation for service_item
- AP approvals (Finance Controller, budget_owner_user_id if over tolerance, etc.).
- AP Aging.
- Payments:
  - Record supplier payment, post to GL (credit cash/bank, debit AP).
- Can be blocked by QC hold if Store/Quality flagged “suspiciously cheap / failed inspection.”

### 3.3 Accounts Receivable (AR)

- Customer master.
- AR Invoices for:
  - Sales Orders / Deliveries,
  - Service tickets (SLA module),
  - Microfinance loan interest/fees,
  - Donor billables (if applicable).
- Receipts:
  - Record incoming payments, post against invoice in GL.
- AR Aging, overdue chase tracking, bad debt provisioning workflow.

### 3.4 Cash & Bank

- Maintain bank accounts and cash accounts.
- Post payments/receipts to correct accounts.
- Support basic bank reconciliation.
- Cash-in-transit control (e.g. microfinance field officer collections not yet deposited).

### 3.5 Fixed Assets & Depreciation

- Integrates with Asset Management:
  - Capex PO/GRN registers an asset.
  - Finance assigns depreciation method, useful life.
- Periodic depreciation runs:
  - Debit Depreciation Expense
  - Credit Accumulated Depreciation
- Asset disposal workflow posts gain/loss to GL.

### 3.6 Manufacturing Costing & COGS

- When production consumes materials and labor (from Production & Manufacturing module):
  - Move cost into WIP / Finished Goods inventory.
- When goods ship / sell:
  - Post COGS:
    - Debit COGS
    - Credit Inventory/Finished Goods
- Track variances between:
  - Standard BOM cost vs Actual consumption.
  - Post variance to variance accounts in GL.

### 3.7 NGO Grant / Program Accounting

- Every cost line (AP Bill, Journal, etc.) can carry `grant_id`, `program_id`.
- Finance can generate donor spend reports by category vs approved donor budgets.
- Overspend on restricted donor funds triggers compliance red flags.

### 3.8 Microfinance Integration

- Loan disbursement:
  - Debit Loan Portfolio (asset)
  - Credit Cash/Bank
- Repayment:
  - Debit Cash
  - Credit Loan Portfolio (principal recovery)
  - Credit Interest Income / Penalty Income
- Write-off workflow:
  - Approved via Workflow Studio,
  - Post bad debt expense.

### 3.9 Payroll Posting from HR

- HR runs payroll (salaries, allowances, deductions, overtime).
- Finance receives final payroll journal:
  - Debit salary expense (split by cost center / grant / program / project)
  - Credit payroll liabilities (payables, statutory deductions)
- Tracks employee advances and loan recoveries.

### 3.10 Budget Enforcement & KPI Visibility

Finance is embedded in the budget governance loop:

- Reviews and approves all cost center proposed budgets.
- Sets or adjusts standard_price and tolerance_percent per budget_line.
- Approves capex budgets.
- Can block or allow Out-of-Budget requests in escalated cases.
- Sees KPI dashboards:
  - Out-of-Budget spend volume per department/branch,
  - Over-tolerance approvals,
  - Emergency spend count,
  - Unplanned capex,
  - Donor compliance violations.

Finance is the final escalation layer.  
Finance owns the integrity of “what was allowed vs what was actually spent.”

---

## 4. Production & Manufacturing (with Planning)

### 4.1 Core Manufacturing Entities

- **BOM (Bill of Materials)**  
  Components, quantities, yield/scrap assumptions.
- **Work Order / Production Order**  
  Which product to make, how much, which line, due date, status.
- **Material Issue / Consumption**  
  Consumes `stock_item`s from Inventory, posts cost to WIP.
- **Production Receipt**  
  Moves finished goods into stock, finalizes cost.

### 4.2 Master Production Schedule (MPS)

- High-level production commitments:
  - Item/variant
  - Quantity
  - Target completion date/shipping date
  - Priority
- Inputs:
  - Confirmed Sales Orders
  - Forecast demand
  - Safety stock thresholds

### 4.3 Material Requirements Planning (MRP)

- Explodes MPS + BOM.
- Calculates required raw/semi-finished materials.
- Compares against current on-hand stock.
- Identifies shortages → generates:
  - Internal Requisitions for stock transfer/issue, OR
  - Purchase Requisition to Procurement.

These shortages are checked against Budget Lines (`stock_item`) and cannot proceed without budget coverage or Out-of-Budget approval.

### 4.4 Capacity Planning / Scheduling

- Assign Work Orders to:
  - specific work centers/machines,
  - specific shifts/days.
- Factors:
  - Machine capacity
  - Machine downtime (from Asset Management)
  - Labor availability (from HR/attendance)
  - Setup/changeover time
- Outputs:
  - Detailed production schedule
  - Late risk alerts
  - “Bottleneck work center” visibility
- Workflow Studio can escalate if a high-priority order is projected late (notify Production Manager, Procurement, Sales, etc.).

### 4.5 Cost Posting to Finance

- On completion:
  - Actual material + labor + overhead cost rolled into Finished Goods inventory.
  - Variance between standard BOM cost and actual is tracked and posted to variance accounts in Finance.

This connects production execution directly to Finance and Budget consumption.

---

## 5. HR & Workforce Management

HR is a full module, not an add-on. It drives cost, capacity, compliance, and payroll integration into Finance.

### 5.1 Employee Master & Org

- Employee profile (ID, grade/band, designation)
- Assigned department / cost_center_id
- Supervisor hierarchy
- Work location / shift group
- Employment status (active, leave, exited)
- Integrated with Policy & Document Control for mandatory acknowledgements

### 5.2 Attendance, Shift, Overtime

- Shift definitions (day/night/rotating).
- Attendance capture:
  - biometric import,
  - manual supervisor input,
  - GPS/mobile check-in for field staff (important in microfinance/branch model).
- Overtime calculation rules per grade or department.
- Feeds:
  - Payroll (overtime payout),
  - Production Capacity (labor availability by shift),
  - SLA staffing (who is on duty for service tickets).

### 5.3 Leave & Holiday

- Leave types (annual, sick, unpaid, etc.).
- Accrual policies per grade.
- Leave request workflow via Workflow Studio.
- Blackout periods (e.g. “no leave during shutdown”).
- Leave approval affects:
  - payroll pay,
  - production capacity planning,
  - SLA coverage.

### 5.4 Payroll & Compensation

- Salary structure (basic, allowances, deductions).
- Overtime payouts, incentive components.
- Advances / loans to employees, tracked and recovered.
- Payroll run (monthly/weekly/etc. per company).
- Final payroll journal posted to Finance:
  - Debit salary expense per cost center / grant / project,
  - Credit liabilities/payables.

### 5.5 Recruitment & Onboarding

- Job requisition workflow (request to hire).
- Candidate pipeline.
- Onboarding checklist:
  - required documents,
  - role assignment,
  - issue initial assets (laptop/PPE/etc.),
  - policy acknowledgements.
- Automatically ties new hire to cost_center_id and to budgeted headcount/cost.

### 5.6 Performance & Appraisal

- Periodic review cycles (quarterly/annual).
- Goals, KPIs, ratings, raise/increment recommendations.
- Approved increments affect next cycle’s budget proposals (HR pushes updated payroll cost forecast into Budget Module so Finance sees expected salary increases).

### 5.7 Disciplinary / Exit

- Incident/disciplinary records, link to Policy & Document Control (which SOP/policy was violated).
- Final settlement:
  - Leave encashment,
  - Deduction for unreturned assets (Asset Management check),
  - Final payroll payout.
- Finance posts settlement journal.

---

## 6. NGO & Microfinance Suite

### 6.1 Grant & Program Management (NGO)

- **Grant:**
  - Donor,
  - allowed cost categories,
  - reporting frequency,
  - restricted uses.
- **Program / Project under Grant:**
  - Region/site,
  - output targets,
  - time window.
- **Spend Tagging:**
  - Every AP Bill / Journal Line can be tagged with:
    - `grant_id`,
    - `program_id`.
- Budget enforcement:
  - If a spend would exceed donor restriction or program allocation, Workflow Studio blocks or escalates.
- Donor reporting:
  - Spend vs approved donor budget, by category and period.

This behaves like a special cost center + budget line model, but with donor compliance rules.

### 6.2 Microfinance

This submodule supports small-loan operations, collections, delinquency, and branch officer accountability.

Core elements:

- **Client / Group Registry:**
  - Individual borrowers and/or group lending (joint liability groups).
  - KYC/ID, assigned field officer, center/branch.
- **Loan Product:**
  - Interest model (flat/declining),
  - Tenure,
  - Installment plan,
  - Fees/penalties,
  - Funding source (donor fund / internal capital).
- **Loan Origination Workflow:**
  - Field officer applies,
  - System checks exposure limits and repayment history,
  - Approval routing through Workflow Studio (Branch Manager → Credit Officer → HQ).
- **Disbursement:**
  - Posts to Finance:
    - Debit Loan Portfolio (asset),
    - Credit Cash/Bank.
- **Repayment Tracking:**
  - Record installment receipts per client/group,
  - Split principal / interest / penalty,
  - Track overdue days.
- **Delinquency / PAR:**
  - Portfolio At Risk metrics (30+ days late etc.).
  - Workflow escalation for high-risk groups.
- **Savings / Deposits (optional):**
  - Track savings balances for clients/groups (liability to the org).
- **Branch / Officer KPIs:**
  - Disbursement volume,
  - Collection rate,
  - PAR,
  - Cash still in transit (not deposited yet),
  - These feed Finance dashboards and HR performance incentives.

Microfinance also feeds Payroll incentives for field officers and compliance analytics for Finance and donor reports.

---

## 7. Project & Task Management

### 7.1 Project

- `project_id`, `company_id`
- Owner / manager
- Cost center link
- Schedule (start/end dates, completion status)
- Budget association (operational, capex, donor-funded)
- KPI: on-time vs late, budget vs actual, emergency purchases triggered.

### 7.2 Task

- `task_id`
- Assigned user
- Deadline, priority
- Status (todo / in_progress / blocked / done)
- Dependency graph

### 7.3 Cost Tracking

- Materials consumed for the project (stock_item issues) → hit project budget lines.
- Services procured for the project (service_item PRs) → hit project budget lines.
- Capex purchased for the project (capex_item PRs) → becomes asset on completion.
- Labor time from HR timesheets/attendance can optionally be costed to the project.

### 7.4 Workflow Integration

- Overdue/high-priority tasks trigger Workflow Studio escalation.
- Management dashboards show:
  - % tasks blocked,
  - spend vs project budget,
  - schedule risk.

---

## 8. Asset Management

### 8.1 Asset Lifecycle

- Asset register:
  - asset_id,
  - asset category,
  - acquisition cost,
  - PO reference,
  - assigned location / cost center / responsible person.
- Integration to capex budget lines.

### 8.2 Maintenance & Downtime

- Maintenance tickets / preventive maintenance schedules.
- Downtime tracking.
- Downtime feeds Production Capacity Planning (machine availability).
- SLA module can also generate maintenance tickets if servicing customer equipment under contract.

### 8.3 Depreciation

- Asset assigned depreciation method, useful life, salvage value.
- Finance auto-posts depreciation journal:
  - Debit Depreciation Expense,
  - Credit Accumulated Depreciation.
- Disposal workflow:
  - Approval for sale/scrap,
  - Post gain/loss to Finance.

### 8.4 Handover & Exit

- HR onboarding: assign asset to employee (laptop, phone, PPE).
- HR exit: ensure asset returned or deduct from final settlement.
- This closes asset compliance and reduces loss.

---

## 9. Policy & Document Control

### 9.1 Controlled Documents

- Versioned SOPs, safety procedures, HR policies, donor compliance rules, internal governance policies.
- Each has:
  - version number,
  - effective date,
  - status (draft / approved / published / archived),
  - owning department,
  - Workflow Studio approval before publish.

### 9.2 Acknowledgement Tracking

- Assign required policies to roles or to individual employees.
- Track which employees have acknowledged which version.
- Unacknowledged = non-compliant.

### 9.3 Compliance Linkage

- QC incidents, safety incidents, disciplinary actions can be linked to:
  - “Which SOP/policy version was in force when this violation occurred?”
- HR onboarding requires acknowledgment of mandatory policies.
- SLA teams and production floor teams can be forced to read updated SOPs.

---

## 10. Quality & Compliance

### 10.1 QC Checkpoints

- At GRN (incoming material):
  - Store can hold items in “quarantine” if they look substandard, especially if Procurement purchased below the expected price (“suspiciously cheap”).
- In-Process / Final QC:
  - Record test results, tolerance specs, pass/fail outcomes.
  - Associate QC checks with Work Orders / Batches.

### 10.2 Quarantine & Release

- Quarantined materials cannot be issued to production and AP Bill might be held.
- Workflow route: Quality / Procurement / budget_owner_user_id / Finance must clear or reject.
- This connects Procurement pricing decisions to actual delivered quality.

### 10.3 NCR (Non-Conformance Report) and CAPA

- When QC fails:
  - Create NCR,
  - Assign root cause and corrective & preventive action plan (CAPA),
  - Assign owner and due date.
- Workflow Studio escalates unresolved CAPA.
- KPIs:
  - NCR recurrence,
  - Rework/scrap cost,
  - Supplier quality score.

### 10.4 Vendor Quality Scoring

- Based on QC passes/fails, quarantine events, and CAPA escalations.
- Procurement sees this when selecting vendors next time.
- Finance sees this when approving supplier invoices.

---

## 11. SLA / Service Management

### 11.1 Tickets

- Internal IT tickets, customer support tickets, maintenance tickets for installed assets.
- Ticket fields:
  - requester / customer,
  - asset (optional),
  - severity/priority,
  - SLA target (response time, resolution time),
  - assigned user/team,
  - current status (new / assigned / in_progress / waiting / closed / escalated).

### 11.2 SLA Enforcement

- SLA definitions per contract / per service type.
- Workflow Studio:
  - If nearing SLA breach (e.g. 90% of resolution time elapsed while still open), auto-escalate to Tier 2 or Manager.
- HR integration:
  - Who is on shift / available to respond?
- KPI:
  - SLA compliance %,
  - number of escalations,
  - overdue high-priority tickets.

### 11.3 Billing

- Resolved/closed service tickets can generate billable lines.
- Those lines become AR Invoices in Finance.
- Revenue from service support can appear alongside SLA KPIs in dashboards.

---

## 12. Cross-Cutting: Workflow Studio, AuditLog, Dashboard Builder, KPIs, AI Hooks

### 12.1 Workflow Studio Integration

All approvals and escalations MUST run through the metadata-driven Workflow Studio (from Phase 4):

- Budget approval (cost center proposed budget → Finance → Management).
- Out-of-Budget Exception approvals (must reach `budget_owner_user_id`).
- Over-tolerance price approvals.
- Capex approvals (CFO/CEO).
- Leave approvals (HR).
- Loan approvals (Microfinance).
- NCR/CAPA escalation (Quality).
- SLA escalation for overdue tickets.
- Production late-risk escalation (notify Production / Procurement / Sales).
- Quarantine release approvals for suspicious materials.
- Emergency purchases (escalate to Finance instantly).

No business-critical approval is hard-coded in UI; it’s defined in Workflow Studio and versioned/audited.

---

### 12.2 AuditLog

Every critical financial/operational/compliance event writes to AuditLog with:

- `user_id`
- `company_id`
- `entity_name` (PO, BudgetLine, WorkOrder, Asset, PayrollRun, etc.)
- `record_pk`
- timestamp
- `action_type`
- special flags:
  - `out_of_budget: true/false`
  - `over_tolerance: true/false`
  - `emergency: true/false`
  - in future: `via_ai: true/false` (if initiated by the AI assistant)

Examples of audited events:

- BudgetLine approved / changed
- Out-of-Budget spend approved
- Over-tolerance purchase approved
- PR → PO commit
- Capex approval
- GRN with quality hold
- QC NCR created & CAPA escalated
- Payroll posted to GL
- Loan disbursement, write-off approval
- SLA escalation
- Policy published / acknowledged

This audit trail enables legal defensibility and internal review.

---

### 12.3 Dashboard Builder & KPIs

Every module emits data that becomes available to Dashboard Builder (from Phase 4). We will expose the following KPIs/widgets for Phase 6:

- **Budget & Cost Control**

  - Budget vs Actual (qty & value)
  - Remaining budget per cost center
  - Out-of-Budget spend count/value (penalty KPI)
  - Over-tolerance approvals count
  - Emergency purchase events

- **Finance**

  - Cash position
  - AP Aging
  - AR Aging / overdue customers
  - Donor spend vs donor budget (NGO)
  - Microfinance PAR (Portfolio At Risk)
  - Intercompany balances
  - Payroll cost by cost center

- **Manufacturing**

  - Production schedule adherence
  - Capacity utilization
  - Late-risk orders
  - Scrap / rework rate
  - Material shortages blocking production

- **HR**

  - Attendance / shift coverage
  - Overtime cost
  - Leave utilization
  - Headcount vs approved/budgeted headcount cost
  - Performance cycle status

- **NGO & Microfinance**

  - Spend vs grant budget
  - Compliance breaches (donor restriction violations)
  - PAR %
  - Field officer cash-in-transit

- **Project Management**

  - Project progress vs plan
  - Budget burn vs approved budget
  - Blocked tasks

- **Asset Management**

  - Asset downtime
  - Upcoming maintenance
  - Depreciation values this period vs plan

- **Quality & Compliance**

  - NCR open/closed
  - Supplier quality score
  - Quarantine holds

- **SLA / Service**
  - SLA compliance %
  - Overdue high-priority tickets
  - Escalation count
  - Revenue from service work

All dashboards must respect RBAC and company scope.  
A cost center manager only sees their cost center.  
Group CFO / HQ role can view consolidated cross-company.

---

### 12.4 AI Assistant Hooks (Phase 5 Integration)

Phase 6 modules are designed so the AI assistant (Phase 5 capabilities) can:

- Explain “why something is blocked”
  - e.g. “This PO was blocked because price exceeded tolerance and budget owner hasn’t approved.”
- Summarize status
  - “Your cost center has already used 88% of spares budget, and you requested another Out-of-Budget issue.”
- Suggest next actions
  - “Production for SKU A will be 2 days late due to machine downtime. Escalate to Maintenance?”
  - “Loan group XYZ is at high risk (PAR 30+). Schedule field visit?”
  - “Marketing PR is out-of-budget. Request approval from budget owner?”
- Review compliance
  - “These 3 policies are still unacknowledged by line staff, which ties to repeated QC nonconformance.”

All AI-triggered actions will still hit Workflow Studio for approval and log AuditLog with `via_ai: true`.

---

## 13. Phase 6 Deliverable Summary

By the end of Phase 6, Twist ERP will deliver:

1. **Budget & Cost Control Module**

   - Cost Centers and ownership.
   - Budget submission workflow from each cost center (bottom-up forecasting).
   - Budget approval and locking by Finance/Management.
   - Budget Lines with procurement_class, qty/value limits, standard_price, tolerance_percent, budget_owner_user_id.
   - Live Budget Usage tracking.
   - Mandatory budget check for all requests.
   - Out-of-Budget Exception Workflow (with KPI penalty).
   - KPI tracking per cost center (Out-of-Budget count, over-tolerance approvals, emergency purchases, etc.).

2. **Procurement & Store Governance**

   - Internal Requisition flow for `stock_item`.
   - External Purchase Requisition flow for `service_item`.
   - Capex Purchase Requisition flow for `capex_item`.
   - Store as gatekeeper for physical (`stock_item`) demand and GRN, but never directly buying.
   - Procurement as the only team allowed to create POs.
   - Price tolerance enforcement (block over-price, alert on suspiciously cheap).
   - Quality hold at GRN that can block AP Bill.
   - Emergency PR escalation with immediate Finance visibility.

3. **Finance Module (Core Class)**

   - GL, AP, AR.
   - Cash & Bank, bank reconciliation, cash-in-transit.
   - Fixed Assets & Depreciation.
   - Manufacturing costing & COGS posting.
   - Payroll journal posting (HR → Finance).
   - Donor/grant accounting and reporting.
   - Microfinance loan accounting (disbursement, repayment, PAR).
   - Intercompany and consolidation.
   - Budget oversight and KPI visibility.

4. **Production & Manufacturing**

   - BOM, Work Orders, Material Issue, Production Receipt, WIP costing.
   - Master Production Schedule (MPS).
   - Material Requirements Planning (MRP).
   - Capacity Planning (machines, labor shifts, downtime).
   - Late-risk alerts and escalation via Workflow Studio.
   - Direct link into Finance cost postings and Budget consumption for stock_item.

5. **HR & Workforce Management**

   - Employee master, org structure, cost center assignment.
   - Attendance / shift / overtime tracking (including field/GPS for microfinance/remote staff).
   - Leave management with approvals.
   - Payroll generation and GL posting.
   - Recruitment, onboarding checklist, asset issuance, policy acknowledgements.
   - Performance reviews and increments feeding next-period budget planning.
   - Exit process with asset return and final settlement.

6. **NGO & Microfinance**

   - Grant and Program budgeting, spend tagging, donor compliance, overspend blocking.
   - Loan products, origination approval workflow, disbursement posting, repayment, delinquency (PAR), savings balances.
   - Branch/officer KPIs (collection rate, PAR, cash-in-transit).
   - Integration to Finance (loan portfolio as asset, interest/penalty as income).

7. **Project & Task Management**

   - Project definition, owner, timeline, cost center link.
   - Tasks with assignment, priority, deadline, status.
   - Spend tracking by project (materials, services, capex, labor).
   - Overdue tasks escalation through Workflow Studio.
   - Project health dashboards (progress vs spend vs deadlines).

8. **Asset Management**

   - Asset register (capex item → asset).
   - Preventive and corrective maintenance tickets.
   - Downtime logging and effect on production capacity.
   - Depreciation scheduling and GL posting.
   - Asset assignment to employees (HR onboarding/offboarding).
   - Disposal approval workflow, gain/loss posting.

9. **Policy & Document Control**

   - Versioned SOPs/policies with Workflow Studio approval before publish.
   - Role-based acknowledgement tracking.
   - Linking SOP versions to QC incidents, disciplinary actions, onboarding.
   - Compliance dashboards: who is not trained/compliant.

10. **Quality & Compliance**

    - QC checkpoints at GRN, in-process, finished goods.
    - Quarantine/Release flow with AP Bill/Inventory blocking.
    - NCR and CAPA tracking with deadlines and escalation.
    - Supplier quality scoring visible to Procurement.
    - KPIs for NCR recurrence, scrap/rework, and repeated vendor failures.

11. **SLA / Service Management**

    - Ticket capture (internal IT or external support).
    - SLA timer and escalation via Workflow Studio.
    - Billing integration to AR for billable service work.
    - SLA performance KPIs, per team and per shift.

12. **Cross-Layer Infrastructure**
    - Workflow Studio as the single approval/escalation engine for ALL processes above.
    - AuditLog capturing every approval, override, GRN hold, payroll post, loan disbursement, capex approval, etc.
    - Dashboard Builder surfacing KPIs in finance terms, production terms, HR terms, compliance terms.
    - AI Assistant hooks capable of:
      - explaining block reasons (“PO blocked due to tolerance breach and awaiting budget owner approval”),
      - surfacing risk (“Your cost center has 3 Out-of-Budget approvals this month”),
      - recommending next actions (“Escalate CAPA for recurring NCR?”),
      - summarizing performance (PAR levels, SLA breaches, budget burn).

---

**Phase 6 is the layer where Twist ERP stops being a passive system of records and becomes an active enforcer of spending discipline, operational discipline, compliance discipline, and delivery discipline across the entire organization.**
