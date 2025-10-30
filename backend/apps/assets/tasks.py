import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="apps.assets.tasks.calculate_monthly_depreciation")
def calculate_monthly_depreciation():
    """Placeholder depreciation calculation.

    Implement actual depreciation posting when Asset models exist.
    """
    try:
        logger.info("Assets: Running monthly depreciation calculation")
        # TODO: Calculate and post depreciation journal entries
        return {"status": "ok", "message": "Depreciation calculation executed"}
    except Exception as exc:
        logger.exception("Assets depreciation job failed: %s", exc)
        return {"status": "error", "error": str(exc)}
