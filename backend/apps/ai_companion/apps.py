import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AICompanionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai_companion'
    verbose_name = 'AI Companion'

    def ready(self):
        import apps.ai_companion.signals  # noqa: F401
        try:
            from apps.ai_companion.services import orchestrator  # noqa: F401
            logger.debug("AI orchestrator bootstrapped.")
        except Exception as exc:  # pragma: no cover - safe guard for optional deps
            logger.warning("AI orchestrator initialisation deferred: %s", exc)
