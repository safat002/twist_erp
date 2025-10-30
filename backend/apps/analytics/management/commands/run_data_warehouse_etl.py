from django.core.management.base import BaseCommand, CommandError

from apps.analytics.services.etl import run_warehouse_etl
from apps.companies.models import Company


class Command(BaseCommand):
    help = 'Run the analytics data warehouse ETL pipeline.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--period',
            default='30d',
            help='Period window to aggregate (e.g. 7d, 30d, month).',
        )
        parser.add_argument(
            '--company',
            action='append',
            type=int,
            help='Optional company ID(s) to restrict the ETL run. Repeatable.',
        )

    def handle(self, *args, **options):
        period = options['period']
        company_ids = options.get('company') or []

        companies = Company.objects.filter(is_active=True)
        if company_ids:
            companies = companies.filter(id__in=company_ids)
            missing = set(company_ids) - set(companies.values_list('id', flat=True))
            if missing:
                raise CommandError(f"Companies not found or inactive: {', '.join(str(x) for x in missing)}")

        result = run_warehouse_etl(period=period, companies=companies)
        processed = result.get('processed_companies', 0)
        errors = result.get('errors', [])

        if errors:
            self.stderr.write(self.style.ERROR(f"Completed with errors. Processed: {processed}, errors: {len(errors)}"))
            for err in errors:
                self.stderr.write(f" - Company {err['company_id']}: {err['error']}")
            raise CommandError('ETL run completed with errors.')

        self.stdout.write(self.style.SUCCESS(f"ETL completed successfully for {processed} company(ies)."))
