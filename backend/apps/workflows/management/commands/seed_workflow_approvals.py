from django.core.management.base import BaseCommand, CommandParser
from django.utils.text import slugify

from apps.companies.models import Company
from apps.workflows.models import WorkflowTemplate


class Command(BaseCommand):
    help = "Seed GRN and DO approval workflow templates (simple draft→submitted→approved)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--company-id', type=int, help='Target company ID (omit for global templates)')

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        company = None
        if company_id:
            try:
                company = Company.objects.get(pk=company_id)
            except Company.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Company {company_id} not found"))
                return

        def upsert(name: str):
            definition = {
                "states": ["draft", "submitted", "approved"],
                "initial": "draft",
                "transitions": {
                    "draft": ["submitted"],
                    "submitted": ["approved", "draft"],
                },
            }
            qs = WorkflowTemplate.objects
            if company:
                tpl, created = qs.update_or_create(
                    name=name,
                    company=company,
                    defaults={
                        'definition': definition,
                        'scope_type': 'COMPANY',
                        'status': 'active',
                        'version': 1,
                        'slug': slugify(name),
                    },
                )
            else:
                tpl, created = qs.update_or_create(
                    name=name,
                    company__isnull=True,
                    defaults={
                        'definition': definition,
                        'scope_type': 'GLOBAL',
                        'status': 'active',
                        'version': 1,
                        'slug': slugify(name),
                    },
                )
            return tpl, created

        made = []
        for n in ("GRN Approval", "DO Approval"):
            tpl, created = upsert(n)
            made.append((n, created))

        for name, created in made:
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created workflow template: {name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Updated workflow template: {name}"))

