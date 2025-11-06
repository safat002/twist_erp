
import csv
from django.core.management.base import BaseCommand
from apps.finance.models import Account
from apps.companies.models import Company

class Command(BaseCommand):
    help = 'Uploads a chart of accounts from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file.')
        parser.add_argument('company_code', type=str, help='The code of the company.')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        company_code = options['company_code']

        try:
            company = Company.objects.get(code=company_code)
        except Company.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Company with code "{company_code}" does not exist.'))
            return

        with open(csv_file_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header row

            for row in reader:
                (
                    account_code,
                    account_name,
                    account_type,
                    parent_account_code,
                    allow_direct_posting,
                    description,
                ) = row

                parent_account = None
                if parent_account_code:
                    try:
                        parent_account = Account.objects.get(code=parent_account_code, company=company)
                    except Account.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'Parent account with code "{parent_account_code}" does not exist. Skipping row.'))
                        continue
                
                # Map CSV account type to model's account type
                account_type_mapping = {
                    "Asset": "ASSET",
                    "Liability": "LIABILITY",
                    "Equity": "EQUITY",
                    "Income": "REVENUE",
                    "Expense": "EXPENSE",
                    "Contra Asset": "ASSET",
                }
                account_type_value = account_type_mapping.get(account_type)
                if not account_type_value:
                    self.stdout.write(self.style.WARNING(f'Invalid account type "{account_type}". Skipping row.'))
                    continue


                Account.objects.update_or_create(
                    company=company,
                    code=account_code,
                    defaults={
                        'name': account_name,
                        'account_type': account_type_value,
                        'parent_account': parent_account,
                        'allow_direct_posting': allow_direct_posting.lower() == 'yes',
                        'is_active': True,
                    },
                )

        self.stdout.write(self.style.SUCCESS('Successfully uploaded chart of accounts.'))
