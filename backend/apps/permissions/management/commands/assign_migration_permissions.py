from django.core.management.base import BaseCommand, CommandParser

from apps.permissions.models import Permission, Role
from apps.companies.models import Company


class Command(BaseCommand):
    help = "Assign data migration permissions to a role (optionally company-scoped)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--role-name', type=str, required=True, help='Role name')
        parser.add_argument('--company-id', type=int, help='Company ID for company-specific role (omit for global role)')
        parser.add_argument('--importer', action='store_true', help='Grant data_migration.importer')
        parser.add_argument('--approver', action='store_true', help='Grant data_migration.approver')

    def handle(self, *args, **options):
        role_name = options['role_name']
        company_id = options.get('company_id')
        want_importer = options.get('importer')
        want_approver = options.get('approver')

        company = None
        if company_id:
            try:
                company = Company.objects.get(pk=company_id)
            except Company.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Company {company_id} not found"))
                return

        role, _ = Role.objects.get_or_create(name=role_name, company=company)
        perms_to_add = []
        if want_importer:
            perm = Permission.objects.filter(code='data_migration.importer').first()
            if perm:
                perms_to_add.append(perm)
        if want_approver:
            perm = Permission.objects.filter(code='data_migration.approver').first()
            if perm:
                perms_to_add.append(perm)

        if not perms_to_add:
            self.stderr.write(self.style.WARNING('No permissions selected or permissions not found.'))
            return

        role.permissions.add(*perms_to_add)
        self.stdout.write(self.style.SUCCESS(
            f"Assigned {[p.code for p in perms_to_add]} to role '{role_name}'"
        ))

