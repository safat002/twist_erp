from django.apps import AppConfig

class DataMigrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.data_migration'
    verbose_name = 'Data Migration'

    def ready(self):
        import apps.data_migration.signals
