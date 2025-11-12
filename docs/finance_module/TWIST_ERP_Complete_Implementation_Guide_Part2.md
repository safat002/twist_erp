# TWIST ERP FINANCE MODULE - IMPLEMENTATION GUIDE PART 2
## Remaining Models, Configuration System & Business Logic

---

## 2.4 Finance Models - Fiscal Period

**File: `backend/apps/finance/models/period.py`**

```python
"""
Fiscal period and closing models
"""
from django.db import models
from django.core.exceptions import ValidationError
from apps.core.models import TimeStampedModel, Company, User
import uuid


class PeriodStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    CLOSED = 'CLOSED', 'Closed'
    LOCKED = 'LOCKED', 'Locked'


class FiscalPeriod(TimeStampedModel):
    """Accounting periods"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='fiscal_periods')
    
    # Period identification
    year = models.IntegerField(db_index=True)
    period = models.IntegerField(help_text="1-12 for monthly, 1-4 for quarterly")
    name = models.CharField(max_length=50)  # e.g., "Jan 2025", "Q1 2025"
    
    # Dates
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    
    # Status
    status = models.CharField(max_length=20, choices=PeriodStatus.choices, default='OPEN')
    
    # Closing
    closed_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='periods_closed')
    closed_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='periods_locked')
    locked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'finance_fiscal_period'
        unique_together = [['company', 'year', 'period']]
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]
        ordering = ['-year', '-period']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"
    
    @property
    def is_open(self):
        return self.status == 'OPEN'
    
    @property
    def is_closed(self):
        return self.status in ['CLOSED', 'LOCKED']
    
    @property
    def is_locked(self):
        return self.status == 'LOCKED'
    
    def can_post(self):
        """Can transactions be posted to this period?"""
        return self.status == 'OPEN'


class CloseChecklist(TimeStampedModel):
    """Period close checklist"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    period = models.ForeignKey(FiscalPeriod, on_delete=models.CASCADE, related_name='checklist_items')
    
    step_number = models.IntegerField()
    task_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    
    # Status
    is_completed = models.BooleanField(default=False)
    completed_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='close_tasks_completed')
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Verification
    requires_verification = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='close_tasks_verified')
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'finance_close_checklist'
        unique_together = [['period', 'step_number']]
        ordering = ['step_number']
```

---

## 2.5 Finance Models - Accounts Receivable

**File: `backend/apps/finance/models/ar.py`**

```python
"""
Accounts Receivable models
"""
from django.db import models
from django.core.exceptions import ValidationError
from apps.core.models import TimeStampedModel, Company, User
from .coa import GLAccount
from .period import FiscalPeriod
from decimal import Decimal
import uuid


class ARInvoiceStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SENT = 'SENT', 'Sent'
    PENDING = 'PENDING', 'Pending Payment'
    PARTIALLY_PAID = 'PARTIALLY_PAID', 'Partially Paid'
    PAID = 'PAID', 'Paid'
    CANCELLED = 'CANCELLED', 'Cancelled'
    OVERDUE = 'OVERDUE', 'Overdue'


class ARInvoice(TimeStampedModel):
    """Customer Invoice"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    period = models.ForeignKey(FiscalPeriod, on_delete=models.PROTECT)
    
    # Invoice details
    invoice_number = models.CharField(max_length=50, db_index=True)
    invoice_date = models.DateField(db_index=True)
    due_date = models.DateField(db_index=True)
    
    # Customer
    customer_id = models.UUIDField()  # FK to customer module
    customer_name = models.CharField(max_length=200)
    
    # Amounts
    subtotal = models.DecimalField(max_digits=20, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=20, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    balance = models.DecimalField(max_digits=20, decimal_places=2)
    
    # GL mapping
    ar_account = models.ForeignKey(GLAccount, on_delete=models.PROTECT, related_name='ar_invoices')
    revenue_account = models.ForeignKey(GLAccount, on_delete=models.PROTECT, related_name='revenue_invoices')
    
    # Status
    status = models.CharField(max_length=20, choices=ARInvoiceStatus.choices, default='DRAFT')
    
    # Posting
    journal_voucher = models.ForeignKey('JournalVoucher', on_delete=models.PROTECT, null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    
    # Terms
    payment_terms_days = models.IntegerField(default=30)
    
    # Reference
    customer_po = models.CharField(max_length=100, blank=True)
    reference = models.CharField(max_length=200, blank=True)
    
    class Meta:
        db_table = 'finance_ar_invoice'
        unique_together = [['company', 'invoice_number']]
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['customer_id', 'status']),
            models.Index(fields=['due_date']),
        ]
        ordering = ['-invoice_date']
    
    def __str__(self):
        return f"{self.invoice_number} - {self.customer_name}"
    
    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.balance > 0 and self.due_date < timezone.now().date()
    
    @property
    def days_overdue(self):
        if not self.is_overdue:
            return 0
        from django.utils import timezone
        return (timezone.now().date() - self.due_date).days


class ARInvoiceLine(TimeStampedModel):
    """Invoice line items"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(ARInvoice, on_delete=models.CASCADE, related_name='lines')
    line_number = models.IntegerField()
    
    # Item
    item_id = models.UUIDField(null=True, blank=True)  # FK to product/service
    description = models.TextField()
    
    # Quantity & Price
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    
    # Tax
    tax_code_id = models.UUIDField(null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    
    # GL Account
    revenue_account = models.ForeignKey(GLAccount, on_delete=models.PROTECT)
    
    class Meta:
        db_table = 'finance_ar_invoice_line'
        unique_together = [['invoice', 'line_number']]
        ordering = ['line_number']


class ARReceipt(TimeStampedModel):
    """Customer Payment Receipt"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    period = models.ForeignKey(FiscalPeriod, on_delete=models.PROTECT)
    
    # Receipt details
    receipt_number = models.CharField(max_length=50, db_index=True)
    receipt_date = models.DateField(db_index=True)
    
    # Customer
    customer_id = models.UUIDField()
    customer_name = models.CharField(max_length=200)
    
    # Amount
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    
    # Payment method
    payment_method = models.CharField(max_length=50)  # CASH, BANK, CARD, etc.
    bank_account = models.ForeignKey('BankAccount', on_delete=models.PROTECT, null=True, blank=True)
    
    # Reference
    reference = models.CharField(max_length=200, blank=True)
    check_number = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    
    # Posting
    journal_voucher = models.ForeignKey('JournalVoucher', on_delete=models.PROTECT, null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'finance_ar_receipt'
        unique_together = [['company', 'receipt_number']]
        indexes = [
            models.Index(fields=['company', 'receipt_date']),
            models.Index(fields=['customer_id']),
        ]


class ARAllocation(TimeStampedModel):
    """Links receipts to invoices"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt = models.ForeignKey(ARReceipt, on_delete=models.PROTECT, related_name='allocations')
    invoice = models.ForeignKey(ARInvoice, on_delete=models.PROTECT, related_name='allocations')
    
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    allocated_by = models.ForeignKey(User, on_delete=models.PROTECT)
    
    class Meta:
        db_table = 'finance_ar_allocation'
```

---

## 2.6 Finance Models - Accounts Payable

**File: `backend/apps/finance/models/ap.py`**

```python
"""
Accounts Payable models
"""
from django.db import models
from apps.core.models import TimeStampedModel, Company, User
from .coa import GLAccount
from .period import FiscalPeriod
from decimal import Decimal
import uuid


class APBillStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    MATCHED = 'MATCHED', '3-Way Matched'
    APPROVED = 'APPROVED', 'Approved'
    SCHEDULED = 'SCHEDULED', 'Scheduled for Payment'
    PAID = 'PAID', 'Paid'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'


class APBill(TimeStampedModel):
    """Supplier Bill"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    period = models.ForeignKey(FiscalPeriod, on_delete=models.PROTECT)
    
    # Bill details
    bill_number = models.CharField(max_length=50, db_index=True)
    bill_date = models.DateField(db_index=True)
    due_date = models.DateField(db_index=True)
    
    # Supplier
    supplier_id = models.UUIDField()
    supplier_name = models.CharField(max_length=200)
    
    # PO reference
    po_id = models.UUIDField(null=True, blank=True)
    po_number = models.CharField(max_length=50, blank=True)
    
    # Amounts
    subtotal = models.DecimalField(max_digits=20, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=20, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    balance = models.DecimalField(max_digits=20, decimal_places=2)
    
    # GL mapping
    ap_account = models.ForeignKey(GLAccount, on_delete=models.PROTECT, related_name='ap_bills')
    expense_account = models.ForeignKey(GLAccount, on_delete=models.PROTECT, related_name='expense_bills')
    
    # Status
    status = models.CharField(max_length=20, choices=APBillStatus.choices, default='DRAFT')
    
    # 3-way matching
    three_way_matched = models.BooleanField(default=False)
    match_variance = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    
    # Posting
    journal_voucher = models.ForeignKey('JournalVoucher', on_delete=models.PROTECT, null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    
    # AI extraction
    extracted_via_ai = models.BooleanField(default=False)
    extraction_confidence = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'finance_ap_bill'
        unique_together = [['company', 'bill_number']]
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['supplier_id', 'status']),
            models.Index(fields=['due_date']),
        ]


class APPayment(TimeStampedModel):
    """Supplier Payment"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    period = models.ForeignKey(FiscalPeriod, on_delete=models.PROTECT)
    
    # Payment details
    payment_number = models.CharField(max_length=50, db_index=True)
    payment_date = models.DateField(db_index=True)
    
    # Supplier
    supplier_id = models.UUIDField()
    supplier_name = models.CharField(max_length=200)
    
    # Amount
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    
    # Payment method
    payment_method = models.CharField(max_length=50)
    bank_account = models.ForeignKey('BankAccount', on_delete=models.PROTECT, null=True, blank=True)
    
    # Reference
    reference = models.CharField(max_length=200, blank=True)
    check_number = models.CharField(max_length=50, blank=True)
    
    # Posting
    journal_voucher = models.ForeignKey('JournalVoucher', on_delete=models.PROTECT, null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'finance_ap_payment'
        unique_together = [['company', 'payment_number']]
```

---

## 2.7 Finance Models - Bank & Cash

**File: `backend/apps/finance/models/bank.py`**

```python
"""
Bank and cash management models
"""
from django.db import models
from apps.core.models import TimeStampedModel, Company, User
from .coa import GLAccount
from decimal import Decimal
import uuid


class BankAccount(TimeStampedModel):
    """Bank account master"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='bank_accounts')
    
    # Account details
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=200)
    branch = models.CharField(max_length=200, blank=True)
    
    # GL mapping
    gl_account = models.ForeignKey(GLAccount, on_delete=models.PROTECT, related_name='bank_accounts')
    
    # Currency
    currency = models.CharField(max_length=3, default='BDT')
    
    # Balance
    current_balance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'finance_bank_account'
        unique_together = [['company', 'account_number', 'bank_name']]
        indexes = [
            models.Index(fields=['company', 'is_active']),
        ]


class BankStatement(TimeStampedModel):
    """Imported bank statement"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name='statements')
    
    # Statement details
    statement_date = models.DateField(db_index=True)
    opening_balance = models.DecimalField(max_digits=20, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=20, decimal_places=2)
    
    # Import
    import_file = models.CharField(max_length=500)
    imported_by = models.ForeignKey(User, on_delete=models.PROTECT)
    imported_at = models.DateTimeField(auto_now_add=True)
    
    # Reconciliation
    is_reconciled = models.BooleanField(default=False)
    reconciled_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='statements_reconciled')
    reconciled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'finance_bank_statement'
        indexes = [
            models.Index(fields=['bank_account', 'statement_date']),
        ]


class BankTransaction(TimeStampedModel):
    """Bank statement line"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    statement = models.ForeignKey(BankStatement, on_delete=models.CASCADE, related_name='transactions')
    
    # Transaction details
    transaction_date = models.DateField(db_index=True)
    value_date = models.DateField(null=True, blank=True)
    description = models.TextField()
    reference = models.CharField(max_length=200, blank=True)
    
    # Amount
    debit = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    credit = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    balance = models.DecimalField(max_digits=20, decimal_places=2)
    
    # Matching
    is_matched = models.BooleanField(default=False)
    matched_to_jv = models.ForeignKey('JournalVoucher', on_delete=models.SET_NULL, null=True, blank=True)
    matched_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    matched_at = models.DateTimeField(null=True, blank=True)
    
    # AI classification
    ai_classification = models.CharField(max_length=100, blank=True)
    ai_confidence = models.IntegerField(null=True, blank=True)
    suggested_account = models.ForeignKey(GLAccount, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'finance_bank_transaction'
        indexes = [
            models.Index(fields=['statement', 'transaction_date']),
            models.Index(fields=['is_matched']),
        ]


class BankRule(TimeStampedModel):
    """Rules for auto-matching bank transactions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='rules')
    
    # Rule details
    name = models.CharField(max_length=200)
    description_pattern = models.TextField(help_text="Regex or keyword pattern")
    
    # Classification
    classification = models.CharField(max_length=100)
    gl_account = models.ForeignKey(GLAccount, on_delete=models.PROTECT)
    cost_center_id = models.UUIDField(null=True, blank=True)
    
    # Confidence
    confidence_score = models.IntegerField(default=0)
    match_count = models.IntegerField(default=0)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    # Status
    is_active = models.BooleanField(default=True)
    created_by_ai = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'finance_bank_rule'
```

---

## 2.8 Configuration Models

**File: `backend/apps/finance/models/config.py`**

```python
"""
Configuration models for no-code customization
"""
from django.db import models
from apps.core.models import TimeStampedModel, Company
import uuid


class GLTemplate(TimeStampedModel):
    """Predefined journal entry templates"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    
    # Template details
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Template structure
    template_lines = models.JSONField(default=list)
    # [
    #   {"account_code": "1000", "dc": "D", "amount_formula": "{{total}}"},
    #   {"account_code": "4000", "dc": "C", "amount_formula": "{{total}}"}
    # ]
    
    # Category
    category = models.CharField(max_length=100)  # SALES, PURCHASE, EXPENSE, etc.
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'finance_gl_template'
        unique_together = [['company', 'code']]


class ApprovalPolicy(TimeStampedModel):
    """Approval workflow configuration"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    
    # Policy details
    name = models.CharField(max_length=200)
    entity_type = models.CharField(max_length=50)  # JV, AR_INVOICE, AP_BILL, etc.
    
    # Conditions (when this policy applies)
    conditions = models.JSONField(default=dict)
    # {
    #   "amount_min": 0,
    #   "amount_max": 50000,
    #   "source_type": "MANUAL"
    # }
    
    # Approval rules
    approval_levels = models.JSONField(default=list)
    # [
    #   {"level": 1, "role": "FINANCE_OFFICER", "required": true},
    #   {"level": 2, "role": "FINANCE_MANAGER", "required": true}
    # ]
    
    # SoD rules
    sod_rules = models.JSONField(default=dict)
    # {
    #   "creator_cannot_approve": true,
    #   "same_person_limit": 1
    # }
    
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text="Higher priority checked first")
    
    class Meta:
        db_table = 'finance_approval_policy'
        ordering = ['-priority']


class DocumentPolicy(TimeStampedModel):
    """Required documents configuration"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    
    # Policy details
    name = models.CharField(max_length=200)
    entity_type = models.CharField(max_length=50)
    
    # Conditions
    conditions = models.JSONField(default=dict)
    # {
    #   "amount_min": 10000,
    #   "account_type": "EXPENSE"
    # }
    
    # Required documents
    required_docs = models.JSONField(default=list)
    # [
    #   {"type": "PO", "required": true},
    #   {"type": "INVOICE", "required": true},
    #   {"type": "GRN", "required": false}
    # ]
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'finance_document_policy'


class NumberSequence(TimeStampedModel):
    """Auto-numbering configuration"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    
    # Sequence details
    entity_type = models.CharField(max_length=50, db_index=True)  # JV, AR_INV, AP_BILL, etc.
    prefix = models.CharField(max_length=20)
    separator = models.CharField(max_length=5, default='-')
    
    # Format: PREFIX-YYYY-MM-NNNNN
    include_year = models.BooleanField(default=True)
    include_month = models.BooleanField(default=False)
    padding = models.IntegerField(default=5, help_text="Number of digits")
    
    # Counter
    current_number = models.IntegerField(default=0)
    reset_on_year = models.BooleanField(default=True)
    reset_on_month = models.BooleanField(default=False)
    
    # Example
    example = models.CharField(max_length=100, editable=False)
    
    class Meta:
        db_table = 'finance_number_sequence'
        unique_together = [['company', 'entity_type']]
    
    def get_next_number(self, date=None):
        """Generate next number in sequence"""
        from django.utils import timezone
        if date is None:
            date = timezone.now().date()
        
        # Check if reset needed
        if self.reset_on_year:
            # Check if year changed
            pass  # Reset logic
        
        self.current_number += 1
        self.save()
        
        # Build number
        parts = [self.prefix]
        if self.include_year:
            parts.append(str(date.year))
        if self.include_month:
            parts.append(f"{date.month:02d}")
        parts.append(str(self.current_number).zfill(self.padding))
        
        return self.separator.join(parts)


class ReportTemplate(TimeStampedModel):
    """Configurable financial report templates"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    
    # Template details
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=50)  # PROFIT_LOSS, BALANCE_SHEET, etc.
    
    # Structure definition
    structure = models.JSONField(default=dict)
    # {
    #   "sections": [
    #     {
    #       "name": "Revenue",
    #       "accounts": ["4000-4999"],
    #       "formula": "SUM",
    #       "show_details": true
    #     }
    #   ]
    # }
    
    # Formatting
    format_settings = models.JSONField(default=dict)
    # {
    #   "show_comparatives": true,
    #   "show_variance": true,
    #   "decimal_places": 2
    # }
    
    # Status
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'finance_report_template'
        unique_together = [['company', 'code']]
```

---

## 3. BACKEND SERVICES LAYER

### 3.1 Posting Service

**File: `backend/apps/finance/services/posting.py`**

```python
"""
GL posting service with idempotency
"""
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from apps.finance.models import JournalVoucher, JournalLine, GLEntry
from apps.core.models import AuditLog
import hashlib
import logging

logger = logging.getLogger(__name__)


class PostingService:
    """Handle GL posting with safety guarantees"""
    
    def __init__(self, user):
        self.user = user
    
    @transaction.atomic
    def post_journal_voucher(self, journal_voucher):
        """
        Post a journal voucher to GL with idempotency
        
        Args:
            journal_voucher: JournalVoucher instance
            
        Returns:
            list of GLEntry instances
            
        Raises:
            ValidationError if posting fails validation
        """
        # Validation checks
        self._validate_can_post(journal_voucher)
        
        # Generate idempotency key
        posting_key = self._generate_posting_key(journal_voucher)
        
        # Check if already posted
        if GLEntry.objects.filter(journal_voucher=journal_voucher).exists():
            logger.warning(f"JV {journal_voucher.voucher_number} already posted")
            return list(journal_voucher.gl_entries.all())
        
        # Set posting key (ensures exactly-once semantics)
        try:
            journal_voucher.posting_key = posting_key
            journal_voucher.status = 'POSTED'
            journal_voucher.posted_by = self.user
            journal_voucher.posted_at = timezone.now()
            journal_voucher.save()
        except IntegrityError:
            logger.warning(f"JV {journal_voucher.voucher_number} posting race condition")
            raise ValidationError("This voucher is already being posted")
        
        # Create GL entries
        gl_entries = []
        for line in journal_voucher.lines.all():
            gl_entry = self._create_gl_entry(journal_voucher, line)
            gl_entries.append(gl_entry)
        
        # Update account balances (if using materialized views)
        self._update_account_balances(journal_voucher.company, journal_voucher.period, gl_entries)
        
        # Audit log
        AuditLog.objects.create(
            company=journal_voucher.company,
            user=self.user,
            action='POST_JV',
            entity_type='JournalVoucher',
            entity_id=journal_voucher.id,
            after_data={'voucher_number': journal_voucher.voucher_number}
        )
        
        logger.info(f"Posted JV {journal_voucher.voucher_number} with {len(gl_entries)} entries")
        return gl_entries
    
    def _validate_can_post(self, jv):
        """Validation before posting"""
        if not jv.can_post():
            raise ValidationError(f"Cannot post voucher in status {jv.status}")
        
        if not jv.is_balanced():
            raise ValidationError("Voucher is not balanced")
        
        if jv.period.is_closed:
            raise ValidationError("Cannot post to closed period")
        
        if jv.lines.count() == 0:
            raise ValidationError("No lines to post")
    
    def _generate_posting_key(self, jv):
        """Generate unique posting key for idempotency"""
        key_data = f"{jv.id}_{jv.voucher_date}_{jv.voucher_number}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:50]
    
    def _create_gl_entry(self, jv, line):
        """Create single GL entry from journal line"""
        gl_entry = GLEntry.objects.create(
            company=jv.company,
            period=jv.period,
            journal_voucher=jv,
            journal_line=line,
            posting_date=jv.voucher_date,
            transaction_date=jv.voucher_date,
            account=line.account,
            debit=line.debit,
            credit=line.credit,
            cost_center=line.cost_center,
            project=line.project,
            description=line.description or jv.description,
            reference=line.reference or jv.reference,
            posted_by=self.user,
            is_reversal=jv.is_reversal,
            reverses_entry=None  # Set if reversal
        )
        return gl_entry
    
    def _update_account_balances(self, company, period, gl_entries):
        """Update materialized balance views"""
        # Implementation depends on your caching strategy
        pass
    
    @transaction.atomic
    def reverse_journal_voucher(self, original_jv, reversal_date, reason):
        """Create reversal journal voucher"""
        # Create reversal JV
        reversal_jv = JournalVoucher.objects.create(
            company=original_jv.company,
            period=FiscalPeriod.get_period_for_date(original_jv.company, reversal_date),
            voucher_number=self._get_next_voucher_number(original_jv.company),
            voucher_date=reversal_date,
            description=f"REVERSAL: {original_jv.description} - {reason}",
            reference=f"REV-{original_jv.voucher_number}",
            source_type='ADJUSTMENT',
            status='APPROVED',  # Auto-approve reversals
            created_by=self.user,
            approved_by=self.user,
            approved_at=timezone.now(),
            is_reversal=True,
            reverses_voucher=original_jv
        )
        
        # Create reverse lines (flip debit/credit)
        for line in original_jv.lines.all():
            JournalLine.objects.create(
                journal_voucher=reversal_jv,
                line_number=line.line_number,
                account=line.account,
                debit=line.credit,  # Flip
                credit=line.debit,  # Flip
                cost_center=line.cost_center,
                project=line.project,
                description=f"Reversal of {line.description}",
                reference=line.reference
            )
        
        # Post reversal
        self.post_journal_voucher(reversal_jv)
        
        return reversal_jv
```

This is Part 2. Should I continue with:
- Part 3: API endpoints and views
- Part 4: Frontend components
- Part 5: One-click report generator
- Part 6: Complete deployment guide

?
