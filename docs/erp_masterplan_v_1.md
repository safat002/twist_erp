# ERP Masterplan (Visual, Drag-and-Drop, Multi-Company, AI-Assisted)
**Version:** 2.1  
**Date:** October 27, 2025  
**Status:** Expanded Functional + Technical Blueprint

---

## 1. Vision

We are developing a next-generation ERP platform that is:

- **Plug-and-play** with prebuilt industry templates (Manufacturing, NGO, Trading/Distribution, Retail/POS, Services/Telco, etc.).
- **Visually configurable** using drag-and-drop for forms, workflows, dashboards, schema, and even new modules.
- **AI-assisted and self-evolving**, able to ingest legacy data and reshape itself (new fields, new attributes, new logic) with minimal human effort.
- **Multi-company / multi-tenant**, supporting inter-company transactions and group consolidation.
- **Self-hosted or LAN-hosted**, capable of running offline on a normal office PC (Windows or Linux) with optional internet exposure.
- **Secure and auditable**, with role-based control and immutable financial trails.

The objective is not “an ERP product,” but “a business operating system” that bends to each organization without needing developers.

---

## 2. Core Product Philosophy

1. **Pre-built best practice**  
   When a company is created, the user selects the Nature of Business. That selection loads a full “Industry Pack” which includes:
   - Chart of accounts / ledger groups OR fund/grant structure.
   - Standard processes and approval flows.
   - Pre-modeled entities (Customer, Supplier, Work Order, Grant, etc.) and their fields.
   - Prebuilt dashboards and KPIs.
   - Standard statutory/compliance fields.
   - Default reports.
   The company starts on Day 1 with a usable ERP “template,” not a blank database.

2. **Self-evolving model**  
   The ERP data model is metadata-driven. Admins can add new fields, relationships, and even whole custom entities visually. These updates:
   - Are stored in metadata.
   - Update the database storage layer.
   - Instantly appear in forms, workflows, dashboards, reporting, and AI.

3. **Schema adapts to legacy data**  
   During migration, if uploaded data has columns the ERP doesn’t have yet, the system can propose creating those new fields automatically and attaching them to the right entity. No developer required.

4. **No-code control of processes**  
   Business admins (not engineers) can:
   - Add approval logic.
   - Add workflow steps.
   - Add automation triggers.
   - Add dashboard KPIs.
   - Add brand-new modules.

5. **AI is embedded in the workflow**  
   AI is visible as a “side panel” in every screen, not a separate chatbot. It understands current context (record, module, user role) and can answer, explain, warn, and suggest.

6. **Low-friction deployment**  
   The system is designed to run on commodity hardware in a small office, serve users over LAN, work offline (PWA), and keep data under the customer’s control.

---

## 3. Top-Level Objectives

- Be usable by an SME without a dedicated IT department.
- Migrate historical data fast, without painful cleanup.
- Allow deep customization without code.
- Enforce finance/audit integrity even when the model changes.
- Scale from a single company to a multi-company group with inter-company flows.
- Keep ownership of data local and private.
- Use AI in a way that’s helpful, permission-aware, and cost-controlled.

---

## 4. System Architecture Overview

### 4.1 Multi-Company / Multi-Tenant Core

**Business behavior**
- One installation can host multiple companies/tenants.
- Each company has its own:
  - Base currency, fiscal year, tax/VAT rules.
  - Chart of accounts (or donor fund tree if NGO).
  - Workflows and approval chains.
  - Dashboards and KPIs.
- Inter-company transactions:
  - Company A raises a sales invoice to Company B.
  - Company B automatically gets a purchase entry.
- Consolidation:
  - Group-level reporting (P&L, balance sheet, cash flow) across companies.

**Technical**
- `company_id` scoping on all transactional tables by default.
- Optional per-company schema or DB for high isolation.
- Consolidation logic queries across companies and applies elimination rules.
- Role/permission layer includes which companies a user can access.

---

### 4.2 Industry Packs ("Nature of Business")

**Business behavior**
- On company creation, user picks the industry profile:
  - Manufacturing / Garments / Factory
  - NGO / Donor-funded org
  - Trading & Distribution / FMCG
  - Services / Telco / SLA-driven
  - Retail / POS
- The selected Industry Pack loads:
  - Predefined entities and relationships.
  - Predefined workflows (e.g. Requisition→PO→GRN→Bill→Payment).
  - Predefined dashboards.
  - Predefined approval roles.
  - Predefined standard reports.
  - Predefined chart of accounts or fund/grant structure.

**Technical**
- Industry Packs are versioned bundles of metadata + starter data.
- Each pack contains:
  - Entity definitions (fields, data types, validation rules, relationships, cardinality, visibility).
  - Workflow definitions (graph of steps, conditions, routing rules).
  - Dashboard definitions (widgets, queries, layouts).
  - Permission templates (roles, default access rules).
- Applying an Industry Pack = seeding metadata tables and base records for that company.
- Packs can evolve. New versions of a pack can diff/merge into an existing tenant (with admin approval).
- Packs can be extended: the company's admin can add new fields to any packed entity. Those extensions are stored as tenant-level overrides.

---

### 4.3 Metadata-Driven Schema Layer

**Business behavior**
- Every “thing” the ERP tracks (Customer, Item, Invoice Header, Invoice Line, Supplier, Work Order, Grant, Asset, etc.) is modeled as an **Entity**.
- An Entity has:
  - Fields (with labels, types, validation, allowed values)
  - Relationships to other Entities
  - Security/visibility flags
  - Audit classification (financially sensitive? HR sensitive? etc.)

**Technical**
- Metadata tables define:
  - `entity_definition`
  - `field_definition`
  - `relationship_definition`
  - `workflow_definition`
  - `dashboard_definition`
- UI builders, workflow engine, report builder, AI assistant, and APIs all read from this metadata at runtime.
- When a new field is added:
  - Metadata entry is created.
  - Physical layer is updated (see 4.5).
  - Auto-generated forms and CRUD endpoints are updated.
  - Report Builder and Dashboard Builder see the new field automatically.

---

### 4.4 Visual Schema Designer

**Business behavior**
- Admins see a diagram of all entities, with their fields and how they connect.
- Clicking an entity opens:
  - Field list (name, label, type, required, default, dropdown options, visibility in forms/grids/exports/AI).
  - Relationships (to other entities, with cardinality).
- Admins can:
  - Add fields.
  - Mark fields required/optional.
  - Attach those fields to forms and workflows.
  - Add relationships with defined cardinality and cascade.

**Technical**
- The diagram is a live view of metadata.
- Editing the diagram updates metadata.
- A schema reconciliation service:
  - Applies ALTER TABLE (for promoted fields), or
  - Adds JSONB keys (for flexible fields), or
  - Updates relationship metadata and foreign key constraints.
- Changes are versioned and audited.

---

### 4.5 Physical Storage Strategy

**Business behavior**
- The ERP must accept new fields immediately (during migration or during normal use) without waiting for a developer.

**Technical model**
- Hybrid storage:
  - **Core columns:** Stable, high-use, compliance-critical data is stored as normal columns with indexes.
  - **Flexible extension:** New or rarely-used fields are initially stored under `extra_data` (JSONB or similar) per record.
  - **Promotion path:** Admin can later "Promote to First-Class Field" which:
    - Creates a physical column.
    - Backfills from JSONB.
    - Adds indexing.
- Reporting / dashboards can query both physical columns and JSONB fields.
- Performance tuning can focus on promoted columns.

---

### 4.6 Workflow & Event Bus Layer

**Business behavior**
- Workflows describe how documents move: e.g. Purchase Requisition → Approval → Purchase Order → GRN → Bill → Payment.
- Rules like "If PO > $5,000 require CFO approval" are configurable.
- Alerts, escalations, and SLA timers can be defined.

**Technical**
- Central event bus publishes events (`Invoice.Created`, `Stock.Low`, `Timesheet.Submitted`).
- Workflow Runtime subscribes and executes flow steps.
- Workflow definitions are stored in metadata as graphs of nodes:
  - Trigger nodes
  - Condition nodes
  - Approval nodes
  - Action nodes (create task, send email, update record field, block next step, escalate)
- The Workflow Runtime evaluates conditions against live entity data (including custom fields that were added later).
- All workflow actions are audited.

---

### 4.7 AI Layer

**Business behavior**
- AI is a side panel available everywhere.
- It understands the screen context: "You are viewing Sales Order #SO-0091 for Customer X".
- It can:
  - Explain what you're seeing.
  - Answer questions about policy.
  - Highlight risks (budget overrun, credit limit breach, QC hold stock, etc.).
  - Suggest next steps ("raise PO", "schedule maintenance", "send reminder").

**Technical**
- Local LLM(s) for natural language.
- Retrieval layer that pulls:
  - Entity data (limited by role permissions),
  - Policies / SOP documents,
  - KPI history.
- Intent parser converts user questions into queries on metadata-driven entities.
- Role-awareness ensures AI cannot display restricted fields (salary, donor-sensitive fund balances, etc.) unless the user role can already see them directly.

---

### 4.8 Deployment Model / Runtime Environment

**Business behavior**
- Run on a normal office PC.
- Serve all office users over LAN.
- Optionally expose secure remote access.
- Continue working during internet outages.

**Technical**
- Backend: Python/Django or FastAPI-style service layer, plus a workflow runtime and AI runtime.
- DB: Bundled PostgreSQL with extensions (JSONB, indexing).
- Frontend: Web app (React/Vue/Svelte style) packaged as PWA.
- Optional GPU acceleration for AI inference.
- Offline sync for PWA clients (queue writes, reconcile on reconnect).
- Versioned updater with rollback and snapshot capability.

---

## 5. Data Migration Engine (Onboarding Layer)

### 5.1 Source Ingestion

**Business behavior**
- User can upload Excel/CSV or connect to an old DB to bring in:
  - Customers, Suppliers, Items
  - Chart of Accounts / Donor Funds
  - Opening Balances
  - Stock on hand by location/bin
  - Historical Invoices, Purchase Orders, Work Orders, Grants, etc.

**Technical**
- Every upload creates a Migration Session record.
- Raw files are stored for audit.
- The system profiles the data using heuristics + semantic matching.

### 5.2 Profiling & Detection

**Business behavior**
- The system automatically says "This sheet looks like Customer Master" or "This looks like Invoices (header+lines)."

**Technical**
- Column name similarity, value pattern recognition, and known industry terms from the active Industry Pack.
- Classification tries to map sheets to known Entities from the metadata.
- It also tries to infer header/line structures where repeated values imply parent-child.

### 5.3 Mapping UI

**Business behavior**
- Side-by-side mapping:
  - Left: legacy columns (CustName, Tel, AreaCode, etc.)
  - Right: target fields in the ERP model (Customer.name, Customer.phone, Customer.territory)
- System auto-links most columns.
- User can drag/drop to fix the rest.
- Corrections are saved as a reusable import template.

**Technical**
- Mapping suggestions are stored in metadata as `import_mapping_profile` for that tenant.
- Mapping confidence (high/medium/low) is surfaced to user.
- Mappings can be re-used for incremental imports (monthly donor spend, daily sales, etc.).

### 5.4 Schema Extension During Import

**Business behavior**
- If the legacy data has columns not present in the ERP model (e.g. `CreditRating`, `TerritoryZone`, `IMEI`, `Shade/GSM`), the system proposes adding those as new fields.
- Admin confirms.
- Those fields become part of the entity for this tenant.

**Technical**
- For each new column:
  - Guess data type (text/number/date/dropdown based on unique values).
  - Create metadata entry in `field_definition` under the right entity.
  - Add to storage (`extra_data` initially).
  - Update available fields in forms, reports, dashboards, workflows, and AI context.
- This means migration actively evolves the schema.

### 5.5 Cleaning & Normalization

**Business behavior**
- Before import, system proposes cleanup:
  - Normalize date formats.
  - Normalize currency formats.
  - Suggest dropdowns from repeated values.
  - Fix casing/whitespace.
  - Attempt duplicate merge (same supplier with tiny spelling difference).
  - Offer default fill-ins for required-but-missing fields ("PaymentTerms = NET30 for all missing?").

**Technical**
- Cleaning rules are captured and can be replayed on future imports.
- Deduping can create merge maps ("Legacy Supplier ABC01" → "Supplier ID 118") stored for future reconciliation.
- Address or contact splitting (FullName → first_name + last_name) can be defined as a transform step.

### 5.6 Validation, Staging, Publish

**Business behavior**
- After mapping/cleaning:
  - Validate referential integrity (invoice lines reference existing items/customers).
  - Validate business rules (no future-dated GRN if policy forbids it).
  - Validate regulatory rules (tax fields cannot be blank where mandatory).
- Rows are grouped:
  - ✅ Ready to import
  - ⚠ Fixable with proposed defaults
  - ❌ Blocked, with reason
- User can import good rows now, download error sheet for the rest.
- Imported data first lands in **staging tables**.
- An authorized approver promotes staging → live.

**Technical**
- Staging tables mirror the metadata model.
- Promotion to live is transactional.
- Every row imported is tagged by Migration Session ID.
- We log field-level before/after if we update existing records.

### 5.7 Rollback & Audit

**Business behavior**
- Admin can "Undo This Import" if something is wrong.
- Audit trail shows:
  - Who imported.
  - When.
  - Source file checksum.
  - What entities/fields were touched.

**Technical**
- Soft rollback by tracking which records were inserted/updated in that session.
- For updated records, store pre-update snapshot for reversal.

---

## 6. No-Code Builders

These builders turn the platform into a self-service system for admins.

### 6.1 Form Builder

**Business behavior**
- Drag-and-drop UI fields onto forms for any entity.
- Mark fields required, read-only, hidden, conditional.
- Add sections, tabs, repeatable line items.
- Add inline validation (e.g. "Credit Limit cannot exceed 50000 unless role = CFO").

**Technical**
- Form layouts are metadata objects linked to entities/roles.
- Conditional visibility and validation rules are stored as expressions referencing entity fields.
- Versioning allows draft vs published forms.

### 6.2 Custom Module Builder (Entity Builder)

**Business behavior**
- Create a brand-new entity (e.g. "Franchise Outlet Audit", "Machine Calibration Log").
- Define fields, relationships, and permissions in a wizard.
- Instantly get:
  - List view
  - Detail view
  - Edit form
  - API endpoints

**Technical**
- Creates new `entity_definition` and `field_definition` rows.
- Creates DB backing (flexible storage first, columns on promotion).
- Auto-registers endpoints, permissions, workflow hooks, and reporting availability.

### 6.3 Workflow Automation Studio

**Business behavior**
- Visual flow editor with nodes:
  - Trigger (event/time/manual)
  - Condition (if/else on data)
  - Approval step
  - Action (notify, assign task, update record, block next step)
  - Escalation (SLA breach)
- Used for procurement approvals, credit approvals, QC gates, donor spend authorization, etc.

**Technical**
- Workflows are stored as graphs in metadata.
- Runtime engine listens to event bus and evaluates each workflow.
- Role-based access to approve nodes.

### 6.4 Dashboard / Homepage Builder

**Business behavior**
- Drag-and-drop KPI cards, charts, tables, task lists, alerts, and AI insights onto role dashboards.
- Each role (CFO, Store Manager, Production Manager, Donor Manager, Project Manager) can have a homepage.

**Technical**
- Dashboard definitions stored as metadata (`dashboard_definition`).
- Widgets reference entity queries. Queries are built from metadata (so they can handle custom fields).
- Access to widgets respects permissions.

---

## 7. Business Modules (Functional Layer)

Each module:
- Ships with defaults from the Industry Pack.
- Can be extended (fields, workflows, dashboards) by the admin.
- Interacts with other modules through shared entities and the event bus.

For each module below we describe:
1. **Purpose**
2. **Core Flow / How It Works**
3. **Integration With Other Modules**
4. **Technical Notes**

---

### 7.1 Finance & Accounting

**Purpose**
- General Ledger (GL), Accounts Payable (AP), Accounts Receivable (AR), tax/VAT, cash/bank, budgeting, and consolidation.

**Core Flow**
- All operational modules (Purchase, Sales, Payroll, etc.) post entries into Finance automatically.
- Finance manages:
  - Chart of Accounts (or Grant/Fund tree for NGOs).
  - Journals and adjustments.
  - AP (supplier bills, due dates, payments).
  - AR (customer invoices, collections, aging).
  - Tax/VAT calculations and returns.
  - Closing periods.
- Budget vs Actual is monitored per cost center.

**Integration**
- Procurement → AP.
- Sales → AR.
- Payroll → GL.
- Inventory valuation → COGS postings.
- Cost Centers and Projects link spend and revenues to budgets/donors.
- Inter-company postings generate mirror entries in sister companies.

**Technical Notes**
- Finance entities are marked "financially critical" in metadata.
- Certain core finance fields (amount, tax rate, posting date, ledger account) are protected: users can extend them with analytic tags (Region, DonorCode, etc.) but cannot delete/reshape them.
- Consolidation queries run across companies, applying elimination rules.
- Audit trail is immutable for posted journals.

---

### 7.2 Procurement / Purchase

**Purpose**
- Control spend from request to payment, maintain supplier relationships, enforce approvals and budgets.

**Core Flow**
1. Requisition / Purchase Request (PR).
2. Approval workflow (conditions based on amount/category/budget availability).
3. Purchase Order (PO) issuance to supplier.
4. Goods Receipt Note (GRN) at warehouse.
5. Supplier Invoice (Bill).
6. Payment scheduling and posting to AP.

**Integration**
- Inventory module updates stock on GRN.
- Finance/AP module gets bills and schedules payments.
- Budget module checks if spend is within the allocated cost center budget.
- Quality/Compliance module can inject QC hold steps before GRN is accepted.

**Technical Notes**
- Procurement workflows are metadata-defined and editable in Workflow Automation Studio.
- Supplier master is an entity in metadata, so admins can add custom fields like ComplianceRating, LeadTimeDays, etc.
- The event bus emits `PO.Approved`, `GRN.Received`, `Invoice.Matched`; Finance listens and posts accounting entries.

---

### 7.3 Inventory / Warehouse / Materials

**Purpose**
- Track quantity, location, valuation, and quality status of stock.

**Core Flow**
- Items/SKUs are defined with UoM, category, batch/lot rules, expiry.
- Stock movements:
  - GRN increases stock.
  - Issue to production decreases raw materials.
  - Production receipt creates finished goods.
  - Sales shipment decreases finished goods.
- Stock adjustments follow approval workflows.
- Bin- / location-level tracking with quarantine and QC states.

**Integration**
- Procurement feeds GRN.
- Production consumes and produces inventory.
- Sales dispatch consumes finished goods.
- Finance pulls valuation snapshots and posts inventory/cost-of-goods-sold.
- Quality/Compliance module can mark lots as "on hold" or "rejected".

**Technical Notes**
- Item, Batch, Lot, Bin, StockLedger are entities in metadata.
- Custom attributes like Shade, GSM, DyeLot, SerialNo can be attached per tenant via Visual Schema Designer or migration.
- IoT (barcode/RFID scanners) can push stock movement events into the event bus.

---

### 7.4 Sales & CRM

**Purpose**
- Manage leads, quotations, orders, dispatch, invoicing, and receivables.

**Core Flow**
1. Lead / Opportunity (pipeline view).
2. Quotation.
3. Sales Order with credit check.
4. Delivery / Dispatch.
5. Sales Invoice.
6. Collection / Receipt.

**Integration**
- Inventory is reserved/allocated for Sales Orders.
- Finance/AR manages invoicing and collections.
- Cost Center / Budget may track revenue targets.
- AI can surface “credit limit exceeded” warnings from Finance.
- Customer Service/SLA module (if service industry) can attach active service tickets and SLA status to the Customer entity.

**Technical Notes**
- Customer entity is metadata-driven: admins can add TerritoryZone, ChannelType, CreditRating fields.
- Sales workflow (quote→order→invoice) is editable in the Workflow Automation Studio.
- Event bus emits `SalesOrder.Confirmed`, `Invoice.Created`, etc. Finance and Inventory consume these.

---

### 7.5 Production / Manufacturing (Manufacturing Pack)

**Purpose**
- Plan and record production execution, material usage, and output quality.

**Core Flow**
1. Bill of Materials (BOM) defines required materials per finished good (multi-level allowed).
2. Work Order / Production Order is opened.
3. Materials are issued to the line.
4. Operator/machine/line efficiency and WIP are tracked.
5. QC checkpoints (inline, final).
6. Finished goods are received back into Inventory.

**Integration**
- Inventory is decremented for raw material issues and incremented for finished goods.
- Finance posts WIP and COGS.
- Quality/Compliance records inspections and rejections.
- Cost Center/Budget can compare planned vs actual cost.
- Asset Management can track machine maintenance needs based on runtime.

**Technical Notes**
- BOM, WorkOrder, OperationStep, QCCheck are entities defined in metadata.
- Admin can add fields like MachineID, NeedleType, ShadeBatch, Style/Color/Size breakdowns.
- Event bus captures `WorkOrder.Started`, `QC.Fail`, `FG.Received` and triggers dashboards, alerts, and postings.

---

### 7.6 NGO / Grant / Project Accounting (NGO Pack)

**Purpose**
- Track donors, grants/funds, budget allocations, program spend, and donor reporting.

**Core Flow**
1. Donor / Grant setup with allowed cost categories.
2. Budget allocation per program / activity / region.
3. Expenditure is coded against grant+activity.
4. System enforces "don’t overspend donor budget" rules and routes exceptions for approval.
5. Generate donor-use reports (spend vs allocation, outcomes/impact KPIs).

**Integration**
- Finance posts journals but tags them with GrantID / ActivityCode.
- Procurement and AP link bills to grant-coded cost centers.
- HR/Payroll can allocate staff cost to grants.
- Project Management can tie milestones and deliverables to grant reporting.
- AI can summarize donor compliance notes from Policy documents.

**Technical Notes**
- Donor, Grant, ActivityLine, Allocation, SpendTransaction are metadata-defined entities.
- Grant-specific budgets map into the Budget/Cost Center module.
- Approval workflows for donor spend are managed in Workflow Automation Studio.

---

### 7.7 Cost Center & Budget Control

**Purpose**
- Enforce financial discipline by comparing planned budgets/targets vs actual spend/revenue.

**Core Flow**
1. Define Cost Centers or Programs (Department, Branch, Project, Grant Activity).
2. Assign budgets and sales targets.
3. Every spend (PR/PO/Bill) and every revenue (SO/Invoice) is tagged to a cost center.
4. System monitors burn/achievement in real time.
5. If over-budget or under-target risk appears, trigger escalation.

**Integration**
- Procurement checks budget availability before approving PR/PO.
- Finance postings include cost center tags.
- Sales pipeline shows target vs actual by zone/rep.
- AI can warn “Budget for Marketing is 90% consumed, 2 weeks left in month.”

**Technical Notes**
- CostCenter, BudgetPlan, BudgetConsumptionSnapshot are metadata entities.
- Workflows can block or require CFO approval if spend exceeds threshold.
- Dashboard widgets and AI are fed by budget consumption snapshots.

---

### 7.8 Project & Task Management

**Purpose**
- Coordinate execution work: projects, tasks, milestones, assignments, timelines.

**Core Flow**
1. Create Project with milestones and owners.
2. Assign tasks, due dates, dependencies.
3. Track progress via Kanban/Gantt.
4. Timesheets log effort, feed Payroll.
5. Project costs and purchases tag to that project’s cost center/budget.

**Integration**
- Procurement requests can be tied to a Project.
- Finance/budget sees spend against each Project.
- HR/Payroll uses timesheets for pay.
- AI can flag stalled milestones or resource overload.

**Technical Notes**
- Project, Task, Milestone, Timesheet are all metadata-defined entities.
- Relationship: Task → Assignee (Employee from HR), Task → Project.
- Workflow automation can escalate overdue tasks.

---

### 7.9 HR & Payroll

**Purpose**
- Manage people, attendance, leave, payroll, and compliance.

**Core Flow**
1. Employee master data (grade, department, salary structure).
2. Attendance capture (manual, biometric, geo-fenced mobile, etc.).
3. Leave requests and approvals.
4. Payroll run calculates gross/net, deductions, overtime, etc.
5. Payslips generated and posted to Finance.

**Integration**
- Finance posts payroll journals.
- Project Management pulls timesheets for cost allocation.
- Asset Management can tie assets (laptop, phone) to employees.
- Policy/Document module stores HR policies (leave, overtime rules).
- AI can answer “What is carry-forward leave policy?” based on Policy documents.

**Technical Notes**
- Employee, AttendanceRecord, LeaveRequest, PayrollRun are metadata-defined entities.
- Sensitive fields (salary, bank details) are permission-locked at field level.
- Payroll posting triggers Finance with cost center splits.

---

### 7.10 Asset Management

**Purpose**
- Track fixed assets, their depreciation, maintenance, movement, and disposal.

**Core Flow**
1. Register asset (purchase info, cost center, custodian, location).
2. Schedule maintenance / service.
3. Log maintenance events.
4. Calculate depreciation.
5. Handle asset transfer or disposal.
6. Post depreciation and disposal entries to Finance.

**Integration**
- Finance recognizes assets as capitalized items and books depreciation.
- Maintenance tasks can feed Project & Task Management.
- Production can tag downtime/failures to specific assets.
- Quality/Compliance can log audit findings against assets.

**Technical Notes**
- Asset, MaintenanceSchedule, MaintenanceLog, DepreciationRun are metadata-defined.
- IoT/machine runtime data can feed maintenance schedules.
- Disposal workflow triggers Finance gain/loss postings.

---

### 7.11 Policy & Document Management

**Purpose**
- Centralize SOPs, HR policies, compliance guidelines, contracts, certifications.

**Core Flow**
1. Upload policy/contract/SOP with metadata (effective date, owner, expiry).
2. Version control and approval workflow.
3. Link policies to modules. Example: Procurement policy applies to PO approval flow.
4. AI can read and summarize policies for end users.

**Integration**
- HR uses leave & overtime policies.
- Quality/Compliance uses QC standards.
- Procurement references vendor approval policy.
- AI retrieval uses Policy documents to answer “what is allowed” questions contextually.

**Technical Notes**
- PolicyDocument entity includes version, owner, effective/expiry dates, access roles.
- Policy can be attached to Workflow rules (block/allow actions).

---

### 7.12 Quality / Compliance / Audit

**Purpose**
- Enforce standards, record QC checkpoints, track nonconformances, support audits.

**Core Flow**
1. Define QC checkpoints (Incoming material, In-line, Pre-shipment).
2. Record inspection results (pass/fail, measurements, photos).
3. Trigger corrective action tasks if fail.
4. Maintain compliance scorecards for suppliers.
5. Maintain audit findings and follow-up actions.

**Integration**
- Inventory lots can be held in quarantine if QC not passed.
- Procurement uses supplier scorecards.
- Production captures in-line QC results.
- Asset Management links audit findings to specific machines.
- Policy/Document stores compliance standards.

**Technical Notes**
- QCCheck, NonconformanceReport, CorrectiveAction, AuditFinding are metadata entities.
- Workflow Automation Studio handles corrective action routing and escalation.
- AI can summarize recurring failure patterns.

---

### 7.13 Customer Service / SLA / Subscription (Service/Telco Pack)

**Purpose**
- Manage service tickets, SLAs, subscriptions/recurring billing, and field technician work.

**Core Flow**
1. Customer raises issue / ticket.
2. Ticket is prioritized, assigned, and SLA timer starts.
3. Technician dispatched, work logged.
4. Resolution captured, ticket closed.
5. Subscription billing / recurring invoice issued if applicable.

**Integration**
- Sales/CRM sees active tickets when negotiating renewals.
- Finance handles recurring billing AR.
- Asset Management tracks which hardware is under service.
- AI can warn "SLA at risk" or "Churn risk" for high-complaint customers.

**Technical Notes**
- Ticket, SLAContract, SubscriptionPlan, TechnicianAssignment are metadata-defined entities.
- Workflow Automation Studio drives escalation if SLA is about to breach.
- Event bus emits `Ticket.Opened`, `SLA.BreachWarning`.

---

## 8. Industry Template Management

**How templates work across different industries**

1. **Template Definition**
   - Each Industry Pack is a bundle of metadata:
     - Standard entities and their fields.
     - Relationships + cardinality.
     - Default workflows.
     - Default dashboards and KPIs.
     - Default reports.
     - Default permissions/roles.
     - Chart of accounts or Donor/Fund trees.
   - Manufacturing Pack emphasizes BOM, Work Order, QC, WIP.
   - NGO Pack emphasizes Donor, Grant, Allocation, Spend, Compliance fields.
   - Trading Pack emphasizes Route/Territory, Batch/Expiry, Margin per SKU.
   - Service/Telco Pack emphasizes SLA, Ticketing, Recurring Billing.

2. **Template Application**
   - When a new company is created and chooses its Nature of Business, the platform:
     - Seeds metadata with that Pack’s definitions.
     - Seeds baseline dashboards.
     - Seeds workflows (approval chains, budget checks).
     - Seeds the finance model (CoA or Grant tree).
   - From that point on, the company can:
     - Extend entities (add new fields).
     - Add new entities/modules.
     - Edit workflows, dashboards, and roles.

3. **Template Evolution**
   - Packs are versioned. A newer version of the Manufacturing Pack can introduce improved QC workflow or new standard KPIs.
   - The platform can show: "A newer Manufacturing template is available. Would you like to merge updates?"
   - Merge is admin-approved and not forced.

4. **Technical Storage**
   - Packs live as exportable/importable metadata bundles.
   - A pack bundle can be:
     - Applied to a fresh tenant.
     - Compared against an existing tenant to propose incremental upgrades (new dashboard widgets, new workflow steps).

5. **Consistency vs Flexibility**
   - The base Industry Pack defines a "core spine" which remains recognizable (so we can ship updates and analytics).
   - Tenant-level extensions are layered on top. They never destroy the spine, they enrich it.

This approach lets the platform feel "industry-specific" from day one while still being infinitely adaptable per tenant.

---

## 9. Analytics, Reporting & Dashboards

### 9.1 Report Builder

**Business behavior**
- Drag-and-drop report design:
  - Select entities.
  - Pick fields (including custom fields added post-go-live).
  - Define joins using known relationships from metadata.
  - Add filters, grouping, sorting, calculations.

**Technical**
- Report definitions are stored as metadata.
- Query builder composes SQL under the hood using metadata (entity relationships, cardinality, promoted columns, JSONB fields).
- Reports can be exported (Excel, CSV, PDF) or embedded as dashboard widgets.

### 9.2 Dashboard / KPI Layer

**Business behavior**
- KPI cards, charts, tables, task lists, alerts, AI insights.
- Role-based homepages (CFO, Store Manager, Production Manager, Donor Manager, etc.).
- Drill-down: from KPI → summary list → specific transaction.

**Technical**
- Dashboard definitions are metadata objects referencing queries.
- Widgets can consume both structured data (SQL) and AI insights.
- Access to each widget respects permissions.

### 9.3 Predictive / Prescriptive Insights

**Business behavior**
- Forecast demand, stockout risk, budget overruns, missed sales targets.
- Alert managers early and suggest concrete actions.

**Technical**
- AI layer + historical KPI data.
- Event bus emits warnings which can trigger workflow steps (escalate, create task, request approval, etc.).

---

## 10. AI Companion

### 10.1 User Experience

**Business behavior**
- A floating assistant panel:
  - Available anywhere.
  - Knows what record/module you’re on.
  - Can proactively show “Attention needed” alerts.

**Examples**
- "Show me overdue invoices by customer for this company."
- "Explain why this PO is blocked."
- "Summarize spend vs budget for Program Alpha."
- "Is this supplier high risk?" (AI looks at QC flags, late deliveries.)
- "What is the leave carryover policy?"

### 10.2 Technical

- Uses local LLM(s) for reasoning and natural language, no dependency on external paid APIs.
- Retrieval layer:
  - Knows how to query entities according to metadata.
  - Pulls policy documents.
  - Respects role-based permissions.
- Event bus signals can push alerts into AI panel.
- AI suggestions can trigger workflows (e.g. "Generate Purchase Request to restock Item A").

---

## 11. Security, Roles, Compliance

### 11.1 Roles & Permissions

**Business behavior**
- Roles are not hardcoded. Admins can define roles per company.
- Permissions can be:
  - Module-level (view/create in Procurement).
  - Action-level (approve PO > $5,000).
  - Field-level (can view Salary?).
  - Record-scope (can access Company A, cannot access Company B).

**Technical**
- Permission matrix is metadata-driven and can be edited visually.
- Every field definition can carry visibility rules per role.
- AI inherits the same visibility rules.

### 11.2 Audit & Traceability

**Business behavior**
- We audit:
  - Who approved.
  - Who posted journal entries.
  - Who modified schema.
  - Who imported data.
  - Who rolled back staging.
- Finance data has immutable trails.
- Staging-to-live promotions are logged.

**Technical**
- Audit logs reference entity IDs, user IDs, timestamps, and old/new values.
- Schema changes and workflow changes are versioned objects with rollback.
- Migration sessions store checksums of source files.

### 11.3 Budgetary & Process Control

**Business behavior**
- PR/PO approval checks budget availability.
- Sales dashboards compare target vs actual.
- NGO spend checks donor allocation.
- Exceptions escalate automatically.

**Technical**
- Workflow engine calls Budget module before approving spend.
- Cost Center/Budget snapshots drive alert thresholds.
- Escalations emit event bus messages that trigger notifications/tasks.

### 11.4 Localization / Compliance

**Business behavior**
- Multi-language UI.
- Region-specific VAT/GST.
- Payroll localization (tax, social security, etc.).
- Grant reporting formats for donors.
- Quality/compliance checkpoints for production.

**Technical**
- Industry Packs can ship localized tax schemas and payroll components.
- Localization metadata drives labels, date formats, number formats.

---

## 12. Deployment & Infrastructure

### 12.1 Install Model

**Business behavior**
- Guided installer sets up DB, backend, web UI, AI runtime.
- First admin is prompted to create the first company and choose Industry Pack.
- Role templates and default dashboards are created.

**Technical**
- Installer provisions PostgreSQL, applies base migrations (metadata tables, core entities).
- Seeds industry pack metadata.
- Launches services (web app, workflow engine, AI runtime, event bus).

### 12.2 Local Network Access / Offline

**Business behavior**
- Other staff connect over LAN via browser.
- Offline PWA for warehouse/factory/mobile: local caching + queued transactions.

**Technical**
- Web frontend runs as PWA.
- Sync service queues writes and resolves conflicts on reconnect.
- Reverse proxy or tunnel can be configured to allow secure remote access.

### 12.3 Hardware Guidance

**Small to mid team usage**
- ~32GB RAM, SSD/NVMe, mid-range CPU, optional mid-tier GPU for AI.
- Windows 11 Pro or Linux.

**Larger usage**
- 64GB+ RAM, higher core-count CPU, redundant SSD storage, GPU acceleration.
- Linux preferred for stability and AI performance.

---

## 13. Implementation Phases

**Phase 0: Multi-company architecture planning**
- Define multi-company data isolation, inter-company postings, consolidation logic.

**Phase 1: Platform foundation**
- Metadata engine, schema designer, workflow engine, permissions, company registry.

**Phase 2: Core operational modules**
- Finance (GL/AP/AR), Procurement, Inventory, Sales.
- End-to-end Procure-to-Pay and Order-to-Cash.
- Dashboards and audit logs.

**Phase 3: Data Migration Engine rollout**
- Upload → Detect → Map → Clean → Stage → Approve → Commit → Rollback.
- Schema extension on import.

**Phase 4: No-code builders**
- Form Builder, Custom Module Builder, Workflow Studio, Dashboard Builder.
- Allow admins to extend/automate without dev.

**Phase 5: AI companion**
- Context-aware assistant panel.
- Predictive alerts (budget overrun, stockout, SLA breach).

**Phase 6: Advanced/vertical modules**
- Production/Manufacturing, NGO/Grant Management, Cost Center & Budget Control, Project/Task, HR & Payroll, Asset Management, Policy/Document, Quality/Compliance, SLA/Service.

**Phase 7: Security, training, UAT**
- Permissions hardening.
- User education.
- End-to-end reconciliation with legacy balances.

**Phase 8: Pilot go-live**
- One company goes live.
- Monitor.
- Fix blockers.

**Phase 9: Rollout to all companies**
- Onboard more companies/branches using Industry Packs + saved migration mappings.
- Turn on consolidation.

**Phase 10: Hypercare**
- Stabilize, support, iterate dashboards and workflows.

---

## 14. Strategic Differentiators

- **Industry-ready from Day 1:** No blank ERP. Company creation = working template.
- **Schema that evolves itself:** Migration can extend the data model automatically.
- **No-code everywhere:** Admins can create fields, modules, workflows, dashboards.
- **Finance-safe flexibility:** You can add analytics on finance objects without breaking audit trails.
- **Multi-company aware:** Inter-company flows + consolidation built in.
- **AI-native + private:** Embedded assistant, proactive alerts, no per-token billing.
- **Runs on normal hardware:** LAN-first, offline-capable, no forced cloud.

This is the complete functional + technical blueprint for the ERP platform.

