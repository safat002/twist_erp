from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Dict

from django.db import transaction

from apps.procurement.models import Supplier
from apps.sales.models import Customer

from ..models import Account, Invoice, InvoiceStatus, Journal
from .journal_service import JournalService


class InvoiceService:
    """
    Service responsible for posting Accounts Payable (AP) and Accounts Receivable (AR) invoices.

    Posting an invoice creates and posts a journal voucher that mirrors the financial impact
    of the document. The invoice record is then marked as posted and linked back to the voucher.
    """

    @staticmethod
    def _summarise_lines(invoice: Invoice) -> Dict[int, Decimal]:
        line_totals: Dict[int, Decimal] = defaultdict(Decimal)
        for line in invoice.lines.select_related("account").all():
            line_totals[line.account_id] += Decimal(line.line_total)
        if not line_totals:
            raise ValueError("Invoice must contain at least one line before posting.")
        return line_totals

    @staticmethod
    def _validate_line_accounts(invoice: Invoice, line_totals: Dict[int, Decimal]) -> Dict[int, Account]:
        accounts = {
            account.pk: account
            for account in Account.objects.select_for_update().filter(pk__in=line_totals.keys(), company=invoice.company)
        }
        if len(accounts) != len(line_totals):
            raise ValueError("One or more invoice line accounts are invalid for this company.")
        return accounts

    @staticmethod
    @transaction.atomic
    def post_supplier_invoice(invoice: Invoice, posted_by):
        if invoice.invoice_type != "AP":
            raise ValueError("This service can only post Accounts Payable invoices.")
        if invoice.status not in {InvoiceStatus.DRAFT, InvoiceStatus.POSTED}:
            raise ValueError("Invoice must be in draft state before posting.")

        company = invoice.company

        try:
            supplier = Supplier.objects.select_related("payable_account").get(pk=invoice.partner_id, company=company)
        except Supplier.DoesNotExist as exc:
            raise ValueError(f"Supplier with ID {invoice.partner_id} not found.") from exc

        payable_account = supplier.payable_account
        if payable_account.company_id != company.id:
            raise ValueError("Supplier payable account does not belong to the active company.")

        try:
            purchase_journal = Journal.objects.get(company=company, code="PURCHASE")
        except Journal.DoesNotExist as exc:
            raise ValueError(f"Purchase journal not configured for company {company.name}.") from exc

        line_totals = InvoiceService._summarise_lines(invoice)
        accounts = InvoiceService._validate_line_accounts(invoice, line_totals)

        debit_entries = [
            {
                "account": accounts[account_id],
                "debit": amount,
                "credit": Decimal("0.00"),
                "description": f"Expense recognised for invoice {invoice.invoice_number}",
            }
            for account_id, amount in line_totals.items()
        ]

        total_value = invoice.total_amount
        entries_data = debit_entries + [
            {
                "account": payable_account,
                "debit": Decimal("0.00"),
                "credit": total_value,
                "description": f"Accounts payable for invoice {invoice.invoice_number}",
            }
        ]

        voucher = JournalService.create_journal_voucher(
            company=company,
            journal=purchase_journal,
            entry_date=invoice.invoice_date,
            description=f"Journal entry for AP invoice {invoice.invoice_number}",
            entries_data=entries_data,
            source_document_type="Invoice",
            source_document_id=invoice.id,
            created_by=posted_by,
        )

        JournalService.post_journal_voucher(voucher, posted_by)
        invoice.mark_posted(voucher, posted_by)
        return invoice

    @staticmethod
    @transaction.atomic
    def post_sales_invoice(invoice: Invoice, posted_by):
        if invoice.invoice_type != "AR":
            raise ValueError("This service can only post Accounts Receivable invoices.")
        if invoice.status not in {InvoiceStatus.DRAFT, InvoiceStatus.POSTED}:
            raise ValueError("Invoice must be in draft state before posting.")

        company = invoice.company

        try:
            customer = Customer.objects.select_related("receivable_account").get(pk=invoice.partner_id, company=company)
        except Customer.DoesNotExist as exc:
            raise ValueError(f"Customer with ID {invoice.partner_id} not found.") from exc

        receivable_account = customer.receivable_account
        if receivable_account.company_id != company.id:
            raise ValueError("Customer receivable account does not belong to the active company.")

        try:
            sales_journal = Journal.objects.get(company=company, code="SALES")
        except Journal.DoesNotExist as exc:
            raise ValueError(f"Sales journal not configured for company {company.name}.") from exc

        line_totals = InvoiceService._summarise_lines(invoice)
        accounts = InvoiceService._validate_line_accounts(invoice, line_totals)

        credit_entries = [
            {
                "account": accounts[account_id],
                "debit": Decimal("0.00"),
                "credit": amount,
                "description": f"Revenue recognised for invoice {invoice.invoice_number}",
            }
            for account_id, amount in line_totals.items()
        ]

        total_value = invoice.total_amount
        entries_data = [
            {
                "account": receivable_account,
                "debit": total_value,
                "credit": Decimal("0.00"),
                "description": f"Accounts receivable for invoice {invoice.invoice_number}",
            }
        ] + credit_entries

        voucher = JournalService.create_journal_voucher(
            company=company,
            journal=sales_journal,
            entry_date=invoice.invoice_date,
            description=f"Journal entry for AR invoice {invoice.invoice_number}",
            entries_data=entries_data,
            source_document_type="Invoice",
            source_document_id=invoice.id,
            created_by=posted_by,
        )

        JournalService.post_journal_voucher(voucher, posted_by)
        invoice.mark_posted(voucher, posted_by)
        return invoice
