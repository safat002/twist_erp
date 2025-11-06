# Twist ERP - Finance Module: Complete Final Requirements
## Full Specification - No Code, All Details Included

---

## TABLE OF CONTENTS

1. Module Overview
2. Organizational Structure & Roles
3. Chart of Accounts (CoA)
4. General Ledger (GL)
5. Accounts Receivable (AR)
6. Accounts Payable (AP)
7. Bank Management & Reconciliation
8. Multi-Currency & Exchange Rates
9. Journal Entries & Posting
10. Financial Reports
11. Cost Center Accounting
12. Intercompany Transactions
13. Fiscal Period Management
14. Tax Management
15. Audit Trail & Compliance
16. Integration Points
17. Key Features Summary
18. Implementation Roadmap

---

## SECTION 1: MODULE OVERVIEW

### 1.1 Purpose

The Finance Module manages all accounting operations including General Ledger, Accounts Receivable (AR), Accounts Payable (AP), cash management, and financial reporting. It integrates with Procurement, Budget, Inventory, and HR modules to provide complete financial control and visibility.

### 1.2 Scope & Coverage

**In Scope:**
- Chart of Accounts (CoA) setup and management
- General Ledger (GL) with multi-dimensional accounting
- Accounts Receivable (customer invoicing and collections)
- Accounts Payable (supplier invoicing and payments)
- Bank account management and reconciliation
- Journal entries and posting
- Financial statements (P&L, Balance Sheet, Trial Balance, Cash Flow)
- Cost Center allocation and tracking
- Intercompany transactions
- Multi-currency support with exchange rates
- Tax calculations and reporting
- Audit trail and compliance controls

**Out of Scope:**
- Payroll processing (handled by HR module)
- Fixed asset depreciation (handled by Asset Management)
- Inventory valuation (handled by Inventory module)

### 1.3 Key Integrations

**Procurement Module:**
- AP creation from supplier invoices
- GL posting on GRN and payment
- Budget commitment tracking
- Expense recognition

**Budget Module:**
- Budget vs. Actual comparison
- Consumption tracking
- Variance analysis
- Budget approval workflows

**Inventory Module:**
- Inventory GL posting
- COGS calculation
- Inventory valuation
- Stock transfer GL posting

**HR Module:**
- Payroll GL posting (if included)
- Employee expense reimbursement
- Advance tracking and recovery

---

## SECTION 2: ORGANIZATIONAL STRUCTURE & ROLES

### 2.1 Finance Organization

**Company Group Level:**
- Group CFO (Overall financial strategy, consolidation)
- Group Finance Manager (Group reporting)

**Company Level:**
- Finance Director (Company financial control)
- Finance Manager (GL and reporting)
- Accounts Receivable (AR) Manager (Customer invoicing, collections)
- Accounts Payable (AP) Manager (Supplier payments)
- Bank Reconciliation Officer (Cash management)
- Finance Officer (Data entry, GL posting)

**Department Level:**
- Cost Center Manager (CC expense tracking)
- Department Head (Expense authorization)

**External:**
- External Auditors (Compliance and audit)
- Tax Consultants (Tax planning)

### 2.2 Key Roles in Finance

| Role | Responsibility | Authority Level |
|------|-----------------|-----------------|
| **Finance Officer** | GL entry, invoice processing, reconciliation | Operational |
| **AR Manager** | Customer invoicing, collections, AR aging | Mid-management |
| **AP Manager** | Supplier payment processing, vendor management | Mid-management |
| **Finance Manager** | GL management, reporting, reconciliation oversight | Mid-management |
| **Finance Director** | Financial control, approval authority, reporting | Executive |
| **Bank Officer** | Bank reconciliation, cash management | Operational |
| **Cost Center Mgr** | CC expense tracking and authorization | Department |
| **CFO** | Strategic finance, board reporting, audit | Executive |

---

## SECTION 3: CHART OF ACCOUNTS (COA)

### 3.1 CoA Structure

**Chart of Accounts** = Master list of all GL accounts used by company

**Account Levels:**
- **Level 1: Account Type** (5-digit code)
  - 1xxxx = Assets
  - 2xxxx = Liabilities
  - 3xxxx = Equity
  - 4xxxx = Revenue
  - 5xxxx = Expenses
  - 6xxxx = Other Income
  - 7xxxx = Other Expenses

- **Level 2: Account Category** (5-digit + 2-digit)
  - 11xxx = Current Assets
  - 12xxx = Fixed Assets
  - 21xxx = Current Liabilities
  - 22xxx = Long-term Liabilities

- **Level 3: Account Sub-Category** (5-digit + 2-digit + 2-digit)
  - 11101 = Cash in Bank
  - 11102 = Cash in Hand
  - 12101 = Office Equipment
  - 12102 = Vehicles

### 3.2 Standard CoA Template

**ASSETS (1xxxx):**
- 11xxx Current Assets
  - 11101 Cash in Bank
  - 11102 Cash in Hand
  - 11201 Accounts Receivable - Trade
  - 11202 Accounts Receivable - Other
  - 11301 Inventory - Stock Items
  - 11302 Inventory - WIP
  - 11303 Inventory - Finished Goods
  - 11401 Prepaid Expenses
  - 11402 Advance to Suppliers
  
- 12xxx Fixed Assets
  - 12101 Office Equipment - Cost
  - 12102 Office Equipment - Accumulated Depreciation
  - 12201 Vehicles - Cost
  - 12202 Vehicles - Accumulated Depreciation
  - 12301 Building - Cost
  - 12302 Building - Accumulated Depreciation

**LIABILITIES (2xxxx):**
- 21xxx Current Liabilities
  - 21101 Accounts Payable - Trade
  - 21102 Accounts Payable - Other
  - 21201 Salary Payable
  - 21202 Interest Payable
  - 21301 Short-term Borrowings
  - 21401 Current portion of Long-term Debt
  - 21501 GST/VAT Payable
  - 21502 Income Tax Payable

- 22xxx Long-term Liabilities
  - 22101 Long-term Borrowings
  - 22201 Deferred Tax Liability

**EQUITY (3xxxx):**
- 31001 Capital/Share Capital
- 31002 Retained Earnings
- 31003 Current Year Profit

**REVENUE (4xxxx):**
- 41001 Sales - Product A
- 41002 Sales - Product B
- 41003 Sales - Services
- 41101 Revenue Discount/Returns
- 42001 Interest Income
- 42002 Other Income

**EXPENSES (5xxxx):**
- 51xxx Cost of Goods Sold
  - 51001 COGS - Raw Materials
  - 51002 COGS - Labor
  - 51003 COGS - Manufacturing Overhead
  
- 52xxx Operating Expenses
  - 52101 Salaries & Wages
  - 52102 Rent Expense
  - 52103 Utilities (Electricity, Water)
  - 52104 Office Supplies
  - 52105 Travel Expense
  - 52106 Communication Expense
  - 52107 Professional Fees
  - 52108 Maintenance & Repairs
  - 52109 Depreciation Expense
  - 52110 Insurance Expense

- 53xxx Selling Expenses
  - 53101 Advertising & Marketing
  - 53102 Sales Commission
  - 53103 Sales Person Travel

- 54xxx Administrative Expenses
  - 54101 Management Salaries
  - 54102 Office Rent
  - 54103 Administrative Staff Costs

**OTHER INCOME (6xxxx):**
- 61001 Gain on Sale of Assets
- 61002 Interest Income
- 61003 Foreign Exchange Gain

**OTHER EXPENSES (7xxxx):**
- 71001 Loss on Sale of Assets
- 71002 Interest Expense
- 71003 Foreign Exchange Loss

### 3.3 CoA Management

**CoA Setup:**
- Define all accounts during system setup
- Assign account type (Asset, Liability, Revenue, Expense, etc.)
- Set account number/code format
- Define which accounts are "detail" vs. "header"
- Link to cost centers (optional)
- Set posting rules (can post directly or only via journal)

**CoA Maintenance:**
- Add new accounts as needed
- Inactivate unused accounts (don't delete)
- Maintain hierarchy for reporting
- Review annually for compliance

---

## SECTION 4: GENERAL LEDGER (GL)

### 4.1 GL Overview

**General Ledger** = Core record of all financial transactions
- Double-entry bookkeeping (every transaction has debit and credit)
- All transactions traced to CoA
- Immutable audit trail
- Basis for all financial reporting

### 4.2 GL Transaction Flow

**How Transactions Enter GL:**

```
From Procurement Module:
├─ GRN Received → GL Entry
│   ├─ Dr. Inventory Account
│   └─ Cr. Accounts Payable
│
├─ Supplier Invoice Matched → GL Entry
│   ├─ Dr. Inventory/Expense Account
│   └─ Cr. Accounts Payable
│
└─ Payment Made → GL Entry
    ├─ Dr. Accounts Payable
    └─ Cr. Bank Account

From Sales Module:
├─ Customer Invoice → GL Entry
│   ├─ Dr. Accounts Receivable
│   └─ Cr. Revenue Account
│
└─ Customer Payment → GL Entry
    ├─ Dr. Bank Account
    └─ Cr. Accounts Receivable

From Budget Module:
├─ Budget Consumption → Tracked (not GL entry immediately)
│   └─ Actual GL entry when GRN/Payment made

From HR Module:
├─ Payroll → GL Entry
│   ├─ Dr. Salary Expense
│   └─ Cr. Salary Payable
│
└─ Payment → GL Entry
    ├─ Dr. Salary Payable
    └─ Cr. Bank Account

Manual Journal Entries:
├─ Finance Officer Creates JE
├─ Finance Manager Approves JE
└─ JE Posted to GL
```

### 4.3 GL Account Fields

**Account Master Data:**
- Account Code (unique identifier)
- Account Name (description)
- Account Type (Asset/Liability/Equity/Revenue/Expense)
- Account Level (1/2/3 in hierarchy)
- Opening Balance (at fiscal period start)
- Is Header Account (Y/N) - header accounts show summary only
- Allow Direct Posting (Y/N) - can transactions post directly or only via journal?
- Cost Center (optional link)
- Tax Type (Taxable/Exempt/Input Tax)
- Active/Inactive status

### 4.4 GL Entry Structure

**Each GL Entry (Transaction) Contains:**
- GL Entry ID (auto-generated, immutable)
- Entry Date (date transaction occurred)
- Fiscal Period (which period entry belongs to)
- Description (what the transaction is for)
- Reference (PO #, Invoice #, Check #, etc.)
- Posted By (who entered the transaction)
- Posted Date (when entered)
- Posting Status (Draft/Posted/Reversed)

**Debit Side:**
- Account Code
- Account Name
- Debit Amount
- Cost Center (if applicable)
- Description

**Credit Side:**
- Account Code
- Account Name
- Credit Amount
- Cost Center (if applicable)
- Description

**Validation:**
- Total Debits = Total Credits (always)
- Cannot post if unbalanced
- Cannot reverse posted entry (create reversing entry instead)

### 4.5 GL Posting Rules

**Automatic GL Posting (from other modules):**
- Triggered automatically
- No approval needed (pre-defined by setup)
- Posted to GL at time of event
- Example: GRN received → GL posted immediately

**Manual Journal Entry (JE):**
- Created by Finance Officer
- Requires Finance Manager approval
- Posted after approval
- Example: Depreciation, month-end accruals

**GL Posting Restrictions:**
- Cannot post to header accounts (only detail accounts)
- Cannot post after fiscal period closed (unless reopened by admin)
- Cannot modify posted entries (create reversing entry instead)
- Cannot delete entries (only reverse)

---

## SECTION 5: ACCOUNTS RECEIVABLE (AR)

### 5.1 AR Overview

**Accounts Receivable** = Money owed BY customers TO company
- Customer invoicing
- Customer payment tracking
- Collections management
- AR aging analysis
- Credit limit management

### 5.2 Customer Master Data

**Customer Information:**
- Customer Code (unique)
- Customer Name (legal name)
- Customer Type (Retail, Wholesale, Corporate, Individual)
- Billing Address
- Shipping Address (may differ)
- Contact Person
- Contact Email & Phone
- Tax ID / GST Number
- Customer Tax Status (Taxable/Exempt)

**Credit Terms:**
- Credit Limit ($amount customer can owe)
- Payment Terms (Net 15, Net 30, Net 60, etc.)
- Credit Status (Good/Warning/On Hold/Blocked)
- Discount Terms (if any: e.g., 2% 10 Net 30)

**Bank Details:**
- Bank Name
- Account Number
- IFSC/Swift Code

### 5.3 AR Transactions

**Customer Invoice Creation:**

```
Sales Order Fulfilled → Customer Invoice
├─ Invoice Number (auto-generated)
├─ Invoice Date
├─ Customer (from master)
├─ Line Items
│   ├─ Description
│   ├─ Quantity
│   ├─ Unit Price
│   ├─ Line Total
│   └─ Tax
├─ Subtotal
├─ Tax Amount
├─ Total Amount Due
├─ Payment Terms
├─ Due Date
└─ GL Posting:
    ├─ Dr. Accounts Receivable
    └─ Cr. Revenue

Invoice Status: DRAFT → SENT → PENDING → PAID
```

**Customer Payment Processing:**

```
Customer Pays Invoice → Payment Receipt
├─ Receipt Number (auto-generated)
├─ Payment Date
├─ Customer
├─ Amount Received
├─ Payment Method (Check, Wire, Credit Card, Cash)
├─ Bank Account Deposited
├─ Invoices Paid (can pay multiple invoices)
└─ GL Posting:
    ├─ Dr. Bank Account
    └─ Cr. Accounts Receivable

Payment Status: DRAFT → POSTED → RECONCILED
```

**GL Impact of AR:**
- Invoice: Dr. AR, Cr. Revenue
- Payment: Dr. Bank, Cr. AR
- Credit Memo (refund): Dr. Revenue, Cr. AR

### 5.4 AR Aging Analysis

**Aging Categories (based on due date):**
- Current (Due within 0-30 days)
- 31-60 Days Overdue
- 61-90 Days Overdue
- 91-180 Days Overdue
- >180 Days Overdue

**Report shows:**
- Customer name
- Invoice number
- Invoice date
- Due date
- Amount due
- Days overdue
- Aging bucket

**Collections Actions:**
- Automated reminder emails (at 15, 30, 60 days)
- Manual collection follow-up tracking
- On-hold status for non-paying customers
- Credit limit blocking

### 5.5 Credit Management

**Credit Limit:**
- Set per customer
- Prevents orders exceeding limit
- Can be exceeded with approval
- Reviewed quarterly

**Credit Memo (for returns/adjustments):**
- Issued to customer
- Reduces AR balance
- GL: Dr. Revenue, Cr. AR
- Tracks reason for credit (return, discount, adjustment)

---

## SECTION 6: ACCOUNTS PAYABLE (AP)

### 6.1 AP Overview

**Accounts Payable** = Money owed BY company TO suppliers
- Supplier invoice recording
- Payment scheduling
- Supplier payment processing
- AP aging analysis
- Vendor management

### 6.2 Supplier Master Data

**Supplier Information:**
- Supplier Code (unique)
- Supplier Name (legal name)
- Supplier Type (Vendor, Contractor, Service Provider)
- Tax ID / GST Number
- Billing Address
- Contact Person
- Contact Email & Phone
- Supplier Tax Status (Registered/Unregistered)

**Payment Terms:**
- Standard Payment Terms (Net 15, Net 30, Net 60, COD, Advance)
- Discount Terms (e.g., 2% 10 Net 30)
- Preferred Payment Method (Check, Wire, Cash)
- Bank Details (Encrypted)

**Performance Tracking:**
- On-Time Delivery %
- Quality Rating
- Payment Terms Adherence

### 6.3 AP Transactions

**Supplier Invoice Recording:**

```
Invoice Received → Invoice Entry in AP
├─ Invoice Number (supplier's)
├─ Invoice Date
├─ Supplier (from master)
├─ PO Number (linked from Procurement)
├─ GRN Number (linked from Procurement)
├─ Line Items
│   ├─ Description
│   ├─ Quantity
│   ├─ Unit Price
│   ├─ Line Total
│   └─ Tax
├─ Subtotal
├─ Tax Amount
├─ Total Invoice Amount
├─ Payment Terms
├─ Due Date
└─ GL Posting (if 3-way match complete):
    ├─ Dr. Inventory/Expense Account
    └─ Cr. Accounts Payable

Invoice Status: MATCHED → APPROVED → SCHEDULED → PAID
```

**Supplier Payment Processing:**

```
Payment Due → Payment Made
├─ Payment Voucher Created
├─ Supplier
├─ Amount to Pay
├─ Invoices to Pay (can pay multiple invoices)
├─ Payment Method (Check, Wire, ACH, Cash)
├─ Bank Account
├─ Payment Date
├─ Approval (Finance Manager)
└─ GL Posting:
    ├─ Dr. Accounts Payable
    └─ Cr. Bank Account

Payment Status: DRAFT → APPROVED → PROCESSED → RECONCILED
```

**GL Impact of AP:**
- Invoice: Dr. Expense/Inventory, Cr. AP
- Payment: Dr. AP, Cr. Bank
- Debit Memo (if supplier owes): Dr. AP, Cr. Expense

### 6.4 AP Aging Analysis

**Aging Categories:**
- Current (Due within 0-30 days)
- 31-60 Days Overdue
- 61-90 Days Overdue
- >90 Days Overdue

**Report shows:**
- Supplier name
- Invoice number
- Invoice date
- Due date
- Amount due
- Days overdue
- Payment status

**Payment Planning:**
- Identify upcoming payments
- Plan cash requirements
- Prioritize payments (critical suppliers first)
- Track discount opportunities (early payment discounts)

### 6.5 Three-Way Matching

**Before AP Invoice Posted (from Procurement Integration):**
1. **PO:** What we ordered
2. **GRN:** What we received
3. **Invoice:** What we're charged

Must match before GL posting:
- Quantity match: PO Qty = GRN Qty = Invoice Qty
- Price match: PO Price = Invoice Price
- Amount match: PO Amount = Invoice Amount

If variance:
- Flag for approval
- Approver reviews variance
- If approved: Post GL
- If rejected: Return to supplier

---

## SECTION 7: BANK MANAGEMENT & RECONCILIATION

### 7.1 Bank Account Setup

**Bank Account Master:**
- Bank Name
- Account Number (masked for security)
- Account Holder Name
- Currency
- Account Type (Checking, Savings, Investment)
- Opening Balance
- Reconciliation Account (in GL)
- Authorized Users (who can access)

**Bank Connections:**
- Manual reconciliation (user enters bank data)
- Bank API integration (auto-fetch transactions, if available)
- Bank file import (CSV/MT940 format)

### 7.2 Bank Reconciliation Process

**Monthly Bank Reconciliation:**

```
Step 1: Get Bank Statement
├─ Starting Balance (from prior month)
├─ Deposits
├─ Withdrawals
├─ Ending Balance
└─ Bank Statement Date

Step 2: Match GL Transactions to Bank
├─ GL Bank Account shows:
│   ├─ Starting Balance
│   ├─ Deposits posted
│   ├─ Withdrawals posted
│   ├─ Ending Balance (per GL)
│   └─ Unreconciled items
│
└─ Match: Bank Deposits = GL Deposits
         Bank Withdrawals = GL Withdrawals

Step 3: Identify Reconciling Items
├─ Outstanding Checks (written but not cleared)
├─ Deposits in Transit (deposited but not cleared)
├─ Bank Fees (not yet in GL)
├─ Interest Income (not yet in GL)
├─ NSF Checks (rejected payments)
└─ Timing Differences

Step 4: Reconcile
├─ Bank Ending Balance: $X,XXX
├─ (+) Deposits in Transit: $XXX
├─ (-) Outstanding Checks: ($XXX)
├─ (+) Interest Income: $XX
├─ (-) Bank Fees: ($XX)
└─ = GL Ending Balance: $X,XXX ✓

Step 5: Post Bank Items to GL
├─ Bank Fees → Dr. Bank Expense, Cr. Bank
├─ Interest Income → Dr. Bank, Cr. Interest Income
└─ NSF Checks → Dr. AP, Cr. Bank

Step 6: Mark as Reconciled
└─ Status: RECONCILED
```

### 7.3 Cash Flow Management

**Cash Flow Forecasting:**
- Projected receivables (AR aging)
- Projected payables (AP aging)
- Planned expenses (from budget)
- Cash projection by week/month

**Cash Position Report:**
- Beginning cash balance
- Expected inflows (AR collections)
- Expected outflows (AP payments, expenses)
- Projected cash at period end

**Low Cash Alert:**
- If cash projected below minimum: Alert finance team
- Trigger: If cash < safety buffer ($XXX), alert

---

## SECTION 8: MULTI-CURRENCY & EXCHANGE RATES

### 8.1 Multi-Currency Support

**Company Base Currency:**
- All GL accounts in base currency (e.g., USD)
- Transactions in other currencies converted to base

**Supported Currencies:**
- Admin configures which currencies allowed
- Exchange rates maintained

**Transaction Currency:**
- Invoice in customer's currency
- Automatically converted to base currency at invoice date
- Exchange gain/loss tracked

### 8.2 Exchange Rate Management

**Exchange Rate Types:**
- Spot Rate (rate on transaction date)
- Average Rate (average for period)
- Closing Rate (rate at period end)

**Exchange Rate Sources:**
- Manual entry (user enters rates)
- Bank feed (if available)
- API integration (auto-fetch from service)

**GL Impact of Exchange Transactions:**

```
Example: Invoice to US customer in USD when company is in INR

Invoice: $100 USD
Exchange Rate: 1 USD = 85 INR
GL Entry:
├─ Dr. Accounts Receivable (in INR): 8,500
└─ Cr. Revenue (in INR): 8,500

Payment Received: $100 USD (but later when rate = 1 USD = 86 INR)
GL Entry:
├─ Dr. Bank (in INR): 8,600
├─ Cr. Accounts Receivable (in INR): 8,500
└─ Cr. Foreign Exchange Gain: 100

Foreign Exchange Gain = Positive impact on P&L
Foreign Exchange Loss = Negative impact on P&L
```

### 8.3 Month-End Revaluation

**Revaluation of AR/AP in Foreign Currency:**
- At month-end: Revalue all foreign currency AR/AP
- Use closing rate
- Recognize gain/loss

```
Example: AR Balance 1,000 USD
Prior GL: Dr. AR 85,000 INR (at 85 rate)
Month-End Closing Rate: 1 USD = 84 INR
Revaluation: AR should be 84,000 INR
GL Entry:
├─ Dr. Accounts Receivable: -1,000 (reduction)
└─ Cr. Foreign Exchange Loss: 1,000
```

---

## SECTION 9: JOURNAL ENTRIES & POSTING

### 9.1 Journal Entry Types

**Automatic JE (from other modules):**
- GRN Posting: Dr. Inventory, Cr. AP
- Invoice Posting: Dr. AP, Cr. Revenue
- Payment Posting: Dr. AP, Cr. Bank
- Payroll Posting: Dr. Salary Expense, Cr. Salary Payable

**Manual JE (entered by Finance):**
- Month-end accruals
- Depreciation
- Allowance for doubtful debts
- Expense allocation
- Correction entries

### 9.2 Manual JE Process

**Step 1: Create JE**
- Finance Officer clicks "Create Journal Entry"
- Enter JE Date
- Enter Description
- Enter Debit Lines:
  - Account Code
  - Amount
  - Cost Center (optional)
  - Description
- Enter Credit Lines:
  - Account Code
  - Amount
  - Cost Center (optional)
  - Description

**Validation:**
- Total Debits = Total Credits
- Both lines have accounts
- Amounts > 0

**Step 2: Submit for Approval**
- Status: SUBMITTED
- Notification to Finance Manager

**Step 3: Approval**
- Finance Manager reviews
- Checks:
  - Correct accounts
  - Correct amounts
  - Valid description
  - Proper cost center allocation
- Can: Approve, Reject, or Request Changes

**Step 4: Post JE**
- After approval: Post to GL
- Status: POSTED
- Immutable (cannot edit)

**Step 5: Reversal (if needed)**
- Cannot delete/edit posted JE
- Create reversing JE:
  - Same accounts, opposite amounts
  - Reference original JE
  - Clear description of why reversed

### 9.3 JE Fields

**JE Header:**
- JE Number (auto-generated)
- JE Date (date of transaction)
- Fiscal Period (which period)
- Description (what is it for)
- Narration (detailed explanation)
- Created By (user)
- Created Date
- Submitted By (approver)
- Submitted Date
- Status (Draft/Submitted/Posted/Reversed)
- Posting Status (Posted/Unposted)

**JE Line (Debit Side):**
- Account Code
- Account Name
- Amount
- Cost Center (optional)
- Description
- Tax (if applicable)

**JE Line (Credit Side):**
- Account Code
- Account Name
- Amount
- Cost Center (optional)
- Description
- Tax (if applicable)

---

## SECTION 10: FINANCIAL REPORTS

### 10.1 Standard Financial Statements

**Profit & Loss (P&L) Statement**
```
Revenue
├─ Sales Revenue
├─ Service Revenue
├─ Other Income
└─ Total Revenue: $XXX,XXX

Less: Cost of Goods Sold (COGS)
├─ Raw Materials
├─ Direct Labor
├─ Manufacturing Overhead
└─ Total COGS: ($XX,XXX)

Gross Profit: $XX,XXX

Less: Operating Expenses
├─ Salaries & Wages: $XX,XXX
├─ Rent Expense: $XX,XXX
├─ Utilities: $XX,XXX
├─ Marketing: $XX,XXX
├─ Depreciation: $XX,XXX
├─ Other Expenses: $XX,XXX
└─ Total Operating Expenses: ($XX,XXX)

Operating Income (EBIT): $X,XXX

Other Income/Expenses
├─ Interest Income: $XXX
├─ Interest Expense: ($XXX)
├─ Foreign Exchange Gain: $XXX
└─ Total Other: $XXX

Profit Before Tax: $X,XXX
Less: Income Tax: ($XXX)
Net Profit: $X,XXX
```

**Balance Sheet (Statement of Financial Position)**
```
ASSETS
Current Assets
├─ Cash: $XXX,XXX
├─ Accounts Receivable: $XXX,XXX
├─ Inventory: $XXX,XXX
├─ Prepaid Expenses: $XX,XXX
└─ Total Current Assets: $XXX,XXX

Fixed Assets
├─ Office Equipment (Net): $XX,XXX
├─ Vehicles (Net): $XX,XXX
├─ Buildings (Net): $XXX,XXX
└─ Total Fixed Assets: $XXX,XXX

Total Assets: $XXX,XXX

LIABILITIES
Current Liabilities
├─ Accounts Payable: $XX,XXX
├─ Salary Payable: $XX,XXX
├─ Short-term Borrowings: $XX,XXX
├─ Current Tax Payable: $XX,XXX
└─ Total Current Liabilities: $XXX,XXX

Long-term Liabilities
├─ Long-term Borrowings: $XX,XXX
├─ Deferred Tax: $XX,XXX
└─ Total Long-term Liabilities: $XXX,XXX

Total Liabilities: $XXX,XXX

EQUITY
├─ Capital: $XXX,XXX
├─ Retained Earnings: $XX,XXX
├─ Current Year Profit: $XX,XXX
└─ Total Equity: $XXX,XXX

Total Liabilities + Equity: $XXX,XXX
```

**Trial Balance**
```
Account Code | Account Name | Debit | Credit
10101 | Cash | 100,000 |
11201 | AR - Trade | 250,000 |
12101 | Office Equipment | 50,000 |
12102 | Accum. Depr. | | 10,000
21101 | AP - Trade | | 75,000
31001 | Capital | | 200,000
41001 | Sales | | 500,000
52101 | Salaries | 100,000 |
─────────────────────────────
Total | | 500,000 | 500,000
```

**Cash Flow Statement**
```
Operating Activities
├─ Net Income: $50,000
├─ Add: Depreciation: $5,000
├─ Add: AR Increase: ($20,000)
├─ Add: AP Increase: $15,000
└─ Cash from Operations: $50,000

Investing Activities
├─ Purchase Equipment: ($10,000)
├─ Sale of Assets: $5,000
└─ Cash from Investing: ($5,000)

Financing Activities
├─ Loan Repayment: ($10,000)
├─ Dividend Paid: ($5,000)
└─ Cash from Financing: ($15,000)

Net Change in Cash: $30,000
Opening Cash Balance: $70,000
Ending Cash Balance: $100,000
```

### 10.2 Management Reports

**Budget vs. Actual Report:**
```
Expense Category | Budget | Actual | Variance | % Var
─────────────────────────────────────────────────────
Salaries | 100,000 | 102,000 | (2,000) | -2.0%
Rent | 50,000 | 50,000 | — | 0.0%
Utilities | 10,000 | 12,000 | (2,000) | -20.0%
Supplies | 5,000 | 3,000 | 2,000 | 40.0%
─────────────────────────────────────────────────────
Total | 165,000 | 167,000 | (2,000) | -1.2%
```

**Expense Report by Cost Center:**
```
Cost Center | Salaries | Rent | Utilities | Total | % of Total
─────────────────────────────────────────────────────────────
Finance | 30,000 | 10,000 | 2,000 | 42,000 | 25%
Operations | 40,000 | 20,000 | 5,000 | 65,000 | 39%
Sales | 20,000 | 15,000 | 2,000 | 37,000 | 22%
HR | 12,000 | 5,000 | 1,000 | 18,000 | 11%
─────────────────────────────────────────────────────
Total | 102,000 | 50,000 | 10,000 | 162,000 | 100%
```

**Aging Reports:**
- AR Aging (by customer, days overdue)
- AP Aging (by supplier, payment status)
- Inventory Aging (by item, quantity on hand)

---

## SECTION 11: COST CENTER ACCOUNTING

### 11.1 Cost Center Setup

**Cost Center Definition:**
- Unique code and name
- Parent cost center (optional, for hierarchy)
- Cost center manager
- Budget allocated (links to Budget module)
- Active/Inactive

**Cost Center Hierarchy:**
```
Company
├─ Operations
│   ├─ Production
│   └─ Warehouse
├─ Finance
│   ├─ Accounting
│   └─ Treasury
├─ Sales
│   ├─ Sales Team A
│   └─ Sales Team B
└─ HR
    ├─ Recruitment
    └─ Administration
```

### 11.2 Expense Allocation to Cost Centers

**When JE Posted:**
- Each GL line can specify cost center
- If not specified: Posted to "Company" or "Unallocated"
- Example:

```
Dr. Salary Expense (CC: Finance) 10,000
Dr. Salary Expense (CC: Operations) 15,000
Cr. Salary Payable 25,000

Finance CC gets charged: 10,000
Operations CC gets charged: 15,000
```

**Direct Allocation:**
- Directly attributable to CC
- Example: Sales commission → Sales CC

**Indirect Allocation:**
- Shared by multiple CCs
- Allocated by formula:
  - Headcount
  - Square footage
  - Revenue
  - Usage

### 11.3 Cost Center Reports

**CC Expense Summary:**
```
Cost Center | Salaries | Rent | Utilities | COGS | Total
───────────────────────────────────────────────────────
Finance | 30,000 | 5,000 | 1,000 | — | 36,000
Operations | 40,000 | 20,000 | 5,000 | 50,000 | 115,000
Sales | 20,000 | 10,000 | 2,000 | — | 32,000
```

**CC Profit Center (if applicable):**
```
Cost Center | Revenue | COGS | Gross Margin | Expenses | Net
──────────────────────────────────────────────────────────
Sales Team A | 500,000 | 300,000 | 200,000 | 50,000 | 150,000
Sales Team B | 400,000 | 240,000 | 160,000 | 40,000 | 120,000
Total | 900,000 | 540,000 | 360,000 | 90,000 | 270,000
```

---

## SECTION 12: INTERCOMPANY TRANSACTIONS

### 12.1 Intercompany Setup

**When Applicable:**
- Company Group with multiple legal entities
- Inter-company goods transfer
- Inter-company service charges
- Inter-company loans

**Intercompany Accounts:**
- Due from Company A (what Co A owes us)
- Due to Company B (what we owe Co B)

### 12.2 Intercompany Transaction Flow

```
Company A (Selling) → Company B (Buying)

Company A GL Entry:
├─ Dr. Due from Company B: 50,000
└─ Cr. Sales Revenue: 50,000

Company B GL Entry:
├─ Dr. Expense/COGS: 50,000
└─ Cr. Due to Company A: 50,000

Both entries created simultaneously (linked)
```

### 12.3 Intercompany Reconciliation

**Monthly Reconciliation:**
- Due from Company A (Co A's view): vs.
- Due to Company A (other Co's view)
- Must match at month-end

**Elimination (for Consolidated Reports):**
- Group consolidated statement eliminates IC entries
- Ensures no double-counting

---

## SECTION 13: FISCAL PERIOD MANAGEMENT

### 13.1 Fiscal Period Setup

**Fiscal Calendar:**
- Define fiscal year (e.g., Jan 1 - Dec 31 or Apr 1 - Mar 31)
- Divide into periods:
  - Monthly: 12 periods
  - Quarterly: 4 periods
  - Bi-weekly: 26 periods
  - Custom: Any schedule

**Fiscal Period Definition:**
- Period Number
- Period Name (e.g., "Jan 2025")
- Start Date
- End Date
- Status: Open/Closed/Locked

### 13.2 Period Closing Process

**Weekly/Monthly Close Checklist:**

```
1. Bank Reconciliation
   ├─ Reconcile all bank accounts
   └─ Post reconciling entries
   
2. AR/AP Aging
   ├─ Generate AR aging
   ├─ Generate AP aging
   └─ Review aging exceptions
   
3. Accruals & Prepayments
   ├─ Accrue unpaid utilities
   ├─ Accrue unpaid services
   ├─ Record pre-paid insurance
   └─ Record pre-paid rent
   
4. Inventory Verification
   ├─ Physical count (if applicable)
   ├─ Compare to GL
   └─ Adjust if differences
   
5. Depreciation & Amortization
   ├─ Calculate monthly depreciation
   ├─ Post to GL
   └─ Update accumulated depreciation
   
6. Currency Revaluation
   ├─ Revalue AR/AP in foreign currency
   ├─ Calculate exchange gain/loss
   └─ Post adjusting JE
   
7. Tax Accruals
   ├─ Calculate estimated tax
   ├─ Accrue on GL
   └─ Create tax payable liability
   
8. Month-End Adjustments
   ├─ Review unsupported transactions
   ├─ Post required JEs
   └─ Validate period-end balances
   
9. Financial Statement Review
   ├─ Generate P&L
   ├─ Generate Balance Sheet
   ├─ Review for reasonableness
   └─ Identify exceptions
   
10. Management Reports
    ├─ Budget vs. Actual
    ├─ CC Expense Report
    └─ Key metrics
```

### 13.3 Period Status

**OPEN:**
- New transactions can be posted
- Existing transactions can be modified
- Reports are preliminary

**CLOSED:**
- Transactions cannot be posted (without reopening)
- Existing transactions cannot be modified (only reversals)
- Reports final

**LOCKED:**
- Period is closed to all users except admin
- No transactions can be posted
- No modifications allowed

**Period Lock Timeline:**
```
Day 1-5: Period OPEN
├─ All entries posted
├─ Period-end close performed
└─ JEs posted

Day 6-27: Period CLOSED (Auditor can review)
├─ No new transactions allowed
├─ No modifications allowed
├─ Read-only for all

Day 28+: Period LOCKED
├─ Locked by Admin
├─ Cannot be changed (only by Admin reversal)
└─ Final for all purposes
```

---

## SECTION 14: TAX MANAGEMENT

### 14.1 Tax Types

**Sales Tax / VAT:**
- Tax on sales revenue
- Collected from customer
- Remitted to government
- Tracked in GL as: Sales Tax Payable

**Input Tax / GST:**
- Tax on purchases
- Paid to suppliers
- Recoverable from government
- Tracked in GL as: Input Tax Receivable

**Income Tax:**
- Tax on company profit
- Calculated annually or quarterly
- Tracked in GL as: Income Tax Payable
- Withholding taxes (if applicable)

### 14.2 Tax Calculation & Accrual

**Sales Tax Example:**
```
Invoice Total: $1,000
Tax Rate: 10%
Tax Amount: $100
Total Due: $1,100

GL Entry:
├─ Dr. Accounts Receivable: 1,100
├─ Cr. Sales Revenue: 1,000
└─ Cr. Sales Tax Payable: 100
```

**Input Tax (Recoverable):**
```
Purchase Invoice: $500
Tax Rate: 10%
Tax Amount: $50
Total to Pay: $550

GL Entry:
├─ Dr. Inventory: 500
├─ Dr. Input Tax Receivable: 50
└─ Cr. Accounts Payable: 550

If Recoverable:
├─ Net GST: Recoverable - Payable
├─ If Positive: Claim from government
└─ If Negative: Pay to government
```

### 14.3 Tax Reporting

**Tax Return Preparation:**
- Sales Tax Summary (sales, tax collected)
- Input Tax Summary (purchases, tax paid)
- Net Tax Payable/Refundable
- Monthly/Quarterly Tax Return filing

**Tax Audit Trail:**
- All tax transactions traced
- Supporting documents linked
- GL codes tagged for tax reporting
- Automated tax reports

---

## SECTION 15: AUDIT TRAIL & COMPLIANCE

### 15.1 Complete Audit Trail

**Every Transaction Tracked:**
- Who created it
- When created (date & time)
- Who modified it (if any)
- When modified
- Who posted it
- When posted
- Who approved it
- When approved

**Immutability:**
- Posted entries cannot be edited
- Only create reversing entries
- Full history maintained
- Deletion not allowed

**Audit Log Report:**
```
Date | User | Action | Object | Old Value | New Value | Status
─────────────────────────────────────────────────────────────
11/04 | alice | Created | JE-2025-001 | — | Amount: 10,000 | Draft
11/04 | bob | Approved | JE-2025-001 | Draft | Posted | Posted
11/04 | system | Posted | GL Entry | — | [JE Posted] | Completed
```

### 15.2 Internal Controls

**Segregation of Duties (SoD):**
- Create ≠ Approve ≠ Post
- Example:
  - Finance Officer creates JE
  - Finance Manager approves JE
  - System posts JE (automatic)
- Different users for each step

**Authorization Limits:**
- Transaction value → Approver level
- Example:
  - < $5k: Department Manager
  - $5k-$50k: Finance Manager
  - > $50k: Finance Director

**Exception Reporting:**
- Large transactions flagged
- Unusual entries flagged
- Missing supporting docs flagged
- Manual reviews scheduled

### 15.3 Compliance Controls

**Regulatory Compliance:**
- GL codes mapped to tax reporting
- Audit trail for tax purposes
- Supporting documents stored (encrypted)
- GL export in standard formats (IIF, XML, CSV)

**Financial Reporting:**
- Standard financial statements
- Notes to accounts
- Compliance with accounting standards (GAAP/IFRS)
- External audit support

---

## SECTION 16: INTEGRATION POINTS

### 16.1 Procurement Module Integration

**GRN Posting:**
- Triggers GL entry: Dr. Inventory, Cr. AP
- Updates inventory balance
- Updates AP balance

**Invoice Matching:**
- 3-way match must complete before GL posting
- Variance requires approval before posting

**Payment:**
- Triggers GL entry: Dr. AP, Cr. Bank
- Clears AP balance

### 16.2 Budget Module Integration

**Budget Consumption:**
- Actual spending compared to budget
- Budget vs. Actual report
- Variance analysis and alerts
- CC budget tracking

### 16.3 Inventory Module Integration

**Stock Movements:**
- Purchase: Dr. Inventory, Cr. AP
- Sales: Dr. COGS, Cr. Inventory
- Transfers: Dr. One CC Inventory, Cr. Other CC Inventory

### 16.4 HR Module Integration

**Payroll:**
- Salary expense posting
- Salary payable tracking
- Payroll deductions (taxes, advances)

**Reimbursement:**
- Employee expense reimbursement
- Advance settlement
- Payroll deduction integration

---

## SECTION 17: KEY FEATURES SUMMARY

✅ **Chart of Accounts** - Hierarchical with multi-level support
✅ **General Ledger** - Double-entry with immutable audit trail
✅ **Accounts Receivable** - Customer invoicing, collections, aging
✅ **Accounts Payable** - Supplier payments, aging, 3-way matching
✅ **Bank Management** - Account setup, reconciliation, cash flow
✅ **Multi-Currency** - Exchange rates, revaluation, gain/loss tracking
✅ **Journal Entries** - Manual JE with approval workflow
✅ **Financial Reports** - P&L, Balance Sheet, Trial Balance, Cash Flow
✅ **Cost Center Accounting** - Allocation and reporting
✅ **Intercompany** - IC transactions and elimination
✅ **Fiscal Period Management** - Multi-period calendar, closing process
✅ **Tax Management** - Sales/input tax, accruals, reporting
✅ **Audit Trail** - Complete tracking, immutable records
✅ **Compliance Controls** - SoD, authorization limits, exception reports

---

## SECTION 18: IMPLEMENTATION ROADMAP

### Phase 1: Core Finance (Weeks 1-3)
- [ ] CoA setup and maintenance
- [ ] GL posting from Procurement (GRN/Invoice/Payment)
- [ ] Manual Journal Entry creation and approval
- [ ] Basic bank account setup
- [ ] GL report generation (Trial Balance)

### Phase 2: AR/AP (Weeks 4-5)
- [ ] AR module (customer invoicing, payment receipt)
- [ ] AP module (supplier payment processing)
- [ ] AR aging analysis
- [ ] AP aging analysis
- [ ] 3-way matching integration with Procurement

### Phase 3: Advanced Finance (Weeks 6-7)
- [ ] Bank reconciliation
- [ ] Multi-currency support
- [ ] Cost center accounting
- [ ] Month-end close checklist
- [ ] Tax management (accruals, reporting)

### Phase 4: Reporting & Integration (Week 8-9)
- [ ] Financial statement generation (P&L, BS, CF)
- [ ] Budget vs. Actual reporting
- [ ] Intercompany transactions
- [ ] Audit trail and compliance controls
- [ ] External audit support features
- [ ] Integration testing with all modules
- [ ] Performance optimization

### Phase 5: Go-Live (Week 10)
- [ ] UAT and user training
- [ ] Data migration (if applicable)
- [ ] Year-end close procedures
- [ ] Go-live support

---

## CONCLUSION

The Finance Module provides comprehensive financial management including:

✅ **Complete GL Management** - Multi-dimensional accounting with audit trail
✅ **Receivables & Payables** - AR/AP with aging and collections
✅ **Bank & Cash** - Account management and reconciliation
✅ **Multi-Currency** - Currency conversion and revaluation
✅ **Financial Reporting** - Standard statements and management reports
✅ **Cost Center Tracking** - Detailed expense allocation
✅ **Compliance & Audit** - Full audit trail, SoD enforcement
✅ **Tax Management** - Sales tax, input tax, accruals
✅ **Period Closing** - Structured month/quarter-end process
✅ **Integration Ready** - Connected with all other modules

This specification is **production-ready** and provides a solid foundation for comprehensive financial management!
