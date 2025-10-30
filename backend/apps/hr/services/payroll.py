from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.finance.models import Account, Journal
from apps.finance.services.journal_service import JournalService

from ..models import (
    OvertimeEntry,
    OvertimeRequestStatus,

    Attendance,
    AttendanceStatus,
    Employee,
    EmployeeStatus,
    LeaveRequest,
    LeaveRequestStatus,
    PayrollLine,
    PayrollRun,
    PayrollRunStatus,
)


class PayrollService:
    @staticmethod
    def _quantize(value) -> Decimal:
        value = value or Decimal("0.00")
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _calculate_period_label(period_start: date, period_end: date, period_label: str | None) -> str:
        if period_label:
            return period_label
        if period_start.month == period_end.month and period_start.year == period_end.year:
            return period_start.strftime("%B %Y")
        return f"{period_start.strftime('%d %b %Y')} - {period_end.strftime('%d %b %Y')}"

    @staticmethod
    def _resolve_account(account_or_id, company):
        if not account_or_id:
            return None
        if isinstance(account_or_id, Account):
            if account_or_id.company_id != company.id:
                raise ValueError("Account belongs to a different company.")
            return account_or_id
        return Account.objects.get(pk=account_or_id, company=company)

    @staticmethod
    def _collect_attendance(company, employees, period_start, period_end):
        data = defaultdict(lambda: {"present": Decimal("0.00"), "leave": Decimal("0.00"), "overtime": Decimal("0.00")})
        attendance_qs = (
            Attendance.objects.filter(
                company=company,
                employee__in=employees,
                date__gte=period_start,
                date__lte=period_end,
            )
            .select_related("employee")
        )
        for record in attendance_qs:
            key = record.employee_id
            if record.status in {AttendanceStatus.PRESENT, AttendanceStatus.REMOTE}:
                data[key]["present"] += Decimal("1.0")
            elif record.status == AttendanceStatus.HALF_DAY:
                data[key]["present"] += Decimal("0.5")
            elif record.status == AttendanceStatus.LEAVE:
                data[key]["leave"] += Decimal("1.0")
            if record.overtime_hours:
                data[key]["overtime"] += record.overtime_hours
        return data

    @staticmethod
    def _collect_leave(company, employees, period_start, period_end):
        data = defaultdict(lambda: Decimal("0.00"))
        leave_qs = LeaveRequest.objects.filter(
            company=company,
            employee__in=employees,
            status=LeaveRequestStatus.APPROVED,
            end_date__gte=period_start,
            start_date__lte=period_end,
        )
        for request in leave_qs:
            effective_start = max(request.start_date, period_start)
            effective_end = min(request.end_date, period_end)
            span = (effective_end - effective_start).days + 1
            if span > 0:
                data[request.employee_id] += Decimal(str(span))
        return data

    @staticmethod
    def _collect_overtime(company, employees, period_start, period_end):
        data = defaultdict(
            lambda: {
                "hours": Decimal("0.00"),
                "amount": Decimal("0.00"),
                "entries": [],
            }
        )
        overtime_qs = (
            OvertimeEntry.objects.filter(
                company=company,
                employee__in=employees,
                status=OvertimeRequestStatus.APPROVED,
                posted_to_payroll=False,
                date__gte=period_start,
                date__lte=period_end,
            )
            .select_related("employee")
        )
        for entry in overtime_qs:
            summary = data[entry.employee_id]
            summary["hours"] += entry.effective_hours
            summary["amount"] += entry.amount
            summary["entries"].append(entry)
        return data

    @staticmethod
    def _ensure_payroll_journal(company, created_by):
        journal = Journal.objects.filter(company=company, code="PAYROLL").first()
        if journal:
            return journal
        return Journal.objects.create(
            company=company,
            code="PAYROLL",
            name="Payroll Journal",
            type="GENERAL",
            created_by=created_by,
        )

    @staticmethod
    @transaction.atomic
    def generate_payroll_run(
        *,
        company,
        period_start: date,
        period_end: date,
        period_label: str | None = "",
        notes: str = "",
        expense_account=None,
        liability_account=None,
        created_by=None,
    ) -> PayrollRun:
        if period_start > period_end:
            raise ValueError("Payroll period start must be on or before the period end date.")

        existing = (
            PayrollRun.objects.filter(
                company=company,
                period_start=period_start,
                period_end=period_end,
            )
            .exclude(status=PayrollRunStatus.CANCELLED)
            .first()
        )
        if existing:
            raise ValueError("A payroll run already exists for the selected period.")

        label = PayrollService._calculate_period_label(period_start, period_end, period_label or "")
        expense_account = PayrollService._resolve_account(expense_account, company) if expense_account else None
        liability_account = PayrollService._resolve_account(liability_account, company) if liability_account else None

        employees_qs = (
            Employee.objects.select_related("salary_structure", "department")
            .filter(company=company, is_active=True)
            .filter(Q(date_of_joining__isnull=True) | Q(date_of_joining__lte=period_end))
            .filter(Q(date_of_exit__isnull=True) | Q(date_of_exit__gte=period_start))
            .exclude(status__in=[EmployeeStatus.TERMINATED, EmployeeStatus.RESIGNED])
        )
        employees = list(employees_qs)

        run = PayrollRun.objects.create(
            company=company,
            period_start=period_start,
            period_end=period_end,
            period_label=label,
            notes=notes,
            expense_account=expense_account,
            liability_account=liability_account,
            generated_by=created_by,
            generated_at=timezone.now(),
            status=PayrollRunStatus.COMPUTED,
        )

        attendance_data = PayrollService._collect_attendance(company, employees, period_start, period_end)
        leave_data = PayrollService._collect_leave(company, employees, period_start, period_end)

        total_days = Decimal(str((period_end - period_start).days + 1))
        lines = []

        for employee in employees:
            structure = employee.salary_structure
            if structure:
                base_salary = structure.base_salary or Decimal("0.00")
                allowance_fixed = (
                    (structure.housing_allowance or Decimal("0.00"))
                    + (structure.transport_allowance or Decimal("0.00"))
                    + (structure.meal_allowance or Decimal("0.00"))
                    + (structure.other_allowance or Decimal("0.00"))
                )
                overtime_rate = structure.overtime_rate or Decimal("0.00")
                tax_rate = structure.tax_rate or Decimal("0.00")
                pension_rate = structure.pension_rate or Decimal("0.00")
            else:
                base_salary = Decimal("0.00")
                allowance_fixed = Decimal("0.00")
                overtime_rate = Decimal("0.00")
                tax_rate = Decimal("0.00")
                pension_rate = Decimal("0.00")

            attendance_summary = attendance_data.get(employee.id, {})
            overtime_summary = overtime_data.get(employee.id)
            present_days = PayrollService._quantize(attendance_summary.get("present", Decimal("0.00")))
            recorded_leave_days = PayrollService._quantize(attendance_summary.get("leave", Decimal("0.00")))
            approved_leave_days = PayrollService._quantize(leave_data.get(employee.id, Decimal("0.00")))

            if overtime_summary:
                overtime_hours = PayrollService._quantize(overtime_summary["hours"])
                overtime_pay = PayrollService._quantize(overtime_summary["amount"])
                overtime_entry_ids = [entry.id for entry in overtime_summary["entries"]]
            else:
                overtime_hours = PayrollService._quantize(attendance_summary.get("overtime", Decimal("0.00")))
                overtime_pay = PayrollService._quantize(overtime_hours * overtime_rate)
                overtime_entry_ids = []

            leave_days = max(recorded_leave_days, approved_leave_days)
            paid_days = min(present_days + leave_days, total_days) if total_days else Decimal("0.00")
            attendance_ratio = ((paid_days / total_days).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if total_days else Decimal("0.00"))

            base_pay = PayrollService._quantize(base_salary * attendance_ratio)
            allowance_total = PayrollService._quantize(allowance_fixed * attendance_ratio)

            gross_pay = PayrollService._quantize(base_pay + allowance_total + overtime_pay)
            tax_amount = PayrollService._quantize(gross_pay * (Decimal(str(tax_rate)) / Decimal("100")) if tax_rate else Decimal("0"))
            pension_amount = PayrollService._quantize(gross_pay * (Decimal(str(pension_rate)) / Decimal("100")) if pension_rate else Decimal("0"))
            deduction_total = PayrollService._quantize(tax_amount + pension_amount)
            net_pay = PayrollService._quantize(gross_pay - deduction_total)

            line = PayrollLine(
                payroll_run=run,
                employee=employee,
                company=company,
                created_by=created_by,
                attendance_days=present_days,
                leave_days=leave_days,
                base_pay=base_pay,
                allowance_total=allowance_total,
                overtime_hours=overtime_hours,
                overtime_pay=overtime_pay,
                gross_pay=gross_pay,
                deduction_total=deduction_total,
                net_pay=net_pay,
                remarks="" if structure else "No salary structure linked",
                details={
                    "attendance_ratio": float(attendance_ratio),
                    "tax_amount": str(tax_amount),
                    "pension_amount": str(pension_amount),
                    "paid_days": str(paid_days),
                    "total_days": str(total_days),
                    "overtime_entry_ids": overtime_entry_ids,
                },
            )
            lines.append(line)

        if lines:
            PayrollLine.objects.bulk_create(lines)
            for summary in overtime_data.values():
                for entry in summary.get("entries", []):
                    entry.mark_posted(run)

        run.recalculate_totals(save=True)
        return run

    @staticmethod
    @transaction.atomic
    def finalize_run(
        *,
        run: PayrollRun,
        posted_by=None,
        expense_account=None,
        liability_account=None,
        post_to_finance: bool = True,
    ) -> PayrollRun:
        run = (
            PayrollRun.objects.select_for_update()
            .select_related("expense_account", "liability_account")
            .get(pk=run.pk)
        )

        if run.status == PayrollRunStatus.POSTED:
            return run
        if run.status == PayrollRunStatus.CANCELLED:
            raise ValueError("Cancelled payroll runs cannot be finalised.")

        if expense_account:
            run.expense_account = PayrollService._resolve_account(expense_account, run.company)
        if liability_account:
            run.liability_account = PayrollService._resolve_account(liability_account, run.company)

        run.recalculate_totals(save=True)

        if post_to_finance:
            if not run.expense_account or not run.liability_account:
                raise ValueError("Expense and liability accounts are required to post payroll.")
            voucher = PayrollService._post_to_finance(run=run, posted_by=posted_by)
            run.mark_posted(voucher)
        else:
            run.status = PayrollRunStatus.APPROVED
            run.save(update_fields=["status", "updated_at"])

        return run

    @staticmethod
    def _post_to_finance(*, run: PayrollRun, posted_by):
        journal = PayrollService._ensure_payroll_journal(run.company, posted_by)

        entries_data = [
            {
                "account": run.expense_account,
                "debit": run.gross_total,
                "description": f"Payroll expense: {run.label}",
            },
            {
                "account": run.liability_account,
                "credit": run.gross_total,
                "description": f"Payroll payable: {run.label}",
            },
        ]

        voucher = JournalService.create_journal_voucher(
            journal=journal,
            entry_date=run.period_end,
            description=f"Payroll for {run.label}",
            entries_data=entries_data,
            reference=f"PAYROLL-{run.pk}",
            source_document_type="hr.PayrollRun",
            source_document_id=run.pk,
            company=run.company,
            created_by=run.generated_by or posted_by,
        )
        JournalService.post_journal_voucher(voucher, posted_by or run.generated_by)
        return voucher



