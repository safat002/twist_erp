# Twist ERP — Project Functionality (Module‑Wise, No Code)

This document describes the complete functional scope of Twist ERP v1, organized module‑wise. It focuses on what the system does, data it manages, user roles, rules/validations, workflows, and reporting. It excludes implementation details and code.

## 1) Platform & Cross‑Cutting

- Multi‑company, multi‑currency, multi‑jurisdiction.
- Company context: every record is scoped by `company` (and optional `company_group`).
- Role‑based access control (RBAC) with permission contexts (company + cost centers + modules).
- Maker–checker approvals: configurable per module/workflow (enforced or optional per company).
- Numbering/naming schemes per company for documents (invoices, journals, POs, budgets, etc.).
- Notifications: in‑app and email for key events (submissions, approvals, rejections, assignment changes).
- Audit trail on all critical models (created_by, updated_by, timestamps, state transitions, field deltas).
- Attachments & comments on major documents (POs, invoices, budgets, journals, tasks).
- API‑first: REST endpoints with company scoping; OpenAPI spec for integration.
- Data import/export: CSV/Excel templates for master data and bulk transactions (company‑safe).
- System configuration: toggles for approvals, numbering, price policies, tax defaults, cutoff dates.

## 2) Companies & Administration

- Master records: Company, Company Group, Fiscal Calendars, Currencies, Tax jurisdictions, Number series.
- User directory & roles; mapping users to default company and allowed companies.
- Module enablement per company (feature flags) and configurable settings per module.
- Environment & integration settings: email, notification channels, storage, AI features, SSO (future).

## 3) Users, Roles & Permissions

- Roles: System Admin, Company Admin, Module Owner/Sub‑Owner (per module), Functional Users (Finance, Sales, etc.).
- Permission scopes: by company, cost center(s), project(s), and document ownership.
- Assignment UIs:
  - Map users to permitted cost centers (Budgeting/Finance usage).
  - Assign module owner/sub‑owner for Budgeting (and others) per company.

## 4) Budgeting Module (Company‑wide Budgets + Cost‑Center Entry)

Business goals
- Define company‑wide “Declared Budgets” with entry windows; collect cost‑center itemized budgets under them; enable price policies and multi‑stage approvals; provide visibility of budget utilization.

Entities
- Budget (Declared Budget Name):
  - Fields: `name`, `category` (e.g., opex/capex), `period_start`, `period_end`, `entry_start_date`, `entry_end_date`, `status` (DRAFT, ENTRY_OPEN, ENTRY_CLOSED, FINALIZED), `currency`, `notes`, `company`, `created_by`.
  - Access: Only Budget module Owner/Sub‑Owner can create; no approval required; notification is sent on creation.
  - Selector: Shown to end users only if today is within `[entry_start_date, entry_end_date]` (valid entry time range).
- Cost Center:
  - Fields: `code`, `name`, `type` (department, unit, project, etc.), `currency`, `is_active`, `owners`/`members`, `company`.
  - Users are explicitly assigned permitted cost centers; all entry UIs filter by permitted cost centers.
- Budget Entry (Cost‑center scope, versioned):
  - Linked to Declared Budget + Cost Center.
  - Revision model: users can submit multiple times for the same Declared Budget; each submit creates/increments `revision_no` per cost center.
  - Statuses: DRAFT (user working), SUBMITTED (awaiting CC owner), PENDING_CC_APPROVAL, CC_APPROVED/REJECTED, PENDING_FINAL_APPROVAL (budget module owner), APPROVED (final), REJECTED.
  - Edit guards: After SUBMITTED or any approval, end user cannot modify. CC owner can modify only while PENDING_CC_APPROVAL. Approved or rejected revisions are immutable.
- Budget Line (itemized):
  - Fields: `item_code`, `description`, `uom`, `qty`, `unit_price`, `price_source` (STANDARD | LAST_PO | AVERAGE | MANUAL), `price_lookback_days` (default 365), `line_total`, `notes`.
  - Price Policy (company setting): default order = Standard Price → Last PO Price → Average Price (last 1 year); if none found, `unit_price = 0` and user can input manual unit price for that line only.

Key workflows
- Declared budget creation (Owner/Sub‑Owner only):
  1) Owner defines Budget with entry window and currency; save → notify relevant users.
  2) Appears in selectors for end‑users only while entry window is active.
- Budget Entry Page (end‑user):
  - Cards show: Budget Items Count, Total Budget Value, Used Value, Remaining Value; aggregated across all permitted cost centers for the selected Declared Budget; if user has multiple cost centers, values are summed.
  - “Add Budget Item” modal:
    - Select Cost Center (dropdown filtered to permitted ones only).
    - Select Declared Budget (date‑filtered list).
    - Select/enter item code and quantity.
    - System resolves unit price using Price Policy (Standard→Last PO→Average 365d); shows computed value (qty × price). If not found, sets 0 and allows manual entry of unit price.
    - Save creates/updates a DRAFT entry/line for that cost center under this Declared Budget and current revision.
  - Submit:
    - Submits the current DRAFT as a new revision for each cost center involved; locks user editing; notifies cost center owner(s).
- Cost Center Owner review:
  - Receives submission; can modify lines during PENDING_CC_APPROVAL; Approve or Reject.
  - Approval moves to budget module owner; rejection returns to user with comments.
- Final approval (Budget module Owner):
  - Can approve or reject CC‑approved revision; final approval locks revision for use.

Business rules
- Declared budget selector only shows active entry window budgets.
- Users can submit multiple times to the same Declared Budget; each submission creates a new `revision_no` (Rev 1, Rev 2, ...). Revision label format: “Rev N”.
- After submission or any approval, users cannot modify that revision.
- Price Policy is configurable per company including order and fallbacks; default order is Standard → Last PO → Average; lookback 365 days.
- Budget is for the whole company (declared scope); cost center is chosen per line during entry; there is no cost center on the declared budget itself.
- Notifications at key events (declared budget created, CC submission, CC approval/rejection, final approval/rejection).

Reports & views
- Declared Budget list; entry window calendar.
- Budget Entry summary (cards, by cost center, by item).
- Revision history per cost center + compare revisions.
- Utilization: used vs remaining (integrates with actuals from Finance/Procurement/Inventory postings).

Permissions
- Declared budget: create/edit by Module Owner/Sub‑Owner only; no approval required.
- Entry: end‑users with permitted cost centers; submit allowed during entry window.
- CC Review: cost center owners; Final approval: Budget module Owner/Sub‑Owner.

Integrations
- Finance: committed/actual spend for utilization (e.g., PR/PO/Invoice postings mapped to budgets and cost centers).
- Procurement: last PO price and average price calculations; items master standard price.

## 5) Finance (Overview; see Finance‑Module‑Detailed‑Spec)

- Chart of Accounts, multi‑currency ledgers, fiscal periods.
- Journals (general, AP, AR, inventory adjustments, accruals) with optional enforced approvals.
- Taxes (VAT/GST) configurable by company/jurisdiction; tax codes & rates.
- Bank accounts & reconciliation: CSV imports and auto‑match rules in v1.
- Multi‑currency revaluation for monetary accounts; FX gain/loss postings supported in v1.
- Numbering and naming formats per company.
- Reports: Trial Balance, GL, AR/AP Aging, VAT returns, Bank Reconciliation, FX Revaluation.

## 6) Procurement

- Master data: Suppliers, Items, Price lists (standard price), Terms.
- PR → RFQ → Quote → PO → GRN → AP Invoice flow.
- Price sources exposed to Budgeting (Last PO line, Average price last 365 days, Standard price).
- Approval workflows for PR/PO; vendor performance and lead times.

## 7) Inventory

- Items, Warehouses, Bins; Stock moves; Adjustments and Costing.
- Valuation methods (moving average v1); integrations with Procurement and Finance.
- Issue/receipt against projects/cost centers for utilization reporting.

## 8) Sales

- Customers, Quotes, Sales Orders, Delivery, AR Invoices, Receipts.
- Tax handling (customer tax regimes), currency handling, numbering schemes.

## 9) Production

- Work centers, BOMs (basic v1), Production Orders, Material Issues/Receipts.
- Integrates with Inventory and Finance for costing and postings.

## 10) Projects

- Project master, budgets (optional separate from cost centers), tasks, time/expense capture.
- Cost center mapping for finance postings.

## 11) HR

- Employees, Departments (can overlap Cost Centers), Basic payroll GL postings (v1).

## 12) Assets

- Asset register, capitalization, depreciation schedules, disposals, GL postings.

## 13) Quality

- QA plans, inspections, results, holds/releases; ties to Procurement and Production.

## 14) Analytics & Dashboards

- Role‑based dashboards; KPIs for Budgets, Finance, Procurement, Inventory, Sales.

## 15) Form Builder

- Create custom forms for data capture; validation; mapping to entities.

## 16) AI Companion

- Contextual assistance; alerts; anomaly hints; summarizes approvals.

## 17) Workflows

- Visual definition of approval/processing flows; conditions based on values/roles.

## 18) Report Builder

- Self‑service reports with filters; export CSV/Excel/PDF.

## 19) Tasks & Notifications

- Tasks linked to documents; notifications on due dates, assignments, state changes.

## 20) Policies

- Company policies: spending thresholds, approval matrices, numbering schemes, price policy order and fallbacks.

## 21) NGO & Microfinance (v1 outlines)

- NGO: Projects/grants, restricted fund tracking, donor reporting.
- Microfinance: Member accounts, loan products, disbursements, collections, GL impact.

## 22) Metadata & Security

- Custom fields/attributes per company; field‑level visibility; CSRF/JWT; permission context middleware.

## 23) Audit & Admin Settings

- Event log, model diffs; company settings UI; system health; job queues (future).

---

### Budgeting: Admin & Setup Checklist
- Assign Budget module Owner/Sub‑Owner.
- Define Cost Centers; assign owners and permitted users.
- Configure Price Policy order and lookback (default 365 days; Standard → Last PO → Average).
- Define Declared Budgets with entry window covering current date.
- Ensure items have standard prices; ensure PO history exists (optional) for price resolution.

### Budgeting: UI Pages
- Declared Budgets (admin only) — create/edit; no approval; sends notification.
- Budget Entry — selectors (Declared Budget + Cost Center), summary cards, lines grid, add‑item modal, submit.
- CC Review — modify lines (when pending), approve/reject; comments.
- Final Approval — approve/reject; finalizes revision.
- Revision History — compare revisions; read‑only detail.

### Finance: See `docs/Finance-Module-Detailed-Spec.md`

