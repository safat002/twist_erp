# Twist ERP - Procurement Module: Complete Final Requirements
## Full Specification - No Code, All Details Included

---

## TABLE OF CONTENTS

1. Module Overview
2. Organizational Structure & Roles
3. Procurement Request (PR) - Complete Process
4. Purchase Order (PO) - Complete Process
5. Goods Receipt Note (GRN) - Stock Items
6. Service Received/Completion Statement (SRS) - Service Items
7. Invoice Processing - AI Document Reading
8. 3-Way Matching
9. Supplier Management
10. Budget Integration & Aggregate Logic
11. Approval Routing & Admin Configuration
12. Internal Requisition (IR) Integration
13. Amendments & Cancellations
14. Roles & Permissions
15. Workflows & Notifications
16. Analytics & Reports
17. Key Features Summary
18. Implementation Roadmap

---

## SECTION 1: MODULE OVERVIEW

### 1.1 Purpose

The Procurement Module manages the complete end-to-end procurement lifecycle from requirement identification through supplier payment and relationship management. It integrates with Budget, Finance, and Inventory modules to provide comprehensive procurement governance.

### 1.2 Scope & Coverage

**In Scope:**
- Procurement Request (PR) creation and approval
- Purchase Order (PO) creation, amendment, cancellation
- Goods Receipt (GRN) for stock items
- Service Receipt/Completion Statement (SRS) for service items
- Supplier Invoice processing with AI document reading
- 3-way matching (PO-GRN-Invoice)
- Supplier management and performance tracking
- Budget commitment and consumption tracking
- Multi-level approval routing (admin-configurable)
- Internal Requisition (IR) integration

**Out of Scope:**
- Payment processing (handled by Finance module)
- GL posting (handled by Finance module)
- Inventory physical receipt (warehouse operations)

### 1.3 Key Integrations

**Budget Module:**
- PR items from budget line items only (no alien items)
- Budget commitment tracking (Allocated → Committed → Consumed)
- Aggregate budget validation
- Budget remaining checks

**Finance Module:**
- GL posting on GRN/SRS and payment
- AP account management
- Invoice processing and payment authorization

**Inventory Module:**
- Stock receipt and management
- Reorder level tracking
- Inventory consumption
- Internal Requisition (IR) linking

---

## SECTION 2: ORGANIZATIONAL STRUCTURE & ROLES

### 2.1 Organizational Hierarchy

**Company Group Level:**
- Corporate Procurement Head (policies, vendor relationships)
- CFO (high-value approvals > $100k)

**Company Level:**
- Procurement Manager (PO approval, vendor selection)
- Finance Director (budget validation, invoice approval)
- Procurement Officer (PR/PO entry, GRN receipt)

**Department/Cost Center Level:**
- Cost Center Owner (PR approval for CC)
- Budget Owner (budget tracking and control)
- Department Head (departmental procurement authority)

**Warehouse Level:**
- Warehouse Officer (GRN receipt for stock items)
- Receiving Officer (quality inspection)

**External:**
- Registered Suppliers
- New Suppliers (onboarding)

### 2.2 Key Roles in Procurement

| Role | Responsibility | Authority Level |
|------|-----------------|-----------------|
| **Procurement Officer** | PR/PO entry, GRN creation, invoice upload | Operational |
| **Procurement Manager** | PO approval, supplier selection, vendor management | Mid-management |
| **Department Head** | PR approval for department, cost control | Department-level |
| **Finance Director** | High-value approvals, budget validation | Executive |
| **Budget Owner** | Budget tracking, commitment monitoring | Financial control |
| **Warehouse Officer** | Stock receipt inspection and GRN creation | Operational |
| **Cost Center Owner** | CC-specific budget management | Department-level |
| **CFO** | Very high-value approvals (> $100k) | Executive |

---

## SECTION 3: PROCUREMENT REQUEST (PR) - COMPLETE PROCESS

### 3.1 PR Overview

**What is a PR?**
- Formal request to procure goods or services
- Originated from department need
- Links to budget line items (mandatory from budget only)
- Specifies quantity, type, and required delivery date
- May be linked to Internal Requisition (IR)

**Key Features:**
- Cost Center selection: OPTIONAL (can be blank for corporate purchases)
- Budget line items: MANDATORY (dropdown from budget only)
- Item selection: Rigid governance (no alien items allowed)
- Service vs. Stock: Different workflows for each
- IR tagging: Optional link to Internal Requisition

### 3.2 PR Creation - Step by Step

**Step 1: Initiate PR**
- User clicks "Create Procurement Request"
- System shows blank PR form

**Step 2: Select Budget (Mandatory)**
- Dropdown: List of active, approved budgets
- System filters: Only approved budgets in active period
- Example budgets: "FY 2025 OpEx", "Q4 2025 CapEx", "Annual Maintenance"
- User selects budget

**Step 3: Select Cost Center (Optional)**
- Dropdown: List of active cost centers
- User may:
  - Select specific cost center (departmental purchase)
  - Leave blank (corporate/shared purchase)
- If selected: PR routed to CC manager, budget committed to CC
- If blank: PR routed to company procurement, budget committed to company

**Step 4: Add Line Items (From Budget Only)**
- Click "Add Line Item"
- Item Dropdown: Shows ONLY items from selected budget
- System displays:
  - Item Code
  - Item Name
  - Procurement Class (Stock/Service/CapEx)
  - Category
  - Budget Allocated
  - Already Committed
  - Already Consumed
  - Remaining Available
- Validation: Cannot add items NOT in budget

**Step 5: Enter Quantity & Price Per Line**
- Quantity: User enters quantity needed
- Unit Price: Auto-populated from budget
- Can override price (with justification)
- Line Total: Calculated automatically (Qty × Price)
- System warns if exceeds budget remaining

**Step 6: Service Item Details (If Service Item Selected)**
- Scope of Work: Detailed description
- Deliverables: What will be delivered
- Timeline: Start date - End date
- Milestones: Phased delivery dates (if applicable)
- Acceptance Criteria: How to verify completion
- Service Contact: Person receiving service

**Step 7: Link to Internal Requisition (Optional)**
- Checkbox: "Link to Internal Requisition"
- If checked: IR dropdown appears (shows active IRs)
- Select IR to link
- System auto-populates items from IR
- If not checked: Continue as external procurement

**Step 8: Delivery Details**
- Delivery Location: Address/warehouse
- Special Instructions: Packaging, handling, etc.
- Required By Date: When needed
- Priority: Normal/High/Urgent

**Step 9: Review Summary**
- Display: All items, quantities, prices, total PR amount
- Aggregate Budget calculation shows
- Display: Budget remaining after this PR
- Display: Approval routing (auto-calculated)

**Step 10: Submit PR**
- User clicks "Submit PR"
- System calculates: AGGREGATE BUDGET (sum of all line items)
- System determines: Approval routing based on aggregate
- Notifications sent to designated approvers
- PR Status: SUBMITTED

### 3.3 PR Aggregate Budget - Conditional Logic

**Conditional Budget Calculation:**

**If Cost Center IS Selected:**
- Aggregate = Sum of items for that CC only
- Approval routing = Based on CC budget remaining
- Budget commitment = Applied to CC budget
- Approver = CC manager or department head
- Check: PR amount ≤ CC budget remaining

**If Cost Center IS NOT Selected (Blank):**
- Aggregate = Sum of items (company-wide)
- Approval routing = Based on company total budget remaining
- Budget commitment = Applied to company-wide budget
- Approver = Company procurement manager or CFO
- Check: PR amount ≤ Company budget remaining

### 3.4 PR Status & Workflow

```
DRAFT
└─ User entering/editing PR
  └─ Can save draft without submitting

SUBMITTED
└─ PR submitted for approval
  └─ Awaiting designated approvers

APPROVED
└─ All approvers approved PR
  └─ Ready for PO creation

REJECTED
└─ PR rejected by approver
  └─ User can revise and resubmit

CONVERTED_TO_PO
└─ PO created from this PR
  └─ PR cycle complete
```

### 3.5 PR Fields Summary

**PR Header:**
- PR Number (auto-generated)
- PR Date (current date)
- Submitted By (user who created)
- Budget Name (mandatory dropdown)
- Cost Center (optional dropdown)
- IR Link (optional checkbox)
- Total PR Amount (auto-calculated aggregate)
- PR Status (auto-managed)

**PR Line Item (Per Line):**
- Budget Line Item Code (from budget dropdown, mandatory)
- Item Name (auto-populated from budget)
- Procurement Class (auto: Stock/Service/CapEx)
- Category (auto from budget)
- Quantity Required (user entry)
- Unit of Measure (auto from budget)
- Unit Price (auto-populated, can override)
- Line Total (auto-calculated)
- For Service Items: Scope, Deliverables, Timeline, Milestones, Acceptance Criteria
- Special Instructions (optional)
- Preferred Supplier (optional)

---

## SECTION 4: PURCHASE ORDER (PO) - COMPLETE PROCESS

### 4.1 PO Overview

**What is a PO?**
- Formal order placed with supplier
- Created from approved PR or standalone
- Legally binding commitment with supplier
- Contains all purchase terms and conditions
- Commitment recorded against budget

### 4.2 PO Creation Methods

**Method 1: From Approved PR**
- Navigate to approved PR
- Click "Create PO"
- System auto-populates:
  - All line items from PR
  - Quantities and prices
  - Delivery location
  - Special instructions
- Procurement officer modifies if needed
- Selects supplier from master

**Method 2: Direct PO Entry**
- Click "Create Purchase Order" (standalone)
- User enters all details manually
- Used for urgent purchases or repeat orders
- May or may not be linked to PR

### 4.3 PO Components

**PO Header:**
- PO Number (auto-generated: PO-YYYY-0001)
- PO Date (current date)
- Supplier (mandatory, from supplier master)
- PR Number (if created from PR)
- Delivery Address (warehouse/location)
- Billing Address (may differ from delivery)
- Delivery Date Expected
- Payment Terms (e.g., Net 30, Net 60, COD, Advance)

**PO Line Items:**
- Item Code/Description
- Quantity Ordered
- Unit Price (negotiated or from supplier quote)
- Unit of Measure
- Delivery Date (item-specific if different)
- Specification/Notes per line
- Line Total (Qty × Price)

**PO Terms & Conditions:**
- Payment Terms: Net 30, Net 60, Net 90, COD, Advance, Milestone-based
- Delivery Terms: FOB, CIF, DDP, etc.
- Quality Acceptance Criteria: Specifications items must meet
- Warranty/Return Period: How long supplier is responsible
- Late Delivery Penalty: If applicable
- Early Payment Discount: If applicable (e.g., 2% 10 Net 30)

**Financial Summary:**
- Line Totals (sum per line)
- Subtotal (sum of all lines)
- Tax: GST/VAT applicable
- Shipping: If included in PO
- Other Charges: If applicable
- Total PO Value (everything combined)

**Budget Impact:**
- Budget Line Item Referenced
- PO Amount (shown as commitment against budget)
- Budget Remaining After PO (auto-calculated)

### 4.4 PO Approval Routing (Admin-Configured)

**Approval Levels Based on Aggregate PO Amount:**

**System uses admin-configured thresholds** (not hardcoded):

Example Configuration (customizable):
```
Level 1: $0 - $5,000
├─ Approver: Procurement Manager or Department Head
├─ SLA: 24 hours
└─ Auto-escalate if delayed > 24 hours

Level 2: $5,001 - $25,000
├─ Approvers: Dept Head → Procurement Manager (Sequential)
├─ SLA: 48 hours each
└─ Auto-escalate if delayed > 48 hours each

Level 3: $25,001 - $100,000
├─ Approvers: Dept Head → Proc Manager → Finance Director (Sequential)
├─ SLA: 72 hours each
└─ Auto-escalate if delayed > 72 hours each

Level 4: > $100,000
├─ Approvers: Dept Head → Proc Manager → Finance Director → CFO (Sequential)
├─ SLA: 5 days each
├─ Requires: Business justification attached
└─ Can have: Condition-based special rules
```

**Important:** Thresholds and approvers are configured in admin backend, not hardcoded.

### 4.5 PO Approval Actions

**Approver Can:**

1. **APPROVE**
   - Accept PO as-is
   - Forward to next approver (if sequential)
   - Final approver: PO status = APPROVED

2. **MODIFY**
   - Change quantities on items
   - Change unit prices
   - Add/remove items (if allowed)
   - Change delivery dates
   - Track modifications for audit
   - Require justification for changes

3. **REJECT**
   - Send back to procurement with reason
   - Status: REJECTED
   - Procurement revises and resubmits

4. **REQUEST INFORMATION**
   - Ask for clarification
   - Status: PENDING (awaiting response)
   - Response timer started

### 4.6 PO Status & Workflow

```
DRAFT
└─ Procurement entering PO details
  └─ Can save draft

SUBMITTED
└─ PO submitted for approval
  └─ Awaiting designated approvers

APPROVED
└─ All required approvers approved
  └─ Ready to send to supplier

SENT_TO_SUPPLIER
└─ PO sent (email, portal, print)
  └─ Awaiting supplier acknowledgment

ACKNOWLEDGED
└─ Supplier confirmed receipt
  └─ Ready for delivery

GRN_RECEIVED
└─ Goods/Service received
  └─ Awaiting invoice

INVOICE_RECEIVED
└─ Invoice received from supplier
  └─ 3-way match triggered

CLOSED
└─ All processing complete, paid
  └─ PO cycle finished

CANCELLED
└─ PO cancelled before completion
  └─ Reason documented
```

---

## SECTION 5: GOODS RECEIPT NOTE (GRN) - STOCK ITEMS

### 5.1 GRN Overview

**What is GRN?**
- Formal record of stock items physically received
- Physical goods matched to PO
- Quality inspection completed
- Triggers inventory receipt
- Triggers GL posting (Debit Inventory, Credit AP)
- Consumption recorded against budget

### 5.2 GRN Creation

**Who:** Warehouse Officer, Receiving Officer

**When:** Stock items physically arrive from supplier

**Process:**

1. **Initiate GRN**
   - Select Purchase Order
   - System shows: Expected items, quantities, specifications
   - Warehouse staff verify physical goods match PO

2. **Receive Each Item**
   - For each line item:
     - Actual quantity received
     - Condition: OK, Damaged, Defective, Partial
     - Acceptance: Accept or Reject this line

3. **Quality Inspection**
   - Check item specifications match PO
   - Visual inspection (damage, defects)
   - Measurement/testing if required per policy
   - Photo evidence (optional)
   - Inspector sign-off
   - Pass/Fail determination

4. **Quantity Variance Analysis**
   - Compare: Ordered qty vs. Received qty
   - **Over-Receipt:** Received > Ordered
   - **Short Receipt:** Received < Ordered
   - **Complete:** Received = Ordered

5. **Variance Handling**

   **Over-Receipt:**
   - Reason documented
   - Options: Accept excess (supplier error), Return, Hold for decision
   - User must approve over-receipt

   **Short Receipt:**
   - Reason documented
   - Options: Accept short (balance cancelled), Wait for remainder, Reject
   - If accept short: Create separate receipt for balance when arrives

   **Quality Rejection:**
   - Mark items as Rejected
   - Create return/replacement order
   - Notify supplier of defect

6. **GRN Finalization**
   - All items inspected and accepted/rejected
   - Quantity variance documented and approved
   - Quality issues (if any) documented
   - GRN Status: ACCEPTED

7. **Impact After GRN**
   - Stock added to warehouse inventory
   - Budget status: Commitment → Consumption (moves from committed to consumed)
   - GL posting triggered: Debit Inventory, Credit AP

### 5.3 GRN Fields

**GRN Header:**
- GRN Number (auto-generated: GRN-YYYY-0001)
- GRN Date (date received)
- PO Number (linked PO)
- Supplier Name (from PO)
- Received By (warehouse officer)

**GRN Line Items (per item):**
- Item Code/Description (from PO)
- Quantity Ordered (from PO)
- Quantity Received (actual receipt)
- Quality Status: OK, Damaged, Defective, Partial
- Variance if any: Over/Short/Exact
- Special Notes: Any issues noted

**Quality & Inspection:**
- Inspector Name & Date
- Inspection Notes
- Photos (if needed)
- Pass/Fail Status

**Approval & Status:**
- Status: DRAFT, RECEIVED, ACCEPTED, REJECTED
- Accepted By (approver if required)
- Rejection Reason (if rejected)

---

## SECTION 6: SERVICE RECEIVED/COMPLETION STATEMENT (SRS) - SERVICE ITEMS

### 6.1 SRS Overview

**What is SRS?**
- Service Received/Completion Statement (also called: Service GRN)
- Created when SERVICE is completed/delivered
- NOT for physical goods (no warehouse receipt)
- End-user/Department signs off completion
- Triggered by service deliverables completion

**Key Difference from Stock GRN:**
- Stock GRN: Warehouse receives physical goods
- Service SRS: Department accepts service completion

### 6.2 SRS Creation

**Who:** End-user/Department staff receiving the service

**When:** Service is completed and delivered

**Process:**

1. **Initiate SRS**
   - Select Purchase Order (service PO)
   - System shows: Service scope, deliverables, timeline

2. **Deliverables Checklist**
   - For each deliverable in PO:
     - [ ] Deliverable 1: [Completed/Not Completed]
     - [ ] Deliverable 2: [Completed/Not Completed]
     - [ ] Deliverable 3: [Completed/Not Completed]
   - Mark each as completed or not

3. **Quality Assessment**
   - Service Quality: Excellent/Good/Acceptable/Poor
   - Supplier Responsiveness: Excellent/Good/Acceptable/Poor
   - Timeline Adherence: On-Time/Delayed/Early
   - Issues or Defects Found: [Text field]

4. **Acceptance Decision**
   - **FULLY ACCEPTED:** All deliverables completed, ready for payment
   - **ACCEPTED WITH MINOR ISSUES:** Deliverables OK but minor issues noted
   - **PARTIALLY ACCEPTED:** Some deliverables done, others pending
   - **REJECTED:** Service not acceptable, supplier must redo

5. **Sign-Off**
   - Signed By: Name & designation of end-user/department manager
   - Date: When service accepted
   - Comments: Any additional notes

6. **Approval (Optional)**
   - If policy requires: Manager approval of SRS
   - Manager verifies acceptance before payment

7. **SRS Finalization**
   - Status: ACCEPTED (ready for invoice matching)
   - Budget status: Commitment → Consumption
   - GL posting triggered: Debit Service Expense, Credit AP

### 6.3 SRS Examples by Service Type

**Example 1: Monthly Maintenance Service**
```
Service: Building Maintenance (Monthly)
Deliverables:
├─ [✓] Cleaning (3x/week completed)
├─ [✓] Repairs (4 reported issues fixed)
├─ [✓] Pest control (monthly spray completed)
└─ [✓] Report submitted

Quality: Good
Issues: None
Accepted By: Facilities Manager
Status: FULLY ACCEPTED → Ready for Payment ($4,000/month)
```

**Example 2: Consulting Service**
```
Service: IT System Audit
Deliverables:
├─ [✓] Initial Assessment Report (submitted)
├─ [✓] Security Audit Report (submitted)
├─ [✓] Recommendations Document (submitted)
├─ [✓] Executive Presentation (completed)
└─ [✓] 30-day Support (available)

Quality: Excellent
Supplier Responsiveness: Excellent
Issues: None
Accepted By: IT Manager
Status: FULLY ACCEPTED → Ready for Payment ($25,000)
```

**Example 3: Training Service**
```
Service: Employee Training Program (5 days)
Deliverables:
├─ [✓] Module 1 Training (completed)
├─ [✓] Module 2 Training (completed)
├─ [✓] Materials Provided (all attendees)
├─ [✓] Certificates Issued (25 attendees)
└─ [✓] Post-Training Support (30 days)

Quality: Good
Attendance: 92% (23 of 25 employees)
Feedback: 4.2/5.0 average
Accepted By: HR Manager
Status: FULLY ACCEPTED → Ready for Payment ($15,000)
```

### 6.4 SRS Fields

**SRS Header:**
- SRS Number (auto-generated: SRS-YYYY-0001)
- Statement Date (date service completed)
- PO Number (linked service PO)
- Supplier Name (from PO)
- Service Description (from PO scope)
- Received By: Name & Designation

**Deliverables Section:**
- Deliverable 1: [Description] - [✓] Completed or [ ] Not Completed
- Deliverable 2: [Description] - [✓] Completed or [ ] Not Completed
- (Repeats for all deliverables in PO)

**Quality Assessment:**
- Service Quality: [Excellent/Good/Acceptable/Poor]
- Supplier Responsiveness: [Excellent/Good/Acceptable/Poor]
- Timeline Adherence: [On-Time/Delayed/Early]
- Issues Found: [Text field]

**Acceptance:**
- Status: [Fully Accepted / Accepted with Issues / Partially Accepted / Rejected]
- Comments: [Text field]
- Signed By: [Name, Designation]
- Date: [Signature date]

**Approval (Optional):**
- Manager Approval: [Required/Not Required]
- Approved By: [Name]
- Approval Date: [Date]

---

## SECTION 7: SUPPLIER INVOICE PROCESSING - AI DOCUMENT READING

### 7.1 Invoice Upload & AI Extraction

**Traditional Process (Manual):**
- User types invoice data manually
- Time-consuming, error-prone
- Prone to data entry mistakes

**New Process (AI-Powered):**
- User uploads invoice PDF or image
- AI reads document automatically
- Extracts key fields
- User verifies and corrects
- Much faster and more accurate

### 7.2 Invoice Upload Process

**Step 1: Upload Invoice**
- User clicks "Upload Invoice"
- Drag & drop or file browser
- Supported formats: PDF, JPG, PNG, TIFF
- Max file size: 10 MB

**Step 2: AI Reads Document**
- System sends to AI document reading service
- AI analyzes invoice content
- Extracts fields and values
- Generates confidence score per field

**Step 3: AI Extraction Results**
- System displays extracted data
- Shows confidence level per field:
  - **>95% confidence:** Green checkmark (auto-verified)
  - **80-95% confidence:** Yellow warning (user verify)
  - **<80% confidence:** Red flag (user correct)

**Step 4: User Review & Correction**
- User reviews extracted data
- Accepts high-confidence fields
- Corrects low-confidence fields
- Can select from dropdown options for corrections
- Provides justifications for corrections if needed

**Step 5: Save Invoice**
- User clicks "Verify & Proceed"
- System saves invoice with extracted data
- Moves to 3-way match process

### 7.3 Invoice Fields AI Extracts

**From Invoice:**
- Supplier Name & Address
- Invoice Number (unique)
- Invoice Date
- PO Number (if referenced)
- Due Date
- Payment Terms (e.g., Net 30)

**Line Items:**
- Item Description
- Quantity
- Unit Price
- Unit of Measure
- Line Total
- Tax per line (if separate)

**Summary:**
- Subtotal
- Tax Amount & Rate
- Shipping/Freight (if any)
- Other Charges (if any)
- Total Invoice Amount

**Payment Details:**
- Payment Terms (Net 30, Net 60, COD, etc.)
- Early Payment Discount (if any)
- Bank Details (if provided)

### 7.4 AI Confidence Levels

**High Confidence (>95%):**
- Automatically verified
- Green checkmark
- User can override if needed

**Medium Confidence (80-95%):**
- Yellow warning icon
- User must verify
- Can select corrected value from dropdown
- Example: "Qty: 500 (was OCR'd as 5OO)"

**Low Confidence (<80%):**
- Red flag warning
- User must manually correct
- Cannot proceed until corrected
- Example: Item description unclear from scan

### 7.5 AI Benefits

✅ **Speed:** 5 minutes manual entry → 30 seconds AI extraction
✅ **Accuracy:** 99% extraction accuracy vs. 95% manual
✅ **Volume:** Can process 100s of invoices daily
✅ **OCR Correction:** Auto-detects OCR errors (5OO → 500)
✅ **Audit Trail:** Original document + extracted data kept
✅ **Document Storage:** Encrypted secure storage for compliance

---

## SECTION 8: 3-WAY MATCHING

### 8.1 Stock Items 3-Way Match

**Three Documents Must Match:**
1. **Purchase Order:** What we ordered
2. **Goods Receipt Note:** What we received
3. **Supplier Invoice:** What we're being charged

**Matching Process:**

```
PO: Item A, 100 units, $5 each = $500
GRN: Item A, 100 units received ✓
Invoice: Item A, 100 units, $5 each = $500 ✓

Match Status: ALL 3 MATCH ✓
Approval: Ready for Payment
```

### 8.2 Service Items 3-Way Match

**Three Documents Match (Different Criteria):**
1. **Purchase Order:** Service scope and deliverables
2. **Service SRS:** Deliverables completed confirmation
3. **Supplier Invoice:** Invoice amount matches PO

**Matching Process:**

```
PO: Maintenance service, monthly, $4,000
SRS: Service completed, all deliverables ✓
Invoice: INV-2025-001, Maintenance service, $4,000 ✓

Match Status: ALL 3 MATCH ✓
Approval: Ready for Payment
```

### 8.3 Automatic Matching Logic

**When Invoice is Received:**

1. **System searches for matching PO**
   - By: Supplier + Invoice Amount + Description
   - Finds: Associated PO

2. **System looks for GRN/SRS**
   - Looks for: GRN (stock) or SRS (service) for that PO
   - Validates: All items received/service completed

3. **System matches Invoice to PO & GRN/SRS**
   - Quantity match: Invoice qty = GRN qty = PO qty
   - Price match: Invoice price = PO price
   - Amount match: Invoice total = PO total (or within variance)

4. **System flags any variances**
   - Qty variance: Invoice qty ≠ GRN qty
   - Price variance: Invoice price ≠ PO price
   - Amount variance: Invoice total ≠ PO total

5. **Variance Handling**
   - **Automatic Match:** No variance → Ready for payment
   - **Variance Flag:** Variance exists → Hold for approval
   - **Require Approver:** Approver reviews and approves variance
   - **Variance Types:**
     - Over-invoice: Charged more than PO
     - Under-invoice: Charged less than PO
     - Extra items: Invoice has items not in PO
     - Missing items: Invoice missing items from PO

### 8.4 Match Result States

**MATCHED ✓**
- All three documents aligned
- Ready for payment approval

**VARIANCE - HOLD**
- Discrepancy exists
- Requires approver review
- Approver can: Approve variance, Request correction, Hold for investigation

**PARTIALLY MATCHED**
- Some items matched, some pending
- Awaiting remaining GRN/SRS or invoice
- Automatic match when all documents received

---

## SECTION 9: SUPPLIER MANAGEMENT

### 9.1 Supplier Master Data

**Supplier Information:**
- Supplier Code (unique)
- Supplier Name (legal name)
- Supplier Type: Vendor, Contractor, Distributor, Service Provider
- Tax ID / GST Number / PAN
- Contact Person (primary)
- Contact Email & Phone
- Billing Address
- Shipping Address (may differ)

**Supplier Status:**
- ACTIVE: Can receive POs
- INACTIVE: Historical records only
- BLACKLISTED: Cannot receive POs (poor performance)
- ON_PROBATION: Limited PO authorization

**Payment Terms:**
- Standard Payment Terms: Net 15, Net 30, Net 60, COD, Advance, Milestone
- Discount Terms: 2% 10 Net 30, etc. (early payment discount)
- Bank Details: Encrypted storage
- Tax Status: Registered, Unregistered, Exempt

### 9.2 Supplier Performance Tracking

**Metrics Tracked:**
- On-Time Delivery %: (On-time deliveries / Total deliveries) × 100
- Quality Rating: (Items accepted / Total items received) × 100
- Price Competitiveness: Comparison vs. market average
- Response Time: Average days to respond to inquiries
- Payment Reliability: Provides invoice timely, correct details
- Overall Supplier Score: 0-100 rating

**Performance Reports:**
- Monthly supplier scorecard
- Quality trend analysis (improving/declining)
- Delivery reliability tracking
- Cost trends (price increases/decreases)
- Performance recommendations

### 9.3 Supplier Selection for PO

**Methods:**

**Method 1: Single Supplier**
- Only one supplier available or preferred
- Direct order placement
- Used when: Sole supplier, preferred vendor, specific requirement

**Method 2: Competitive Bidding**
- Create Request for Quote (RFQ) sent to multiple suppliers
- Suppliers submit quotes
- Compare offerings (price, quality, delivery)
- Select best supplier

**Method 3: Approved Vendor List (AVL)**
- Department has pre-approved suppliers for item category
- Procurement selects from AVL
- Faster ordering, known quality

**Method 4: Automatic Selection (AI)**
- System suggests supplier based on:
  - Lowest price
  - Best quality rating
  - Fastest delivery
  - Best availability
- Procurement approves selection

---

## SECTION 10: BUDGET INTEGRATION & AGGREGATE LOGIC

### 10.1 Budget Line Items - PR Item Selection

**Rigid Item Governance:**
- PR items MUST come from budget line items
- Cannot add items NOT in budget
- Cannot add items from expired budgets
- Cannot add items with zero allocation

**Item Selection Process:**

1. User selects Budget (e.g., "FY 2025 OpEx")
2. System filters and shows ONLY budget line items in that budget
3. User selects item from dropdown
4. System displays:
   - Item name & code
   - Category
   - Budget allocated
   - Already committed (POs)
   - Already consumed (GRNs)
   - Remaining available
5. User enters quantity
6. System validates: Qty × Price ≤ Budget remaining
7. If exceeds: Warning shown, user can proceed with override

### 10.2 Budget Commitment Tracking

**Three States of Budget:**

1. **Allocated:** Budget amount originally assigned (from Budget Module)
2. **Committed:** PO created against budget (pending delivery)
3. **Consumed:** GRN/SRS received (actual spend against budget)

**Example Budget Line:**
```
Budget Line: "Office Supplies" - $5,000 allocated

State 1 (Initial):
├─ Allocated: $5,000
├─ Committed: $0
├─ Consumed: $0
└─ Remaining: $5,000

State 2 (PR Created & PO Sent):
├─ Allocated: $5,000
├─ Committed: $2,000 (PO sent to supplier)
├─ Consumed: $0
└─ Remaining: $3,000

State 3 (GRN Received):
├─ Allocated: $5,000
├─ Committed: $0 (moved to consumed)
├─ Consumed: $2,000 (goods received)
└─ Remaining: $3,000

State 4 (Another PR & PO):
├─ Allocated: $5,000
├─ Committed: $1,500 (new PO)
├─ Consumed: $2,000 (from before)
└─ Remaining: $1,500
```

### 10.3 Aggregate Budget Calculation

**Two Scenarios:**

**Scenario 1: Cost Center SELECTED**
- Aggregate = Sum of all items for that specific Cost Center
- Approval routing = Based on that CC's budget
- Budget commitment = Applied to CC budget only
- Approver = CC-level (Department Head)
- Check: PR amount ≤ CC budget remaining

**Example:**
```
Finance Department PR:
├─ Item 1: Printer Paper ($300)
├─ Item 2: Pens ($200)
├─ Item 3: Folders ($100)
├─ AGGREGATE: $600

Finance CC Budget Remaining: $1,500
Check: $600 ≤ $1,500 ✓
Approval: Finance Department Head (24 hrs)
Commitment: Applied to Finance CC budget
```

**Scenario 2: Cost Center NOT SELECTED (Blank)**
- Aggregate = Sum of all items (company-wide)
- Approval routing = Based on company's total budget
- Budget commitment = Applied to company-wide budget
- Approver = Company-level (Procurement Manager)
- Check: PR amount ≤ Company budget remaining

**Example:**
```
Company-Wide PR (No CC):
├─ Item 1: Printer Paper ($300)
├─ Item 2: Pens ($200)
├─ Item 3: Folders ($100)
├─ AGGREGATE: $600

Total Company Budget Remaining: $12,000
Check: $600 ≤ $12,000 ✓
Approval: Company Procurement Manager (24 hrs)
Commitment: Applied to company-wide budget
```

### 10.4 Budget Validation on PR Submission

**Before PR is APPROVED:**

1. **If Cost Center Selected:**
   - Get CC budget remaining
   - Check: PR aggregate ≤ CC remaining?
   - If YES: Allow PR
   - If NO: Show error "PR exceeds CC budget" or allow with override

2. **If Cost Center NOT Selected:**
   - Get company-wide budget remaining (all CCs combined)
   - Check: PR aggregate ≤ Company remaining?
   - If YES: Allow PR
   - If NO: Show error "PR exceeds company budget" or allow with override

---

## SECTION 11: APPROVAL ROUTING & ADMIN CONFIGURATION

### 11.1 Dynamic Approval Matrix (Admin-Configurable)

**Access:** Settings → Procurement → Approval Configuration

**Not Hardcoded:** All thresholds and approvers configured in backend by admin

**Admin Can Configure:**

**1. Approval Thresholds**
- Define amount ranges (customizable):
  - Level 1: $0 - $10,000 (or custom)
  - Level 2: $10,001 - $50,000 (or custom)
  - Level 3: $50,001 - $250,000 (or custom)
  - Level 4: > $250,000 (or custom)
- Can have any number of levels

**2. Approvers Per Level**
- Level 1: [Select role] - e.g., Department Manager
- Level 2: [Select roles & order] - e.g., Dept Manager → Procurement Manager
- Level 3: [Select roles & order] - e.g., Dept Mgr → Proc Mgr → Finance Director
- Level 4: [Select roles & order] - e.g., Dept Mgr → Proc Mgr → Finance Dir → CFO

**3. SLA Per Level**
- Level 1: [X] hours (e.g., 24 hours)
- Level 2: [X] hours per approver (e.g., 48 hours)
- Level 3: [X] hours per approver (e.g., 72 hours)
- Level 4: [X] days per approver (e.g., 5 days)

**4. Escalation Rules**
- If pending > SLA:
  - Day 1 overdue: Send reminder email
  - Day 3 overdue: Escalate to approver's manager
  - Day 5 overdue: Escalate to next level
  - Day 7 overdue: Auto-approve (optional toggle)

**5. Special Rules** (Optional)
- Service Items: Add special approval (e.g., IT approval for IT services)
- Supplier Changes: Flag for manager review
- Cross-Company: Additional intercompany approval
- CapEx Items: Additional finance approval
- New Suppliers: Additional vendor approval

### 11.2 Approval Routing Process

**When PR is SUBMITTED:**

1. System calculates AGGREGATE BUDGET
2. System determines scope (CC or Company-wide)
3. System looks up admin-configured approval matrix
4. System finds matching amount threshold
5. System retrieves assigned approvers for that tier
6. System sets SLA timer
7. System routes PR to designated approvers
8. System sends notifications to approvers

**Example:**

```
PR Submitted with aggregate $12,500:
├─ System looks up approval matrix
├─ Finds: $12,500 falls in Level 2 ($5,001-$25,000)
├─ Retrieves: Approvers = [Dept Head, Proc Manager]
├─ Sets: SLA = 48 hours each (sequential)
├─ Routes: To Dept Head first
└─ Notification: "PR-2025-001 ($12,500) awaiting your approval"

After Dept Head approves:
├─ Routes: To Procurement Manager
└─ Notification: "PR-2025-001 ($12,500) forwarded for your approval"

After Proc Manager approves:
├─ Status: PR APPROVED
└─ Ready for PO creation
```

---

## SECTION 12: INTERNAL REQUISITION (IR) INTEGRATION

### 12.1 What is Internal Requisition?

**IR = Request for goods transfer between departments**
- Request from one CC to another CC
- Or from warehouse to department
- For internal inventory items
- No external purchase needed
- Inventory movement only

### 12.2 PR Linking to IR

**Optional Feature:**

1. **User Creates IR** (in Inventory Module)
   - Request items from warehouse
   - Status: IR PENDING

2. **User Creates PR** (in Procurement Module)
   - Checkbox: "Link to Internal Requisition"
   - If checked: Select IR from dropdown
   - System auto-populates items from IR
   - If not checked: Standard external procurement

3. **PR Approval & Processing**
   - PR approved normally
   - If linked to IR:
     - Check warehouse stock available
     - If available: Fulfill IR from warehouse (no PO needed)
     - If not available: Create PO to replenish (then fulfill IR)

4. **Fulfillment**
   - If stock available: Transfer from warehouse to requesting CC
   - If not available: PO created, stock received, then transferred
   - IR Status: FULFILLED

### 12.3 Benefits of IR Integration

✅ **Avoid unnecessary external procurement**
✅ **Reduce waste (use existing inventory)**
✅ **Better inventory utilization**
✅ **Track internal transfers**
✅ **Reduce costs (no external purchase)**

---

## SECTION 13: PO AMENDMENTS & CANCELLATIONS

### 13.1 PO Amendment

**Reasons for Amendment:**
- Delivery date change (need later or earlier)
- Quantity increase (additional need)
- Quantity decrease (plan changed)
- Price negotiation (better deal secured)
- Item substitution (original unavailable)
- Specification change (requirements updated)

**Amendment Process:**

1. **Initiate Amendment**
   - Select PO to amend
   - Specify what's changing
   - Provide reason/justification

2. **Create Amendment**
   - System shows:
     - Original value
     - New value
     - Variance amount
   - Save amendment for review

3. **Approval**
   - If cost increases: Requires Procurement Manager approval
   - If cost same/decreases: Auto-approved
   - If large increase (>20%): Requires Finance Director approval

4. **Notify Supplier**
   - Email amendment to supplier
   - Get supplier acknowledgment
   - Update system when acknowledged

5. **Track Amendment**
   - Amendment history maintained
   - All changes documented for audit
   - Budget commitment updated if amount changed

### 13.2 PO Cancellation

**When Allowed:**
- PO created by mistake
- Requirement cancelled or postponed
- Budget constraint
- No delivery yet (or very early)

**When NOT Allowed:**
- Partial delivery already received
- GRN already created (create return PO instead)
- Service partially completed

**Cancellation Process:**

1. **Request Cancellation**
   - Procurement officer requests
   - Reason specified
   - Procurement Manager approval required

2. **Notify Supplier**
   - Email cancellation notification to supplier
   - Request acknowledgment
   - Handle cancellation costs (if any)

3. **Financial Impact**
   - If no GRN: Cancellation clean
   - If GRN exists: Cannot cancel (create return instead)
   - Budget commitment released
   - PO Status: CANCELLED

4. **Document**
   - Cancellation reason recorded
   - Approvals documented
   - Maintained for audit trail

---

## SECTION 14: ROLES & PERMISSIONS

### 14.1 Role Definitions & Permissions

| Role | Can Create | Can Approve | Can Receive | View Only |
|------|----------|-----------|-----------|-----------|
| **Procurement Officer** | PR, PO | ✗ | GRN, SRS | No |
| **Procurement Manager** | PR, PO | POs <$50k | ✗ | No |
| **Department Head** | PR | PR for own CC | ✗ | Own CC |
| **Finance Director** | ✗ | POs >$50k | ✗ | All |
| **Warehouse Officer** | ✗ | ✗ | GRN only | No |
| **End-User (Service)** | ✗ | ✗ | SRS only | No |
| **CFO** | ✗ | POs >$100k | ✗ | All |
| **Auditor** | ✗ | ✗ | ✗ | All (read-only) |

### 14.2 Permission Matrix

```
╔════════════════════════════════╦═══════════════════════════════════╗
║ Action / Screen                ║ Permission Level                  ║
╠════════════════════════════════╬═══════════════════════════════════╣
║ Create PR                       ║ Procurement Officer, Department   ║
║                                 ║ Head (for own CC)                 ║
║ Submit PR for Approval          ║ Procurement Officer, Department   ║
║                                 ║ Head                              ║
║ Approve PR ($0-$5k)             ║ Procurement Manager               ║
║ Approve PR ($5k-$25k)           ║ Dept Head + Procurement Manager   ║
║ Approve PR ($25k-$100k)         ║ Dept Head + Proc Mgr + Finance    ║
║ Approve PR (>$100k)             ║ + CFO (if configured)             ║
║                                 ║                                   ║
║ Create PO                       ║ Procurement Officer               ║
║ Approve PO (<$5k)               ║ Procurement Manager               ║
║ Approve PO ($5k-$25k)           ║ Proc Mgr + Department Head        ║
║ Approve PO (>$25k)              ║ + Finance Director (if configured)║
║ Amend PO                        ║ Procurement Manager (+ approval   ║
║                                 ║ if cost increases)                ║
║ Cancel PO                       ║ Procurement Manager               ║
║                                 ║                                   ║
║ Create GRN (Stock)              ║ Warehouse Officer                 ║
║ Create SRS (Service)            ║ End-User/Department Staff         ║
║                                 ║                                   ║
║ Upload Invoice                  ║ Procurement Officer, AP Officer   ║
║ Approve 3-Way Match             ║ Finance Officer (if variance)     ║
║                                 ║                                   ║
║ View Supplier Data              ║ All roles (read-only)             ║
║ Edit Supplier Data              ║ Procurement Manager only          ║
║                                 ║                                   ║
║ View Reports                    ║ All roles (own budget only)       ║
║ View All Reports                ║ Finance, Procurement Manager      ║
║                                 ║                                   ║
║ Configure Approval Matrix       ║ System Admin only                 ║
║ Configure Supplier Data         ║ Procurement Manager, Admin        ║
╚════════════════════════════════╩═══════════════════════════════════╝
```

---

## SECTION 15: WORKFLOWS & NOTIFICATIONS

### 15.1 Key Notifications

**PR Workflow Notifications:**

| Event | Recipients | Message |
|-------|-----------|---------|
| PR Created | Approver | "PR #{} from {} awaiting approval" |
| PR Approved | Procurement | "PR #{} approved, proceed with PO creation" |
| PR Rejected | Submitter | "PR #{} rejected. Reason: {}" |
| PR Overdue | Approver Manager | "PR #{} pending for {} days" |

**PO Workflow Notifications:**

| Event | Recipients | Message |
|-------|-----------|---------|
| PO Created | Approver | "PO #{} for {} requires approval" |
| PO Approved | Procurement | "PO #{} approved, ready to send to supplier" |
| PO Sent | Supplier | "PO #{} attached. Please acknowledge receipt" |
| Supplier Acknowledges | Procurement | "Supplier acknowledged PO #{}" |
| PO Amendment | Approver | "PO #{} amendment requires review" |

**GRN/SRS Notifications:**

| Event | Recipients | Message |
|-------|-----------|---------|
| GRN Created | Finance | "GRN #{} created, awaiting invoice for 3-way match" |
| Quality Issue | Warehouse Mgr | "GRN #{} has quality issues. Action needed" |
| Short Receipt | Procurement | "GRN #{} short by {} units. Notify supplier?" |
| SRS Created | Finance | "SRS #{} created, service accepted" |

**Invoice Notifications:**

| Event | Recipients | Message |
|-------|-----------|---------|
| Invoice Received | Finance | "Invoice {} received, 3-way match in progress" |
| 3-Way Match Complete | Finance | "Invoice {} ready for payment" |
| Match Variance | Finance Manager | "Invoice {} has variance. Approve?" |
| Payment Approved | Supplier | "Payment for invoice {} approved" |

---

## SECTION 16: ANALYTICS & REPORTS

### 16.1 Key Procurement KPIs

| KPI | Calculation | Target | Frequency |
|-----|-------------|--------|-----------|
| **PR to PO Cycle Time** | Days from PR approval to PO sent | < 3 days | Weekly |
| **PO to GRN Cycle** | Days from PO sent to GRN received | Per contract | Weekly |
| **GRN to Payment Cycle** | Days from GRN to payment | < 10 days | Weekly |
| **Supplier On-Time %** | (On-time / Total) × 100 | > 95% | Monthly |
| **Quality Acceptance Rate** | (Accepted / Total received) × 100 | > 98% | Monthly |
| **Budget Variance %** | (Actual - Budget) / Budget × 100 | < 10% | Monthly |
| **Price Variance %** | (Invoice - PO) / PO × 100 | < 5% | Monthly |
| **Order Fulfillment %** | (Complete orders / Total) × 100 | > 95% | Monthly |

### 16.2 Standard Reports

| Report | Contents | Users | Frequency |
|--------|----------|-------|-----------|
| **PR Status Report** | All PRs by status, age, amount | Procurement, Finance | Daily |
| **PO Status Report** | All POs by status, supplier, value | Procurement, Finance | Daily |
| **GRN Pending Report** | GRNs not received against POs | Warehouse, Procurement | Daily |
| **Invoice Exception Report** | Invoices with 3-way match issues | Finance, Procurement | Daily |
| **Supplier Performance** | On-time %, quality %, pricing | Procurement Mgr | Monthly |
| **Procurement Spend** | Total spend by supplier, category | Finance, Management | Monthly |
| **Budget Consumption** | Committed vs. consumed by line | Finance, Budget Owner | Monthly |
| **Variance Analysis** | All PO-GRN-Invoice variances | Procurement, Finance | Monthly |

---

## SECTION 17: KEY FEATURES SUMMARY

**✅ Procurement Request (PR)**
- Optional cost center selection
- Budget line items ONLY (no alien items)
- Optional IR linking
- Multi-level approval routing
- Admin-configurable approval amounts

**✅ Purchase Order (PO)**
- From PR or standalone
- Amendment management
- Cancellation handling
- Supplier acknowledgment tracking

**✅ Goods Receipt (GRN) - Stock Items**
- Physical receipt & inspection
- Quantity variance handling
- Quality acceptance criteria
- Budget consumption tracking

**✅ Service Receipt/Completion Statement (SRS) - Service Items**
- Deliverables checklist
- Quality assessment
- Department sign-off
- Budget consumption tracking

**✅ Supplier Invoice Processing**
- AI document reading (PDF/Image)
- Auto-extraction with confidence scores
- User verification & correction
- Automated 3-way matching

**✅ 3-Way Matching**
- Automatic matching (PO-GRN-Invoice)
- Variance detection & approval
- Stock items (qty-based)
- Service items (deliverables-based)

**✅ Budget Integration**
- Aggregate budget calculation
- Conditional logic (CC selected vs. not)
- Budget commitment tracking
- Budget remaining validation

**✅ Approval Routing**
- Admin-configurable thresholds
- Dynamic approver assignment
- SLA management & escalation
- Parallel or sequential approvals

**✅ Supplier Management**
- Master data maintenance
- Performance tracking
- Rating system (0-100)
- Status management

**✅ Internal Requisition Integration**
- Optional IR linking
- Avoid external procurement
- Track internal transfers
- Stock reuse optimization

**✅ Advanced Features**
- Multi-level approvals
- Budget governance
- Audit trail
- Compliance controls
- SoD enforcement

---

## SECTION 18: IMPLEMENTATION ROADMAP

### Phase 1: Core (Weeks 1-3)
- [ ] PR creation & approval workflow
- [ ] PO creation & approval workflow
- [ ] GRN creation (stock items)
- [ ] SRS creation (service items)
- [ ] Budget line item integration
- [ ] Aggregate budget calculation

### Phase 2: Advanced (Weeks 4-5)
- [ ] AI invoice document reading
- [ ] 3-way matching logic
- [ ] Approval matrix configuration (admin backend)
- [ ] Internal Requisition linking
- [ ] PO amendments

### Phase 3: Optimization (Weeks 6-7)
- [ ] Supplier management & performance tracking
- [ ] Advanced reporting & analytics
- [ ] Notifications & alerts
- [ ] KPI dashboards
- [ ] Budget variance reports

### Phase 4: Polish & Integration (Week 8)
- [ ] Testing & UAT
- [ ] Finance module integration (GL posting)
- [ ] Inventory module integration
- [ ] Performance optimization
- [ ] Go-live support

---

## CONCLUSION

The Procurement Module provides a comprehensive, flexible, and governance-focused procurement system featuring:

✅ **Flexible PR Creation** - Optional cost center, budget-aligned items, IR integration
✅ **Admin-Configurable Approvals** - Dynamic thresholds and routing (not hardcoded)
✅ **Service Item Support** - Separate workflow with deliverables-based acceptance
✅ **AI Invoice Processing** - Auto-extraction with confidence scoring
✅ **Aggregate Budget Logic** - Conditional on cost center selection
✅ **Complete 3-Way Matching** - Automatic with variance handling
✅ **Budget Governance** - Tight control on item selection and commitment tracking
✅ **Comprehensive Audit Trail** - All transactions immutable and tracked
✅ **Advanced Analytics** - KPIs, reports, supplier performance

This specification is **production-ready** and incorporates all your custom requirements!
