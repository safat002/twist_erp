# Twist ERP - Comprehensive User Guide (v3)

This document serves as the official user guide for the Twist ERP platform. It details the purpose, usage, and cross-functional impact of each module.

---

## Backend User Guide

### 1. Introduction & Philosophy

The Twist ERP backend is a modular, multi-tenant, and AI-assisted "business operating system." Its core philosophy is to provide a flexible foundation that can be visually configured to adapt to various industries without developer intervention.

- **Multi-Company Core:** Supports multiple companies within a group, allowing for data isolation, inter-company transactions, and financial consolidation.
- **Metadata-Driven:** All elements (entities, fields, workflows, forms) are defined as metadata, allowing administrators to extend the ERP's data model and processes in real-time.
- **API-First & Event-Driven:** Modules communicate via a shared event bus and expose services through APIs, ensuring loose coupling and scalability.
- **Embedded Intelligence:** An AI layer provides contextual insights, proactive alerts, and operational assistance.
- **Secure & Auditable:** Every action is governed by a granular Role-Based Access Control (RBAC) system and recorded in an immutable audit trail.

### 2. Core Platform Modules

These modules provide common services to all business functions.

#### a. Intelligent Data Migration Engine

- **Purpose:** To enable non-technical users to import legacy data (e.g., from Excel) into the ERP.
- **Key Functions & Usage:**
  1.  **Upload:** A user uploads a file (e.g., customer list) and selects the target company and entity type (e.g., "Customer Master").
  2.  **Map Fields:** The system profiles the file and auto-suggests mappings between the file's columns and the ERP's fields. If a column like "Customer_Loyalty_Tier" doesn't exist in the ERP, the engine suggests creating it as a new custom field.
  3.  **Validate:** The engine validates the data for errors (e.g., missing names, invalid email formats, duplicate entries) and presents a list of valid and invalid rows.
  4.  **Approve & Commit:** A manager reviews the validation summary and potential schema changes, then approves the job. The system then transactionally commits the valid data to the live database.
- **Cross-Module Integration & Business Impact:**
  - **Impact on All Modules:** This engine is the primary tool for populating master data (Customers, Suppliers, Items) and opening balances (Stock, AR, AP) for all other modules, forming the foundation for go-live.
  - **Impact on Metadata:** By allowing the creation of custom fields during import, it directly extends the data model for modules like Sales (new customer fields) or Inventory (new item attributes), which are then immediately available in the Form Builder and Reporting engine.

#### b. Workflow & Automation Engine

- **Purpose:** To automate and enforce business processes.
- **Key Functions & Usage:**
  1.  **Design Workflow:** An admin uses the visual Workflow Studio to draw a process flow, such as for purchase approvals.
  2.  **Define Rules:** They add conditional nodes (e.g., `IF amount > $5,000`) and action nodes (e.g., `ROUTE to CFO for approval`).
  3.  **Execution:** When a user submits a transaction (like a Purchase Requisition), the engine intercepts it, evaluates the rules, and routes it to the correct approver's task list.
- **Cross-Module Integration & Business Impact:**
  - **Impact on All Transactional Modules:** This engine is the gatekeeper for critical processes in Procurement, Sales, Finance, and HR. It ensures that company policies (like spending limits) are enforced automatically, reducing manual oversight and improving compliance.
  - **Impact on Tasks & Notifications:** The engine is the primary source of system-generated tasks. When an approval is required, it creates a `TaskItem` for the approver and sends a notification, directly driving user actions.

### 3. The AI Ecosystem: Your Intelligent Assistant

Think of the AI in Twist ERP not as a simple chatbot, but as a capable, context-aware assistant integrated into your daily workflow. It has a dual personality: it's a knowledgeable assistant that can answer questions and perform tasks, and a behind-the-scenes data analyst that provides insights.

#### What Your AI Can Do For You

- **Answer Complex Questions Across Departments:** You can ask questions that require pulling information from multiple modules. For example: `"Why was our profit margin lower last month?"` The AI can analyze data from Sales (discounts given), Procurement (higher material costs), and Finance (unexpected expenses) to give you a consolidated answer.

- **Perform Actions on Your Behalf:** You can give it direct commands in natural language. For instance: `"Approve the first three purchase orders on my list and notify the procurement team."` The AI will execute these actions, following all the standard approval rules as if you had clicked the buttons yourself.

- **Provide Proactive Nudges and Alerts:** The AI constantly monitors business operations. It can warn you about potential issues before they become critical. You might get a nudge like: `"Heads up, the budget for the marketing department is 85% consumed with two weeks left in the quarter."` or `"This sales order might be delayed; the required items are running low in the warehouse."`

- **Explain What You're Seeing:** If you're on a screen with unfamiliar fields, you can ask the AI, `"What does the 'GRNI Account' field mean?"` The AI can access the system's metadata and policy documents to explain the business purpose of different elements in the ERP.

- **Remember Your Preferences:** You can tell the AI how you like to work. For example: `"From now on, always show my financial reports in USD, not BDT."` The AI will save this as a long-term preference and apply it automatically in the future.

- **Guide You Through Complex Tasks:** The AI can act as a guide for multi-step processes. You can say, `"Help me migrate our supplier list from this Excel file."` The AI will then initiate the Data Migration Engine and walk you through the steps of mapping, validating, and importing the data.

#### How Your AI Works (In Simple Terms)

- **It Acts As You (And Only You):** This is the most important concept. The AI is not a global, all-seeing entity. When you interact with it, it inherits **your exact permissions**. It cannot see a report, approve a payment, or access a record unless you already have the permission to do so. Think of it as a perfectly trustworthy human assistant who uses your login to operate the system on your behalf.

- **It Has a Team of "Skills":** The AI has a modular design, with different "skills" for different business domains. It has a `FinanceSkill`, an `InventorySkill`, and a `PolicySkill`. When you ask a question, the AI Orchestrator routes it to the right expert skill (or combination of skills) to formulate the best possible answer.

- **It Has Both Short-Term and Long-Term Memory:** The AI can remember the immediate context of your conversation (e.g., the list of invoices it just showed you). It also has a long-term memory to store your explicit preferences, ensuring it becomes more personalized to your working style over time.

- **Everything is Audited:** For your protection and for compliance, every significant action the AI takes on your behalf is recorded in the main system audit trail. If the AI approves a PO for you, the log will clearly state that the action was performed by the AI based on your request.

### 4. Business Process Modules

#### a. Financial Management

- **Purpose:** To be the system of record for all financial transactions and ensure compliance.
- **Key Functions & Usage:**
  1.  **Automated Journal Posting:** Users do not create manual debit/credit entries. Instead, when an operational event occurs (e.g., a sales invoice is approved), the system automatically generates the corresponding balanced journal entries based on pre-configured posting rules.
  2.  **Manage Payables (AP):** The finance team reviews supplier bills that are automatically created from procurement, schedules them for payment, and records the payment transaction.
  3.  **Manage Receivables (AR):** The team tracks customer invoices, sends reminders for overdue payments, and records collections.
  4.  **Bank Reconciliation:** The system provides an interface to match bank statement lines with ERP transactions.
- **Cross-Module Integration & Business Impact:**
  - **Procurement â†’ Finance:** When a supplier invoice is posted in Procurement, it creates a bill in AP, increasing the company's liabilities. When the payment is made, it reduces cash and clears the liability.
  - **Sales â†’ Finance:** An approved customer invoice from the Sales module creates an invoice in AR, increasing revenue and accounts receivable. A customer receipt increases cash and clears the receivable.
  - **Inventory â†’ Finance:** Every stock movement that has a cost implication (like a sale or a write-off) triggers a journal entry to update the inventory asset value and Cost of Goods Sold (COGS) on the Profit & Loss statement.
  - **Business Impact:** This module provides the ultimate view of the company's health. By consolidating data from all other modules, it produces the P&L, Balance Sheet, and Cash Flow statements that are critical for strategic decision-making.

#### b. Procurement & Supplier Management

- **Purpose:** To control company spending and manage supplier relationships.
- **Key Functions & Usage:**
  1.  **Create Purchase Requisition (PR):** A user requests to buy goods/services. This is a non-binding internal request.
  2.  **Approve PR & Create Purchase Order (PO):** The PR is routed for approval via the Workflow Engine. Once approved, it is converted into a legally binding PO sent to a supplier.
  3.  **Record Goods Receipt (GRN):** When goods arrive, the warehouse team creates a Goods Receipt Note, confirming what was received.
  4.  **Match & Post Invoice:** The finance team matches the supplier's bill to the PO and GRN (3-way match) before posting it for payment.
- **Cross-Module Integration & Business Impact:**
  - **Impact on Budgeting:** An approved PO places a **commitment** on a cost center's budget, reducing the available funds. This prevents budget overruns before they happen.
  - **Impact on Inventory:** A posted GRN immediately increases the stock quantity in the **Inventory module**, making those items available for use.
  - **Impact on Finance:** The 3-way matched supplier bill creates a liability in **Accounts Payable**, ensuring suppliers are paid on time and accurately.

#### c. Sales & Customer Relationship Management (CRM)

- **Purpose:** To manage the entire customer lifecycle from lead to cash collection.
- **Key Functions & Usage:**
  1.  **Manage Leads & Opportunities:** Salespeople track potential deals in a visual pipeline (Kanban board).
  2.  **Create Quotation & Sales Order (SO):** A quotation is sent to a customer. If accepted, it's converted into a Sales Order.
  3.  **Fulfill Order (Delivery):** The warehouse team is notified to pick, pack, and ship the items, creating a Delivery Note.
  4.  **Invoice Customer:** Based on the delivery, a customer invoice is generated and sent.
- **Cross-Module Integration & Business Impact:**
  - **Impact on Inventory:** A confirmed Sales Order can **reserve** stock. A posted Delivery Note **decreases** the stock quantity, preventing the sale of unavailable items.
  - **Impact on Finance:** A customer invoice increases **Accounts Receivable** and **Revenue**. This directly impacts the company's top-line performance and cash flow projections.
  - **Impact on Manufacturing:** If an item is not in stock, a confirmed SO can trigger a demand signal to the **Manufacturing module** to produce it.

#### d. Advanced Inventory & Warehouse Management (Full Guide Below)

- **Purpose:** To maintain an accurate, real-time, event-sourced view of all stock with complete traceability.
- **Key Functions & Usage:**
  1.  **Track Stock Movements:** Every physical movement is recorded as an immutable event via GRN (in), Delivery Note (out), or Stock Transfer (internal).
  2.  **Manage Stock Levels:** The system tracks on-hand quantity, reserved quantity, available quantity, and in-transit quantity per item in each warehouse.
  3.  **Quality Control:** Integrated QC checkpoints with batch/lot tracking, serial number management, and hold/release workflows.
  4.  **Valuation:** Automatic inventory costing using FIFO, LIFO, Weighted Average, or Standard Cost methods with cost layer consumption tracking.
  5.  **Batch & Serial Tracking:** Full batch/lot lifecycle with FEFO allocation, expiry management, and individual serial number tracking with warranty.
  6.  **Advanced Features:** Landed cost allocation, return to vendor workflows, multi-UoM conversions, auto-replenishment, and variance management.
- **Cross-Module Integration & Business Impact:**
  - **Business Impact:** Event-sourced inventory provides complete audit trail and real-time accuracy. Prevents stock-outs, optimizes working capital, ensures quality compliance, and provides accurate COGS for financial statements.
  - **Linkages:** The physical heart connecting Procurement (goods receipt) → Quality Control (inspection) → Finance (valuation & COGS) → Sales (fulfillment) → Manufacturing (material consumption).
- **See Full Inventory Module Guide Below for Complete Documentation**

#### e. Manufacturing / Production

- **Purpose:** To manage the conversion of raw materials into finished goods.
- **Key Functions & Usage:**
  1.  **Define Bill of Materials (BOM):** Users define the "recipe" for a finished product, listing all raw materials and quantities required.
  2.  **Create Work Order:** A production run is initiated via a Work Order, which consumes the BOM.
  3.  **Issue Materials:** The system generates a pick list for the warehouse to issue the required raw materials to the production floor.
  4.  **Record Production:** As finished goods are produced, they are recorded and received back into inventory.
- **Cross-Module Integration & Business Impact:**
  - **Impact on Inventory:** Work Orders **consume** raw materials (decreasing their stock) and **produce** finished goods (increasing their stock).
  - **Impact on Finance:** The cost of raw materials and labor is moved from individual expense/asset accounts into a **Work-in-Progress (WIP)** account. When production is finished, the value is moved from WIP to the **Finished Goods Inventory** asset account. This provides an accurate cost for each unit produced.

### 5. To-Be-Implemented Backend Features

The following features are on the implementation roadmap to enhance user productivity and system intelligence.

- **Unified Task & To-Do System:** A central `TaskItem` object to manage both system-assigned tasks (e.g., "Approve PO-123") and personal to-dos. These tasks can be linked to any ERP entity and will have due dates, priorities, and statuses.
- **Calendar Integration:** The system will automatically push tasks and deadlines with due dates to the user's Outlook calendar, ensuring they never miss a critical action item.
- **Email Awareness:** The ERP will monitor the user's inbox for relevant, unread emails (e.g., workflow notifications) and surface alerts within the ERP, linking directly to Outlook.
- **Enhanced Notification System:** A comprehensive notification center will provide an auditable "inbox" for all ERP events, including approvals, escalations, and AI-driven nudges, with snooze and "assign follow-up task" capabilities.

---

## Frontend User Guide

### 1. Introduction & Philosophy

The Twist ERP frontend is a visual, configurable, and context-aware interface designed to make the powerful backend accessible to non-technical users. It prioritizes clarity and ease of use through a drag-and-drop interaction model.

### 2. Key UI Concepts

#### a. Visual Builders

- **Purpose:** To allow administrators to customize the ERP without writing code.
- **Key Functions & Usage:**
  - **Form Builder:** An admin wants to add a "Region" field to the Customer screen. They open the Form Builder, drag a "Dropdown" field onto the form canvas, label it "Region," and enter the possible values (e.g., "North," "South"). After saving, the "Region" field immediately appears on the Customer form for all users.
  - **Workflow Builder:** A manager wants all POs over $10,000 to be approved by the CEO. They open the Workflow Studio, add a condition node (`IF PO.total > 10000`), and drag a line from it to an approval node assigned to the "CEO" role. The rule is now live.

#### b. AI Assistant Panel

- **Purpose:** To provide contextual help and perform actions via natural language.
- **Key Functions & Usage:**
  - A sales manager is viewing a Sales Order and asks the AI, **"Is this customer reliable?"** The AI accesses the customer's record, sees several overdue invoices in the **Finance module**, and replies, "This customer has 3 overdue invoices totaling $5,200. Proceed with caution."
  - A user types, **"Create a PO for 100 units of Item X from Supplier Y."** The AI drafts the Purchase Order by calling the **Procurement** service and presents it to the user for confirmation before submitting.

#### c. Notification Center & Taskboard

- **Purpose:** To be the user's central hub for all required actions.
- **Key Functions & Usage:**
  - A manager approves a Purchase Requisition. The **Workflow Engine** sends a notification and creates a `TaskItem` for the procurement officer.
  - The officer sees "New Task: Convert PR-056 to Purchase Order" on their Taskboard. Clicking it takes them directly to the PO creation screen with all the information from the PR pre-filled.
  - This creates a seamless, auditable chain of action, ensuring no requests are dropped and accountability is clear.

---

## Finance Module â€” User Guide (v1)

### 1) Scope & Capabilities

- Multi-company, multi-currency foundations with configurable numbering formats.
- Chart of Accounts (CoA); Journals & Journal Vouchers (JV) with makerâ€“checker; AR/AP Invoices; Payments/Receipts; Period control (Open/Close/Lock); Bank Reconciliation v1; VAT basics; Core reports; FX Revaluation (preview and post).
- Role-based permissions and optional segregation-of-duties (SoD).

### 2) Roles & Permissions

- View: `finance_view_dashboard`, `finance_view_coa`, `finance_view_journal`, `finance_view_invoice`, `finance_view_payment`, `finance_view_reports`.
- Manage/Post: `finance_manage_coa`, `finance_manage_journal`, `finance_post_journal`, `finance_manage_invoice`, `finance_manage_payment`, `finance_reconcile_bank`, `finance_close_period`.
- SoD: Creator cannot approve/post their own JV/Invoice/Payment when SoD is enabled.

### 3) Company Settings (Toggles)

These are read from `Company.settings.finance` (JSON). Defaults in parentheses:

- `require_journal_review` (false): require Draft â†’ Review before posting JV.
- `require_invoice_approval` (true): require approval before posting invoices.
- `require_payment_approval` (true): require approval before posting payments.
- `enforce_finance_sod` (true): enforce creator â‰  approver/poster.
- `enforce_period_posting` (true): block posting to non-OPEN periods.

### 4) Setup Checklist

1. Create Chart of Accounts (Finance â†’ Accounts) including Receivable/Payable and at least one Bank/Cash account.
2. Create Journals: GENERAL, SALES, PURCHASE, BANK, CASH (Finance â†’ Journals list is read-only; use admin if needed).
3. Set Finance settings in Company (Admin) if you want to change approval/review defaults.
4. Create current Fiscal Period (Finance â†’ Fiscal Periods) or run the seed command.
5. Optional: Define TaxJurisdiction/TaxCode (Admin) and map tax GL accounts.

Management commands:

- Seed current period: `python backend/manage.py seed_current_period --company-id <ID>`
- Seed sample bank statement: `python backend/manage.py seed_bank_statement_sample --company-id <ID> [--bank-account-id <ACCOUNT_ID>]`

### 5) UI Navigation

- Finance Control Tower: `/finance`
- Accounts (CoA): `/finance/accounts`
- Journal Vouchers: `/finance/journals`
- Invoices: `/finance/invoices`
- Payments: `/finance/payments`
- Fiscal Periods: `/finance/periods`
- Bank Reconciliation: `/finance/bank-recon`
- Reports:
  - Trial Balance: `/finance/reports/trial-balance`
  - General Ledger: `/finance/reports/general-ledger`
  - AR Aging: `/finance/reports/ar-aging`
  - AP Aging: `/finance/reports/ap-aging`
  - VAT Return: `/finance/reports/vat-return`

### 6) Day-to-Day Workflows

#### a. Journal Vouchers (JV)

- Create JV: Finance â†’ Journal Vouchers â†’ New Voucher. Enter journal, date, narrative, and balanced lines.
- Submit (if required): Draft â†’ Submit (moves to REVIEW).
- Approve & Post (if review required): Approve (moves to POSTED). Otherwise Post directly.
- SoD: the user who created the voucher cannot approve/post when SoD is enabled.

#### b. AR/AP Invoices

- Create Invoice: Finance â†’ Invoices â†’ New Invoice (choose AR or AP). Add lines (revenue/expense accounts, taxes as needed).
- Approve: Click Approve on the invoice row (required by default).
- Post: Click Post. System creates and posts a Journal Voucher. AR impacts receivable; AP impacts payable.
- Payment updates invoice status automatically (Partial/Paid).

#### c. Payments/Receipts

- Create Entry: Finance â†’ Payments â†’ New Entry. Set type (Receipt or Payment), method, bank/cash account, partner, amount.
- Allocate to invoices: In the modal, add allocations to open invoices for that partner (amounts must sum to the entry amount).
- Approve: Click Approve (required by default).
- Post: Click Post. System produces and posts JV and applies invoice settlements.

#### d. Fiscal Periods

- Create Period: Finance â†’ Fiscal Periods â†’ Create (month-level `YYYY-MM`).
- Open/Close/Lock: Use action buttons on the list. If `enforce_period_posting` is true, only OPEN periods permit posting.

#### e. Bank Reconciliation (v1)

- Create Statement: Finance â†’ Bank Reconciliation â†’ Create (choose bank account, date, opening balance).
- Statement Lines: For now, lines can be seeded via the sample command or added inline (basic v1).
- Match Line: Admin API/UI supports matching a statement line to a posted Payment or Voucher.

#### f. FX Revaluation (v1)

- Endpoint-driven (admin function): POST `/api/v1/finance/reports/fx-revaluation/` with date, rates, gain/loss accounts, and monetary lines.
- Preview without posting: set `post: false` (default). Returns balanced preview entries.
- Post: set `post: true`. Creates and posts JV to General or fallback journal (requires `finance_post_journal`).

### 7) Reports

All accessible under Finance â†’ Reports:

- Trial Balance: pick a date range; shows opening, debits, credits, closing by account.
- General Ledger: select account + date range; shows opening and running balance lines.
- AR Aging: pick As-of date; shows bucket cards and tabbed lists: Current, 1â€“30, 31â€“60, 61â€“90, >90.
- AP Aging: same as AR but for payables.
- VAT Return (v1): pick date range; shows output (AR) VAT, input (AP) VAT, and net. Enhanced breakdown by tax codes can be enabled when invoices carry tax codes.

### 8) Notifications & Audit

- Every create/update/transition/post logs an audit event. Key actions also emit notifications (if enabled) that appear in the Notification Center.

### 9) Troubleshooting & FAQs

- â€œCannot post â€” period is CLOSED/LOCKEDâ€: Open period from Finance â†’ Fiscal Periods, or disable `enforce_period_posting` in company settings.
- â€œVoucher must be in review state before postingâ€: Enable Submit â†’ Approve path, or set `require_journal_review` = false.
- â€œSegregation of duties violationâ€: Approval/Post must be done by someone other than the creator when SoD is enabled.
- â€œBank Recon match missing paymentâ€: Ensure the payment is POSTED and belongs to the same company and bank account currency.
- â€œApprove button missingâ€: Confirm you have `finance_manage_*` permissions and company settings require approval; also confirm youâ€™re authenticated and a company is selected.

### 10) API Endpoints (Selected)

- Accounts: `/api/v1/finance/accounts/`
- Journals: `/api/v1/finance/journals/`; Vouchers: `/api/v1/finance/journal-vouchers/`
  - Actions: `/:id/submit/`, `/:id/approve/`, `/:id/post/`
- Invoices: `/api/v1/finance/invoices/`
  - Actions: `/:id/approve/`, `/:id/post/`
- Payments: `/api/v1/finance/payments/`
  - Actions: `/:id/approve/`, `/:id/post/`
- Periods: `/api/v1/finance/periods/` (actions: `/open`, `/close`, `/lock`, `/unlock`)
- Bank Statements: `/api/v1/finance/bank-statements/` (action: `/:id/match-line/`)
- Reports: `/api/v1/finance/reports/*` (`trial-balance`, `general-ledger`, `ar-aging`, `ap-aging`, `vat-return`, `fx-revaluation`)

### 11) Security & Best Practices

- Use separate roles for creators and approvers/posters when SoD is enabled.
- Keep periods aligned with your fiscal calendar and lock after close to prevent back-dated postings.
- Ensure journals (GENERAL, SALES, PURCHASE, BANK, CASH) are configured per company.
- Maintain tax code tables consistently to enable accurate VAT reporting.

---

## Budgeting Module - User Guide (Phase 10 Ready)

The budgeting module is both the corporate planning engine and the master data authority for every item that flows into procurement, inventory, or projects. This section covers day-to-day operations, governance expectations, and the master/detail responsibilities introduced in Phase 10.

### Roles & Access

- **Budget Module Owner** - Sets up budget periods, owns toggles (entry, review, impact), performs final approval, activates or pauses budgets, and maintains global policies like auto-approval.
- **Budget Moderator** - Runs the Moderator Dashboard, performs analytical review, attaches remarks/holds, and escalates issues. Cannot approve final budgets.
- **Cost Center (CC) Owner / Deputy** - Reviews submissions for assigned cost centers, performs "Modify & Approve," or sends lines back to entry users.
- **Entry User** - Captures line items during the open entry window for specific cost centers; cannot approve.
- **Inventory / Procurement Operators** - Read master data from budgeting (BudgetItemCode) when transacting; cannot mutate budgeting records.

### Core Screens

| Purpose                               | Route                     |
| ------------------------------------- | ------------------------- |
| Control Tower & Actions               | /budgets (Budgeting Hub)  |
| Line Entry                            | /budgets/entry            |
| CC / Final Approvals                  | /budgets/approvals        |
| Moderator Ops                         | /budgets/moderator        |
| Remark Templates                      | /budgets/remark-templates |
| Item Master (BudgetItemCode registry) | /budgets/list             |
| Analytics                             | /budgets/monitor          |

### 1. Declare / Manage Budgets

From **Budgeting Hub -> New Budget** (or edit existing):

- **Duration & Period** - duration_type, period_start, period_end, custom_duration_days.
- **Entry Window** - entry_start_date, entry_end_date, entry_enabled.
- **Grace Period** - grace_period_days between entry close and review start.
- **Review Window** - eview_start_date, eview_end_date, eview_enabled.
- **Budget Impact Window** - udget_impact_start_date, udget_impact_end_date, udget_impact_enabled.
- **Auto Approval** - uto_approve_if_not_approved to auto-promote on start.
- **Actions** - Open Entry -> Submit for CC Approval -> Start/Close Review -> Request Final -> Activate. Clone budgets (with adjustment factors) or derive from prior actuals.

### 2. Maintain the Corporate Item Catalog

Budgeting owns **BudgetItemCode**:

- Add/edit item codes via Budget Registry (/budgets/list). Capture code, description, category, base UoM, standard price, policy flags.
- Once created, the item becomes selectable everywhere: entry UI, procurement requisitions, inventory transfers.
- Inventory operational tables (ItemOperationalExtension, ItemWarehouseConfig, ItemSupplier, ItemUomConversion) reference this BudgetItemCode. Budget owners no longer re-enter data in inventory.
- Changes propagate in real time to Item Detail screens, supplier pickers, replenishment engines, and GL mapping logic.

### 3. Line Entry (Entry Users)

At /budgets/entry:

- Choose the declared budget and permitted cost center.
- Search BudgetItemCode (enforced master linkage) and enter quantity, rate, and justification. Policy defaults/price guidance prefill values.
- Save drafts; submit when complete. Entry locks once submitted unless reopened via Review/Hold.

### 4. Cost Center Review

CC Owners use **My Approval Queue** (/budgets/approvals):

- **Modify & Approve** - adjust quantities/amounts, capture reason, approve.
- **Send Back** - pushes specific lines to entry users; they become editable only if flagged as "Sent Back" and within review rules.
- **Escalate to Moderator** - mark anomalies which appear in the moderator filters.

### 5. Moderator Workflow

/budgets/moderator provides:

- Filters by procurement class, variance %, material group, amount brackets, supplier type, or AI warnings.
- Batch actions: remarks (free text or template), Send Back, Hold (with optional "held until" date).
- Variance audit drawer shows original vs current values, change reason, actor, timestamp.
- Once satisfied, mark the budget "Reviewed" so it advances to final approval.

### 6. Review Period, Holds, and Exceptions

- Review window status (Grace, Review, Closed) is shown per budget.
- During review: only lines flagged as Sent Back or Held remain editable.
- Holds keep a line editable even after the review window closes; use for long-running negotiations.
- Auto-notifications alert CC owners when items are sent back or released from hold.

### 7. Final Approval & Activation

- Module Owner reviews outstanding tasks in /budgets/approvals, runs "Approve Final," then "Activate" inside Budgeting Hub.
- Auto-approval promotes budgets that remain pending when the start date arrives (if toggle is on).
- When activated with udget_impact_enabled, every PO, PR, or stock issue immediately consumes/commits against the budget line and cost center.

### 8. Monitoring & Analytics

/budgets/monitor dashboards include:

- Submission progress, commitment vs. consumption, bottleneck tracker (>5 days in stage), forecast variance heatmaps, and alert cards.
- "Load Alerts" surfaces utilization thresholds, forecast exceedances, and AI insights (see below).
- Drill-through to CC / item detail to inspect actual transactions sourced from procurement, inventory, and finance.

### 9. Integration Touchpoints

- **Procurement** - Approved POs book commitments automatically and release on GRN. Supplier blackout windows and lead times respect budgeting item metadata.
- **Inventory** - Stock movements carry budget item, cost center, and project metadata. Two-step transfers, in-transit ledger, and valuation rules require a valid BudgetItemCode reference.
- **Finance / GL** - Inventory Posting Rules cascade uses budget item -> item -> category -> warehouse -> company defaults. If no rule resolves, finance raises a blocking error.
- **Projects / Tasks** - Project budgets inherit item definitions so project issues consume the same master data without duplication.

### 10. Tips & Troubleshooting

- **Review window not opening** - verify entry window is closed, grace days elapsed, and eview_enabled is true.
- **Cannot edit after submission** - reopen specific lines by sending them back or placing them on hold before review closes.
- **Activation blocked** - ensure Moderator completed review and Module Owner executed "Approve Final."
- **Master data mismatch** - if inventory shows "Legacy Item," run migration inventory.10014+ or link the record via Item detail's "Link Budget Item" drawer.

### 11. Security & Permissions

- Entry permissions are scoped per cost center. Deputies inherit permissions from the CC definition.
- Moderator role grants access to remark templates, batch actions, and analytics but not approvals.
- Module Owner role grants final approval, activation, clone, and configuration toggles.
- API endpoints honor company context (X-Company-ID) and RBAC; cross-company edits are blocked.

### 12. AI & Forecasting Enhancements

- **Price Prediction** - Moderator Insights show PO-history-based suggested prices with confidence bands.
- **Consumption Forecast** - per line forecast vs. limit; flagged items show "Forecast Exceed."
- **Budget-level Forecasts** - Trigger "Forecasts" from Budgeting Hub to compute and store projections for all lines.
- **Alert Engine** - Budget Monitor -> Alerts shows utilization and forecast alerts; notifications also flow to responsible CC owners.

## Budgeting Module - Recent Updates (Phase 8-10)

- Declaration modal captures the full lifecycle switches: duration_type, custom_duration_days, entry_enabled, grace_period_days, eview_start_date / eview_end_date + eview_enabled, udget_impact_start_date / udget_impact_end_date + udget_impact_enabled, and uto_approve_if_not_approved.
- Budgeting Hub grid shows the live status banner (Entry, Grace, Review, Closed) plus quick actions (Open Entry, Request Final, Activate, Clone).
- Moderator Dashboard (/budgets/moderator) adds advanced filters, batch remark templates, batch send-back, batch hold, and full variance audit.
- Approval Queue allows CC Owners to "Modify & Approve" lines with justification, while Module Owners can complete final approval and activation.
- Budget cloning supports uplift factors, deriving from actual consumption, or copying only structure.
- AI (Phase 9) remains available:
  - Price Prediction per line (Moderator -> "Insights").
  - Consumption Forecast per line (Moderator -> "Insights").
  - Compute Forecasts per budget (Budgets grid -> "Forecasts") with red "Forecast Exceed" tags.
  - Alerts in Budget Monitor ("Load Alerts") for utilization threshold and forecast exceedance.
- New in Phase 10: budgeting owns the item master. Inventory/Procurement screens enforce the BudgetItemCode link, and stock/GL postings now pull cost center/project metadata plus GL fallback rules directly from budgeting.

---

## Advanced Inventory Module - Complete User Guide

The Inventory module is the operational heart of Twist ERP, providing real-time visibility and control over all physical stock movements with complete traceability through an event-sourced architecture. This guide covers the full system including Phase 3: Quality & Compliance features.

### 1) Architecture & Core Principles

**Event-Sourced Inventory**: Every stock movement creates an immutable `MovementEvent` that serves as the single source of truth. This provides:

- Complete audit trail - reconstruct stock position at any point in time
- Guaranteed accuracy - no direct manipulation of stock balances
- Finance integration - every movement automatically generates GL postings

**Master-Detail Separation**: Following Phase 10 budgeting integration:

- **Budget Item (Master)**: The corporate item catalog owned by budgeting
- **Item Operational Profile**: Inventory-specific attributes (storage, handling, tracking)
- **Item Warehouse Config**: Location-specific settings (replenishment, bin locations)
- **Item Supplier**: Procurement linkages (lead times, minimum order quantities)

**Multi-Level Tracking**:

- **Warehouse Level**: Track stock across multiple physical locations
- **Batch/Lot Level**: Group items by production run with expiry tracking
- **Serial Level**: Track individual items with warranty and assignment

### 2) Roles & Permissions

- **Inventory Manager**: Full access to all inventory functions including configuration
- **Warehouse Operator**: Create/post stock movements, GRNs, transfers
- **QC Inspector**: Perform quality inspections, manage stock holds
- **QC Manager**: Configure QC checkpoints, release holds, dispose batches
- **Procurement User**: Create goods receipts from purchase orders
- **Finance User**: View inventory valuation, cost layers, variance analysis

### 3) Setup Checklist

1. **Configure Warehouses** (Admin → Inventory → Warehouses):

   - Create physical warehouse locations
   - Set warehouse types (Distribution, Manufacturing, Transit, etc.)
   - Define bin locations (if using bin-level tracking)

2. **Configure Valuation Methods** (Inventory → Valuation → Settings):

   - Set default valuation method per company or item/warehouse
   - Methods: FIFO, LIFO, Weighted Average, Standard Cost
   - Configure cost layer retention policies

3. **Set Up Item Operational Profiles** (Budget Items → Edit → Operational tab):

   - Stock UoM, Purchase UoM, Sales UoM
   - Serial tracking enabled (Yes/No)
   - Batch tracking enabled (Yes/No)
   - Shelf life management (if batch-tracked)

4. **Configure UoM Conversions** (Budgets → UoMs):

   - Define conversion factors (e.g., 1 Box = 12 Pieces)
   - Set conversion contexts (purchase, sales, stock, manufacturing)

5. **Set Up QC Checkpoints** (Admin → Inventory → QC Checkpoints):

   - Define checkpoints per warehouse (e.g., GOODS_RECEIPT, PERIODIC_INSPECTION)
   - Set acceptance thresholds (e.g., 95% pass rate)
   - Assign QC personnel

6. **Configure GL Posting Rules** (Finance → GL Posting Rules):
   - Map inventory movements to GL accounts
   - Configure account resolution hierarchy: Item → Category → Warehouse → Company default
   - Set up COGS, GRNI, Inventory Asset, Variance accounts

### 4) UI Navigation

| Purpose                 | Route                              |
| ----------------------- | ---------------------------------- |
| Inventory Control Tower | `/inventory`                       |
| Products (Item Master)  | `/inventory/products`              |
| Item Detail             | `/inventory/items/:id`             |
| Warehouses              | `/inventory/warehouses`            |
| Stock Movements         | `/inventory/movements`             |
| Goods Receipts (GRN)    | `/procurement/goods-receipts`      |
| Requisitions Hub        | `/inventory/requisitions`          |
| Internal Requisitions   | `/inventory/requisitions/internal` |
| Purchase Requisitions   | `/inventory/requisitions/purchase` |
| Quality Control         | `/inventory/quality-control`       |
| Valuation Settings      | `/inventory/valuation/settings`    |
| Cost Layers View        | `/inventory/valuation/cost-layers` |
| Valuation Report        | `/inventory/valuation/report`      |
| Landed Cost Adjustment  | `/inventory/valuation/landed-cost` |
| Landed Cost Vouchers    | `/inventory/landed-cost-vouchers`  |
| Return to Vendor        | `/inventory/return-to-vendor`      |

### 5) Core Workflows

#### a. Goods Receipt (GRN) - Complete Flow

**Purpose**: Receive goods from purchase orders with batch/serial tracking and QC integration.

**Steps**:

1. Navigate to: **Inventory → Goods Receipts → Create GRN**
2. Select Purchase Order (only ISSUED POs shown)
3. System auto-populates line items from PO
4. For each line, enter:
   - **Quantity Received** (≤ ordered quantity)
   - **Batch Number** (if item is batch-tracked) - Required
   - **Expiry Date** (if batch-tracked and shelf-life managed)
   - **Manufacturer Batch Number** (optional, for traceability)
   - **Serial Numbers** (if item is serialized) - Count must equal quantity
   - **Certificate of Analysis** (optional file upload for QC)
5. Click "Create" to save as DRAFT
6. Review and click "Post"

(need document read and auto creating missing info(AI can be used))

**What Happens on Post**:

```
Backend automatically:
1. Creates StockMovement (type: RECEIPT, status: COMPLETED)
2. Creates StockMovementLine for each GRN line
3. If batch_no provided → Creates/Updates BatchLot record
   - Initial hold_status: QUARANTINE (if QC checkpoint exists)
   - Tracks expiry, manufacturer batch, COA
4. If serial_numbers provided → Creates SerialNumber records
   - Each serial: status=IN_STOCK, linked to batch and warehouse
5. Checks for QC Checkpoint (checkpoint_name='GOODS_RECEIPT')
   - If exists: Sets GRN quality_status='pending', stock state=QUARANTINE
   - If not exists: stock state=RELEASED (immediately available)
6. Creates CostLayer for valuation
7. Updates StockLedger (immutable transaction log)
8. Updates StockLevel (warehouse on-hand quantity)
9. Publishes 'stock.received' event → Finance creates GL posting
```

**Validation Rules**:

- Quantity received cannot exceed PO quantity (need to change this)
- For serialized items: serial count must match quantity
- Batch number required if item profile has is_batch_tracked=True
- Cannot post to closed fiscal period (if enforce_period_posting=True)

#### b. Quality Control Inspection

**Purpose**: Inspect received goods, determine pass/fail, and manage holds.

**Steps**:

1. Navigate to: **Inventory → Quality Control**
2. Tab: **Inspections**
3. System shows:
   - **Pending GRNs** (quality_status='pending') with alert badge
   - **QC Statistics** (pass rate, rejection %, inspection count)
4. Click "Inspect Now" on a pending GRN or click "+ Create Inspection"
5. Fill inspection form:
   - **Select GRN** (from pending list)
   - **QC Checkpoint** (auto-selected if only one for warehouse)
   - **Inspector** (defaults to current user)
   - **Quantities**:
     - Qty Inspected (≤ received quantity)
     - Qty Accepted
     - Qty Rejected (must sum to inspected)
   - **Status** (auto-calculated based on acceptance threshold):
     - PASS: accepted/inspected ≥ acceptance_threshold
     - FAIL: below threshold
     - CONDITIONAL_PASS: manual override
   - **Rejection Reason** (if rejected qty > 0)
   - **Notes** (optional details)
6. Submit inspection

**What Happens on Submit**:

```
Backend automatically:
1. Creates QCResult record
2. If status=FAIL and qty_rejected > 0:
   - Creates StockHold automatically
   - hold_type: QC_INSPECTION
   - qty_held: qty_rejected
   - status: ACTIVE
   - Requires manual disposition decision
3. If status=PASS:
   - Updates all related BatchLot records
   - Changes hold_status: QUARANTINE → RELEASED
   - Updates CostLayer.stock_state: QUARANTINE → RELEASED
   - Stock becomes available for use
4. Updates GRN.quality_status: 'pending' → 'passed'/'rejected'
5. Sends notification to GRN creator and procurement team
```

**QC Checkpoints Configuration**:

- Checkpoint Name: GOODS_RECEIPT, PERIODIC_INSPECTION, CUSTOMER_RETURN, etc.
- Acceptance Threshold: e.g., 95% (if 95 out of 100 pass, inspection passes)
- Escalation Threshold: e.g., 80% (below this, auto-escalate to management)
- Assigned To: User responsible for inspections

#### c. Stock Hold Management

**Purpose**: Manage quarantined or problematic stock with controlled release.

**Navigate to**: Inventory → Quality Control → **Stock Holds** tab

**Hold Types**:

- **QC_INSPECTION**: Auto-created on failed QC (most common)
- **DOCUMENT_HOLD**: Missing paperwork or customs clearance
- **APPROVAL_PENDING**: Awaiting management decision
- **CUSTOMER_RETURN**: Returned goods under investigation
- **DEFECT**: Known quality issue
- **OTHER**: Custom reasons

**Hold Statuses**:

- **ACTIVE**: Currently holding stock (not available)
- **RELEASED**: Released back to warehouse (available)
- **SCRAPPED**: Disposed of as scrap
- **RETURNED**: Returned to supplier

**Disposition Actions**:

1. **TO_WAREHOUSE**: Release to normal warehouse stock
   - Updates BatchLot.hold_status: ON_HOLD → RELEASED
   - Stock becomes available
2. **SCRAP**: Write off as unusable
   - Creates stock adjustment movement (OUT)
   - GL impact: Dr. Inventory Loss → Cr. Inventory Asset
3. **RETURN**: Send back to supplier
   - Creates Return to Vendor (RTV) record
   - Reverses original receipt valuation
4. **REWORK**: Send for rework/reprocessing
   - Transfers to rework location
   - Tracks rework cost separately

**Workflow**:

1. View holds list (filter by status, hold type, warehouse)
2. Click "Release" on a hold
3. Select disposition (TO_WAREHOUSE, SCRAP, RETURN, REWORK)
4. Enter notes (required for audit trail)
5. Submit

#### d. Batch/Lot Tracking with FEFO

**Purpose**: Track stock by production batch with expiry management and FEFO allocation.

**Navigate to**: Inventory → Quality Control → **Batch/Lot Tracking** tab

**Batch Lifecycle**:

```
1. QUARANTINE (initial state from GRN if QC required)
2. ON_HOLD (if QC fails or manual hold)
3. RELEASED (after QC pass, available for use)
4. SCRAP (disposed/expired)
```

**Key Fields**:

- **Internal Batch Code**: Your system batch ID (unique)
- **Manufacturer Batch No**: Vendor's batch number
- **Manufacturing Date**: Production date
- **Expiry Date**: Use-by date
- **FEFO Sequence**: Auto-calculated ranking (earliest expiry = lowest number)
- **Quantity Received**: Original batch size
- **Quantity Available**: Current available (decreases on issues)
- **Hold Status**: Current status in lifecycle
- **Certificate of Analysis**: Attached QC document

**FEFO Allocation** (First Expiry, First Out):

- When issuing stock (sales, production, transfer), system automatically:
  1. Filters batches: hold_status=RELEASED, exp_date > today
  2. Sorts by: fefo_sequence ASC (earliest expiry first)
  3. Allocates from earliest batches first
  4. Returns allocation plan with expiry warnings

**Expiry Management**:

- **Color Coding**:
  - Red: Expired (exp_date < today)
  - Orange: Expiring soon (≤ 30 days)
  - Green: Safe (> 30 days)
- **Auto-Alerts**: System warns when batches approach expiry
- **Disposal**: Click "Dispose" on expired batches
  - Select method: SCRAP, DONATE, RETURN_TO_SUPPLIER, REWORK
  - Creates adjustment movement
  - Updates batch status: SCRAP

**Batch Cost Tracking**:

- Each batch receives its own cost (from GRN)
- FEFO ensures oldest cost layers consumed first
- Accurate COGS calculation per batch sold

#### e. Serial Number Tracking

**Purpose**: Track individual items with unique identifiers (warranties, assets, RMA).

**Navigate to**: Admin → Inventory → Serial Numbers (or via GRN detail)

**Serial Lifecycle**:

```
1. IN_STOCK (received, in warehouse)
2. ASSIGNED (reserved for sales order)
3. ISSUED (shipped to customer)
4. RETURNED (customer return)
5. SCRAPPED (disposed/damaged)
```

**Key Fields**:

- **Serial Number**: Unique identifier (barcode, alphanumeric)
- **Budget Item**: Item this serial belongs to
- **Warehouse**: Current location
- **Batch Lot**: Associated batch (if batch-tracked)
- **Purchase Order**: Original PO received from
- **Sales Order**: Order assigned to (when ASSIGNED)
- **Warranty Start**: Coverage start date (from GRN date)
- **Warranty End**: Calculated from warranty duration
- **Status**: Current lifecycle stage

**Usage Example - Serialized Electronics**:

1. Receive 5 laptops via GRN:
   - Enter serials: SN001, SN002, SN003, SN004, SN005
   - System creates 5 SerialNumber records, status=IN_STOCK
2. Create Sales Order for 2 laptops:
   - Select specific serials: SN001, SN002
   - Status changes: IN_STOCK → ASSIGNED
3. Ship Delivery Order:
   - Status changes: ASSIGNED → ISSUED
4. Customer returns SN001:
   - Create customer return
   - Status changes: ISSUED → RETURNED
   - Can inspect and re-issue or scrap

#### f. Stock Movements & Transfers

**Purpose**: Record all stock movements (receipts, issues, transfers, adjustments).

**Navigate to**: Inventory → Stock Movements

**Movement Types**:

- **RECEIPT**: Goods received (from GRN, production, returns)
- **ISSUE**: Goods issued (sales, production consumption)
- **TRANSFER**: Between warehouses
- **ADJUSTMENT**: Cycle count corrections, damage write-offs

**Transfer Flow** (Two-Step with In-Transit):

1. Create Transfer:
   - From Warehouse, To Warehouse
   - Add line items with quantities
   - Optional: batch/serial selection
   - Status: DRAFT
2. Post Transfer:
   - Stock deducted from From Warehouse
   - Creates InTransitShipmentLine records
   - Movement status: IN_TRANSIT
   - Stock not yet at destination
3. Confirm Receipt at Destination:
   - Click "Confirm Receipt"
   - Stock added to To Warehouse
   - InTransit cleared
   - Movement status: COMPLETED

**What Transfer Creates**:

```
1. Movement OUT from source warehouse:
   - Consumes cost layers (FIFO/LIFO/AvgCost)
   - Creates StockLedger entry (negative quantity)
   - Updates StockLevel (decreases)
   - Creates MovementEvent (type: TRANSFER_OUT)
2. InTransit Record:
   - Tracks quantity and cost in transit
   - Visible in In-Transit Report
3. Movement IN to destination warehouse (on confirm):
   - Creates new cost layer at transfer cost
   - Creates StockLedger entry (positive quantity)
   - Updates StockLevel (increases)
   - Creates MovementEvent (type: TRANSFER_IN)
```

#### g. Requisition Workflows

**Internal Requisition** (Inventory → Requisitions → Internal):

- Purpose: Request stock from warehouse for department/project use
- Workflow:
  1. Create requisition (select warehouse, add items)
  2. Submit for approval
  3. Warehouse approves
  4. Issue stock (creates ISSUE movement)
  5. Stock deducted from warehouse

**Purchase Requisition** (Inventory → Requisitions → Purchase):

- Purpose: Request procurement to buy items
- Workflow:
  1. Create PR (add items, justification)
  2. Submit for approval
  3. Budget check (if budgeting enabled)
  4. Approved PR → Convert to Purchase Order
  5. PO → GRN → Stock received

### 6) Inventory Valuation

**Navigate to**: Inventory → Valuation

#### Valuation Methods

**FIFO (First In, First Out)**:

- Consumes oldest stock first
- Each receipt creates a cost layer
- Issues consume from oldest layer
- Best for: Items with expiry, consistent pricing

**LIFO (Last In, First Out)**:

- Consumes newest stock first
- Issues consume from newest layer
- Best for: High inflation environments (tax optimization)

**Weighted Average**:

- Recalculates average cost on each receipt
- All stock valued at same average
- Perpetual vs. Periodic modes
- Best for: Commodities, bulk materials

**Standard Cost**:

- Fixed predetermined cost
- Variances recorded separately
- Best for: Manufacturing with standard costing

#### Cost Layers

**Navigate to**: Inventory → Valuation → Cost Layers

**What is a Cost Layer?**

- Each goods receipt creates a layer
- Tracks: qty_received, cost_per_unit, qty_remaining
- On issue: consumes layers per valuation method
- Maintains qty_consumed and cost_remaining

**Example - FIFO**:

```
Layers:
1. Received 100 @ $10 = $1,000 (oldest)
2. Received 50 @ $12 = $600
3. Received 75 @ $11 = $825

Issue 120 units:
- Consume Layer 1: 100 @ $10 = $1,000 (fully consumed)
- Consume Layer 2: 20 @ $12 = $240 (30 remaining @ $12)
- Total COGS: $1,240
- Average COGS per unit: $10.33
```

**Layer Fields**:

- Source Document: GRN-001, Transfer-045, etc.
- Receipt Date: When received
- Stock State: RELEASED, ON_HOLD, QUARANTINE
- Landed Cost Adjustment: Additional costs allocated
- Adjustment Reason: Freight, customs, insurance

#### Landed Cost Allocation

**Purpose**: Distribute additional costs (freight, customs, insurance) to inventory value.

**Navigate to**: Inventory → Valuation → Landed Cost or → Landed Cost Vouchers

**Method 1: Direct Adjustment** (Legacy):

1. Navigate to: Inventory → Valuation → Landed Cost
2. Select Goods Receipt (GRN)
3. Enter total adjustment amount (e.g., $500 freight)
4. Select apportionment method:
   - **By Quantity**: Distribute proportionally to quantity
   - **By Value**: Distribute proportionally to item value
5. Submit
6. System updates all cost layers from that GRN
7. Adjustment splits between:
   - **Remaining stock**: Inventory Asset (Dr. Inventory, Cr. Accrued Freight)
   - **Already consumed**: COGS (Dr. COGS, Cr. Accrued Freight)

**Method 2: Landed Cost Vouchers** (Recommended):

1. Navigate to: Inventory → Landed Cost Vouchers
2. Create voucher:
   - Select GRNs to allocate to
   - Add cost components (line items):
     - Freight: $300
     - Customs Duty: $150
     - Insurance: $50
   - Total landed cost: $500
3. Select allocation method (Quantity or Value)
4. Preview allocation breakdown per GRN and item
5. Post voucher
6. System creates GL entries and updates cost layers

**GL Impact**:

```
Dr. Inventory (Asset) - for stock on hand
Dr. COGS (Expense) - for stock already sold
    Cr. Accrued Freight (or direct vendor payable)
```

#### Valuation Report

**Navigate to**: Inventory → Valuation → Report

**Purpose**: Financial inventory valuation as of a specific date.

**Features**:

- Select warehouse(s), item(s), or full company
- As-of date: Historical valuation supported
- Grouping: By warehouse, category, item
- Shows:
  - Quantity on hand
  - Average cost per unit
  - Total value (qty × cost)
  - Cost method used
- Export to Excel for period-end close

### 7) Advanced Features

#### a. Return to Vendor (RTV)

**Navigate to**: Inventory → Return to Vendor

**Purpose**: Return defective or excess goods to supplier with credit.

**Workflow**:

1. Create RTV:
   - Select original GRN (goods receipt to return)
   - Select line items to return
   - Enter quantities (≤ received quantity)
   - Enter reason (DEFECT, EXCESS, WRONG_ITEM, etc.)
2. Submit for approval
3. Approve RTV
4. Post RTV

**What Happens on Post**:

```
1. Creates stock movement (type: ISSUE, direction: OUT)
2. Reduces inventory quantity
3. Reverses cost layers (credits back original cost)
4. Creates supplier credit note (AP credit)
5. GL Posting:
   Dr. Accounts Payable (Supplier)
       Cr. Inventory Asset (reversal)
```

**RTV Statuses**:

- DRAFT: Being created
- SUBMITTED: Awaiting approval
- APPROVED: Ready to ship
- SHIPPED: Sent to vendor
- CREDITED: Supplier credit received

#### b. Auto-Replenishment

**Purpose**: Automated purchase requisition when stock hits reorder point.

**Setup** (per item per warehouse):

1. Admin → Inventory → Item Warehouse Configs
2. Set:
   - Auto Replenish: Enabled
   - Reorder Point (ROP): 50 units
   - Reorder Quantity (ROQ): 100 units
   - Preferred Supplier: Supplier A
   - Lead Time Days: 7 days

**How it Works**:

```
When stock level ≤ ROP:
1. System auto-generates Purchase Requisition
2. PR includes:
   - Item: <item_code>
   - Quantity: ROQ
   - Supplier: Preferred Supplier
   - Justification: "Auto-replenishment (ROP breach)"
3. PR routed for approval via workflow
4. Approved → Converted to PO
5. PO → GRN → Stock replenished
```

**Monitoring**:

- Navigate to: Inventory Control Tower
- "Auto Replenishment" card shows:
  - Items below ROP
  - Pending auto-PRs
  - Recommended quantities
- Click "Auto PR" button to trigger for specific items

#### c. Variance Management

**Purpose**: Identify and resolve discrepancies between physical and system stock.

**Types of Variance**:

1. **Cycle Count Variance**: Physical count ≠ system count
2. **Valuation Variance**: Standard cost ≠ actual cost
3. **Consumption Variance**: Actual usage ≠ planned usage

**Adjustment Process**:

1. Perform physical count
2. Compare to system quantity (StockLevel)
3. If variance found:
   - Create Stock Adjustment (movement type: ADJUSTMENT)
   - Enter counted quantity
   - System calculates variance (counted - system)
   - Enter reason (DAMAGE, THEFT, COUNT_ERROR, etc.)
4. Post adjustment
5. GL Posting:

   ```
   If positive variance (found more):
   Dr. Inventory Asset
       Cr. Inventory Gain (Other Income)

   If negative variance (shortage):
   Dr. Inventory Shrinkage (Expense)
       Cr. Inventory Asset
   ```

**Variance Dashboard**:

- Shows high-variance items
- Trends over time
- Drill-down to adjustment details

### 8) Integration Touchpoints1

#### Procurement Integration

**Purchase Order → Goods Receipt**:

- PO status: ISSUED
- Create GRN from PO (auto-loads lines)
- Post GRN → PO status updates: PARTIALLY_RECEIVED or RECEIVED
- PO line tracks: qty_ordered, qty_received, qty_outstanding

**Budget Commitment**:

- Approved PO creates budget commitment
- Posted GRN releases commitment, creates consumption
- Ensures budget tracking from approval to receipt

#### Finance Integration

**Automatic GL Postings** (Event-Driven):

**On GRN Post (Receipt)**:

```
Dr. Inventory Asset (current value)
Dr. GRNI - Goods Received Not Invoiced (if invoice pending)
    Cr. [Suspense or no entry until invoice]

On Supplier Invoice Match:
Dr. GRNI
    Cr. Accounts Payable
```

**On Sales Shipment (Issue)**:

```
Dr. COGS (consumed cost layers)
    Cr. Inventory Asset
```

**On Transfer**:

```
No GL impact (asset moves between locations)
Exception: If different cost centers, reclassify
```

**GL Posting Rules Resolution**:

1. Try: Item-specific account
2. Fallback: Item category account
3. Fallback: Warehouse default account
4. Fallback: Company default account
5. Error if no rule found (blocking)

#### Sales Integration

**Stock Reservation**:

- Sales Order status: CONFIRMED
- Stock reserved (qty_reserved increases)
- Available = on_hand - reserved
- Prevents overselling

**Fulfillment**:

- Create Delivery Order from Sales Order
- Pick stock (consumes from batches via FEFO if applicable)
- Post Delivery → Stock issued, COGS calculated
- Invoice customer (triggers revenue recognition)

### 9) Reporting & Analytics

**Available Reports**:

1. **Stock Summary**:

   - On-hand quantity per item per warehouse
   - Value (qty × cost)
   - Categorized: A-B-C classification

2. **Stock Movement Register**:

   - All movements over date range
   - Filter: warehouse, item, movement type
   - Audit trail

3. **Cost Layer Report**:

   - All cost layers with remaining quantities
   - Identify old/stuck inventory
   - Aging analysis

4. **Batch Expiry Report**:

   - Batches expiring within X days
   - Color-coded urgency
   - Disposal planning

5. **Serial Number Ledger**:

   - Track serial lifecycle
   - Warranty status
   - RMA tracking

6. **Stock Ledger**:

   - Immutable transaction log
   - Balance validation
   - Reconciliation to StockLevel

7. **In-Transit Report**:
   - Stock currently in transfer
   - ETA tracking
   - Exception alerts (overdue)

### 10) Troubleshooting & FAQs

**Q: Stock shows negative quantity**

- Cause: Issued more than received (data integrity issue)
- Fix: Run stock reconciliation; create adjustment to correct
- Prevention: Enforce validation on issue movements

**Q: Batch not available for selection**

- Cause: Batch hold_status is QUARANTINE or ON_HOLD
- Fix: Complete QC inspection or release hold manually

**Q: Serial count validation error**

- Cause: Number of serials doesn't match quantity
- Fix: Ensure serial array length equals quantity (e.g., qty=5 → 5 serials)

**Q: GRN posting fails "No GL posting rule found"**

- Cause: Missing inventory account mapping
- Fix: Finance → GL Posting Rules → Add rule for item/category/warehouse

**Q: Transfer stuck IN_TRANSIT**

- Cause: Destination warehouse hasn't confirmed receipt
- Fix: Go to stock movements, find transfer, click "Confirm Receipt"

**Q: Cost layer shows incorrect cost**

- Cause: Missing landed cost allocation or wrong valuation method
- Fix: Check valuation settings; allocate landed costs if needed

**Q: Cannot edit GRN after posting**

- Cause: Posted movements are immutable
- Fix: Create RTV (return to vendor) or adjustment to correct

**Q: QC inspection not showing pending GRN**

- Cause: No QC checkpoint configured for warehouse
- Fix: Admin → QC Checkpoints → Create checkpoint (checkpoint_name: GOODS_RECEIPT)

**Q: Expiry date warning not showing**

- Cause: Item not configured for batch tracking or expiry
- Fix: Edit item operational profile → Enable batch tracking, set shelf life

### 11) Security & Best Practices

**Permissions**:

- Separate create vs. post permissions
- QC inspectors cannot post GRNs (segregation of duties)
- Finance can view but not post inventory movements
- Audit log records all critical actions

**Best Practices**:

1. **Master Data Hygiene**:

   - Maintain accurate UoM conversions
   - Keep item operational profiles current
   - Review and archive inactive items

2. **Cycle Counting**:

   - Schedule regular cycle counts (weekly/monthly)
   - Focus on high-value (Class A) items
   - Investigate and resolve variances promptly

3. **Batch Management**:

   - Always capture batch numbers for regulated/expiry items
   - Monitor expiry dashboard weekly
   - Implement FEFO discipline in warehouse operations

4. **Serial Tracking**:

   - Use for high-value or warranty items
   - Scan barcodes to reduce manual entry errors
   - Maintain warranty database for customer service

5. **Valuation Method**:

   - Choose method aligned with accounting policy
   - Document choice for auditors
   - Don't change mid-year (impacts financial statements)

6. **Landed Costs**:

   - Allocate freight/customs promptly (don't wait for month-end)
   - Use Landed Cost Vouchers for better traceability
   - Reconcile accrued freight account monthly

7. **QC Process**:

   - Define acceptance criteria clearly
   - Train inspectors consistently
   - Document rejection reasons for supplier feedback

8. **Stock Transfers**:
   - Always use two-step with in-transit tracking
   - Don't allow destination to "pull" stock (creates ghost inventory)
   - Reconcile in-transit report daily

### 12) API Endpoints (Selected)

**Items**:

- GET `/api/v1/inventory/items/` - List items
- GET `/api/v1/inventory/items/:id/` - Item detail
- PATCH `/api/v1/inventory/items/:id/` - Update item

**Stock Movements**:

- GET `/api/v1/inventory/stock-movements/` - List movements
- POST `/api/v1/inventory/stock-movements/` - Create movement
- POST `/api/v1/inventory/stock-movements/:id/confirm_receipt/` - Confirm transfer

**Goods Receipts**:

- GET `/api/v1/inventory/goods-receipts/` - List GRNs
- POST `/api/v1/inventory/goods-receipts/` - Create GRN
- POST `/api/v1/inventory/goods-receipts/:id/post/` - Post GRN (triggers inventory update)

**Quality Control**:

- GET `/api/v1/inventory/qc-results/` - List QC inspections
- POST `/api/v1/inventory/qc-results/` - Create inspection
- GET `/api/v1/inventory/qc-results/pending_inspections/` - Get pending GRNs
- GET `/api/v1/inventory/qc-results/statistics/` - QC performance stats

**Stock Holds**:

- GET `/api/v1/inventory/stock-holds/` - List holds
- POST `/api/v1/inventory/stock-holds/:id/release/` - Release hold

**Batch Lots**:

- GET `/api/v1/inventory/batch-lots/` - List batches
- POST `/api/v1/inventory/batch-lots/:id/dispose/` - Dispose batch

**Serial Numbers**:

- GET `/api/v1/inventory/serial-numbers/` - List serials
- GET `/api/v1/inventory/serial-numbers/:id/` - Serial detail

**Valuation**:

- GET `/api/v1/inventory/valuation/cost-layers/` - Cost layers view
- POST `/api/v1/inventory/valuation/landed-cost/` - Apply landed cost

**Replenishment**:

- GET `/api/v1/inventory/replenishment/suggestions/` - Auto-replenishment suggestions
- POST `/api/v1/inventory/replenishment/auto-pr/` - Trigger auto-PR

---

### Local Run (No Docker)

- Backend (Django):

  1. cd backend && python -m venv venv && . .\venv\Scripts\Activate.ps1
  2. pip install -r requirements.txt
  3. Set USE_SQLITE=true in ackend/.env
  4. python manage.py migrate && python manage.py createsuperuser
  5. python manage.py runserver 0.0.0.0:8000

- Frontend (Vite):
  1. cd frontend && npm ci
  2. Create rontend/.env.local with VITE_API_BASE_URL=http://localhost:8000/api/v1
  3. pm run dev and open http://localhost:5173

Note: If organizational lists (branches/departments) appear empty after an update, restart the backend server.
