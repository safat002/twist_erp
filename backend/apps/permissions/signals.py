from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.apps import apps as django_apps
from django.core.management import call_command


@receiver(post_migrate)
def seed_defaults_after_migrate(sender, app_config, **kwargs):
    """Seed global default permissions and roles after migrations.

    Idempotent: safe to run multiple times.
    """
    try:
        # Only run once after the permissions app (or core) migrates
        if not app_config or app_config.label not in {
            'permissions', 'companies', 'finance', 'inventory', 'procurement', 'budgeting', 'workflows', 'data_migration'
        }:
            return
        # Ensure models are ready
        django_apps.get_model('permissions', 'Permission')
        django_apps.get_model('permissions', 'Role')
        # Seed global roles
        call_command('seed_default_roles')
    except Exception:
        # Soft-fail: never block migrations
        return

