from django.core.management.base import BaseCommand, CommandParser

from apps.companies.models import Company
from apps.finance.models import Account, AccountType, InventoryPostingRule


class Command(BaseCommand):
    help = "Seed example inventory posting rules for a company (fallbacks by txn)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--company-id', type=int, required=True, help='Target company ID')
        parser.add_argument('--inventory-code', type=str, default='1100-INV', help='Inventory account code (optional)')
        parser.add_argument('--cogs-code', type=str, default='5000-COGS', help='COGS account code (optional)')

    def handle(self, *args, **options):
        company_id = options['company_id']
        inv_code = options['inventory_code']
        cogs_code = options['cogs_code']

        try:
            company = Company.objects.get(pk=company_id)
        except Company.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Company {company_id} not found"))
            return

        inv = Account.objects.filter(company=company, code=inv_code).first()
        if not inv:
            inv = Account.objects.filter(company=company, account_type=AccountType.ASSET, allow_direct_posting=True).order_by('code').first()
        if not inv:
            self.stderr.write(self.style.ERROR("No suitable Inventory (ASSET) account found"))
            return

        cogs = Account.objects.filter(company=company, code=cogs_code).first()
        if not cogs:
            cogs = Account.objects.filter(company=company, account_type=AccountType.EXPENSE, allow_direct_posting=True).order_by('code').first()
        if not cogs:
            self.stderr.write(self.style.ERROR("No suitable COGS (EXPENSE) account found"))
            return

        created = 0
        for txn in ('RECEIPT', 'ISSUE', 'TRANSFER'):
            rule, is_created = InventoryPostingRule.objects.update_or_create(
                company=company,
                category=None,
                warehouse_type='',
                transaction_type=txn,
                defaults={
                    'inventory_account': inv,
                    'cogs_account': cogs,
                    'is_active': True,
                }
            )
            created += 1 if is_created else 0

        self.stdout.write(self.style.SUCCESS(f"Seeded/updated {created} posting rules for company {company.code}"))

