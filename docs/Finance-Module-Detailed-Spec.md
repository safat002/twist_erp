# Finance Module — Detailed Functional Specification (No Code)

This specification defines the Finance module scope and behavior for v1. It is implementation‑agnostic and focuses on functional requirements, data structures, validations, processes, approvals, and reporting. All items marked in discovery are confirmed as in‑scope for v1.

## 1) Scope & Principles

- Multi‑company, multi‑currency, multi‑jurisdiction.
- Accurate, auditable, period‑based accounting aligned with IFRS‑style principles.
- Maker–checker approvals configurable per company (enforced or optional by document type).
- Naming/numbering formats configurable per company per document type.
- Integration with Budgeting, Procurement, Inventory, Sales, Projects, HR/Payroll, Assets.

## 2) Master Data & Configuration

- Chart of Accounts (CoA): hierarchy with account types (Assets/Liabilities/Equity/Income/Expense).
- Currencies: base currency per company; support for transactional currencies; daily (or periodic) FX rates.
- Tax Regimes (VAT/GST):
  - Configurable tables per company: tax jurisdictions, tax codes, rates, input/output accounts, exemptions, reverse charge.
  - Defaults per company and per customer/supplier; override per document line.
- Dimensions: Cost Centers, Projects (optional), Departments — usable on journal lines and postings.
- Number series: per document type (journal, invoice, payment, receipt, credit note, etc.).
- Periods/Calendars: fiscal years, periods, open/close/lock flags.
- Approval policies: per document type; enable/disable maker–checker and thresholds.

## 3) Currencies & FX

- FX Rates: manual import or API load; effective date; source; mid, buy, sell (store mid in v1).
- Transaction Posting: document currency → functional (company base) currency at document date rate.
- Revaluation (v1 in scope):
  - Scope: Unrealized FX revaluation of monetary accounts (AR/AP, bank, cash) at period end.
  - Process: For each monetary account with foreign balances, compute difference between carrying amount and amount at closing rate; post FX gain/loss to designated accounts.
  - Journals: auto‑generated revaluation journal with references per account and currency.
  - Reversal: next period opening can reverse revaluation entries (configurable).
  - Realized FX: On settlement, recognize realized FX gain/loss between invoice rate and payment rate.

## 4) Taxes (VAT/GST)

- Tax Codes: standard, zero‑rated, exempt, out‑of‑scope; jurisdiction mapping.
- Tax Calculation: per line; supports inclusive/exclusive amounts; rounding rules.
- Posting: tax components mapped to tax GL accounts (input/output VAT) per company.
- Reporting: VAT return summary by jurisdiction, detailed transactions, adjustments.
- Defaults: per company and per partner (customer/supplier) with override.

## 5) Journals & Approvals

- Journal Types: General, AP Invoice, AR Invoice, Payment, Receipt, Credit Note, Accrual/Provision, FX Revaluation, Bank Charges/Interest, Inventory Adjustments.
- Structure: header (date, number, currency, period, doc ref, notes, company) + lines (account, debit/credit, currency, fx rate, cost center, project, tax code, partner, memo).
- Validations: balanced (sum debits == credits), posting period open, account active/valid for posting, required dimensions.
- Approvals: configurable per company; can enforce a review stage or be optional. Default: enforced for external‑facing journals (AP/AR, payments), optional for internal adjustments.
- Locking: approved/posted journals are immutable; corrections via reversal/adjustment entries.

## 6) AR & AP

- Partners: Customers and Suppliers with currency, payment terms, tax profiles.
- Invoices/Credit Notes: line taxes; due dates; dunning/aging for AR; vendor aging for AP.
- Payments/Receipts: application to open invoices; partials; write‑offs within configured tolerance.
- Realized FX on settlement recorded automatically.

## 7) Bank & Reconciliation (v1)

- Bank Accounts: master with currency; GL account linkage.
- Bank Statements: CSV import (configurable mapping templates per bank); fields include date, description, amount, balance, reference.
- Auto‑Match Rules in v1:
  - Exact match by amount + date tolerance.
  - Reference/description contains known invoice/payment numbers.
  - Counterparty patterns (learned or admin‑defined).
- Manual matching UI; create adjusting entries for bank charges/interest.
- Reconciliation report: matched/unmatched lines, reconciling items, closing balance check.

## 8) Period Close & Controls

- Periods: open/close/lock; user with rights can close period; locked periods prevent postings.
- Accruals/Provisions: templates to accrue expenses/revenues and reverse next period.
- FX Revaluation: as per Section 3; generates journals; supported per company.
- Year‑end close: retain earnings transfer; ability to re‑open with audit log.

## 9) Numbering & Naming

- Per company, per document type sequences (prefix, zero‑pad, reset rules by year/month, optional suffixes).
- Examples: `JRN-2025-000123`, `AP-INV-25-11-000045`.

## 10) Integrations

- Budgeting: journal lines carry cost center/project to enable budget utilization reports.
- Procurement: AP invoices from POs/GRNs; price sources feed Budgeting policy (standard/last PO/average 365d).
- Inventory: valuation postings (moving average v1), stock adjustments.
- Sales: AR invoices from deliveries/orders.
- Projects: WIP and revenue recognition (basic tagging v1).
- HR/Payroll: summarized GL postings by cost center.

## 11) Reporting

- Trial Balance; General Ledger; Account Schedules; AR Aging; AP Aging.
- VAT Returns (summary/details) per jurisdiction.
- Bank Reconciliation report.
- FX Revaluation report (by account, currency, delta, postings). 
- Document registers (journals, invoices, payments).

## 12) Security, Audit, and Compliance

- Role‑based permissions; maker–checker; document locks after posting.
- Audit trail for changes, approvals, and postings (who/when/what changed).
- Data retention and export per company.

## 13) Data Migration & Imports

- Opening balances by account and dimension.
- Master imports: CoA, partners, tax codes, currencies/rates, cost centers, projects.
- Bank CSV mapping templates per bank.

## 14) User Experience (Key Screens)

- Chart of Accounts browser with balances.
- Journal entry & approval; reversal/copy.
- AP/AR Invoices and payments; application screen.
- Bank statement import & reconcile; rules configuration; exceptions.
- Tax setup and VAT return view.
- Period management (open/close/lock); FX revaluation wizard.
- Numbering sequences editor per document type.

## 15) Acceptance Criteria (Samples)

- Journals cannot post to locked periods; system explains why.
- FX revaluation generates balanced entries with correct gain/loss accounts; supports reversal next period if enabled.
- Bank auto‑match hits ≥ X% on clean statements with reference numbers (configurable).
- VAT reports tie to posted transactions; totals by jurisdiction match GL tax accounts.
- Approvals: configured enforcement is respected; audit trail shows approver and timestamp; posted documents are immutable.

## 16) Appendix A — CSV Bank Formats (v1)

- Required columns (configurable map): `Date`, `Description`, `Amount`, `Balance`, `Reference`.
- Date formats: `YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY` (selectable per template).
- Amount sign convention: positive=credit or debit flag; mapped during import.

## 17) Appendix B — Numbering Format Rules

- Pattern fields: `{SEQ}`, `{YYYY}`, `{YY}`, `{MM}`; example: `JRN-{YYYY}-{SEQ:000000}`.
- Reset: yearly or monthly; independent per document type; preview and lock.

## 18) Configurable “Yes” Items (Confirmed In‑Scope v1)

- Multi‑currency revaluation & FX gain/loss postings.
- Tax regime specifics (VAT types, jurisdictions) with configurable tables and per‑company defaults.
- Bank reconciliation with CSV import formats and auto‑match rules.
- Journal approvals: can enforce review stage or keep optional (per company, per doc type).
- Naming/numbering formats per company.

---

### Links
- See overall module map and processes in `docs/project_functionality.md`.

