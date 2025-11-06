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

#### d. Inventory & Warehouse Management
- **Purpose:** To maintain an accurate, real-time view of all stock.
- **Key Functions & Usage:**
    1.  **Track Stock Movements:** Every physical movement is recorded via a GRN (in), Delivery Note (out), or Stock Transfer (internal).
    2.  **Manage Stock Levels:** The system tracks on-hand quantity, reserved quantity, and available quantity per item in each warehouse.
    3.  **Perform Cycle Counts:** Users can perform periodic stock takes to ensure physical stock matches system records.
    4.  **Valuation:** The system automatically calculates the financial value of the inventory using methods like FIFO or Weighted Average.
- **Cross-Module Integration & Business Impact:**
    - **Business Impact:** Accurate inventory management is critical for business operations. It prevents stock-outs that halt sales/production and avoids over-stocking that ties up cash. The valuation directly impacts the company's balance sheet.
    - **Linkages:** This module is the physical heart of the operation, connecting the purchasing of goods (**Procurement**) with the selling (**Sales**) and production (**Manufacturing**) of goods.

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

1) Create Chart of Accounts (Finance â†’ Accounts) including Receivable/Payable and at least one Bank/Cash account.
2) Create Journals: GENERAL, SALES, PURCHASE, BANK, CASH (Finance â†’ Journals list is read-only; use admin if needed).
3) Set Finance settings in Company (Admin) if you want to change approval/review defaults.
4) Create current Fiscal Period (Finance â†’ Fiscal Periods) or run the seed command.
5) Optional: Define TaxJurisdiction/TaxCode (Admin) and map tax GL accounts.

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

---

## Budgeting Module – User Guide (Phase 8 Ready)

This section explains how to plan, enter, review, moderate, approve, and monitor budgets using the new Phase 8 UI and workflows.

### Roles & Access
- Budget Module Owner: Defines budget periods/toggles, final approval, activation, auto-approval control.
- Budget Moderator: Reviews all CC budgets, adds remarks, performs batch actions, can hold or send items back; no approval authority.
- Cost Center (CC) Owner/Deputy: Reviews submitted entries for their cost center; can modify and approve or send back.
- Entry User: Adds line items during the entry window for their assigned cost centers only.

### Key Screens (routes)
- Budgeting Hub: /budgets
- Budget Entry: /budgets/entry
- My Approval Queue: /budgets/approvals
- Moderator Dashboard: /budgets/moderator
- Remark Templates: /budgets/remark-templates
- Budget Monitor (analytics): /budgets/monitor
- Budget Registry: /budgets/list

### 1) Declare a Budget (Module Owner)
Use Budgeting Hub → “New Budget” or edit an existing budget.

Required configuration captured in one modal:
- Duration: duration_type (Monthly/Quarterly/Half-Yearly/Yearly/Custom) and optional custom_duration_days.
- Period: period_start → period_end (when the budget is effective).
- Entry Window: entry_start_date → entry_end_date and entry_enabled toggle.
- Grace Period: grace_period_days (default 3 days) between entry end and review start.
- Review Period: eview_start_date → eview_end_date and eview_enabled toggle.
- Budget Impact: udget_impact_start_date → udget_impact_end_date and udget_impact_enabled toggle (controls actual consumption tracking).
- Auto-Approval: uto_approve_if_not_approved (auto-approve on budget start if still pending).

Actions in grid:
- Open Entry → Submit for CC Approval → Start/Close Review → Request Final Approval → Activate.
- Clone: Create a new budget from an existing one; optionally clone lines, apply an adjustment factor, or derive from actual consumption.

### 2) Enter Budget Lines (Entry Users)
Go to Budget Entry (/budgets/entry).
- Select declared budget and your permitted cost center.
- Add items with quantity and unit price (auto-populated from policy or manual override).
- Submit to CC Owner when ready. You can save drafts before submission.

### 3) Cost Center Owner Review
Open My Approval Queue (/budgets/approvals). For each pending budget:
- Modify & Approve: Adjust quantities/amounts with justification and approve.
- Send Back: Return to Entry Users for corrections (only flagged items become editable during review period).
- For final stage (Module Owner approvals), “Approve Final” or “Send Back”.

### 4) Review Period & Sent-Back Items
The review window is indicated in Budgeting Hub and per-budget by ReviewPeriodStatus.
- During Review Period: Only lines marked “Sent Back” are editable by CC Owners/Entry Users.
- After Review Period: Lines are locked, except lines on Hold.

Held Items (line-level):
- Mark one or multiple lines as Held with reason and optional “held until” date.
- While Held, lines remain editable even after the review period ends.

### 5) Moderator Review (No Approval Power)
Go to Moderator Dashboard (/budgets/moderator) to process budgets in “Pending Moderator Review”.
- Filters: by procurement class, category, variance, amount thresholds.
- Batch actions:
  - Add Remarks (custom text or apply templates to many lines).
  - Send Back for Review (flags items for CC corrections).
  - Hold (reason + hold-until) to allow edits after review close.
- Mark Reviewed: When finished, forward to final approval.
- Variance Audit: Open the audit drawer on a line to view original vs. modified values and who changed what/when/why.

Remark Templates (/budgets/remark-templates):
- Create shared or private templates (e.g., “Qty Exceeds Standard”, “Price Outdated”).
- Apply from Moderator Dashboard during batch remarking.

### 6) Final Approval & Activation
- Module Owner “Approve Final” from My Approval Queue, then “Activate” in Budgeting Hub.
- If Auto-Approval is on, budgets auto-approve on start date if still pending.
- When activated, Budget Impact ON: real-time consumption matches against budget.

### 7) Variance Tracking & Audit
Every modification to a line records:
- Original vs. current values (qty/price/value), variance/variance%.
- Who changed it, when, and why.
- View per-line variance audit in Moderator Dashboard (Audit drawer) and generate reports via API.

### 8) Real-Time Monitoring
Open Budget Monitor (/budgets/monitor).
- Submission Progress: % submitted (and counts of submitted vs. not-started CCs).
- Allocation Overview: Consumed vs. Remaining stacks per budget.
- Bottlenecks: Budgets stuck >5 days in pending stages.
- Status Summary: Count and allocation by status.

### 9) Tips & Troubleshooting
- Review Period doesn’t open: Ensure entry window ended and grace period elapsed; set review dates and enable eview_enabled.
- Can’t edit during review: Only Sent-Back items are editable; moderators/owners can send back or put lines on hold.
- Activation blocked: Approvals must be completed; use “Approve Final”, then “Activate.”
- Auto-Approval: Ensure uto_approve_if_not_approved is toggled on the declared budget.

### 10) Security & Permissions (summary)
- Entry: CC owners/deputies/entry users of that CC can add/edit during entry.
- Moderator: Users with moderation permission can access Moderator Dashboard/batch ops.
- Module Owner: Users with final approval permission can approve final and activate budgets.

This Phase 8 UI aligns with the formal spec in docs/Budget-Module-Final-Requirements.md and supports end-to-end planning → entry → review/moderation → approval → activation → monitoring.

### 11) AI Features (Phase 9)
- Price Prediction (per line): Open Moderator Dashboard → Insights on a line to see predicted price from PO history with confidence.
- Consumption Forecast (per line): Insights show projected consumption vs. limit; a red tag appears on lines flagged to exceed after you compute forecasts.
- Compute Forecasts (per budget): In Budgeting Hub, click “Forecasts” on a budget row to compute and store projections for all lines.
- Alerts: Budget Monitor → Alerts → “Load Alerts” to see utilization threshold and forecast exceedance alerts.

---

## Budgeting Module — Recent Updates (Phase 8 + 9)

- Declaration modal now includes: duration_type, custom_duration_days, entry_enabled, grace_period_days, eview_start_date/eview_end_date + eview_enabled, udget_impact_start_date/udget_impact_end_date + udget_impact_enabled, and uto_approve_if_not_approved.
- Review indicators (Grace/Review/Open/Closed) are shown in the Budgets grid.
- Moderator Dashboard (/budgets/moderator) supports filters, batch remarks/templates, batch send‑back, batch hold, and per‑line variance audit.
- Approval Queue allows “Modify & Approve” by CC Owners (adjust quantities/values with justification).
- Budget cloning available from the Budgets grid (“Clone”).
- AI (Phase 9):
  - Price Prediction per line (Moderator → “Insights”).
  - Consumption Forecast per line (Moderator → “Insights”).
  - Compute Forecasts per budget (Budgets grid → “Forecasts”), and lines projected to exceed show a red “Forecast Exceed” tag.
  - Alerts in Budget Monitor (click “Load Alerts”) for utilization threshold and forecast exceedance.

### Local Run (No Docker)

- Backend (Django):
  1) cd backend && python -m venv venv && . .\venv\Scripts\Activate.ps1
  2) pip install -r requirements.txt
  3) Set USE_SQLITE=true in ackend/.env
  4) python manage.py migrate && python manage.py createsuperuser
  5) python manage.py runserver 0.0.0.0:8000

- Frontend (Vite):
  1) cd frontend && npm ci
  2) Create rontend/.env.local with VITE_API_BASE_URL=http://localhost:8000/api/v1
  3) 
pm run dev and open http://localhost:5173

Note: If organizational lists (branches/departments) appear empty after an update, restart the backend server.
