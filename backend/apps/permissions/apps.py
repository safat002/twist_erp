from django.apps import AppConfig


class PermissionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.permissions'
    verbose_name = 'Permissions & Roles'

    def ready(self):
        # Ensure signal handlers are registered
        from . import signals  # noqa: F401

