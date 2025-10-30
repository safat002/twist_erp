from django.apps import AppConfig

class HRConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.hr'
    verbose_name = 'Human Resources & Payroll'
    
    def ready(self):
        import apps.hr.signals