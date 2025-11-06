from django.core.management.base import BaseCommand, CommandParser

from apps.companies.models import Company
from apps.data_migration.models.session import MigrationTemplate


TEMPLATES = [
    {
        'name': 'Item Master (Product)',
        'target_model': 'inventory.Product',
        'target_module': 'inventory',
        'field_mappings': {
            'Item Code': 'code',
            'Item Name': 'name',
            'Category': 'category',
            'UoM': 'uom',
            'Cost Price': 'cost_price',
            'Selling Price': 'selling_price',
        },
        'validation_rules': {
            'required': ['code', 'name'],
            'unique_together': [['code']],
        },
    },
    {
        'name': 'Customer Master',
        'target_model': 'sales.Customer',
        'target_module': 'sales',
        'field_mappings': {
            'Customer Code': 'code',
            'Customer Name': 'name',
            'Email': 'email',
            'Phone': 'phone',
        },
        'validation_rules': {
            'required': ['code', 'name'],
        },
    },
    {
        'name': 'Supplier Master',
        'target_model': 'procurement.Supplier',
        'target_module': 'procurement',
        'field_mappings': {
            'Supplier Code': 'code',
            'Supplier Name': 'name',
            'Email': 'email',
            'Phone': 'phone',
        },
        'validation_rules': {
            'required': ['code', 'name'],
        },
    },
    {
        'name': 'Opening AR Invoices',
        'target_model': 'finance.Invoice',
        'target_module': 'finance',
        'field_mappings': {
            'Invoice Number': 'invoice_number',
            'Customer Id': 'partner_id',
            'Invoice Date': 'invoice_date',
            'Due Date': 'due_date',
            'Total Amount': 'total_amount',
        },
        'validation_rules': {
            'required': ['invoice_number', 'partner_id', 'invoice_date', 'total_amount'],
        },
    },
]


class Command(BaseCommand):
    help = "Seed reusable migration templates for common entities (company-scoped)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--company-id', type=int, required=True, help='Target company ID')

    def handle(self, *args, **options):
        company_id = options['company_id']
        try:
            company = Company.objects.get(pk=company_id)
        except Company.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Company {company_id} not found"))
            return

        created = 0
        for tpl in TEMPLATES:
            obj, is_created = MigrationTemplate.objects.update_or_create(
                company=company,
                name=tpl['name'],
                target_model=tpl['target_model'],
                defaults={
                    'description': f"Auto-seeded template for {tpl['target_model']}",
                    'target_module': tpl['target_module'],
                    'field_mappings': tpl['field_mappings'],
                    'validation_rules': tpl['validation_rules'],
                    'transformation_rules': {},
                    'default_values': {},
                },
            )
            created += 1 if is_created else 0

        self.stdout.write(self.style.SUCCESS(f"Seeded/updated {created} migration templates for company {company.code}"))

