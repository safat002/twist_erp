# Twist ERP - Budget Module: Final Complete Requirements

## Organized & Detailed Overview (No Code)

---

## SECTION 1: ORGANIZATIONAL HIERARCHY & SETUP

### 1.1 Multi-Tier Organizational Structure

The system supports a hierarchical organizational structure:

**Tier 1: Company Group**

- Top-level holding company or conglomerate
- Can contain multiple companies

**Tier 2: Company**

- Individual business entity within a group
- Each company is independent with its own:
  - Chart of Accounts (GL)
  - Budgets
  - Fiscal periods
  - Tax configurations
  - Users & permissions

**Tier 3: Branch** (Optional)

- Location or division within a company
- Can be optional per company setting
- Each branch can have its own departments

**Tier 4: Department/Cost Center**

- Functional grouping (e.g., Finance, Operations, Sales, HR)
- This is where budget entry happens
- Each CC has an owner and deputy
- Each CC has assigned budget entry users

---

## SECTION 2: BUDGET MODULE - COMPLETE WORKFLOW

### 2.1 Budget Declaration Phase

**Who:** Budget Module Owner or Budget Module Sub-Owner

**What Happens:**

- Create a new declared budget with a unique name
- Define budget type (OpEx, CapEx, Revenue, Operational)
- Configure all time periods and settings in ONE place

**What Gets Configured:**

#### Custom Budget Duration (REQUIRED)

- Duration Type: Choose one:

  - **Monthly** - Budget for 1 calendar month
  - **Quarterly** - Budget for 3-month quarter
  - **Half-Yearly** - Budget for 6-month period
  - **Yearly** - Budget for full fiscal year
  - **Custom** - User-defined number of days

- Budget Start Date & End Date (actual effective dates)

#### Entry Period (REQUIRED)

- Start Date: When department users can START entering budget lines
- End Date: Deadline for department users to SUBMIT budget
- Entry Toggle: ON/OFF switch
  - ON = Users can add/edit lines
  - OFF = Users blocked from entering (pause entry)

#### Grace Period (REQUIRED - NEW)

- Default: 3 days (configurable)
- Automatic delay AFTER entry period ends before review period starts
- Example: Entry ends 01/31 → Grace period 02/01-02/03 → Review starts 02/03
- Purpose: Buffer time for system to process submissions

#### Review Period (CONDITIONAL)

- Start Date: When department/cost center owners review submitted budgets
- End Date: Deadline for review corrections
- Review Toggle: Auto-enabled when first item is sent back for review
- CRITICAL: After review period ends, NO CHANGES allowed except:
  - Lines marked as "HELD FOR REVIEW" by owner/moderator
  - Until the hold expires

#### Budget Impact Period (WHEN ACTIVATED)

- Start Date: When consumption tracking begins
- End Date: When consumption tracking stops
- Budget Impact Toggle: ON/OFF switch
  - ON = Real-time consumption tracking active
  - OFF = No consumption tracking (paused)
- Purpose: Controls when actual spending is matched against budget

#### Auto-Approval Setting (NEW - OPTIONAL)

- Toggle: Auto-Approve if Not Approved (ON/OFF)
- Only Budget Module Owner can control this in frontend
- If ON: Budget automatically approved on budget start date if still pending
- System role applied: Module Owner (System Auto-Approved)
- Example: Budget starts 03/01 but not approved yet → Auto-approved on 03/01

---

### 2.2 Budget Entry Phase (Department Users)

**Who:** Budget Entry Users (assigned per Cost Center)

**When:** During Entry Period (only if Entry = ON)

**What They Do:**

1. Select the declared budget from available list
2. Select their cost center (only assigned CCs visible)
3. Add budget line items (products/services to be procured/used)
4. For each line item, enter:
   - Item Code (product code or service code)
   - Item Name (description)
   - Category (classification)
   - Procurement Class (Stock Item / Service Item / CapEx Item)
   - Quantity Required
   - Unit Price (auto-populated from price policy OR manually entered)
   - Calculated Total Value (Qty × Price)
5. Submit budget for Cost Center Owner review

**Status During Entry:**

- Budget Status: DRAFT (in work)
- Can edit/delete lines freely
- Save draft without submitting

---

### 2.3 Cost Center Owner Review Phase

**Who:** Cost Center Owner or Cost Center Deputy

**When:** After entry period ends (during grace period or review period)

**What They Receive:**

- Notification: Budget submitted by entry user
- Shows: All line items, quantities, prices, total value
- Shows: Original vs. current values (if modified)

**What They Can Do:**

#### Option 1: APPROVE

- Accept all line items as-is
- Forward to Budget Moderator for technical review
- Status changes: SUBMITTED → CC_APPROVED

#### Option 2: MODIFY & APPROVE

- Change quantities on line items
- Change unit prices on line items
- Add new line items
- Add justification/notes for each change
- Forward to Budget Moderator
- Status changes: SUBMITTED → CC_APPROVED
- System tracks: Original value vs. modified value (Variance)

#### Option 3: REJECT

- Send budget back to entry users
- Provide rejection reason
- Entry users must re-create budget from scratch
- Status changes: SUBMITTED → DRAFT (back to start)

#### Option 4: SEND BACK FOR REVIEW

- Send budget back to entry users for corrections
- During Review Period, entry users can ONLY modify flagged items
- Entry users can view moderator remarks if any
- CC Owner can specify which lines need fixes
- Status changes: SUBMITTED → SENT_BACK_FOR_REVIEW
- in review period user can request to add new items to moderator but if moderator approves user can add new items

---

### 2.4 Budget Moderator Review Phase (NEW - CRITICAL ROLE)

**Who:** Budget Moderator (NEW role - no approval authority)

**When:** After CC Owner approves (parallel to other reviews possible)

**Scope:** Reviews ALL cost center budgets submitted in this budget cycle

**What Moderator CAN Do:**

#### Review All Budgets

- View budgets from all cost centers in company
- See all line items across all departments
- Compare spending patterns across departments

#### Add Item-Wise Remarks

- Add comments/remarks to individual line items
- Choose remark type:
  - Suggestion (improvement idea)
  - Concern (something looks off)
  - Clarification Needed (needs explanation)
  - Approval Note (looks good, approved)
  - Data Issue (data problem)

#### Use Remark Templates

- Apply pre-defined templates for common issues:
  - "Qty Exceeds Standard"
  - "Price Outdated"
  - "High Variance Detected"
  - "Budget Optimization Opportunity"
  - "Approved - Looks Good"
- Moderators can also create custom templates
- Templates are shared with all moderators
- Apply same template to multiple items at once (BATCH)

#### Batch Operations (FAST PROCESSING)

- Filter line items by:
  - Category (Consumables, Services, Equipment, etc.)
  - Procurement Class (Stock/Service/CapEx)
  - Variance Status (>10% variance highlighted)
  - High-Value Items (>$5k, >$10k, etc.)
- Actions on selected items:
  - Approve All Selected (mark as reviewed OK)
  - Send All Back (flag for CC Owner review)
  - Hold Selected for Further Review
  - Apply Template to All Selected
  - Mark Zero-Variance (no issues detected)

#### Send Back to CC Owner

- Send budget back with remarks
- Moderator specifies which lines need review
- During Review Period, CC Owner can modify those lines
- CC Owner provides responses to remarks
- Then resubmits back to moderator

#### Mark as Reviewed

- When done reviewing, mark budget as "Reviewed"
- Forward to Budget Module Owner for final approval
- Moderator cannot approve - only review

**What Moderator CANNOT Do:**

- ✗ Approve budgets (no approval authority)
- ✗ Reject budgets
- ✗ Modify line items directly
- ✗ Make final approval decisions

---

### 2.5 Final Approval Phase

**Who:** Budget Module Owner or Budget Module Sub-Owner

**When:** After moderator review complete

**What They Receive:**

- Complete budget with all CC submissions
- Moderator remarks and concerns
- Variance tracking for all modifications
- Summary of changes made during approval chain

**What They Can Do:**

#### Option 1: FINAL APPROVE

- Accept entire budget as reviewed
- Status changes: PENDING_FINAL_APPROVAL → APPROVED
- Budget ready for activation

#### Option 2: SEND BACK TO CC OWNER

- Send budget back for specific corrections
- CC Owner can modify during Review Period
- Then resubmit to moderator and back to final approval

#### Option 3: REJECT ENTIRE BUDGET

- Reject budget completely
- Goes back to entry phase
- Entry users must re-enter/modify entire budget

#### Option 4: ACTIVATE BUDGET

- Once approved, can activate for consumption tracking
- Status changes: APPROVED → ACTIVE
- Budget Impact Toggle: Turns ON automatically
- Consumption tracking begins immediately

---

## SECTION 3: REVIEW PERIOD & SENT-BACK ITEMS LOGIC

### 3.1 Review Period Functionality (NEW & CRITICAL)

**When Review Period Starts:**

- Configured by Budget Module Owner during budget declaration
- Typically starts after grace period ends
- Can be triggered manually or automatically

**During Review Period:**

- Entry users CAN edit lines that were "SENT BACK FOR REVIEW"
- Entry users CANNOT edit lines that were NOT sent back
- Entry users can see moderator remarks on items

**Sent-Back Item Editing Rules:**

- ONLY items marked as "sent back" are editable
- All other items are locked/read-only
- Users can view the reason why sent back
- Users provide responses/corrections to remarks

**What Moderator Can See:**

- Original proposed value vs. correction
- User's explanation for changes
- Comparison to what was requested

### 3.2 After Review Period Ends (CRITICAL NEW LOGIC)

**When Review Period End Date Passes:**

- NO further changes allowed
- EXCEPT: Lines marked as "HELD FOR REVIEW"

**Held Items (Hold Marks):**

- Budget Module Owner, Sub-Owner, or Moderator can mark a line as HELD
- Hold Reason: Explanation of why it's held
- Hold Until Date: Specific date when hold expires
- While held: Entry users CAN edit that line even after review period ends
- After hold date: Line becomes locked again

**Purpose of Holds:**

- Additional time needed for specific items
- Pending information to arrive
- Pending approval from stakeholder
- Complex decision requiring more time

**End of Review Complete Conditions:**

- Review period end date passed AND
- No held items remain with active holds OR
- All held items past their hold dates

Then: Review is FINALIZED, NO MORE CHANGES possible

---

## SECTION 4: VARIANCE TRACKING & AUDIT (NEW & COMPREHENSIVE)

### 4.1 What Gets Tracked (Complete Audit Trail)

**Original State (At Submission):**

- Original Quantity (as entry user submitted)
- Original Unit Price (as looked up/entered)
- Original Total Value (Qty × Price)

**Current State (After modifications):**

- Current Quantity (after all changes)
- Current Unit Price (after all changes)
- Current Total Value (Qty × Price)

**Variance Calculations:**

- Quantity Variance: Current Qty - Original Qty
- Price Variance: Current Price - Original Price
- Value Variance: Current Value - Original Value
- Variance Percent: (Variance / Original) × 100%

### 4.2 Who Modifies & Why

**Modifiers:**

- CC Owner (during PENDING_CC_APPROVAL)
- Moderator (can flag/modify in remarks)
- Module Owner (during final review)

**Each Modification Records:**

- WHO made the change (user name/role)
- WHEN the change was made (timestamp)
- WHAT changed (qty/price/both)
- WHY changed (justification/reason field)
- ORIGINAL value before change
- NEW value after change

### 4.3 Variance Report (GENERATED)

**Shows:**

- Each line item with:
  - Original submitted value
  - Current approved value
  - Total variance amount
  - Variance percent
  - Who modified it and when
  - Justification for change
- Summary totals:
  - Total variance across all lines
  - Number of lines modified
  - % of budget that changed

**Purpose:**

- Financial controls & compliance
- Understand approval chain changes
- Identify trends in modifications
- Audit trail for internal/external auditors

---

## SECTION 5: PERIOD CONTROLS & TOGGLES

### 5.1 Entry ON/OFF Toggle

**Where:** Budget declaration screen, set by Budget Module Owner

**Function:**

- ON = Entry Period Active: Users can create/edit lines
- OFF = Entry Period Paused: Users blocked from entering

**Use Cases:**

- Pause entry mid-period for review
- Resume entry if deadline extended
- Allow entry period to be opened/closed dynamically

**When Turned OFF:**

- No one can add new lines
- No one can edit existing draft lines
- System prevents all entry operations

### 5.2 Budget Impact ON/OFF Toggle

**Where:** Budget declaration screen, set by Budget Module Owner

**Function:**

- ON = Consumption Tracking Active: GL/PO/GRN amounts deducted from budget
- OFF = Consumption Tracking Paused: No consumption updates

**Use Cases:**

- Turn ON after budget approved (activation)
- Turn OFF temporarily if budget need adjustment
- Turn OFF if fiscal period changed

**When ON:**

- Real-time consumption tracking enabled
- Spending compared against budget
- Threshold alerts triggered if > 90% consumed
- Budget remaining value updated in real-time

**When OFF:**

- No consumption tracking
- Budget allocated amount frozen
- No alerts generated

### 5.3 Review Toggle (AUTO-MANAGED)

**When Activated:**

- Automatically enabled when first item sent back for review
- Moderator or CC Owner marks items for send-back

**When Disabled:**

- Review period end date passes
- No active held items remain

---

## SECTION 6: AUTO-APPROVAL MECHANISM (NEW)

### 6.1 Configuration (Budget Declaration)

**Checkbox:** Auto-Approve if Not Approved by Budget Start Date

**Setting:** ON/OFF (only Module Owner can toggle)

### 6.2 Trigger Condition

**System checks daily:**

- If today = budget_start_date
- AND auto_approve checkbox = ON
- AND budget status NOT in [Approved, Active]
- THEN: Auto-approve budget

### 6.3 What Gets Auto-Approved

- Declared budget marked as auto-approved
- ALL pending CC budgets auto-approved
- ALL pending final approvals auto-approved

### 6.4 Notification

- All stakeholders notified
- Alert: "Budget auto-approved as of [date]"
- Status changes to ACTIVE immediately
- Budget Impact tracking starts

### 6.5 Use Cases

- Prevent perpetual pending budgets
- Meet fiscal year start deadlines
- Automatic activation if approvals delayed
- Safety net to prevent process bottlenecks

---

## SECTION 7: BATCH OPERATIONS FOR MODERATORS

### 7.1 Selection Capabilities

**Filter Options:**

- By Procurement Class (Stock Items / Service Items / CapEx Items)
- By Category (Consumables / Equipment / Services, etc.)
- By Variance Status (Items with variance >10%)
- By Amount Range (>$5k, >$10k, etc.)
- Select All (entire budget)
- Select Variance Items (only items with changes)

### 7.2 Batch Actions

**Approve All Selected:**

- Mark multiple items as reviewed and approved
- One click instead of item-by-item

**Send All Back:**

- Send multiple items back to CC Owner for revision
- All selected items marked for review

**Hold for Review:**

- Mark multiple items as held
- Specify common hold until date
- Add hold reason once, applies to all

**Apply Template:**

- Select pre-defined or custom template
- Apply to all selected items with one click
- System auto-populates template text

**Mark Zero-Variance:**

- Mark items as no issues detected
- No remarks needed
- Speeds up review of straightforward items

### 7.3 Processing Speed Impact

**Without Batch:** Review 50-item budget = 50 clicks, 5 minutes
**With Batch:** Group by category, 5 batch actions, 1 minute

---

## SECTION 8: GRACE PERIOD LOGIC

### 8.1 Configuration

**Where:** Budget declaration screen

**Setting:** Configurable number of days (default 3 days)

### 8.2 Timing

**Entry Period Ends:** 01/31/2025
**Grace Period:** 02/01 - 02/03 (3 days, configurable)
**Review Period Starts:** 02/03/2025

### 8.3 Purpose

- System processing time after entry ends
- Time for data consolidation
- Buffer before heavy moderator review period

### 8.4 User Visibility

- Entry users: Cannot modify during grace period
- CC Owners: Can view submitted budgets
- Moderators: Waiting for formal review period

---

## SECTION 9: BUDGET CLONING (NEW)

### 9.1 What Can Be Cloned

**Declared Budgets:**

- Clone any previous declared budget by name
- Example: Clone "FY 2024 OpEx" to create "FY 2025 OpEx"

**Cost Center Budgets:**

- Auto-clone all CC budgets from source budget
- Each CC gets copy of prior budget

### 9.2 What Gets Copied

- All line items (products/services)
- Quantities per item
- Categories and classifications
- Structure and organization

### 9.3 What Can Be Adjusted

**Before Cloning:**

- Select source budget
- Enter new budget name
- Set new date ranges
- Apply blanket adjustments:
  - Price Adjustment: +5% increase all prices
  - Quantity Adjustment: +10% increase all quantities
  - System shows preview impact before confirming

### 9.4 Price Population

**Auto-populate Prices:**

- Use current price policy to look up prices
- Replace old prices with fresh prices
- Quantities can remain same or be adjusted

### 9.5 Use Cases

- Budgeting faster if structure similar to prior year
- Increment budgets by percentage (5% increase)
- Quickly create multiple similar budgets

---

## SECTION 10: REMARK TEMPLATES SYSTEM (NEW)

### 10.1 Pre-defined Templates (System-Provided)

**Template 1: Qty Exceeds Standard**

- "Quantity ({qty}) exceeds standard procurement level ({standard_qty}). Please justify."
- Type: Concern
- Use: When department orders more than typical

**Template 2: Price Outdated**

- "Unit price ({price}) appears outdated. Last PO price was {last_po_price}. Verify current."
- Type: Suggestion
- Use: When price seems old

**Template 3: High Variance Detected**

- "Item {item_name} shows {variance}% variance from standard. Please review."
- Type: Concern
- Use: When significant variance from baseline

**Template 4: Budget Optimization Opportunity**

- "Consider bulk ordering {item_name} to reduce per-unit cost. Potential savings: {savings}."
- Type: Suggestion
- Use: Cost reduction recommendations

**Template 5: Approved - Looks Good**

- "Approved. {item_name} budget is appropriate for {cc_name}."
- Type: Approval Note
- Use: Items that are approved

### 10.2 Custom Templates (Moderator-Created)

**Each Moderator Can Create:**

- Custom remarks for their frequent issues
- Named templates (e.g., "Check with Vendor", "IT Policy Compliance")
- Add placeholders for dynamic text
- Save as personal or shared template

### 10.3 Template Library & Sharing

**Shared Library:**

- All moderators access pre-defined templates
- All moderators can see shared custom templates
- Templates marked as private stay personal
- Usage tracking - shows how many times each used

### 10.4 Batch Template Application

**Process:**

1. Moderator selects multiple items
2. Chooses template from library
3. System populates placeholders with item data
4. Applies to all selected items at once

**Time Saving:** Instead of typing same remark 10 times, apply template once

---

## SECTION 11: REAL-TIME DASHBOARD & MONITORING

### 11.1 Budget Module Owner Dashboard

**Submission Progress:**

- Total CCs in company
- CCs Submitted: Green checkmark
- CCs Pending CC Owner Approval: Yellow indicator
- CCs Not Yet Started: Red with nudge link

**Visual Progress Bar:**

- Shows % of CCs completed (submitted + approved)
- Example: 8 of 12 CCs complete = 67%

### 11.2 Bottleneck Detection

**Stuck Budgets Highlighted:**

- If budget in same stage > 5 days: Flag as bottleneck
- Shows: Budget name, stage, days stuck
- Actions: Nudge button (send reminder email), Escalate button

**Example Bottlenecks:**

- Finance CC budget stuck in CC Owner review for 7 days
- Operations CC budget stuck in Moderator review for 5 days

### 11.3 Timeline Visualization

**Shows:** Entry Period → Grace Period → Review Period → Budget Start → Impact Period
**Color Coded:**

- Green = Active/In Progress
- Gray = Future/Not Started
- Blue = Timeline milestones
- Shows days remaining for each period

### 11.4 Key Metrics Displayed

- Avg Submission Time (from entry start to submission)
- Avg CC Approval Time (from submission to CC approval)
- Avg Moderator Review Time (from CC approval to moderation)
- High-Variance Count (budgets with >10% variance)
- Held Items Count (items marked for hold)
- Total Variance Impact ($amount)

### 11.5 Nudge Functionality

**Who:** CCs that haven't submitted yet (by countdown date)

**Message:** "Friendly reminder: Budget entry closes in 3 days. Please submit {CC_Name} budget"

**Actions:** Send Email, Escalate to CC Manager, View Budget Progress

---

## SECTION 12: AI-POWERED FEATURES

### 12.1 Price Prediction

**Data Used:**

- Historical PO data for item
- Last 12 months of procurement
- Price trend analysis

**What It Calculates:**

- Predicted price for next purchase
- Trend: Price going up or down
- Trend percentage: +5%, -10%, etc.
- Confidence level: How confident in prediction (0-100%)

**Suggestion:**

- "Predicted price for Item X: $55 (up 3% from average)"
- "Confidence: 85% (based on 15 prior purchases)"

**Use Case:**

- Moderator reviews price in budget
- System suggests "Price seems high, predicted should be $50"
- Moderator can flag for CC Owner review

### 12.2 Consumption Forecasting

**Data Used:**

- Historical consumption for item (from prior year)
- Current budget allocation
- Budget period duration

**What It Predicts:**

- Estimated consumption by end of budget period
- Will allocated budget be sufficient?
- Projected overspend or surplus

**Alert:** "Based on historical trends, this item will consume $12,000 but budget is $10,000. Budget may be exceeded."

**Recommendation:** Increase allocation or reduce quantity

### 12.3 Budget Alerts

**If Projected Consumption > Budget:**

- Alert: "WARNING: Item X projected to exceed budget"
- Recommendation: "Consider increasing budget allocation"

**If Budget Utilization > Threshold (90%):**

- Alert: "Budget 92% consumed, only 8% remaining"
- Action: Freeze new orders or increase budget

---

## SECTION 13: GAMIFICATION & BADGES

### 13.1 Badge System

**Early Bird Badge ⚡**

- Earned when: Submitted budget in first 30% of entry period
- Recognition: Efficient, proactive department

**Perfect Submission ✓**

- Earned when: Zero variance (no modifications by CC/Moderator)
- Recognition: Accurate budgeting

**Sweet Spot Badge 🎯**

- Earned when: Budget utilization 95-105% (optimal)
- Recognition: Accurate forecasting & execution

**Efficient Process ⚙️**

- Earned when: Budget approved within 2 days of submission
- Recognition: Smooth approval workflow

**Clear Review ✅**

- Earned when: No items held for further review
- Recognition: Quality budget, no issues

### 13.2 Leaderboard

**Ranking by Metric:** Budget Utilization Percent

**Display:**

- 🥇 Best: Operations Dept (102% - closest to 100%)
- 🥈 Second: Finance Dept (98%)
- 🥉 Third: HR Dept (96%)
- 4. Sales Dept (75%)

**Incentive:** CCs with closest-to-100% utilization earn "Sweet Spot" badge

### 13.3 Performance Recognition

**Monthly Recognition:**

- Top 3 CCs with best metrics
- Email recognition to CC managers
- Dashboard highlight
- Optional: Incentive/reward

---

## SECTION 14: KEY ROLES & PERMISSIONS SUMMARY

### 14.1 Budget Module Owner/Sub-Owner

**Can:**

- Declare budgets
- Set all periods, toggles, settings
- Enable/disable auto-approval (only this role)
- Final approval of budgets
- Activate budgets (turn on impact)
- Mark items as held for review
- Activate/deactivate all toggles

**Cannot:**

- Enter budget lines
- Approve at CC owner level
- Modify line items

### 14.2 Budget Moderator (NEW - NO APPROVAL POWER)

**Can:**

- View all CC budgets in company
- Add remarks to line items
- Batch apply remarks/templates
- Send budgets back to CC owner
- Mark items as held for review
- Create custom templates
- Filter and batch operations

**Cannot:**

- Approve any budget (no approval authority)
- Reject budgets
- Make final decisions
- Modify line item values directly

### 14.3 Cost Center Owner

**Can:**

- Review submitted budget
- Modify line quantities/prices
- Add justification for changes
- Approve and forward to moderator
- Reject and send back to entry user
- Send back for review
- Mark items as held for review

**Cannot:**

- Approve final budget
- Cannot access other CC's budgets

### 14.4 Budget Entry User

**Can:**

- Add line items during entry period
- Edit own submissions
- Submit budget for CC review
- Edit sent-back items (during review period)
- View moderator remarks

**Cannot:**

- Approve budget
- Access other CC's budgets
- Edit after review period (unless item held)

---

## SECTION 15: WORKFLOW STATES & TRANSITIONS

### 15.1 Declared Budget States

**DRAFT** → Create/Edit
↓
**ENTRY_OPEN** → Entry Period Active (Module Owner activation)
↓
**ENTRY_CLOSED_REVIEW_PENDING** → Entry period ended, awaiting review start
↓
**REVIEW_OPEN** → Review period active (for sent-back items)
↓
**PENDING_MODERATOR_REVIEW** → All CCs submitted, moderator reviewing
↓
**MODERATOR_REVIEWED** → Moderator completed, sent to final approval
↓
**PENDING_FINAL_APPROVAL** → Awaiting Module Owner final decision
↓
**APPROVED** → Approved, ready for activation
↓
**ACTIVE** → Budget activated (impact tracking ON)
↓
**CLOSED** → Budget period ended

**Special States:**

- **AUTO_APPROVED** → Auto-approved at budget start date (if configured)

### 15.2 Cost Center Budget States

Similar to declared budget, tracks per-CC progress

---

## SECTION 16: CRITICAL BUSINESS LOGIC

### 16.1 Entry Period Management

**Entry Period Active (Entry = ON):**

- Users CAN add new lines
- Users CAN edit existing lines
- Users CAN delete draft lines
- Users CAN submit for review

**Entry Period Ended (Entry = OFF):**

- Users CANNOT add new lines
- Users CANNOT edit ANY lines
- Exception: Review period can be ON for sent-back edits

### 16.2 Review Period Rules

**During Review Period:**

- ONLY sent-back items can be edited
- Other items are locked/read-only
- Users see moderator remarks
- Users provide responses

**After Review Period Ends:**

- NO changes allowed
- Exception: Items marked as HELD remain editable until hold expires
- Exception: New holds can be marked by owner/moderator

### 16.3 Variance Tracking Rules

**Every Modification Triggers:**

- Record original value
- Record new value
- Calculate variance (amount & %)
- Store modifier info (who, when, why)
- Flag for audit trail

**Variance Report Generated:**

- Shows all changes made during approval chain
- Justification for each change
- Total impact on budget

---

## SECTION 17: TIMELINE EXAMPLE

**FY 2025 Operating Expenses Budget - Monthly Cycle**

| Date        | Event                                       | Status             | Entry | Review | Impact |
| ----------- | ------------------------------------------- | ------------------ | ----- | ------ | ------ |
| 01/01       | Budget declared                             | ENTRY_OPEN         | ON    | OFF    | OFF    |
| 01/15       | Early submission nudge                      | ENTRY_OPEN         | ON    | OFF    | OFF    |
| 01/28       | Entry closes in 2 days                      | ENTRY_OPEN         | ON    | OFF    | OFF    |
| 01/31       | Entry period ends                           | ENTRY_CLOSED       | OFF   | OFF    | OFF    |
| 02/01-02/02 | Grace period                                | ENTRY_CLOSED       | OFF   | OFF    | OFF    |
| 02/03       | Review period opens                         | REVIEW_OPEN        | OFF   | ON     | OFF    |
| 02/10       | Moderator starts review                     | PENDING_MOD_REVIEW | OFF   | ON     | OFF    |
| 02/15       | Review period ends                          | MODERATOR_REVIEWED | OFF   | OFF    | OFF    |
| 02/20       | Final approval                              | APPROVED           | OFF   | OFF    | OFF    |
| 03/01       | Budget start date (Auto-approve if pending) | ACTIVE             | OFF   | OFF    | ON     |
| 03/01-03/31 | Budget active, consumption tracked          | ACTIVE             | OFF   | OFF    | ON     |
| 04/01       | Budget period ends                          | CLOSED             | OFF   | OFF    | OFF    |

---

## SECTION 18: KEY FEATURES SUMMARY TABLE

| Feature               | Module Owner | Moderator    | CC Owner   | Entry User |
| --------------------- | ------------ | ------------ | ---------- | ---------- |
| Declare Budget        | ✅           | ✗            | ✗          | ✗          |
| Control Entry ON/OFF  | ✅           | ✗            | ✗          | ✗          |
| Control Impact ON/OFF | ✅           | ✗            | ✗          | ✗          |
| Enter Budget Lines    | ✗            | ✗            | ✗          | ✅         |
| Review & Modify       | Limited      | ✅ (remarks) | ✅ (lines) | ✗          |
| Approve Budget        | ✅ (final)   | ✗ (NO)       | ✅ (CC)    | ✗          |
| Batch Operations      | Limited      | ✅           | Limited    | ✗          |
| Add Remarks           | ✅           | ✅           | Limited    | ✗          |
| Mark as Held          | ✅           | ✅           | ✅         | ✗          |
| View Variance Report  | ✅           | ✅           | ✅         | ✗          |
| View Dashboard        | ✅           | ✅           | Partial    | Partial    |

---

## SECTION 19: VALIDATION RULES

### Entry Validations

- Budget name required, unique per company
- Budget start date must be ≤ end date
- Entry period must be ≤ budget period
- Grace period must be positive number
- All dates must be valid

### Line Item Validations

- Item code required
- Quantity must be > 0
- Price must be > 0 or manually entered if lookup returns 0
- Line total calculated automatically
- Cannot have >10 decimal places on amounts

### Workflow Validations

- Cannot send back if budget status not in [SUBMITTED, PENDING_MOD]
- Cannot approve if variance not documented
- Cannot end review if held items active
- Cannot modify after review period (unless held)

---

## SECTION 20: REPORTING & ANALYTICS

### Budget Reports

- **Variance Report:** All changes made during approval chain
- **Budget vs Actual:** Compare allocated vs. consumed
- **Submission Progress:** % of CCs submitted
- **Bottleneck Report:** Budgets stuck > 5 days
- **Performance Dashboard:** Metrics and KPIs
- **Gamification Report:** Badges earned, leaderboard

### KPI Reports

- Submission Rate (% submitted)
- Approval Cycle Time (days)
- Zero-Variance Rate (perfect submissions)
- Best Utilization (closest to 100%)
- Early Submission Rate (submitted first 30%)

---

## CONCLUSION

This Budget Module is designed to provide:

- **Flexibility** - Custom durations, toggles, held items, grace periods
- **Control** - Auto-approval, entry management, impact tracking
- **Transparency** - Real-time dashboards, variance tracking, audit trails
- **Efficiency** - Batch operations, templates, gamification
- **Compliance** - Complete audit trail, role-based access, SoD
- **Intelligence** - AI predictions, forecasting, analytics

All requirements are organized, documented, and ready for development.
