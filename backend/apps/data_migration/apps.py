from django.apps import AppConfig

class DataMigrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.data_migration'
    verbose_name = 'Data Migration'

    def ready(self):
        from .services.pipeline import MigrationPipeline

        try:
            MigrationPipeline.ensure_permissions()
        except Exception:
            # During migrations or app loading we ignore permission bootstrap errors.
            pass
