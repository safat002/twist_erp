import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="apps.assets.tasks.calculate_monthly_depreciation")
def calculate_monthly_depreciation():
    """Placeholder depreciation calculation.

    Implement actual depreciation posting when Asset models exist.
    """
    try:
        from .models import DepreciationRun
        from apps.companies.models import Company

        logger.info("Assets: Running monthly depreciation calculation")
        today = timezone.now()
        year, month = today.year, today.month
        results = []
        for company in Company.objects.filter(is_active=True):
            run = DepreciationRun.run_for_month(company=company, year=year, month=month)
            results.append({"company": company.code, "period": run.period, "amount": float(run.total_amount)})
        return {"status": "ok", "runs": results}
    except Exception as exc:
        logger.exception("Assets depreciation job failed: %s", exc)
        return {"status": "error", "error": str(exc)}
