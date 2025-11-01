from django.core.management.base import BaseCommand
from apps.security.models import SecPermission
from apps.security.permission_registry import ALL_PERMISSIONS

class Command(BaseCommand):
    help = 'Synchronizes declared permissions with the database.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting permission synchronization...'))

        # Get existing permission codes from the database
        existing_permission_codes = set(SecPermission.objects.values_list('code', flat=True))

        # Track permissions that are still declared
        declared_permission_codes = set()

        for perm_data in ALL_PERMISSIONS:
            code = perm_data['code']
            declared_permission_codes.add(code)

            defaults = {
                'description': perm_data.get('description', ''),
                'category': perm_data.get('category', 'general'),
                'scope_required': perm_data.get('scope_required', False),
                'is_sensitive': perm_data.get('is_sensitive', False),
                'is_assignable': perm_data.get('is_assignable', True),
            }

            obj, created = SecPermission.objects.update_or_create(
                code=code,
                defaults=defaults
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'Created permission: {code}'))
            else:
                self.stdout.write(self.style.MIGRATE_HEADING(f'Updated permission: {code}'))
        
        # Delete permissions that are no longer declared in code
        permissions_to_delete = existing_permission_codes - declared_permission_codes
        if permissions_to_delete:
            SecPermission.objects.filter(code__in=permissions_to_delete).delete()
            for code in permissions_to_delete:
                self.stdout.write(self.style.WARNING(f'Deleted obsolete permission: {code}'))
        
        self.stdout.write(self.style.SUCCESS('Permission synchronization complete.'))
