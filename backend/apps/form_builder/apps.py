import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)

class FormBuilderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.form_builder'
    verbose_name = 'Form & Module Builder'
    
    def ready(self):
        try:
            from .services.dynamic_entities import register_all_entities
            register_all_entities()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Dynamic entity registration skipped: %s", exc)
        import apps.form_builder.signals
