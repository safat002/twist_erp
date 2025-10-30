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
    currency = models.CharField(max_length=3, default='BDT')
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

    class Meta:
        ordering = ['voucher', 'line_number']

class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
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

    def save(self, *args, **kwargs):
        is_new = self._state.adding and not self.invoice_number
        _ensure_company_group(self)
        super().save(*args, **kwargs)
        if is_new:
            prefix = "INV" if self.invoice_type == "AR" else "BILL"
            generated = f"{prefix}-{timezone.now():%Y%m}-{self.pk:05d}"
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
        ('POSTED', 'Posted'),
        ('RECONCILED', 'Reconciled'),
        ('CANCELLED', 'Cancelled'),
    ], default='DRAFT')
    bank_account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True)
    journal_voucher = models.ForeignKey(JournalVoucher, on_delete=models.PROTECT, null=True, blank=True)

    def save(self, *args, **kwargs):
        _ensure_company_group(self)
        is_new = self._state.adding and not self.payment_number
        super().save(*args, **kwargs)
        if is_new:
            prefix = "RCPT" if self.payment_type == "RECEIPT" else "PAY"
            generated = f"{prefix}-{timezone.now():%Y%m}-{self.pk:05d}"
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
