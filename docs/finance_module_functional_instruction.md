Document Metadata

- Title: “Finance Module — Detailed Functional Specification”
- File: docs/Finance-Module-Detailed-Spec.md
- Version, Author, Date, Status
- Change log table

1. Scope & Objectives

- In scope: COA, Journals (JV), AR/AP Invoices, Payments/Receipts, Period Close, Accruals/Provisions, Bank
  Reconciliation, Tax/VAT, Multi‑Currency basics, Numbering.
- Out of scope (v1): Advanced consolidation, fixed asset depreciation posting (if handled by Assets), IFRS/GAAP
  reporting nuances beyond basics.
- Success criteria: Describe the measurable outcomes (e.g., period locking works across companies, all journal
  postings audited, budget vs actuals available).

2. Assumptions & Constraints

- Single source of truth: PostgreSQL; one chart of accounts per company.
- Multi‑company separation: no cross‑company postings; consolidation handled separately.
- Time zone, currency precision, tax rounding rules (define defaults).
- Performance & retention expectations.

3. Roles & Permissions

- Roles: Accountant, Controller, CFO, Auditor (view), Cashier (payments), AR/AP Clerk.
- Permission matrix (what each role can do):
  - Create/Review/Post journals
  - Create/Approve invoices
  - Create/Approve payments
  - Lock/unlock periods
  - Maintain COA, numbering, tax tables
- Scopes: company scope; optional cost center/project scope on lines.

4. Entities & Data Model (Field Tables)

- Chart of Accounts (COA)
  - Fields: code, name, type (asset/liability/equity/income/expense), parent, currency, allow_posting (Y/N),
    is_active.
  - Rules: parent roll‑up, code uniqueness, posting constraints (e.g., non‑posting headers).
- JournalVoucher (JV)
  - Header: company, date, ref_no, status (DRAFT/REVIEW/POSTED), narration, period.
  - Lines: account, debit, credit, tax code, cost center, project, description.
  - Rules: debits = credits; blocked accounts; period open; approval required if enabled.
- AR/AP Invoices
  - Header: company, customer/supplier, invoice_no, date, due_date, currency, status, terms.
  - Lines: product/service, qty, unit_price, discount, tax, account mapping (income/expense).
  - Rules: mandatory partner; tax calc; exchange rate handling (if multi‑currency).
- Payments/Receipts
  - Header: company, customer/supplier/bank, doc_no, date, method (cash/bank), status.
  - Lines: allocations to invoices (partial/full), write‑offs, bank/fees.
- Accrual/Provision Entries
  - Define how accruals are captured (e.g., from GRNs, month‑end provisions), reversal policy.
- Bank Reconciliation
  - Statement lines: date, ref, amount, matched JV/payment, remaining balance; reconciliation status.
- Tax/VAT Table
  - Tax code, rate, inclusive/exclusive flag, jurisdiction, accounts for tax capture/settlements.
- Numbering & Period Control
  - Numbering rules per doc type; open/close period flags per company.

For each entity: include a field table with Name, Type, Required, Constraints, Notes.

5. Process Flows (State Machines + Sequence)

- Journal Voucher: DRAFT → REVIEW (optional) → POSTED; Reversal allowed (auto JV).
- AR Invoice: DRAFT → APPROVED → POSTED; credit notes flow.
- AP Invoice: DRAFT → APPROVED → POSTED; debit notes flow.
- Payment: DRAFT → APPROVED (optional) → POSTED; allocations to invoices.
- Period Close: Pre‑checks (unposted JVs, open invoices), freeze, unlock by Controller/CFO.
- Bank Reconciliation: import statement (future), match transactions, reconcile.
- Accruals: month‑end accrual JVs; optional auto‑reverse on next period open.

Provide for each flow:

- Preconditions, transitions, who can act, validations at each step, system effects (e.g., GL impact).

6. Validations & Business Rules

- Journals must balance (sum debit = sum credit).
- GL posting forbidden if:
  - Period closed
  - Non‑posting accounts used
  - Invalid cost center/project (if required)
- Invoices:
  - Due date ≥ invoice date
  - Lines map to correct income/expense accounts
  - Tax calc consistent (rounding, inclusive/exclusive)
- Payments:
  - Allocation cannot exceed open amount
  - Bank account required for bank payments
- Multi‑currency (if applicable):
  - Rate capture per doc date; G/L revaluation policy for period close
- Numbering:
  - Uniqueness per company & doc type; format (prefix + FY + width)
- Period lock:
  - Prevent postings; Controller overrides (tracked/audited)

7. Approvals & SoD

- Approvals:
  - Journals: reviewer → poster (Controller)
  - Invoices: preparer → approver (manager/controller)
  - Payments: cashier → approver (controller/CFO); support thresholds
- SoD examples:
  - Creator cannot approve/post the same JV
  - AR invoicer cannot approve their own invoices
- Approval Matrix (link to Appendix G style)
  - Define stages, roles, thresholds (amount), scope (company/CC), SLA, delegation

8. Screens & UX (Wireframe‑Level)

- Master Data:
  - Chart of Accounts: tree view, add/edit accounts, non‑posting flags, import/export
- Journals:
  - JV List: filters (date, status, account, company)
  - JV Form: header (company/date/ref), lines grid (account picker, debit, credit, CC/project), balance indicator,
    save/submit/post, reversal button
- Invoices (AR/AP):
  - Lists: by status/partner; buttons (create, approve, post, credit/debit note)
  - Forms: header + lines + tax breakdown; allocations (payments link)
- Payments:
  - List & Form: method, bank account, allocations UI, fees
- Period Control:
  - Period calendar; open/close buttons; pre‑check results; force unlock (with reason)
- Bank Reconciliation:
  - Bank account selector; statement import (future); match suggestions; reconciliation status
- Reports:
  - TB, P&L, Balance Sheet, Cash Flow; budget vs actual; aging
- Error states & dialogs:
  - Period closed, unbalanced JV, missing accounts, SoD violation warnings

Include minimal wireframe sketches/annotations (text descriptions suffice).

9. Reports & KPIs

- Core financial reports:
  - Trial Balance (as-of date/period)
  - Profit & Loss (period range, comparison vs budget)
  - Balance Sheet (as-of date)
  - Cash Flow (direct/indirect simplified)
- Operational:
  - AR Aging, AP Aging, Collections, Payables projections
- Budget vs Actual:
  - By company, by cost center, by account group
- Export: CSV/PDF; parameterized filters; saved views

Define each report’s filters, grouping, and columns.

10. Integrations

- Budget:
  - JV lines optionally tagged with budget/cost center; actuals roll up to budget vs actual reporting
- Procurement:
  - Accruals from GRNs; AP invoices from POs (future automation details)
- Inventory/Production:
  - Inventory valuation postings; WIP adjustments (future)
- Assets:
  - Depreciation JVs (future)
- Taxes:
  - Tax account postings; return prep exports
- Import/Export:
  - Initial COA import; JV import template; export reports

Define integration points and data mapping at a functional level.

11. APIs (Functional)
    Document endpoints and behaviors (no code):

- COA
  - GET/POST/PATCH /finance/accounts
- Journals
  - GET/POST /finance/journals; transitions: /submit, /post, /reverse
- Invoices
  - GET/POST /finance/ar-invoices, /finance/ap-invoices; transitions: /approve, /post, /credit-note, /debit-note
- Payments
  - GET/POST /finance/payments; transitions: /approve, /post
- Periods
  - GET/POST /finance/periods; /close, /open, /unlock
- Bank Reconciliation
  - GET/POST /finance/bank-recon; /match, /unmatch, /reconcile

13. Audit, Logging, Monitoring

- Audit every create/update/transition/post action, with user/time/changes
- Security: JWT required; SoD enforced; least privilege
- Compliance: document retention, PII rules (if applicable)

15. Acceptance Criteria & Test Scenarios

- Balanced JV cannot post → error; balanced JV posts → success, audit created
- Period closed: any post attempt blocked; unlock with Controller permission and audit note
- AR invoice approved posts to revenue and AR; payment allocation reduces AR balance
- Approval matrix: routes correctly by amount threshold; SoD violation blocked/warned
- Budget vs Actual shows posted amounts driven by CC/account mapping

List 20–30 prioritized test cases with preconditions and expected results.

16. Open Questions & Decisions

- Multi‑currency: scope of revaluation and FX gain/loss postings in v1?
- Tax regime specifics (VAT types, jurisdictions): configurable table or per company defaults?
- Bank reconciliation: CSV import formats; auto‑match rules in v1?
- Journal approvals: enforce review stage or optional?
- Naming/numbering formats per company?

17. Implementation Plan (Doc‑Only)

- Draft sections 1–7 first; review with finance stakeholders
- Add entity field tables and screen flows
- Validate validations and SoD rules with controllers

If you want, I can produce a first draft of docs/Finance-Module-Detailed-Spec.md using this outline (still no code),
and you can review/edit it with your finance stakeholders before we start building screens and endpoints.
