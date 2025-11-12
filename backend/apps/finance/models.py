from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AccountType(models.TextChoices):
    ASSET = "ASSET", _("Asset")
    LIABILITY = "LIABILITY", _("Liability")
    EQUITY = "EQUITY", _("Equity")
    REVENUE = "REVENUE", _("Revenue")
    EXPENSE = "EXPENSE", _("Expense")


def _ensure_company_group(instance):
    """
    Convenience helper to mirror the company group relationship whenever only company is supplied.
    """
    if instance.company_id and not instance.company_group_id:
        instance.company_group = instance.company.company_group
    return instance

class Account(models.Model):
    company_group = models.ForeignKey('companies.CompanyGroup', on_delete=models.PROTECT, help_text="Company group this record belongs to")
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    is_active = models.BooleanField(default=True)
    is_bank_account = models.BooleanField(default=False)
    is_control_account = models.BooleanField(default=False)
    is_grni_account = models.BooleanField(default=False)
    allow_direct_posting = models.BooleanField(default=True)
    current_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    currency = models.CharField(
        max_length=3,
        default='BDT',
        help_text="Primary currency for this account (ISO 4217 code)"
    )
    is_multi_currency = models.BooleanField(
        default=False,
        help_text="If True, this account can have transactions in multiple currencies"
    )
    currency_balances = models.JSONField(
        default=dict,
        blank=True,
        help_text="Balances by currency: {'USD': 1000.00, 'EUR': 500.00, 'BDT': 5000.00}"
    )
    is_default_template = models.BooleanField(
        default=False,
        help_text="System default account from industry template (can be customized)"
    )
    parent_account = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='sub_accounts')

    def save(self, *args, **kwargs):
        _ensure_company_group(self)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['code']
        unique_together = ('company', 'code')
        indexes = [
            models.Index(fields=['company', 'account_type']),
            models.Index(fields=['company', 'is_active']),
        ]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"

    @property
    def children_count(self) -> int:
        return self.sub_accounts.count()

class Journal(models.Model):
    company_group = models.ForeignKey('companies.CompanyGroup', on_delete=models.PROTECT, help_text="Company group this record belongs to")
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=[
        ('GENERAL', 'General Journal'),
        ('SALES', 'Sales Journal'),
        ('PURCHASE', 'Purchase Journal'),
        ('CASH', 'Cash Journal'),
        ('BANK', 'Bank Journal'),
    ])
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        _ensure_company_group(self)
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('company', 'code')

class JournalStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    REVIEW = "REVIEW", _("In Review")
    POSTED = "POSTED", _("Posted")
    CANCELLED = "CANCELLED", _("Cancelled")

class JournalVoucher(models.Model):
    company_group = models.ForeignKey('companies.CompanyGroup', on_delete=models.PROTECT, help_text="Company group this record belongs to")
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    voucher_number = models.CharField(max_length=50)
    entry_date = models.DateField()
    period = models.CharField(max_length=7)
    reference = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=JournalStatus.choices, default=JournalStatus.DRAFT)
    source_document_type = models.CharField(max_length=50, blank=True)
    source_document_id = models.IntegerField(null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name='posted_vouchers')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    journal = models.ForeignKey(Journal, on_delete=models.PROTECT)
    sequence_number = models.PositiveIntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        _ensure_company_group(self)
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('company', 'voucher_number')
        indexes = [
            models.Index(fields=['company', 'entry_date']),
            models.Index(fields=['company', 'status']),
        ]

    def __str__(self) -> str:
        return f"{self.voucher_number} ({self.get_status_display()})"

    @property
    def total_debit(self) -> Decimal:
        return self.entries.aggregate(total=Sum("debit_amount")).get("total") or Decimal("0.00")

    @property
    def total_credit(self) -> Decimal:
        return self.entries.aggregate(total=Sum("credit_amount")).get("total") or Decimal("0.00")

class JournalSequence(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE)
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE)
    fiscal_year = models.CharField(max_length=4)
    current_value = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('company', 'journal', 'fiscal_year')
        indexes = [
            models.Index(fields=['company', 'journal', 'fiscal_year']),
        ]

class JournalEntry(models.Model):
    voucher = models.ForeignKey(JournalVoucher, on_delete=models.CASCADE, related_name='entries')
    line_number = models.IntegerField()
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    debit_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    credit_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    description = models.CharField(max_length=255, blank=True)
    cost_center = models.ForeignKey('budgeting.CostCenter', on_delete=models.PROTECT, null=True, blank=True, related_name='journal_entries')
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT, null=True, blank=True, related_name='journal_entries')

    class Meta:
        ordering = ['voucher', 'line_number']


class InventoryPostingRule(models.Model):
    """GL posting rule for inventory by category/warehouse type/transaction type."""
    TRANSACTION_CHOICES = [
        ('RECEIPT', 'Stock Receipt'),
        ('ISSUE', 'Stock Issue'),
        ('TRANSFER_OUT', 'Transfer Out'),
        ('TRANSFER_IN', 'Transfer In'),
        ('ADJUSTMENT', 'Adjustment'),
        ('SCRAP', 'Scrap'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='inventory_posting_rules')
    budget_item = models.ForeignKey(
        'budgeting.BudgetItemCode',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='inventory_posting_rules',
        help_text="Specific budget item for this posting rule"
    )
    item = models.ForeignKey(
        'inventory.Item',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='inventory_posting_rules',
        help_text="Legacy item reference (deprecated, prefer budget item)"
    )
    # Optional scoping
    category = models.ForeignKey(
        'inventory.ItemCategory',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='inventory_posting_rules',
        help_text="Item category for this posting rule"
    )
    sub_category = models.ForeignKey(
        'inventory.ItemCategory',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='inventory_posting_rules_sub',
        help_text="Item sub-category for this posting rule"
    )
    warehouse_type = models.CharField(max_length=20, blank=True, default='')
    warehouse = models.ForeignKey(
        'inventory.Warehouse',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='inventory_posting_rules',
        help_text="Specific warehouse for this rule"
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_CHOICES, blank=True, default='')
    # Accounts
    inventory_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT, related_name='+')
    cogs_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=100, help_text="Lower numbers win when multiple rules match")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['company', 'warehouse_type', 'transaction_type']),
            models.Index(fields=['company', 'category']),
            models.Index(fields=['company', 'warehouse']),
            models.Index(fields=['company', 'budget_item']),
            models.Index(fields=['company', 'item']),
            models.Index(fields=['company', 'priority']),
        ]

    def __str__(self) -> str:
        parts = [getattr(self.company, 'code', self.company_id)]
        if self.budget_item_id:
            parts.append(f"item:{self.budget_item.code}")
        if self.category_id:
            parts.append(f"cat:{getattr(self.category, 'code', self.category_id)}")
        if self.sub_category_id:
            parts.append(f"sub:{getattr(self.sub_category, 'code', self.sub_category_id)}")
        if self.warehouse_id:
            parts.append(f"wh:{getattr(self.warehouse, 'code', self.warehouse_id)}")
        if self.warehouse_type:
            parts.append(f"wh:{self.warehouse_type}")
        if self.transaction_type:
            parts.append(f"txn:{self.transaction_type}")
        return ' | '.join(parts)

class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    APPROVED = "APPROVED", _("Approved")
    POSTED = "POSTED", _("Posted")
    PARTIAL = "PARTIAL", _("Partially Paid")
    PAID = "PAID", _("Fully Paid")
    CANCELLED = "CANCELLED", _("Cancelled")


class Invoice(models.Model):
    company_group = models.ForeignKey('companies.CompanyGroup', on_delete=models.PROTECT, help_text="Company group this record belongs to")
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    invoice_number = models.CharField(max_length=50)
    invoice_type = models.CharField(max_length=10, choices=[
        ('AR', 'Accounts Receivable'),
        ('AP', 'Accounts Payable'),
    ])
    partner_type = models.CharField(max_length=20)
    partner_id = models.IntegerField()
    invoice_date = models.DateField()
    due_date = models.DateField()
    subtotal = models.DecimalField(max_digits=20, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=20, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='BDT')
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6, default=1)
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)
    notes = models.TextField(blank=True)
    journal_voucher = models.ForeignKey(JournalVoucher, on_delete=models.PROTECT, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='+')

    def save(self, *args, **kwargs):
        is_new = self._state.adding and not self.invoice_number
        _ensure_company_group(self)
        super().save(*args, **kwargs)
        if is_new:
            from core.doc_numbers import get_next_doc_no
            prefix = "INV" if self.invoice_type == "AR" else "BILL"
            generated = get_next_doc_no(company=self.company, doc_type=prefix, prefix=prefix, fy_format="YYYY", width=5)
            Invoice.objects.filter(pk=self.pk).update(invoice_number=generated)
            self.invoice_number = generated

    class Meta:
        unique_together = ('company', 'invoice_number')
        indexes = [
            models.Index(fields=['company', 'invoice_type', 'status']),
            models.Index(fields=['company', 'due_date']),
        ]

    def __str__(self) -> str:
        return f"{self.invoice_number} ({self.get_status_display()})"

    @property
    def balance_due(self) -> Decimal:
        return max(Decimal(self.total_amount or 0) - Decimal(self.paid_amount or 0), Decimal("0.00"))

    @property
    def is_overdue(self) -> bool:
        return self.balance_due > 0 and timezone.now().date() > self.due_date

    def recalculate_totals(self, commit: bool = True) -> tuple[Decimal, Decimal]:
        aggregates = self.lines.aggregate(subtotal=Sum("line_total"))
        subtotal = aggregates.get("subtotal") or Decimal("0.00")
        self.subtotal = subtotal
        gross = subtotal - Decimal(self.discount_amount or 0) + Decimal(self.tax_amount or 0)
        self.total_amount = gross
        if commit:
            self.save(update_fields=["subtotal", "total_amount", "updated_at"])
        return self.subtotal, self.total_amount

    def refresh_payment_status(self, commit: bool = True) -> str:
        outstanding = self.balance_due
        if self.status == InvoiceStatus.CANCELLED:
            return self.status
        if outstanding <= Decimal("0.00"):
            new_status = InvoiceStatus.PAID
        elif self.paid_amount and Decimal(self.paid_amount) > 0:
            new_status = InvoiceStatus.PARTIAL
        elif self.status == InvoiceStatus.POSTED:
            new_status = InvoiceStatus.POSTED
        else:
            new_status = InvoiceStatus.DRAFT
        if new_status != self.status:
            self.status = new_status
            if commit:
                self.save(update_fields=["status", "updated_at"])
        return self.status

    def register_payment(self, amount: Decimal, commit: bool = True) -> None:
        self.paid_amount = Decimal(self.paid_amount or 0) + Decimal(amount or 0)
        if self.paid_amount > self.total_amount:
            self.paid_amount = self.total_amount
        if commit:
            self.save(update_fields=["paid_amount", "updated_at"])
        self.refresh_payment_status(commit=commit)

    def mark_posted(self, voucher: JournalVoucher, posted_by) -> None:
        self.status = InvoiceStatus.POSTED
        self.journal_voucher = voucher
        self.updated_at = timezone.now()
        self.save(update_fields=["status", "journal_voucher", "updated_at"])

class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    line_number = models.IntegerField()
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=15, decimal_places=3, default=1)
    unit_price = models.DecimalField(max_digits=20, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=20, decimal_places=2)
    product_id = models.IntegerField(null=True, blank=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)

    class Meta:
        ordering = ['invoice', 'line_number']

class Payment(models.Model):
    company_group = models.ForeignKey('companies.CompanyGroup', on_delete=models.PROTECT, help_text="Company group this record belongs to")
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payment_number = models.CharField(max_length=50)
    payment_date = models.DateField()
    payment_type = models.CharField(max_length=20, choices=[
        ('RECEIPT', 'Customer Payment'),
        ('PAYMENT', 'Supplier Payment'),
    ])
    payment_method = models.CharField(max_length=20, choices=[
        ('CASH', 'Cash'),
        ('BANK', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
        ('CARD', 'Card'),
        ('MOBILE', 'Mobile Payment'),
    ])
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.CharField(max_length=3, default='BDT')
    partner_type = models.CharField(max_length=20)
    partner_id = models.IntegerField()
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=[
        ('DRAFT', 'Draft'),
        ('APPROVED', 'Approved'),
        ('POSTED', 'Posted'),
        ('RECONCILED', 'Reconciled'),
        ('CANCELLED', 'Cancelled'),
    ], default='DRAFT')
    bank_account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True)
    journal_voucher = models.ForeignKey(JournalVoucher, on_delete=models.PROTECT, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='+')

    def save(self, *args, **kwargs):
        _ensure_company_group(self)
        is_new = self._state.adding and not self.payment_number
        super().save(*args, **kwargs)
        if is_new:
            from core.doc_numbers import get_next_doc_no
            prefix = "RCPT" if self.payment_type == "RECEIPT" else "PAY"
            generated = get_next_doc_no(company=self.company, doc_type=prefix, prefix=prefix, fy_format="YYYY", width=5)
            Payment.objects.filter(pk=self.pk).update(payment_number=generated)
            self.payment_number = generated

    class Meta:
        unique_together = ('company', 'payment_number')

    def __str__(self) -> str:
        return f"{self.payment_number} ({self.get_payment_type_display()})"

    @property
    def remaining_amount(self) -> Decimal:
        allocated = self.allocations.aggregate(total=Sum("allocated_amount")).get("total") or Decimal("0.00")
        return Decimal(self.amount or 0) - Decimal(allocated)

    def mark_posted(self, voucher: JournalVoucher, posted_by):
        self.status = "POSTED"
        self.journal_voucher = voucher
        self.updated_at = timezone.now()
        self.save(update_fields=["status", "journal_voucher", "updated_at"])

class PaymentAllocation(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='allocations')
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT)
    allocated_amount = models.DecimalField(max_digits=20, decimal_places=2)

    class Meta:
        unique_together = ('payment', 'invoice')


# --- Period Control ---
class FiscalPeriodStatus(models.TextChoices):
    OPEN = "OPEN", _("Open")
    CLOSED = "CLOSED", _("Closed")
    LOCKED = "LOCKED", _("Locked")


class FiscalPeriod(models.Model):
    company_group = models.ForeignKey('companies.CompanyGroup', on_delete=models.PROTECT)
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    period = models.CharField(max_length=7, help_text="YYYY-MM")
    status = models.CharField(max_length=10, choices=FiscalPeriodStatus.choices, default=FiscalPeriodStatus.OPEN)
    locked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    locked_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company', 'period')
        indexes = [models.Index(fields=['company', 'period', 'status'])]

    def __str__(self) -> str:
        return f"{self.company.code} {self.period} [{self.status}]"


# --- Taxes ---
class TaxJurisdiction(models.Model):
    company_group = models.ForeignKey('companies.CompanyGroup', on_delete=models.PROTECT)
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('company', 'code')


class TaxCode(models.Model):
    company_group = models.ForeignKey('companies.CompanyGroup', on_delete=models.PROTECT)
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_inclusive = models.BooleanField(default=False)
    jurisdiction = models.ForeignKey(TaxJurisdiction, on_delete=models.PROTECT, null=True, blank=True)
    input_tax_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='+', null=True, blank=True)
    output_tax_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='+', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('company', 'code')


# --- Bank Reconciliation (v1) ---
class BankStatement(models.Model):
    company_group = models.ForeignKey('companies.CompanyGroup', on_delete=models.PROTECT)
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    bank_account = models.ForeignKey(Account, on_delete=models.PROTECT)
    statement_date = models.DateField()
    opening_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='BDT')
    status = models.CharField(max_length=20, choices=[
        ('IMPORTED', 'Imported'),
        ('PARTIAL', 'Partially Matched'),
        ('RECONCILED', 'Reconciled'),
    ], default='IMPORTED')
    imported_filename = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['company', 'bank_account', 'statement_date'])]


class BankStatementLine(models.Model):
    statement = models.ForeignKey(BankStatement, on_delete=models.CASCADE, related_name='lines')
    line_date = models.DateField()
    description = models.CharField(max_length=255)
    reference = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    balance = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    match_status = models.CharField(max_length=20, choices=[
        ('UNMATCHED', 'Unmatched'),
        ('SUGGESTED', 'Suggested'),
        ('MATCHED', 'Matched'),
    ], default='UNMATCHED')
    matched_payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    matched_voucher = models.ForeignKey(JournalVoucher, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# ========================================
# MULTI-CURRENCY SUPPORT
# ========================================

class Currency(models.Model):
    """
    Currency master for multi-currency support.
    Each company can define currencies they transact in.
    """
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        help_text="Company this record belongs to"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Currency identification (ISO 4217)
    code = models.CharField(
        max_length=3,
        help_text="ISO 4217 currency code (USD, EUR, BDT, etc.)"
    )
    name = models.CharField(max_length=50, help_text="Currency name (US Dollar, Euro, etc.)")
    symbol = models.CharField(max_length=10, help_text="Currency symbol ($, €, ৳, etc.)")

    # Exchange rate config
    is_base_currency = models.BooleanField(
        default=False,
        help_text="Base currency for this company (only one should be True)"
    )

    # Display
    decimal_places = models.IntegerField(
        default=2,
        help_text="Number of decimal places for this currency"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'finance_currency'
        unique_together = ('company', 'code')
        verbose_name_plural = 'Currencies'
        ordering = ['code']
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['company', 'is_base_currency']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class ExchangeRate(models.Model):
    """
    Exchange rates between currencies with date effectivity.
    Supports both direct rates (USD to BDT) and automatic inverse calculation.
    """
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        help_text="Company this record belongs to"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Currency pair
    from_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='rates_from',
        help_text="Source currency"
    )
    to_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='rates_to',
        help_text="Target currency"
    )

    # Rate information
    rate = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        help_text="Exchange rate: 1 from_currency = rate × to_currency"
    )

    effective_date = models.DateField(
        db_index=True,
        help_text="Date from which this rate is effective"
    )

    # Rate type
    rate_type = models.CharField(
        max_length=20,
        choices=[
            ('SPOT', 'Spot Rate'),
            ('AVERAGE', 'Average Rate'),
            ('FIXED', 'Fixed Rate'),
            ('BUDGET', 'Budget Rate'),
        ],
        default='SPOT',
        help_text="Type of exchange rate"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'finance_exchange_rate'
        ordering = ['-effective_date']
        indexes = [
            models.Index(fields=['company', 'from_currency', 'to_currency', '-effective_date']),
            models.Index(fields=['company', 'effective_date']),
            models.Index(fields=['company', 'is_active']),
        ]
        # Allow multiple rates for same pair on different dates
        unique_together = ('company', 'from_currency', 'to_currency', 'effective_date', 'rate_type')

    def __str__(self):
        return f"{self.from_currency.code}/{self.to_currency.code}: {self.rate} ({self.effective_date})"

    @classmethod
    def get_rate(cls, company, from_currency, to_currency, as_of_date=None):
        """
        Get exchange rate for a currency pair as of a specific date.
        If no date specified, uses today's date.
        Returns None if no rate found.
        """
        if as_of_date is None:
            as_of_date = timezone.now().date()

        # Same currency - rate is 1
        if from_currency == to_currency:
            return Decimal('1.000000')

        # Try direct rate
        try:
            rate_record = cls.objects.filter(
                company=company,
                from_currency=from_currency,
                to_currency=to_currency,
                effective_date__lte=as_of_date,
                is_active=True
            ).order_by('-effective_date').first()

            if rate_record:
                return rate_record.rate
        except cls.DoesNotExist:
            pass

        # Try inverse rate
        try:
            inverse_rate = cls.objects.filter(
                company=company,
                from_currency=to_currency,
                to_currency=from_currency,
                effective_date__lte=as_of_date,
                is_active=True
            ).order_by('-effective_date').first()

            if inverse_rate and inverse_rate.rate != 0:
                return Decimal('1.000000') / inverse_rate.rate
        except cls.DoesNotExist:
            pass

        return None

    @classmethod
    def convert_amount(cls, company, amount, from_currency, to_currency, as_of_date=None):
        """
        Convert an amount from one currency to another.
        Returns tuple: (converted_amount, rate_used)
        """
        if from_currency == to_currency:
            return (amount, Decimal('1.000000'))

        rate = cls.get_rate(company, from_currency, to_currency, as_of_date)

        if rate is None:
            raise ValueError(
                f"No exchange rate found for {from_currency.code} to {to_currency.code} "
                f"as of {as_of_date or 'today'}"
            )

        converted_amount = amount * rate
        return (converted_amount, rate)
