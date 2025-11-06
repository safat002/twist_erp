from django.apps import AppConfig


class AdminSettingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.admin_settings'
    verbose_name = 'Admin Settings'

    def ready(self):
        """Import signals when app is ready."""
        try:
            import apps.admin_settings.signals  # noqa
        except ImportError:
            pass
