"""
Django app configuration for companies app.
"""
from django.apps import AppConfig


class CompaniesConfig(AppConfig):
    """Configuration for companies app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.companies'
    verbose_name = 'Companies'

    def ready(self):
        """Import signals when app is ready."""
        import apps.companies.signals  # noqa: F401
