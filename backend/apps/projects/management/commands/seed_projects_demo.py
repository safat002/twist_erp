from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.projects.models import Project, Task


class Command(BaseCommand):
    help = "Seed demo project with tasks (Phase 6/7 UAT)."

    def add_arguments(self, parser):
        parser.add_argument('--company-id', type=int, required=True)

    def handle(self, *args, **options):
        company_id = options['company_id']

        start = date.today().replace(day=1)
        proj, created = Project.objects.get_or_create(
            company_id=company_id,
            name="Demo Project A",
            defaults={
                'start_date': start,
                'end_date': start + timedelta(days=60),
            }
        )

        base = proj.start_date
        tasks = [
            ("Initiation", 0, 7, None),
            ("Planning", 7, 14, None),
            ("Execution", 21, 21, "Planning"),
            ("Monitoring", 21, 30, "Execution"),
            ("Closure", 52, 8, "Execution"),
        ]
        name_to_task = {}
        for name, offset, duration, dep in tasks:
            depends = name_to_task.get(dep)
            t, _ = Task.objects.get_or_create(
                project=proj,
                name=name,
                defaults={
                    'start_date': base + timedelta(days=offset),
                    'end_date': base + timedelta(days=offset+duration),
                    'depends_on': depends,
                }
            )
            name_to_task[name] = t

        self.stdout.write(self.style.SUCCESS(f"Seeded project '{proj.name}' (company={company_id})."))

