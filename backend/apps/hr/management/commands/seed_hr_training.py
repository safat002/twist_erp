from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.hr.models import TrainingCategory, TrainingCourse


class Command(BaseCommand):
    help = "Seed baseline HR training categories and courses (Phase 7 UAT/training)."

    def add_arguments(self, parser):
        parser.add_argument('--company-id', type=int, help='Company ID to seed for')

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        if not company_id:
            self.stderr.write(self.style.ERROR('Please provide --company-id'))
            return

        # Categories
        categories = [
            ("COMPLIANCE", "Compliance & Safety"),
            ("HARASSMENT", "Anti-Harassment & Workplace Conduct"),
            ("DATASEC", "Data Security & Privacy"),
            ("FINANCE", "Finance Controls & SOX"),
        ]
        cat_objs = {}
        for code, name in categories:
            cat, _ = TrainingCategory.objects.get_or_create(
                company_id=company_id,
                code=code,
                defaults={"name": name, "description": f"{name} training"},
            )
            cat_objs[code] = cat

        # Courses
        courses = [
            ("SAFE-101", "Workplace Safety 101", "COMPLIANCE"),
            ("ANTIH-101", "Anti-Harassment Basics", "HARASSMENT"),
            ("GDPR-101", "Data Privacy & GDPR", "DATASEC"),
            ("FINC-CTRLS", "Finance Controls Overview", "FINANCE"),
        ]
        created = 0
        for code, name, cat_code in courses:
            course, is_new = TrainingCourse.objects.get_or_create(
                company_id=company_id,
                code=code,
                defaults={
                    "name": name,
                    "category": cat_objs.get(cat_code),
                    "is_mandatory": True,
                    "validity_days": 365,
                    "description": f"Mandatory training: {name}",
                },
            )
            if is_new:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded HR training (company={company_id}). New courses: {created}"))

