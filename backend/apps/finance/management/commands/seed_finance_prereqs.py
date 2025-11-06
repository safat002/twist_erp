from django.core.management.base import BaseCommand, CommandParser

from apps.companies.models import Company
from apps.finance.models import Account, AccountType, Journal


class Command(BaseCommand):
    help = "Seed finance prerequisites: GRNI, INTRANSIT, ACCRUED_FREIGHT accounts and GENERAL/SALES journals."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--company-id', type=int, required=True, help='Target company ID')
        parser.add_argument('--grni-code', type=str, default='2110-GRNI', help='GRNI account code')
        parser.add_argument('--intransit-code', type=str, default='1300-INTRANSIT', help='In-Transit account code')
        parser.add_argument('--accrued-freight-code', type=str, default='2140-ACCRUED-FREIGHT', help='Accrued Freight account code')

    def handle(self, *args, **options):
        company_id = options['company_id']
        grni_code = options['grni_code']
        intransit_code = options['intransit_code']
        accrued_freight_code = options['accrued_freight_code']

        try:
            company = Company.objects.get(pk=company_id)
        except Company.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Company {company_id} not found"))
            return

        # Accounts
        grni, _ = Account.objects.get_or_create(
            company=company,
            company_group=company.company_group,
            code=grni_code,
            defaults={
                'name': 'Goods Received Not Invoiced',
                'account_type': AccountType.LIABILITY,
                'is_grni_account': True,
                'allow_direct_posting': True,
            },
        )
        intransit, _ = Account.objects.get_or_create(
            company=company,
            company_group=company.company_group,
            code=intransit_code,
            defaults={
                'name': 'In-Transit Inventory',
                'account_type': AccountType.ASSET,
                'allow_direct_posting': True,
            },
        )
        accrued_freight, _ = Account.objects.get_or_create(
            company=company,
            company_group=company.company_group,
            code=accrued_freight_code,
            defaults={
                'name': 'Accrued Freight',
                'account_type': AccountType.LIABILITY,
                'allow_direct_posting': True,
            },
        )

        # Journals
        general, _ = Journal.objects.get_or_create(
            company=company,
            company_group=company.company_group,
            code='GENERAL',
            defaults={'name': 'General Journal', 'type': 'GENERAL', 'is_active': True},
        )
        sales, _ = Journal.objects.get_or_create(
            company=company,
            company_group=company.company_group,
            code='SALES',
            defaults={'name': 'Sales Journal', 'type': 'SALES', 'is_active': True},
        )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded accounts: {grni.code}, {intransit.code}, {accrued_freight.code}; journals: {general.code}, {sales.code}"
        ))

