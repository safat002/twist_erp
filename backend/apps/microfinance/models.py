from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.doc_numbers import get_next_doc_no
from core.id_factory import IDFactory
from apps.finance.models import Journal
from apps.finance.services.journal_service import JournalService


class Borrower(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='borrowers')
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=32, blank=True)
    nid = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    group_name = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ('company', 'code')
        ordering = ['name']

    def save(self, *args, **kwargs):
        is_new = self._state.adding and not self.code
        super().save(*args, **kwargs)
        if is_new:
            generated = IDFactory.make_master_code('BRW', self.company, Borrower, width=5)
            Borrower.objects.filter(pk=self.pk).update(code=generated)
            self.code = generated


class LoanProduct(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='loan_products')
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=255)
    interest_rate_annual = models.DecimalField(max_digits=7, decimal_places=4)
    term_months = models.PositiveIntegerField()
    repayment_frequency = models.CharField(max_length=20, choices=[
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
    ], default='monthly')
    portfolio_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT, null=True, blank=True, related_name='loan_products_portfolio')
    interest_income_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT, null=True, blank=True, related_name='loan_products_interest')
    cash_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT, null=True, blank=True, related_name='loan_products_cash')

    class Meta:
        unique_together = ('company', 'code')

    def save(self, *args, **kwargs):
        is_new = self._state.adding and not self.code
        super().save(*args, **kwargs)
        if is_new:
            generated = IDFactory.make_master_code('LPR', self.company, LoanProduct, width=4)
            LoanProduct.objects.filter(pk=self.pk).update(code=generated)
            self.code = generated


class Loan(models.Model):
    class Status(models.TextChoices):
        APPLIED = 'applied', 'Applied'
        APPROVED = 'approved', 'Approved'
        DISBURSED = 'disbursed', 'Disbursed'
        ACTIVE = 'active', 'Active'
        CLOSED = 'closed', 'Closed'
        WRITTEN_OFF = 'written_off', 'Written Off'

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='loans')
    borrower = models.ForeignKey(Borrower, on_delete=models.PROTECT, related_name='loans')
    product = models.ForeignKey(LoanProduct, on_delete=models.PROTECT, related_name='loans')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    number = models.CharField(max_length=40, blank=True)
    principal = models.DecimalField(max_digits=20, decimal_places=2)
    interest_rate_annual = models.DecimalField(max_digits=7, decimal_places=4)
    term_months = models.PositiveIntegerField()
    repayment_frequency = models.CharField(max_length=20, choices=[
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
    ], default='monthly')
    disburse_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)
    outstanding_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        unique_together = ('company', 'number')

    def disburse(self, *, date=None, user=None):
        if self.status not in {self.Status.APPLIED, self.Status.APPROVED}:
            raise ValueError('Only applied/approved loans can be disbursed.')
        self.disburse_date = date or timezone.now().date()
        if not self.number:
            self.number = get_next_doc_no(company=self.company, doc_type='LN', prefix='LN', fy_format='YYYY', width=5)
        self.status = self.Status.DISBURSED
        self.save(update_fields=['disburse_date', 'number', 'status', 'updated_at'])
        self.generate_schedule()
        # Finance posting: Dr Portfolio (loan receivable), Cr Cash
        cash_acc = getattr(self.product, 'cash_account', None)
        portfolio_acc = getattr(self.product, 'portfolio_account', None)
        if cash_acc and portfolio_acc:
            journal = self._get_default_journal(user=user)
            entries = [
                { 'account': portfolio_acc, 'debit': self.principal, 'credit': Decimal('0.00'), 'description': f"Loan disbursement {self.number}" },
                { 'account': cash_acc, 'debit': Decimal('0.00'), 'credit': self.principal, 'description': f"Loan disbursement {self.number}" },
            ]
            voucher = JournalService.create_journal_voucher(
                company=self.company,
                journal=journal,
                entry_date=self.disburse_date,
                description=f"Loan disbursement {self.number}",
                entries_data=entries,
                reference=self.number,
                source_document_type='Loan',
                source_document_id=self.id,
                created_by=user,
            )
            JournalService.post_journal_voucher(voucher, user)

    def _periods(self) -> int:
        if self.repayment_frequency == 'weekly':
            return self.term_months * 4
        if self.repayment_frequency == 'biweekly':
            return self.term_months * 2
        return self.term_months

    def _next_due(self, start, idx) -> timezone.datetime:
        if self.repayment_frequency == 'weekly':
            return start + timedelta(weeks=idx)
        if self.repayment_frequency == 'biweekly':
            return start + timedelta(weeks=2 * idx)
        # monthly
        return start + timedelta(days=30 * idx)

    def generate_schedule(self):
        LoanRepaymentSchedule.objects.filter(loan=self).delete()
        periods = self._periods()
        principal = Decimal(self.principal)
        rate_annual = Decimal(self.interest_rate_annual)
        if self.repayment_frequency == 'weekly':
            rate_per = rate_annual / Decimal('52')
        elif self.repayment_frequency == 'biweekly':
            rate_per = rate_annual / Decimal('26')
        else:
            rate_per = rate_annual / Decimal('12')
        start = self.disburse_date or timezone.now().date()
        principal_per = (principal / periods).quantize(Decimal('0.01'))
        outstanding = principal
        total_outstanding = Decimal('0.00')
        items = []
        for i in range(1, periods + 1):
            interest = (outstanding * rate_per).quantize(Decimal('0.01'))
            p = principal_per if i < periods else outstanding
            total = (p + interest).quantize(Decimal('0.01'))
            due_date = self._next_due(start, i)
            items.append(LoanRepaymentSchedule(
                loan=self,
                installment_number=i,
                due_date=due_date,
                principal_due=p,
                interest_due=interest,
                total_due=total,
            ))
            outstanding -= p
            total_outstanding += total
        LoanRepaymentSchedule.objects.bulk_create(items)
        self.outstanding_amount = sum((x.total_due for x in items), Decimal('0.00'))
        self.status = self.Status.ACTIVE
        self.save(update_fields=['outstanding_amount', 'status', 'updated_at'])

    def _get_default_journal(self, user=None):
        journal = (
            Journal.objects.filter(company=self.company, code__in=["CASH", "GENERAL"]).order_by("code").first()
        )
        if journal:
            return journal
        return Journal.objects.create(
            company=self.company,
            company_group=self.company.company_group,
            created_by=user,
            code="GENERAL",
            name="General Journal",
            type="GENERAL",
        )


class LoanRepaymentSchedule(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='schedule')
    installment_number = models.PositiveIntegerField()
    due_date = models.DateField()
    principal_due = models.DecimalField(max_digits=20, decimal_places=2)
    interest_due = models.DecimalField(max_digits=20, decimal_places=2)
    total_due = models.DecimalField(max_digits=20, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('paid', 'Paid'), ('overdue', 'Overdue')], default='pending')

    class Meta:
        ordering = ['loan', 'installment_number']


class LoanRepayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, related_name='repayments')
    schedule = models.ForeignKey(LoanRepaymentSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name='repayments')
    payment_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    receipt_number = models.CharField(max_length=40, blank=True)
    principal_component = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    interest_component = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))

    def save(self, *args, **kwargs):
        is_new = self._state.adding and not self.receipt_number
        super().save(*args, **kwargs)
        if is_new:
            generated = get_next_doc_no(company=self.loan.company, doc_type='LRCPT', prefix='LRCPT', fy_format='YYYY', width=5)
            LoanRepayment.objects.filter(pk=self.pk).update(receipt_number=generated)
            self.receipt_number = generated
        # Apply to schedule/outstanding
        loan = self.loan
        remaining = Decimal(self.amount)
        # If schedule selected, apply there first
        qs = loan.schedule.all().order_by('installment_number')
        if self.schedule_id:
            qs = qs.filter(pk=self.schedule_id)
        for inst in qs:
            if remaining <= 0:
                break
            due_left = (inst.total_due - inst.paid_amount).quantize(Decimal('0.01'))
            pay = min(remaining, due_left)
            inst.paid_amount = (inst.paid_amount + pay).quantize(Decimal('0.01'))
            if inst.paid_amount + Decimal('0.001') >= inst.total_due:
                inst.status = 'paid'
            inst.save(update_fields=['paid_amount', 'status'])
            remaining -= pay
        # Update loan outstanding
        paid_total = sum((s.paid_amount for s in loan.schedule.all()), Decimal('0.00'))
        loan.outstanding_amount = max(sum((s.total_due for s in loan.schedule.all()), Decimal('0.00')) - paid_total, Decimal('0.00'))
        if loan.outstanding_amount <= Decimal('0.00'):
            loan.status = Loan.Status.CLOSED
        loan.save(update_fields=['outstanding_amount', 'status', 'updated_at'])
        # Finance posting: Dr Cash, Cr Interest Income (interest_component), Cr Portfolio (principal_component)
        cash_acc = getattr(loan.product, 'cash_account', None)
        portfolio_acc = getattr(loan.product, 'portfolio_account', None)
        interest_acc = getattr(loan.product, 'interest_income_account', None)
        if cash_acc and portfolio_acc and interest_acc:
            principal = self.principal_component or Decimal('0.00')
            interest = self.interest_component or Decimal('0.00')
            if principal + interest == Decimal('0.00'):
                # Heuristic: take interest from first pending installment's interest due up to amount
                first = loan.schedule.filter(status__in=['pending','overdue']).order_by('installment_number').first()
                if first:
                    interest = min(first.interest_due, remaining)
                    principal = max(Decimal('0.00'), self.amount - interest)
            journal = loan._get_default_journal(user=None)
            entries = [
                { 'account': cash_acc, 'debit': self.amount, 'credit': Decimal('0.00'), 'description': f"Repayment {self.receipt_number}" },
            ]
            if interest > Decimal('0.00'):
                entries.append({ 'account': interest_acc, 'debit': Decimal('0.00'), 'credit': interest, 'description': f"Interest {self.receipt_number}" })
            if principal > Decimal('0.00'):
                entries.append({ 'account': portfolio_acc, 'debit': Decimal('0.00'), 'credit': principal, 'description': f"Principal {self.receipt_number}" })
            voucher = JournalService.create_journal_voucher(
                company=loan.company,
                journal=journal,
                entry_date=self.payment_date,
                description=f"Loan repayment {loan.number}",
                entries_data=entries,
                reference=self.receipt_number,
                source_document_type='LoanRepayment',
                source_document_id=self.id,
                created_by=self.loan.created_by,
            )
            JournalService.post_journal_voucher(voucher, self.loan.created_by)
