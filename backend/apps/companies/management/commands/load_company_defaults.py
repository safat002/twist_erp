"""
Management command to load industry-specific default data for companies.

Usage:
    python manage.py load_company_defaults --company=1
    python manage.py load_company_defaults --all
    python manage.py load_company_defaults --industry=MANUFACTURING
"""
from django.core.management.base import BaseCommand, CommandError
from apps.companies.models import Company
from apps.companies.services import DefaultDataService


class Command(BaseCommand):
    help = 'Load industry-specific default master data for companies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company',
            type=int,
            help='Company ID to load defaults for',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Load defaults for all companies that haven\'t loaded defaults yet',
        )
        parser.add_argument(
            '--industry',
            type=str,
            help='Load defaults for all companies with this industry category',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reload even if defaults already loaded (WARNING: May create duplicates)',
        )

    def handle(self, *args, **options):
        company_id = options.get('company')
        load_all = options.get('all')
        industry = options.get('industry')
        force = options.get('force')

        if not any([company_id, load_all, industry]):
            raise CommandError('You must specify --company, --all, or --industry')

        # Load for specific company
        if company_id:
            try:
                company = Company.objects.get(id=company_id)
                self._load_for_company(company, force)
            except Company.DoesNotExist:
                raise CommandError(f'Company with ID {company_id} does not exist')

        # Load for all companies
        elif load_all:
            if force:
                companies = Company.objects.all()
            else:
                companies = Company.objects.filter(default_data_loaded=False)

            self.stdout.write(f'Loading defaults for {companies.count()} companies...')
            for company in companies:
                self._load_for_company(company, force)

        # Load for specific industry
        elif industry:
            if force:
                companies = Company.objects.filter(industry_category=industry.upper())
            else:
                companies = Company.objects.filter(
                    industry_category=industry.upper(),
                    default_data_loaded=False
                )

            self.stdout.write(f'Loading defaults for {companies.count()} {industry} companies...')
            for company in companies:
                self._load_for_company(company, force)

        self.stdout.write(self.style.SUCCESS('[DONE] Default data loading complete!'))

    def _load_for_company(self, company, force=False):
        """Load defaults for a single company."""
        if company.default_data_loaded and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'[SKIP] {company.name}: Defaults already loaded (use --force to reload)'
                )
            )
            return

        self.stdout.write(f'Loading defaults for: {company.name} ({company.industry_category})...')

        try:
            # Temporarily unset the flag if forcing reload
            if force:
                company.default_data_loaded = False
                company.save(update_fields=['default_data_loaded'])

            service = DefaultDataService(company, created_by=company.created_by)
            results = service.load_all_defaults()

            self.stdout.write(self.style.SUCCESS(f'  [OK] {company.name}: {results}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [ERROR] {company.name}: {str(e)}'))
            raise
