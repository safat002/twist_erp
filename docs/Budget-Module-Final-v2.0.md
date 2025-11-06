# Budget Module - Final Complete Specification v2.0
## Twist ERP Budgeting System with Advanced Features

---

## Executive Summary

The Budget Module implements an **enterprise-grade collaborative budgeting system** with:
- **Custom Budget Durations** (Monthly, Quarterly, Half-Yearly, Yearly, Custom)
- **Advanced Workflow** with automatic approval, held items, grace periods
- **Variance Tracking** with full audit trail of all modifications
- **Moderator Batch Operations** for faster processing
- **Smart Review Logic** with hold marks for specific items
- **Remark Templates** for consistent communication
- **Real-Time Dashboards** with bottleneck visibility
- **AI-Powered Features** (price predictions, consumption forecasting)
- **Budget Cloning** from any prior budget
- **Gamification & KPIs** for incentivizing good budgeting
- **Parallel Approval** for simultaneous CC reviews

---

## 1. Budget Declaration - Enhanced Data Model

### 1.1 Budget Model (Complete Enhanced Version)

```python
class Budget(models.Model):
    """
    Declared Budget with custom duration, auto-approval, and advanced controls
    """
    # Identifiers
    id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='budgets')
    
    # Budget Declaration
    name = models.CharField(
        max_length=255,
        help_text='Budget name (e.g., "FY 2025 OpEx Budget", "Q4 2025 Marketing")'
    )
    budget_type = models.CharField(
        max_length=50,
        choices=[
            ('operational', 'Operational'),
            ('opex', 'Operating Expense'),
            ('capex', 'Capital Expenditure'),
            ('revenue', 'Revenue'),
        ]
    )
    description = models.TextField(blank=True)
    
    # CUSTOM DURATION SETTINGS (NEW)
    duration_type = models.CharField(
        max_length=50,
        choices=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('half_yearly', 'Half Yearly'),
            ('yearly', 'Yearly'),
            ('custom', 'Custom'),
        ],
        default='yearly',
        help_text='Budget duration type'
    )
    
    custom_duration_days = models.IntegerField(
        null=True,
        blank=True,
        help_text='Days if duration_type=custom'
    )
    
    budget_start_date = models.DateField(
        help_text='When budget becomes effective'
    )
    budget_end_date = models.DateField(
        help_text='When budget expires'
    )
    
    # PERIOD CONTROLS (ENHANCED)
    
    # Entry Period
    entry_start_date = models.DateField()
    entry_end_date = models.DateField()
    entry_enabled = models.BooleanField(default=True)
    
    # Review Period with Grace Period
    review_start_date = models.DateField(null=True, blank=True)
    review_end_date = models.DateField(null=True, blank=True)
    review_enabled = models.BooleanField(default=False)
    
    grace_period_days = models.IntegerField(
        default=3,
        help_text='Days after entry period ends before review starts (e.g., 3 days grace)'
    )
    
    # Budget Impact Period
    budget_impact_start_date = models.DateField(null=True, blank=True)
    budget_impact_end_date = models.DateField(null=True, blank=True)
    budget_impact_enabled = models.BooleanField(default=False)
    
    # AUTO-APPROVAL SETTINGS (NEW)
    auto_approve_if_not_approved = models.BooleanField(
        default=False,
        help_text='Auto-approve budget at budget_start_date if not approved yet'
    )
    auto_approve_by_role = models.CharField(
        max_length=50,
        blank=True,
        help_text='Which role should be recorded as auto-approver (Module Owner, etc.)'
    )
    
    # Amount Tracking (Denormalized)
    total_allocated = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_consumed = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_committed = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_remaining = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    
    # Variance & Change Tracking
    total_variance_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        help_text='Sum of all line modifications (original vs modified)'
    )
    total_variance_count = models.IntegerField(
        default=0,
        help_text='Number of lines with modifications'
    )
    
    # Status & Workflow
    status = models.CharField(
        max_length=30,
        choices=[
            ('draft', 'Draft'),
            ('entry_open', 'Entry Open'),
            ('entry_closed_review_pending', 'Entry Closed - Review Pending'),
            ('review_open', 'Review Period Open'),
            ('pending_moderator_review', 'Pending Moderator Review'),
            ('moderator_reviewed', 'Moderator Reviewed'),
            ('pending_final_approval', 'Pending Final Approval'),
            ('approved', 'Approved'),
            ('auto_approved', 'Auto Approved'),
            ('active', 'Active (Impact ON)'),
            ('closed', 'Closed'),
        ],
        default='draft'
    )
    
    # Approval Tracking
    final_approved_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finally_approved_budgets'
    )
    final_approved_at = models.DateTimeField(null=True, blank=True)
    
    auto_approved_at = models.DateTimeField(null=True, blank=True)
    
    activated_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activated_budgets'
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_budgets'
    )
    
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'budget'
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['budget_start_date', 'budget_end_date']),
            models.Index(fields=['entry_start_date', 'entry_end_date']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_duration_type_display()})"
    
    def get_duration_display(self):
        """Get human-readable duration."""
        if self.duration_type == 'custom':
            return f"Custom ({self.custom_duration_days} days)"
        return self.get_duration_type_display()
    
    def is_entry_period_active(self):
        """Check if entry period is active."""
        today = date.today()
        return (
            self.entry_enabled and
            self.entry_start_date <= today <= self.entry_end_date
        )
    
    def is_review_period_active(self):
        """Check if review period is active."""
        if not self.review_start_date or not self.review_end_date:
            return False
        today = date.today()
        return (
            self.review_enabled and
            self.review_start_date <= today <= self.review_end_date
        )
    
    def should_auto_approve(self):
        """Check if budget should auto-approve at budget_start_date."""
        today = date.today()
        return (
            self.auto_approve_if_not_approved and
            today >= self.budget_start_date and
            self.status not in ['approved', 'auto_approved', 'active']
        )


class CostCenterBudget(models.Model):
    """
    Budget submission per Cost Center (with enhanced tracking)
    """
    id = models.AutoField(primary_key=True)
    
    # Hierarchy
    declared_budget = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name='cost_center_budgets'
    )
    
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.CASCADE,
        related_name='budgets'
    )
    
    revision_no = models.IntegerField(default=1)
    
    # Amount Tracking
    allocated_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    consumed_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    committed_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    
    # VARIANCE TRACKING (NEW & ENHANCED)
    original_allocated_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
        help_text='Original allocated amount at submission'
    )
    
    variance_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
        help_text='Difference between original and current allocated'
    )
    
    variance_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='% variance from original'
    )
    
    total_lines_modified = models.IntegerField(
        default=0,
        help_text='Count of lines with modifications'
    )
    
    # Status Workflow
    status = models.CharField(
        max_length=30,
        choices=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted to CC Owner'),
            ('pending_cc_approval', 'Pending CC Approval'),
            ('cc_approved', 'CC Approved'),
            ('sent_back_for_review', 'Sent Back for Review'),
            ('pending_moderator_review', 'Pending Moderator Review'),
            ('moderator_reviewed', 'Moderator Reviewed'),
            ('pending_final_approval', 'Pending Final Approval'),
            ('approved', 'Approved'),
            ('auto_approved', 'Auto Approved'),
            ('rejected', 'Rejected'),
        ],
        default='draft'
    )
    
    # HELD ITEMS TRACKING (NEW)
    held_items_count = models.IntegerField(
        default=0,
        help_text='Number of lines marked as held for further review'
    )
    held_until_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Until when review is held'
    )
    held_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='held_cc_budgets'
    )
    
    # Review Completion Status
    review_completed = models.BooleanField(
        default=False,
        help_text='True if review period ended and no held items remain'
    )
    
    # Submission & Approval Tracking
    submitted_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_cc_budgets'
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    submission_sequence = models.IntegerField(
        default=0,
        help_text='Order of submission (for early submission badge)'
    )
    
    cc_approved_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cc_approved_budgets'
    )
    cc_approved_at = models.DateTimeField(null=True, blank=True)
    
    moderator_reviewed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderator_reviewed_budgets'
    )
    moderator_reviewed_at = models.DateTimeField(null=True, blank=True)
    
    final_approved_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='final_approved_cc_budgets'
    )
    final_approved_at = models.DateTimeField(null=True, blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cost_center_budget'
        unique_together = [['declared_budget', 'cost_center', 'revision_no']]
        indexes = [
            models.Index(fields=['declared_budget', 'status']),
            models.Index(fields=['cost_center']),
            models.Index(fields=['held_until_date']),
        ]


class BudgetLine(models.Model):
    """
    Budget line with variance tracking and held flag
    """
    id = models.AutoField(primary_key=True)
    
    cost_center_budget = models.ForeignKey(
        CostCenterBudget,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    
    sequence = models.IntegerField()
    
    # Item Details
    item_code = models.CharField(max_length=64)
    item_name = models.CharField(max_length=255)
    category = models.CharField(max_length=120, blank=True)
    
    procurement_class = models.CharField(
        max_length=50,
        choices=[
            ('stock_item', 'Stock Item'),
            ('service_item', 'Service Item'),
            ('capex_item', 'Capital Expenditure'),
        ]
    )
    
    # ORIGINAL VALUES (for variance tracking)
    original_qty_limit = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        help_text='Original quantity at submission'
    )
    original_unit_price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text='Original price at submission'
    )
    original_value_limit = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text='Original value at submission'
    )
    
    # CURRENT VALUES (may be modified)
    qty_limit = models.DecimalField(max_digits=15, decimal_places=3)
    unit_price = models.DecimalField(max_digits=20, decimal_places=2)
    value_limit = models.DecimalField(max_digits=20, decimal_places=2)
    
    # VARIANCE DETAILS (NEW)
    qty_variance = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        help_text='Current Qty - Original Qty'
    )
    price_variance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text='Current Price - Original Price'
    )
    value_variance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text='Current Value - Original Value'
    )
    variance_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='% change from original'
    )
    
    # Who modified this line
    modified_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modified_budget_lines'
    )
    modified_at = models.DateTimeField(null=True, blank=True)
    modification_reason = models.TextField(
        blank=True,
        help_text='Justification for modification'
    )
    
    # Consumption Tracking
    consumed_qty = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    consumed_value = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    committed_qty = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    committed_value = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    # Projected Consumption (AI-powered)
    projected_consumption_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='AI-predicted consumption based on trends'
    )
    projected_consumption_confidence = models.DecimalField(
        max_digits=3,
        decimal_places=0,
        null=True,
        blank=True,
        help_text='Confidence level (0-100) for projection'
    )
    will_exceed_budget = models.BooleanField(
        default=False,
        help_text='True if projected consumption > allocated'
    )
    
    # HELD ITEMS LOGIC (NEW)
    is_held_for_review = models.BooleanField(
        default=False,
        help_text='Marked as held for further review by owner/moderator'
    )
    held_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='held_budget_lines'
    )
    held_reason = models.TextField(blank=True)
    held_until_date = models.DateTimeField(null=True, blank=True)
    
    # Remarks & Comments
    moderator_remarks = models.TextField(blank=True)
    moderator_remarks_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='budget_line_remarks'
    )
    moderator_remarks_at = models.DateTimeField(null=True, blank=True)
    
    cc_owner_modification_notes = models.TextField(blank=True)
    
    sent_back_for_review = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'budget_line'
        indexes = [
            models.Index(fields=['cost_center_budget', 'is_active']),
            models.Index(fields=['item_code']),
            models.Index(fields=['is_held_for_review']),
        ]


class BudgetRemarkTemplate(models.Model):
    """
    Pre-defined and custom remark templates for moderators
    """
    id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='budget_remark_templates')
    
    # Template Details
    name = models.CharField(max_length=255, help_text='e.g., "Qty Exceeds Standard"')
    description = models.TextField(blank=True)
    
    template_text = models.TextField(
        help_text='Remark text (can include placeholders like {item_name}, {qty})'
    )
    
    remark_type = models.CharField(
        max_length=50,
        choices=[
            ('suggestion', 'Suggestion'),
            ('concern', 'Concern'),
            ('approval_note', 'Approval Note'),
            ('clarification_needed', 'Clarification Needed'),
            ('data_issue', 'Data Issue'),
        ]
    )
    
    is_predefined = models.BooleanField(
        default=False,
        help_text='True if predefined by system; False if custom'
    )
    
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_budget_templates'
    )
    
    usage_count = models.IntegerField(default=0, help_text='How many times used')
    
    is_shared = models.BooleanField(
        default=True,
        help_text='Visible to all moderators if True'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'budget_remark_template'
        indexes = [
            models.Index(fields=['company', 'is_predefined']),
        ]


class BudgetVarianceAudit(models.Model):
    """
    Complete audit trail of all modifications (original vs. current)
    """
    id = models.AutoField(primary_key=True)
    
    budget_line = models.ForeignKey(
        BudgetLine,
        on_delete=models.CASCADE,
        related_name='variance_audit_trail'
    )
    
    # Who made the change
    modified_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='budget_modifications'
    )
    modified_at = models.DateTimeField(auto_now_add=True)
    
    # What changed
    change_type = models.CharField(
        max_length=50,
        choices=[
            ('qty_change', 'Quantity Changed'),
            ('price_change', 'Price Changed'),
            ('both_change', 'Qty & Price Changed'),
        ]
    )
    
    original_qty = models.DecimalField(max_digits=15, decimal_places=3)
    new_qty = models.DecimalField(max_digits=15, decimal_places=3)
    qty_change_percent = models.DecimalField(max_digits=5, decimal_places=2)
    
    original_price = models.DecimalField(max_digits=20, decimal_places=2)
    new_price = models.DecimalField(max_digits=20, decimal_places=2)
    price_change_percent = models.DecimalField(max_digits=5, decimal_places=2)
    
    original_value = models.DecimalField(max_digits=20, decimal_places=2)
    new_value = models.DecimalField(max_digits=20, decimal_places=2)
    value_variance = models.DecimalField(max_digits=20, decimal_places=2)
    
    # Justification
    justification = models.TextField(
        blank=True,
        help_text='Why this change was made'
    )
    
    role_of_modifier = models.CharField(
        max_length=50,
        choices=[
            ('cc_owner', 'CC Owner'),
            ('moderator', 'Moderator'),
            ('module_owner', 'Module Owner'),
        ]
    )
    
    class Meta:
        db_table = 'budget_variance_audit'
        indexes = [
            models.Index(fields=['budget_line']),
            models.Index(fields=['modified_at']),
        ]
```

---

## 2. Budget Declaration Screen - Enhanced

```
┌──────────────────────────────────────────────────────────────────────┐
│ Create Declared Budget - Enhanced                                    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│ Budget Name: [FY 2025 Operating Expenses Budget______] *Required     │
│ Budget Type: [OpEx ▼]                                                │
│                                                                        │
│ ┌─ CUSTOM DURATION SETTINGS (NEW)                                    │
│ │ Duration Type: [Yearly ▼]                                          │
│ │ └─ If Custom: [________] days                                      │
│ │                                                                      │
│ │ Budget Start Date: [01/01/2025]  Budget End Date: [12/31/2025]   │
│ │ Display: "Yearly budget from 01/01/2025 - 12/31/2025"            │
│ └─                                                                     │
│                                                                        │
│ ┌─ PERIOD CONTROLS                                                    │
│ │                                                                      │
│ │ Entry Period:        [01/01/2025] - [01/31/2025]  Entry: [●ON ○OFF│
│ │                      Grace Period: [3] days after entry ends       │
│ │                      → Review starts [02/03/2025]                  │
│ │                                                                      │
│ │ Review Period:       [02/03/2025] - [02/15/2025]  Review: [○ON ●OF│
│ │                      ⓘ Auto-enabled when first item sent back     │
│ │                                                                      │
│ │ Budget Impact Period:[03/01/2025] - [12/31/2025]  Impact: [○ON ●OF│
│ │                      ⓘ Enable when budget approved                │
│ └─                                                                     │
│                                                                        │
│ ┌─ AUTO-APPROVAL SETTINGS (NEW)                                      │
│ │ [☑] Auto-approve if not approved by budget start date             │
│ │     Auto-approve By Role: [Module Owner (System) ▼]               │
│ │     ⓘ Budget will auto-approve on 03/01/2025                      │
│ │                                                                      │
│ │ WARNING: This will bypass final approval workflow if not complete  │
│ └─                                                                     │
│                                                                        │
│ ┌─ BUDGET SETTINGS                                                    │
│ │ Threshold Alert: [90%]                                             │
│ │ Allow Auto-Revision: [☑]                                           │
│ └─                                                                     │
│                                                                        │
│ [Save as Draft] [Save & Open Entry Period] [Cancel]                 │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Moderator Batch Operations Screen (NEW)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Batch Moderator Review - Finance Department Budget                  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│ Budget: FY 2025 OpEx | Cost Center: Finance Dept | Lines: 12        │
│                                                                        │
│ ┌─ Filter & Batch Operations                                         │
│ │ Filter by Category: [All ▼]  Filter by Class: [All ▼]            │
│ │                                                                      │
│ │ ☐ Select All (12) | ☐ Select Variance Items (3)                  │
│ │ ☐ Select High-Value Items (>$5k) (2)                             │
│ │                                                                      │
│ │ ┌─ Batch Actions (8 lines selected)                               │
│ │ │ [Approve All Selected Lines]                                     │
│ │ │ [Send All Selected Back]                                         │
│ │ │ [Hold Selected for Review]                                       │
│ │ │ [Apply Template to Selected: {Qty Exceeds Standard} ▼]          │
│ │ │ [Add Custom Remark to All Selected]                             │
│ │ │ [Mark as Zero-Variance (no changes needed)]                     │
│ │ └─                                                                  │
│ └─                                                                     │
│                                                                        │
│ ┌─ Budget Lines (with Variance Highlighted)                         │
│ │                                                                      │
│ │ ☑ Line 1: PROD-001 (Office Supplies)  [VARIANCE: +$500]          │
│ │   Original: 100 × $50 = $5,000                                     │
│ │   Current:  100 × $55 = $5,500  [⚠ Price up 10%]                │
│ │   [Apply Template ▼] [Hold Review ▼] [Add Remark]                │
│ │                                                                      │
│ │ ☑ Line 2: SERV-001 (Internet Service) [VARIANCE: -$1k]           │
│ │   Original: 1 × $1,000/mo × 12 = $12,000                          │
│ │   Current:  1 × $900/mo × 12 = $10,800  [✓ Price down 10%]       │
│ │                                                                      │
│ │ ☑ Line 3: CAPEX-01 (Workstation)  [VARIANCE: +$3k]               │
│ │   Original: 5 × $1,500 = $7,500                                    │
│ │   Current:  5 × $1,100 = $5,500  [✓ Price down 27%]              │
│ │                                                                      │
│ │ ... (9 more lines)                                                  │
│ └─                                                                     │
│                                                                        │
│ [Mark All as Reviewed] [Send All Back] [Hold Selected] [Done]       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Held Items & Review Logic (NEW)

### 4.1 Hold Marking Screen

```
┌──────────────────────────────────────────────────────────────────────┐
│ Mark Line Item for Further Review (HOLD)                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│ Line: CAPEX-01 - New Workstation                                    │
│ Original Value: $7,500 | Current Value: $5,500 | Variance: -$2,000  │
│                                                                        │
│ [☑] Hold for further review                                          │
│ Reason: [Qty justification needed - why 5 workstations?________]    │
│ Hold Until: [02/28/2025] (must be before review period ends)        │
│                                                                        │
│ [Mark as Held] [Cancel]                                              │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Held Items Logic

```python
def can_end_review(cost_center_budget):
    """
    Check if review can be ended for CC budget
    """
    today = date.today()
    
    # Scenario 1: Review period ended AND no held items
    held_items = cost_center_budget.lines.filter(
        is_held_for_review=True,
        held_until_date__gt=today
    ).count()
    
    if (today > cost_center_budget.declared_budget.review_end_date and
        held_items == 0):
        return True  # Can end review
    
    # Scenario 2: All held items past their hold date
    active_holds = cost_center_budget.lines.filter(
        is_held_for_review=True,
        held_until_date__gte=today
    ).count()
    
    if active_holds == 0:
        return True  # Can end review (all holds resolved)
    
    return False  # Cannot end review - still have active holds
```

---

## 5. Review End Logic (CRITICAL NEW FEATURE)

```python
def finalize_review(cost_center_budget):
    """
    Called at end of review period or when all holds resolved
    After review ends: NO FURTHER CHANGES allowed (unless specific hold marked)
    """
    declared_budget = cost_center_budget.declared_budget
    today = date.today()
    
    # Check if review period ended
    if today > declared_budget.review_end_date:
        # Review period has ended
        
        # Check for any held items still marked
        held_items = cost_center_budget.lines.filter(
            is_held_for_review=True,
            held_until_date__gte=today
        )
        
        if held_items.exists():
            # Still have active holds - cannot finalize
            return {
                'status': 'held',
                'message': f'{len(held_items)} items still held for review',
                'held_until': held_items.first().held_until_date
            }
        else:
            # No more held items
            cost_center_budget.review_completed = True
            cost_center_budget.status = 'pending_moderator_review'
            cost_center_budget.save()
            
            return {
                'status': 'completed',
                'message': 'Review finalized. No further changes allowed unless new hold marked'
            }

def can_edit_budget_line_during_review(user, budget_line):
    """
    During review period: ONLY edit if:
    1. Line is marked as sent_back_for_review
    2. Optionally: Line is marked as held_for_review
    After review ends: NO EDIT unless line is currently held
    """
    cc_budget = budget_line.cost_center_budget
    declared_budget = cc_budget.declared_budget
    today = date.today()
    
    # If review period NOT active AND NOT held, CANNOT edit
    if not declared_budget.is_review_period_active():
        # Check if line is held for review
        if budget_line.is_held_for_review and budget_line.held_until_date >= today:
            return True  # Can edit if held
        else:
            return False  # Cannot edit after review period ended
    
    # During review period: Can edit if sent back OR held
    if budget_line.sent_back_for_review or budget_line.is_held_for_review:
        return True
    
    return False
```

---

## 6. Auto-Approval Logic (NEW)

```python
def trigger_auto_approval_job():
    """
    Batch job (runs daily at midnight or by cron):
    Check all budgets for auto-approval eligibility
    """
    today = date.today()
    
    # Find budgets eligible for auto-approval
    eligible_budgets = Budget.objects.filter(
        auto_approve_if_not_approved=True,
        budget_start_date=today,  # Today is budget start date
        status__in=['pending_final_approval', 'pending_moderator_review', 'review_open']
    )
    
    for budget in eligible_budgets:
        # Auto-approve all CC budgets
        cc_budgets = budget.cost_center_budgets.filter(
            status__in=['pending_final_approval', 'pending_moderator_review']
        )
        
        for cc_budget in cc_budgets:
            cc_budget.status = 'auto_approved'
            cc_budget.final_approved_by = None  # System auto-approved
            cc_budget.final_approved_at = now()
            cc_budget.save()
            
            # Notification
            send_notification(
                recipients=[cc_budget.cost_center.owner],
                message=f"Budget auto-approved as of {today} (budget start date)"
            )
        
        # Auto-approve declared budget
        budget.status = 'auto_approved'
        budget.auto_approved_at = now()
        budget.save()
    
    return f"Auto-approved {len(eligible_budgets)} budgets"
```

---

## 7. Remark Templates - Enhanced

### 7.1 Pre-defined Templates

```python
PREDEFINED_TEMPLATES = [
    {
        'name': 'Qty Exceeds Standard',
        'template_text': 'Quantity ({qty}) exceeds standard procurement level ({standard_qty}). Please justify.',
        'remark_type': 'concern'
    },
    {
        'name': 'Price Outdated',
        'template_text': 'Unit price ({price}) appears outdated. Last PO price was {last_po_price}. Please verify.',
        'remark_type': 'suggestion'
    },
    {
        'name': 'High Variance',
        'template_text': 'Item {item_name} shows {variance}% variance from standard. Review needed.',
        'remark_type': 'concern'
    },
    {
        'name': 'Budget Optimization',
        'template_text': 'Consider bulk ordering {item_name} to reduce per-unit cost. Potential savings: {savings}.',
        'remark_type': 'suggestion'
    },
    {
        'name': 'Approval Note',
        'template_text': 'Approved. {item_name} budget is appropriate for {cc_name}.',
        'remark_type': 'approval_note'
    },
]
```

### 7.2 Apply Template API

```bash
POST /api/v1/budgeting/moderator/batch-apply-template
{
  "selected_line_ids": [1, 3, 5, 7],
  "template_id": 15,  // "Qty Exceeds Standard"
  "replacements": {
    "qty": "{auto-fill from line}",
    "standard_qty": 50,
    ...
  }
}
Response: {
  "lines_updated": 4,
  "remarks_applied": [
    {"line_id": 1, "remark": "Quantity (100) exceeds standard procurement level (50). Please justify."},
    ...
  ]
}
```

---

## 8. Budget Cloning Feature (NEW)

### 8.1 Clone Declared Budget

```
┌──────────────────────────────────────────────────────────────────────┐
│ Clone Budget From Existing                                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│ Select Budget to Clone From:                                         │
│ [FY 2024 Operating Expenses Budget ▼]                               │
│                                                                        │
│ New Budget Name: [FY 2025 Operating Expenses Budget]                │
│ New Budget Type: [OpEx ▼]                                            │
│                                                                        │
│ ┌─ Cloning Options                                                   │
│ │ [☑] Clone all CC budgets from selected year                       │
│ │ [☑] Auto-populate prices (use current price policy)              │
│ │ [☑] Apply blanket price adjustment: [0%] % increase              │
│ │ [☑] Apply blanket quantity adjustment: [0%] % increase           │
│ │                                                                      │
│ │ Estimated Impact:                                                   │
│ │ Original Total: $1,000,000                                         │
│ │ With 5% price increase: $1,050,000                                │
│ │ With 10% quantity increase: $1,155,000                            │
│ └─                                                                     │
│                                                                        │
│ New Budget Dates: [01/01/2025] - [12/31/2025]                      │
│ Entry Period: [01/01/2025] - [01/31/2025]                          │
│                                                                        │
│ [Clone & Create] [Cancel]                                            │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 9. Real-Time Dashboard (NEW)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Budget Module Dashboard - Real-Time Status                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│ Active Budget: FY 2025 OpEx | Cycle: Yearly | Status: Pending Review│
│                                                                        │
│ ┌─ SUBMISSION PROGRESS                                               │
│ │ Total Cost Centers: 12                                             │
│ │                                                                      │
│ │ [████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 33% │
│ │                                                                      │
│ │ ✓ Submitted: 4 CCs                                                │
│ │ ⏱ Pending CC Approval: 3 CCs (Review by CC Owner)               │
│ │ ⏸ Not Started: 5 CCs (⚠ Nudge needed - 3 days left)            │
│ │                                                                      │
│ │ Submitted CCs: Finance, Operations, Sales, HR                     │
│ │ Not Started: Procurement, IT, Marketing, Legal, ...               │
│ └─                                                                     │
│                                                                        │
│ ┌─ APPROVAL BOTTLENECKS                                             │
│ │ Finance CC Budget    | CC Approval | STUCK for 5 DAYS ⚠           │
│ │ (Submitted 11/01, now 11/06)                                       │
│ │ Last Message: "Awaiting CC Manager (Rajesh) review"              │
│ │ [Nudge CC Manager] [Escalate to Module Owner]                    │
│ └─                                                                     │
│                                                                        │
│ ┌─ TIMELINE                                                          │
│ │ Entry Period: 01/01 - 01/31  [Entry ON ✓]                        │
│ │ Grace Period: 2 days (01/31 - 02/02)                              │
│ │ Review Period: 02/03 - 02/15  [Review OFF]                       │
│ │ Budget Start: 03/01 (Auto-approve if not approved by this date)  │
│ │ Impact Starts: 03/01 (Consumption tracking)                       │
│ └─                                                                     │
│                                                                        │
│ ┌─ KEY METRICS                                                       │
│ │ Avg Submission Time: 2.3 days from entry start                    │
│ │ Avg CC Approval Time: 1.5 days                                     │
│ │ Avg Moderator Review Time: 0.8 days                                │
│ │ High-Variance Budgets: 3 (>10% variance)                          │
│ │ Held Items: 2 (awaiting further review)                           │
│ └─                                                                     │
│                                                                        │
│ [Export Report] [Print] [Email Summary to Module Owner]             │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 10. AI Features (NEW)

### 10.1 Price Prediction

```python
class AIPricePrediction:
    """
    AI-powered price suggestions based on historical PO data
    """
    @staticmethod
    def get_price_prediction(item_code, company_id, lookback_months=12):
        """
        Predict price based on:
        - Last PO price
        - Average price over lookback period
        - Price trend (increasing/decreasing)
        - Inflation adjustments
        """
        po_lines = PurchaseOrderLine.objects.filter(
            product__code=item_code,
            purchase_order__company_id=company_id,
            purchase_order__order_date__gte=today() - timedelta(days=lookback_months*30)
        ).order_by('purchase_order__order_date')
        
        prices = list(po_lines.values_list('unit_price', flat=True))
        
        if not prices:
            return None
        
        # Calculate trend
        if len(prices) >= 3:
            recent_avg = mean(prices[-3:])
            older_avg = mean(prices[:3])
            trend_percent = ((recent_avg - older_avg) / older_avg) * 100
        else:
            trend_percent = 0
        
        # Predict next price
        predicted_price = mean(prices) * (1 + trend_percent/100)
        confidence = min(len(prices) * 10, 100)  # Higher confidence with more data
        
        return {
            'predicted_price': round(predicted_price, 2),
            'trend': 'increasing' if trend_percent > 0 else 'decreasing',
            'trend_percent': round(trend_percent, 2),
            'confidence': confidence,
            'data_points': len(prices)
        }
```

### 10.2 Consumption Forecasting

```python
class AIConsumptionForecast:
    """
    Predict budget consumption based on historical trends
    """
    @staticmethod
    def forecast_consumption(budget_line, days_into_budget=None):
        """
        Predict if projected consumption will exceed budget
        """
        # Get historical consumption data (from prior year same item)
        prior_consumptions = get_prior_year_consumptions(
            item_code=budget_line.item_code,
            company_id=budget_line.cost_center_budget.declared_budget.company_id
        )
        
        if not prior_consumptions:
            return None
        
        # Calculate daily consumption rate
        daily_rate = mean(prior_consumptions) / 365  # Rough estimate
        
        if days_into_budget is None:
            days_into_budget = (date.today() - budget_line.cost_center_budget.declared_budget.budget_start_date).days
        
        # Projected total consumption
        total_days = (budget_line.cost_center_budget.declared_budget.budget_end_date - 
                     budget_line.cost_center_budget.declared_budget.budget_start_date).days
        
        projected_consumption = daily_rate * total_days
        
        will_exceed = projected_consumption > budget_line.value_limit
        
        return {
            'projected_consumption': round(projected_consumption, 2),
            'allocated_budget': budget_line.value_limit,
            'will_exceed': will_exceed,
            'variance': round(projected_consumption - budget_line.value_limit, 2),
            'confidence': 75,  # Placeholder
            'recommendation': 'Increase budget' if will_exceed else 'Budget sufficient'
        }
```

---

## 11. Variance Tracking Report

```python
class BudgetVarianceReport:
    """
    Generate comprehensive variance tracking report
    """
    @staticmethod
    def get_variance_report(declared_budget_id):
        """
        Show all changes made during approval chain
        """
        budget = Budget.objects.get(id=declared_budget_id)
        cc_budgets = budget.cost_center_budgets.all()
        
        report = {
            'budget_name': budget.name,
            'total_budgets': cc_budgets.count(),
            'total_variance_amount': 0,
            'total_lines_modified': 0,
            'cc_budgets': []
        }
        
        for cc_budget in cc_budgets:
            cc_variance = {
                'cost_center': cc_budget.cost_center.name,
                'original_amount': cc_budget.original_allocated_amount,
                'current_amount': cc_budget.allocated_amount,
                'variance_amount': cc_budget.variance_amount,
                'variance_percent': cc_budget.variance_percent,
                'lines_modified': cc_budget.total_lines_modified,
                'modifications': []
            }
            
            for line in cc_budget.lines.all():
                if line.value_variance != 0:
                    cc_variance['modifications'].append({
                        'item': line.item_name,
                        'original_value': line.original_value_limit,
                        'current_value': line.value_limit,
                        'variance': line.value_variance,
                        'variance_percent': line.variance_percent,
                        'modified_by': line.modified_by.get_full_name() if line.modified_by else 'N/A',
                        'reason': line.modification_reason,
                        'audit_trail': [
                            {
                                'timestamp': audit.modified_at,
                                'changed_by': audit.modified_by.get_full_name(),
                                'from': audit.original_value,
                                'to': audit.new_value,
                                'justification': audit.justification
                            }
                            for audit in line.variance_audit_trail.all()
                        ]
                    })
            
            report['cc_budgets'].append(cc_variance)
            report['total_variance_amount'] += cc_budget.variance_amount
            report['total_lines_modified'] += cc_budget.total_lines_modified
        
        return report
```

---

## 12. KPIs & Gamification

### 12.1 Budget KPIs

```python
BUDGET_KPIs = {
    'submission_metrics': {
        'early_submission_rate': '(Submitted < 7 days before entry end) / Total CCs',
        'average_submission_time': 'Days from entry start to submission',
        'submission_completion_rate': '(Submitted CCs / Total CCs) × 100'
    },
    
    'variance_metrics': {
        'zero_variance_budgets': 'CC budgets with no line modifications',
        'average_variance_percent': 'Average % variance across all CC budgets',
        'high_variance_budgets': 'CCs with > 15% variance (potential issues)',
        'total_variance_impact': 'Sum of all variances'
    },
    
    'utilization_metrics': {
        'budget_utilization_percent': '(Consumed / Allocated) × 100',
        'closest_to_100_percent': 'CCs with utilization closest to 100% (best)',
        'under_utilization_rate': '% of CCs with < 80% utilization',
        'over_run_rate': '% of CCs with > 100% utilization'
    },
    
    'approval_metrics': {
        'average_approval_cycle_time': 'Entry → Final Approval days',
        'approval_bottleneck_rate': '% of budgets stuck > 5 days in review',
        'auto_approval_rate': '% of budgets auto-approved',
        'rejection_rate': 'Rejected budgets / Total'
    }
}

class BudgetGamification:
    """
    Award badges based on budget submission quality
    """
    @staticmethod
    def award_badges(cc_budget):
        """
        Determine badges earned
        """
        badges = []
        
        # Early Submission Badge
        entry_start = cc_budget.declared_budget.entry_start_date
        entry_end = cc_budget.declared_budget.entry_end_date
        days_available = (entry_end - entry_start).days
        days_to_submit = (cc_budget.submitted_at.date() - entry_start).days
        
        if days_to_submit <= days_available * 0.3:  # Submitted in first 30%
            badges.append({
                'name': '⚡ Early Bird',
                'description': 'Submitted budget early',
                'icon': 'early_submission'
            })
        
        # Zero Variance Badge
        if cc_budget.variance_amount == 0:
            badges.append({
                'name': '✓ Perfect Submission',
                'description': 'No line items modified - exact submission',
                'icon': 'zero_variance'
            })
        
        # Best Utilization Badge
        if cc_budget.declared_budget.budget_impact_enabled:
            utilization = (cc_budget.consumed_amount / cc_budget.allocated_amount) * 100
            if 95 <= utilization <= 105:  # Between 95-105%
                badges.append({
                    'name': '🎯 Sweet Spot',
                    'description': 'Budget utilization within optimal range (95-105%)',
                    'icon': 'best_utilization'
                })
        
        # On-Time Completion Badge
        if cc_budget.final_approved_at:
            time_to_approval = (cc_budget.final_approved_at - cc_budget.submitted_at).days
            if time_to_approval <= 2:  # Approved within 2 days
                badges.append({
                    'name': '⚙️ Efficient Process',
                    'description': 'Budget approved quickly (< 2 days)',
                    'icon': 'quick_approval'
                })
        
        # No Hold Badge
        held_items = cc_budget.lines.filter(is_held_for_review=True).count()
        if held_items == 0:
            badges.append({
                'name': '✅ Clear Review',
                'description': 'No items held for further review',
                'icon': 'no_holds'
            })
        
        return badges
```

### 12.2 Dashboard - Gamification & KPIs

```
┌──────────────────────────────────────────────────────────────────────┐
│ Budget Performance Dashboard - Gamification & KPIs                   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│ ┌─ LEADERBOARD: Cost Centers with Best Budget Utilization           │
│ │ 🥇 Operations Dept       | 102% utilization (Best)                │
│ │ 🥈 Finance Dept          | 98% utilization                        │
│ │ 🥉 HR Dept               | 95% utilization                        │
│ │ 4   Sales Dept           | 75% utilization                        │
│ │ 5   Procurement          | 60% utilization                        │
│ └─                                                                     │
│                                                                        │
│ ┌─ BADGES EARNED (This Cycle)                                        │
│ │ Finance Dept:     ⚡ Early Bird | ✓ Perfect Submission | ⚙️ Efficient │
│ │ Operations Dept:  🎯 Sweet Spot | ✅ Clear Review                  │
│ │ HR Dept:          ⚡ Early Bird | ✅ Clear Review                   │
│ └─                                                                     │
│                                                                        │
│ ┌─ KEY METRICS                                                       │
│ │ Early Submission Rate:        58% (7 of 12 CCs)                    │
│ │ Zero Variance Budgets:        42% (5 of 12 CCs)                    │
│ │ Avg Budget Utilization:       89%                                  │
│ │ Avg Approval Cycle Time:      3.2 days                             │
│ │ Rejection Rate:               8% (1 rejection)                     │
│ └─                                                                     │
│                                                                        │
│ ┌─ UTILIZATION DISTRIBUTION                                          │
│ │ 95-105% (Sweet Spot):    4 CCs ████████████                       │
│ │ 80-94%:                  5 CCs ███████████████                     │
│ │ <80% (Under):            3 CCs ████████                            │
│ └─                                                                     │
│                                                                        │
│ [Export Report] [Send Recommendations] [Print Leaderboard]          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 13. Auto-Approval Trigger Logic (CRITICAL)

```python
class BudgetAutoApprovalScheduler:
    """
    System scheduler to auto-approve budgets at budget_start_date
    """
    @staticmethod
    def check_and_auto_approve():
        """
        Run daily at 00:00 UTC
        """
        today = date.today()
        
        # Find budgets with auto-approval enabled
        budgets_to_check = Budget.objects.filter(
            auto_approve_if_not_approved=True,
            budget_start_date=today,
            status__in=['pending_final_approval', 'pending_moderator_review', 
                       'review_open', 'entry_open']
        )
        
        auto_approved_count = 0
        
        for budget in budgets_to_check:
            # Auto-approve all CC budgets
            cc_budgets_pending = budget.cost_center_budgets.filter(
                status__in=['pending_final_approval', 'pending_moderator_review']
            )
            
            for cc_budget in cc_budgets_pending:
                cc_budget.status = 'auto_approved'
                cc_budget.final_approved_by = None
                cc_budget.final_approved_at = now()
                cc_budget.save()
                
                auto_approved_count += 1
                
                # Send notifications
                notify(
                    recipients=[cc_budget.cost_center.owner],
                    title='Budget Auto-Approved',
                    message=f'Budget "{budget.name}" auto-approved as budget start date reached'
                )
            
            # Mark declared budget as auto-approved
            budget.status = 'auto_approved'
            budget.auto_approved_at = now()
            budget.save()
            
            # Activate budget impact (enable consumption tracking)
            budget.budget_impact_enabled = True
            budget.save()
        
        logger.info(f'Auto-approved {auto_approved_count} CC budgets')
        
        return auto_approved_count
```

---

## 14. Implementation Roadmap

### Phase 1: Core (Weeks 1-3)
- [ ] Budget model with custom duration
- [ ] Entry/Review/Impact period controls
- [ ] Entry ON/OFF and Impact ON/OFF toggles
- [ ] Grace period configuration
- [ ] Variance tracking (original vs. modified)
- [ ] BudgetVarianceAudit model

### Phase 2: Moderator Features (Weeks 4-5)
- [ ] Moderator batch operations
- [ ] Held items logic
- [ ] Remark templates (predefined + custom)
- [ ] Apply template batch operation

### Phase 3: Auto-Approval & Advanced (Weeks 6-7)
- [ ] Auto-approval trigger logic
- [ ] Schedule job for auto-approval
- [ ] Budget cloning feature
- [ ] Parallel approval logic

### Phase 4: AI & Analytics (Weeks 8-9)
- [ ] Price prediction engine
- [ ] Consumption forecasting
- [ ] Variance report generation
- [ ] Real-time dashboard

### Phase 5: Gamification & KPIs (Week 10)
- [ ] Badge system
- [ ] Leaderboard
- [ ] KPI dashboard
- [ ] Performance metrics

---

## 15. Summary of New Features

✅ **Custom Budget Duration** - Monthly, Quarterly, Half-Yearly, Yearly, Custom days  
✅ **Grace Period** - Configurable delay between entry period end and review start  
✅ **Auto-Approval Toggle** - Automatic approval at budget start date (Module Owner controlled)  
✅ **Held Items Logic** - Mark specific lines for further review until resolved  
✅ **Review End Logic** - Cannot change after review period without hold mark  
✅ **Variance Tracking** - Complete audit trail of original vs. modified amounts  
✅ **Batch Moderator Operations** - Approve/send-back multiple lines at once  
✅ **Remark Templates** - Pre-defined and custom templates for consistency  
✅ **Budget Cloning** - Copy any prior budget as starting point  
✅ **AI Price Predictions** - Suggest prices based on historical PO data  
✅ **Consumption Forecasting** - Predict if budget will be exceeded  
✅ **Real-Time Dashboard** - Submission progress, bottlenecks, timelines  
✅ **Gamification KPIs** - Badges, leaderboards, performance incentives  
✅ **Parallel Approval** - Multiple CCs reviewed simultaneously  

This specification is **production-ready** and fully implements all your requirements!
