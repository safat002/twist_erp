
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from ..models import (
    Account,
    AccountType,
    Journal,
    JournalEntry,
    JournalStatus,
    JournalVoucher,
)
from ..models import FiscalPeriod, FiscalPeriodStatus
from apps.budgeting.models import CostCenter
from apps.projects.models import Project
from .config import enforce_period_posting, enforce_segregation_of_duties

class JournalService:
    """
    Service layer for handling all journal voucher and entry logic.
    Ensures that all interactions with the General Ledger are valid and balanced.
    """

    DECIMAL_PLACES = Decimal('0.01')

    @staticmethod
    def _normalize_decimal(value):
        """
        Coerce incoming debit/credit values to Decimal with two decimal places.
        """
        if value in (None, ''):
            value = 0
        quantized = Decimal(value).quantize(JournalService.DECIMAL_PLACES, rounding=ROUND_HALF_UP)
        if quantized < 0:
            raise ValueError("Debit/Credit values cannot be negative.")
        return quantized

    @staticmethod
    def _generate_voucher_number(company, journal, entry_date):
        from core.doc_numbers import get_next_doc_no
        number = get_next_doc_no(company=company, doc_type=journal.code, prefix=journal.code, fy_format="YYYY", width=4)
        # Extract numeric tail for sequence_number compatibility
        try:
            sequence_number = int(number.split("-")[-1])
        except Exception:  # noqa: BLE001
            sequence_number = 0
        return number, sequence_number

    @staticmethod
    def _prepare_entries(entries_data, company):
        prepared = []
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')

        for index, raw in enumerate(entries_data):
            account = raw.get('account')
            if isinstance(account, int):
                account = Account.objects.select_for_update().get(pk=account, company=company)
            elif isinstance(account, Account):
                account = Account.objects.select_for_update().get(pk=account.pk, company=company)
            else:
                raise ValueError("Each journal entry must reference an Account instance or ID.")

            if account.company_id != company.id:
                raise ValueError(f"Account {account.code} does not belong to company {company.code}.")

            debit = JournalService._normalize_decimal(raw.get('debit', 0))
            credit = JournalService._normalize_decimal(raw.get('credit', 0))

            if debit and credit:
                raise ValueError("A journal line cannot have both debit and credit values.")

            if not debit and not credit:
                raise ValueError("Each journal line must have either a debit or credit amount.")

            if not account.allow_direct_posting:
                raise ValueError(f"Direct posting is not allowed for account: {account.code} {account.name}")

            cost_center = raw.get('cost_center')
            if cost_center:
                if isinstance(cost_center, int):
                    cost_center = CostCenter.objects.get(pk=cost_center, company=company)
                elif cost_center.company_id != company.id:
                    raise ValueError("Cost center company mismatch.")
            project = raw.get('project')
            if project:
                if isinstance(project, int):
                    project = Project.objects.get(pk=project, company=company)
                elif project.company_id != company.id:
                    raise ValueError("Project company mismatch.")

            prepared.append(
                {
                    'account': account,
                    'debit': debit,
                    'credit': credit,
                    'description': raw.get('description', ''),
                    'line_number': index + 1,
                    'cost_center': cost_center,
                    'project': project,
                }
            )
            total_debit += debit
            total_credit += credit

        if total_debit != total_credit:
            raise ValueError("Journal entries are not balanced. Debits must equal credits.")

        if total_debit == 0:
            raise ValueError("Journal entries must have a non-zero debit and credit amount.")

        return prepared

    @staticmethod
    @transaction.atomic
    def create_journal_voucher(
        journal,
        entry_date,
        description,
        entries_data,
        reference="",
        source_document_type="",
        source_document_id=None,
        company=None,
        created_by=None,
    ):
        """
        Creates a new Journal Voucher in a DRAFT state.
        """
        if company is None:
            raise ValueError("company must be supplied when creating a journal voucher.")

        if not isinstance(journal, Journal):
            raise ValueError("journal must be a Journal instance.")

        if journal.company_id != company.id:
            raise ValueError("Journal does not belong to the supplied company.")

        prepared_entries = JournalService._prepare_entries(entries_data, company)
        voucher_number, sequence_number = JournalService._generate_voucher_number(
            company=company,
            journal=journal,
            entry_date=entry_date,
        )

        voucher = JournalVoucher.objects.create(
            company=company,
            journal=journal,
            entry_date=entry_date,
            period=entry_date.strftime('%Y-%m'),
            description=description,
            reference=reference,
            status=JournalStatus.DRAFT,
            source_document_type=source_document_type,
            source_document_id=source_document_id,
            voucher_number=voucher_number,
            sequence_number=sequence_number,
            created_by=created_by,
        )

        JournalEntry.objects.bulk_create(
            [
                JournalEntry(
                    voucher=voucher,
                    line_number=entry['line_number'],
                    account=entry['account'],
                    debit_amount=entry['debit'],
                    credit_amount=entry['credit'],
                    description=entry['description'],
                    cost_center=entry.get('cost_center'),
                    project=entry.get('project'),
                )
                for entry in prepared_entries
            ]
        )

        return voucher

    @staticmethod
    @transaction.atomic
    def post_journal_voucher(voucher: JournalVoucher, posted_by):
        """
        Posts a journal voucher, updating account balances.
        """
        voucher = (
            JournalVoucher.objects
            .select_for_update()
            .get(pk=voucher.pk)
        )

        if voucher.status not in {JournalStatus.DRAFT, JournalStatus.REVIEW}:
            raise ValueError(f"Voucher {voucher.voucher_number} is not in Draft state and cannot be posted.")

        # Period enforcement
        if enforce_period_posting(voucher.company):
            try:
                period_row = FiscalPeriod.objects.get(company=voucher.company, period=voucher.period)
            except FiscalPeriod.DoesNotExist:  # If no row exists, treat as open by default
                period_row = None
            if period_row and period_row.status != FiscalPeriodStatus.OPEN:
                raise ValueError(f"Posting blocked: fiscal period {voucher.period} is {period_row.status}.")

        # SoD enforcement
        if enforce_segregation_of_duties(voucher.company):
            if voucher.created_by_id and posted_by and voucher.created_by_id == posted_by.id:
                raise ValueError("Segregation of duties: creator cannot post their own voucher.")

        entries = list(
            voucher.entries
            .select_for_update()
            .select_related('account')
        )

        total_debit = sum((entry.debit_amount for entry in entries), Decimal('0.00'))
        total_credit = sum((entry.credit_amount for entry in entries), Decimal('0.00'))
        if total_debit != total_credit:
            raise ValueError(f"Voucher {voucher.voucher_number} is unbalanced and cannot be posted.")

        account_ids = {entry.account_id for entry in entries}
        accounts = {
            account.pk: account
            for account in Account.objects.select_for_update().filter(pk__in=account_ids)
        }

        for entry in entries:
            account = accounts[entry.account_id]
            balance_change = entry.debit_amount - entry.credit_amount
            if account.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
                Account.objects.filter(pk=account.pk).update(
                    current_balance=F('current_balance') + balance_change
                )
            else:
                Account.objects.filter(pk=account.pk).update(
                    current_balance=F('current_balance') - balance_change
                )

        voucher.status = JournalStatus.POSTED
        voucher.posted_by = posted_by
        voucher.posted_at = timezone.now()
        voucher.save(update_fields=['status', 'posted_by', 'posted_at'])

        return voucher

    @staticmethod
    def submit_for_review(voucher: JournalVoucher, actor):
        if voucher.status != JournalStatus.DRAFT:
            raise ValueError("Only draft vouchers can be submitted for review.")
        voucher.status = JournalStatus.REVIEW
        voucher.save(update_fields=['status'])
        return voucher

    @staticmethod
    def approve_voucher(voucher: JournalVoucher, reviewer):
        if voucher.status != JournalStatus.REVIEW:
            raise ValueError("Voucher is not in review state.")
        # SoD: reviewer cannot be creator
        if enforce_segregation_of_duties(voucher.company):
            if voucher.created_by_id and reviewer and voucher.created_by_id == reviewer.id:
                raise ValueError("Segregation of duties: creator cannot approve their own voucher.")
        voucher.reviewed_by = reviewer
        voucher.reviewed_at = timezone.now()
        voucher.save(update_fields=['reviewed_by', 'reviewed_at'])
        return voucher
