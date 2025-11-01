from django.apps import AppConfig

class SecurityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.security'
    verbose_name = 'Security & Access Control'

    def ready(self):
        import apps.security.permissions # This will register SECURITY_PERMISSIONS
        import apps.finance.permissions
        import apps.inventory.permissions
        import apps.sales.permissions
        import apps.procurement.permissions
        import apps.assets.permissions
        import apps.budgeting.permissions
        import apps.production.permissions
        import apps.hr.permissions
        import apps.projects.permissions
        import apps.ai_companion.permissions

        # Import signals
        import apps.security.signals
