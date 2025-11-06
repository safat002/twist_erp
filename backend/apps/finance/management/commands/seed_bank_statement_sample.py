from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.companies.models import Company
from apps.finance.models import Account, BankStatement, BankStatementLine


class Command(BaseCommand):
    help = "Create a sample bank statement with a few lines for a company's bank account."

    def add_arguments(self, parser):
        parser.add_argument("--company-id", type=int, required=True, help="Company ID")
        parser.add_argument("--bank-account-id", type=int, help="Bank account (Account.id) to use; defaults to first bank account.")

    def handle(self, *args, **options):
        company_id = options["company_id"]
        bank_account_id = options.get("bank_account_id")

        try:
            company = Company.objects.get(pk=company_id)
        except Company.DoesNotExist as exc:
            raise CommandError(f"Company {company_id} not found") from exc

        if bank_account_id:
            try:
                bank_account = Account.objects.get(pk=bank_account_id, company=company)
            except Account.DoesNotExist as exc:
                raise CommandError(f"Bank account {bank_account_id} not found in company {company.code}") from exc
        else:
            bank_account = Account.objects.filter(company=company, is_bank_account=True).first()
            if not bank_account:
                raise CommandError("No bank account found for this company. Create one first.")

        today = timezone.now().date()
        opening = Decimal("100000.00")
        # Create statement
        stmt = BankStatement.objects.create(
            company=company,
            company_group=company.company_group,
            bank_account=bank_account,
            statement_date=today,
            opening_balance=opening,
            closing_balance=opening,
            currency=(company.base_currency or "BDT"),
        )

        # Sample lines: receipt + payment + bank charge
        lines = [
            {
                "line_date": today,
                "description": "Customer receipt INV-1001",
                "reference": "RCPT-001",
                "amount": Decimal("5000.00"),
                "balance": opening + Decimal("5000.00"),
            },
            {
                "line_date": today,
                "description": "Supplier payment BILL-2003",
                "reference": "PAY-001",
                "amount": Decimal("-3200.00"),
                "balance": opening + Decimal("1800.00"),
            },
            {
                "line_date": today,
                "description": "Bank charges",
                "reference": "CHG-001",
                "amount": Decimal("-50.00"),
                "balance": opening + Decimal("1750.00"),
            },
        ]

        for payload in lines:
            BankStatementLine.objects.create(statement=stmt, **payload)

        # Update closing balance
        stmt.closing_balance = lines[-1]["balance"]
        stmt.save(update_fields=["closing_balance"])

        self.stdout.write(self.style.SUCCESS(f"Created sample bank statement {stmt.id} with {len(lines)} lines."))

