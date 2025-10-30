import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import PayrollRun, PayrollRunStatus

logger = logging.getLogger(__name__)


@shared_task(name="apps.hr.tasks.send_payroll_reminders")
def send_payroll_reminders():
    """Notify stakeholders about payroll runs that need attention."""
    try:
        today = timezone.localdate()
        window_end = today + timedelta(days=5)

        pending_runs = PayrollRun.objects.filter(
            status__in=[PayrollRunStatus.DRAFT, PayrollRunStatus.COMPUTED],
            period_end__lte=window_end,
        )
        message = f"{pending_runs.count()} payroll run(s) awaiting approval before {window_end:%d %b %Y}."

        logger.info("HR: Payroll reminder summary - %s", message)

        return {
            "status": "ok",
            "message": message,
            "runs": [
                {
                    "id": run.id,
                    "company": run.company.code,
                    "period": run.label,
                    "status": run.status,
                    "period_end": run.period_end.isoformat(),
                }
                for run in pending_runs
            ],
        }
    except Exception as exc:
        logger.exception("Payroll reminder job failed: %s", exc)
        return {"status": "error", "error": str(exc)}
