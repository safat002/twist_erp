from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.assets.models import Asset


class Command(BaseCommand):
    help = "Seed demo fixed assets (Phase 6/7 UAT)."

    def add_arguments(self, parser):
        parser.add_argument('--company-id', type=int, required=True)

    def handle(self, *args, **options):
        company_id = options['company_id']
        today = date.today()
        demo = [
            ("LAP-1001", "Laptop - Developer", 1500.0, 36, Asset.METHOD_SL),
            ("PRN-2001", "Laser Printer", 800.0, 48, Asset.METHOD_DB),
            ("GEN-3001", "Backup Generator", 4500.0, 60, Asset.METHOD_SL),
        ]
        created = 0
        for code, name, cost, life, method in demo:
            _, is_new = Asset.objects.get_or_create(
                company_id=company_id,
                code=code,
                defaults={
                    'name': name,
                    'acquisition_date': today - timedelta(days=120),
                    'cost': cost,
                    'residual_value': 0,
                    'depreciation_method': method,
                    'useful_life_months': life,
                    'status': Asset.STATUS_ACTIVE,
                }
            )
            if is_new:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} demo assets (company={company_id})."))

