from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.companies.models import Company
from apps.finance.services.period_service import ensure_upcoming_periods


class Command(BaseCommand):
    help = "Ensure current and next fiscal periods exist for all active companies."

    def add_arguments(self, parser):
        parser.add_argument('--days-threshold', type=int, default=15, help='Days before period end to pre-create next period')
        parser.add_argument('--company-id', type=int, help='Only process a single company')

    def handle(self, *args, **options):
        days = options['days_threshold']
        company_id = options.get('company_id')
        qs = Company.objects.filter(is_active=True)
        if company_id:
            qs = qs.filter(id=company_id)
        count = 0
        for company in qs:
            ensure_upcoming_periods(company, days_threshold=days)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Ensured fiscal periods for {count} company(ies)."))

