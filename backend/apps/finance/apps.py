from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.finance'

    def ready(self):
        # Subscribe finance handlers to shared event bus (stock receipts/issues)
        try:
            from .event_handlers import subscribe_to_events
            subscribe_to_events()
        except Exception:
            # Avoid crashing app startup if optional subscriptions fail
            pass
