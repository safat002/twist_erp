from django.core.management.base import BaseCommand
from django.db import transaction
from apps.companies.models import Company, CompanyGroup
from apps.users.models import User
from apps.admin_settings.models import ModuleFeatureToggle
from apps.admin_settings.default_features import DEFAULT_FEATURES


class Command(BaseCommand):
    help = 'Create default feature toggles for the system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scope',
            type=str,
            default='GLOBAL',
            choices=['GLOBAL', 'GROUP', 'COMPANY'],
            help='Scope type for feature toggles (default: GLOBAL)'
        )
        parser.add_argument(
            '--company-group-id',
            type=int,
            help='Company group ID (required if scope=GROUP)'
        )
        parser.add_argument(
            '--company-id',
            type=int,
            help='Company ID (required if scope=COMPANY)'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing feature toggles'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        scope_type = options['scope']
        company_group_id = options.get('company_group_id')
        company_id = options.get('company_id')
        overwrite = options.get('overwrite', False)

        # Validate scope requirements
        if scope_type == 'GROUP' and not company_group_id:
            self.stdout.write(self.style.ERROR(
                'Company group ID is required when scope=GROUP'
            ))
            return

        if scope_type == 'COMPANY' and not company_id:
            self.stdout.write(self.style.ERROR(
                'Company ID is required when scope=COMPANY'
            ))
            return

        # Get company group and company if specified
        company_group = None
        company = None

        if company_group_id:
            try:
                company_group = CompanyGroup.objects.get(id=company_group_id)
            except CompanyGroup.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f'Company group with ID {company_group_id} not found'
                ))
                return

        if company_id:
            try:
                company = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f'Company with ID {company_id} not found'
                ))
                return

        # Get first superuser for created_by field
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
        except User.DoesNotExist:
            admin_user = None

        # Create feature toggles
        created_count = 0
        updated_count = 0
        skipped_count = 0

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\nCreating default feature toggles with scope: {scope_type}'
        ))

        for feature_data in DEFAULT_FEATURES:
            defaults = {
                'feature_name': feature_data['name'],
                'description': feature_data.get('description', ''),
                'help_text': feature_data.get('help_text', ''),
                'icon': feature_data.get('icon', ''),
                'is_enabled': feature_data.get('enabled', True),
                'is_visible': feature_data.get('visible', True),
                'status': feature_data.get('status', 'enabled'),
                'depends_on': feature_data.get('depends_on', []),
                'priority': feature_data.get('priority', 0),
                'config': feature_data.get('config', {}),
                'scope_type': scope_type,
                'company_group': company_group,
                'company': company,
                'created_by': admin_user,
                'updated_by': admin_user,
            }

            lookup = {
                'module_name': feature_data['module'],
                'feature_key': feature_data['key'],
                'scope_type': scope_type,
            }

            if scope_type == 'GROUP':
                lookup['company_group'] = company_group
            elif scope_type == 'COMPANY':
                lookup['company'] = company

            try:
                if overwrite:
                    obj, created = ModuleFeatureToggle.objects.update_or_create(
                        **lookup,
                        defaults=defaults
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(
                            f'  [+] Created: {obj.full_key}'
                        ))
                    else:
                        updated_count += 1
                        self.stdout.write(self.style.WARNING(
                            f'  [~] Updated: {obj.full_key}'
                        ))
                else:
                    obj, created = ModuleFeatureToggle.objects.get_or_create(
                        **lookup,
                        defaults=defaults
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(
                            f'  [+] Created: {obj.full_key}'
                        ))
                    else:
                        skipped_count += 1
                        self.stdout.write(
                            f'  [-] Skipped: {obj.full_key} (already exists)'
                        )

            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'  [!] Error creating {feature_data["module"]}.{feature_data["key"]}: {str(e)}'
                ))

        # Summary
        self.stdout.write(self.style.MIGRATE_HEADING('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS(
            f'\nSummary:\n'
            f'  Created: {created_count}\n'
            f'  Updated: {updated_count}\n'
            f'  Skipped: {skipped_count}\n'
            f'  Total: {len(DEFAULT_FEATURES)}\n'
        ))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60 + '\n'))

        if created_count > 0 or updated_count > 0:
            self.stdout.write(self.style.SUCCESS(
                '\n[OK] Feature toggles created successfully!\n'
                '\nYou can now manage them in the Django admin:\n'
                '  Admin > Admin Settings > Feature Toggles\n'
            ))
