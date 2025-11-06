from datetime import date

from django.core.management.base import BaseCommand

from apps.finance.models import Account, AccountType, Journal
from apps.finance.services.journal_service import JournalService


class Command(BaseCommand):
    help = "Seed demo finance accounts, journal, and a sample journal voucher."

    def add_arguments(self, parser):
        parser.add_argument('--company-id', type=int, required=True)

    def handle(self, *args, **options):
        company_id = options['company_id']

        # Ensure journal
        journal, _ = Journal.objects.get_or_create(
            company_id=company_id, code='GENERAL', defaults={'name': 'General Journal', 'type': 'GENERAL'}
        )

        # Core accounts
        inv, _ = Account.objects.get_or_create(
            company_id=company_id, code='1300-INVENTORY',
            defaults={'name': 'Inventory', 'account_type': AccountType.ASSET}
        )
        cogs, _ = Account.objects.get_or_create(
            company_id=company_id, code='5000-COGS',
            defaults={'name': 'Cost of Goods Sold', 'account_type': AccountType.EXPENSE}
        )
        sales, _ = Account.objects.get_or_create(
            company_id=company_id, code='4000-SALES',
            defaults={'name': 'Sales Revenue', 'account_type': AccountType.REVENUE}
        )
        bank, _ = Account.objects.get_or_create(
            company_id=company_id, code='1000-BANK',
            defaults={'name': 'Bank Account', 'account_type': AccountType.ASSET}
        )
        ap, _ = Account.objects.get_or_create(
            company_id=company_id, code='2100-AP',
            defaults={'name': 'Accounts Payable', 'account_type': AccountType.LIABILITY}
        )

        # Sample JV: Expense debit, Bank credit (office supplies)
        voucher = JournalService.create_journal_voucher(
            company=journal.company,
            journal=journal,
            entry_date=date.today(),
            description='Demo JV: Office supplies purchase',
            entries_data=[
                {'account': cogs, 'debit': 250.00, 'credit': 0, 'description': 'Office supplies'},
                {'account': bank, 'debit': 0, 'credit': 250.00, 'description': 'Bank payment'},
            ],
        )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded finance demo for company={company_id}. JV {voucher.voucher_number} created."
        ))

