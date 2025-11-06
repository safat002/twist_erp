from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.companies.models import Company
from apps.finance.models import FiscalPeriod, FiscalPeriodStatus


class Command(BaseCommand):
    help = "Create current month FiscalPeriod rows for one or all companies if missing."

    def add_arguments(self, parser):
        parser.add_argument("--company-id", type=int, help="Company ID to seed. If omitted, seed all companies.")

    def handle(self, *args, **options):
        company_id = options.get("company_id")
        today = timezone.now().date()
        period_code = today.strftime("%Y-%m")

        if company_id:
            companies = Company.objects.filter(pk=company_id)
        else:
            companies = Company.objects.all()

        created = 0
        for company in companies:
            obj, was_created = FiscalPeriod.objects.get_or_create(
                company=company,
                company_group=company.company_group,
                period=period_code,
                defaults={"status": FiscalPeriodStatus.OPEN},
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created OPEN FiscalPeriod {obj.period} for {company.code}"))
            else:
                self.stdout.write(f"FiscalPeriod {period_code} already exists for {company.code} (status={obj.status}).")

        self.stdout.write(self.style.NOTICE(f"Done. Created {created} period(s)."))

