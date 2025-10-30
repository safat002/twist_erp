from django.apps import AppConfig

class WorkflowsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.workflows'
    verbose_name = 'Workflow Automation'
    
    def ready(self):
        """
        This method is called when the app is ready. We register our event
        listeners here to ensure they are connected at startup.
        """
        from . import listeners
        listeners.register_workflow_listeners()