from __future__ import annotations

from datetime import date, timedelta
from django.utils import timezone

from apps.finance.models import FiscalPeriod
from apps.notifications.models import Notification
from apps.users.models import UserCompanyRole
from apps.permissions.models import Permission


def _month_end(d: date) -> date:
    if d.month == 12:
        return date(d.year, 12, 31)
    first_next = date(d.year + (1 if d.month == 12 else 0), (d.month % 12) + 1, 1)
    return first_next - timedelta(days=1)


def _period_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _finance_recipients(company):
    try:
        owner_perm = Permission.objects.filter(code='finance_close_period').first()
    except Exception:
        owner_perm = None
    try:
        sub_perm = Permission.objects.filter(code='finance_manage_coa').first()
    except Exception:
        sub_perm = None
    user_ids = set()
    if owner_perm:
        for u in UserCompanyRole.objects.filter(company=company, is_active=True, role__permissions=owner_perm).values_list('user_id', flat=True):
            user_ids.add(u)
    if sub_perm:
        for u in UserCompanyRole.objects.filter(company=company, is_active=True, role__permissions=sub_perm).values_list('user_id', flat=True):
            user_ids.add(u)
    # Fallback to company admin if defined
    if getattr(company, 'company_admin_user_id', None):
        user_ids.add(company.company_admin_user_id)
    return list(user_ids)


def _notify(company, title: str, body: str, severity: str = 'info'):
    try:
        recipients = _finance_recipients(company)
        for uid in recipients:
            Notification.objects.create(
                company=company,
                company_group=company.company_group,
                user_id=uid,
                title=title,
                body=body,
                severity=severity,
            )
    except Exception:
        # Soft-fail notifications
        return


def ensure_upcoming_periods(company, days_threshold: int = 15) -> None:
    """
    Ensure monthly fiscal periods exist for the active company.
    - Creates the current month period if missing
    - If within `days_threshold` days of the month end, pre-creates next month
    """
    today = timezone.now().date()
    current_key = _period_key(today)
    current, created_current = FiscalPeriod.objects.get_or_create(
        company=company,
        company_group=company.company_group,
        period=current_key,
        defaults={"status": "OPEN", "notes": "AUTO"},
    )
    if created_current:
        _notify(company, f"Fiscal period {current_key} created", f"Auto-created current fiscal period {current_key}.")

    # Pre-create next month within threshold
    days_left = (_month_end(today) - today).days
    if days_left <= days_threshold:
        # Compute first day of next month
        if today.month == 12:
            next_month = date(today.year + 1, 1, 1)
        else:
            next_month = date(today.year, today.month + 1, 1)
        next_key = _period_key(next_month)
        nxt, created_next = FiscalPeriod.objects.get_or_create(
            company=company,
            company_group=company.company_group,
            period=next_key,
            defaults={"status": "OPEN", "notes": "AUTO"},
        )
        if created_next:
            _notify(company, f"Fiscal period {next_key} pre-created", f"Auto-created next fiscal period {next_key} (within {days_threshold} days of month end).")
