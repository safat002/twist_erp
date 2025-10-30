
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, F, Q, Sum, Case, When, DecimalField
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.budgeting.models import BudgetUsage

from .models import (
    Attendance,
    AttendanceStatus,
    CapacityPlanScenario,
    Department,
    Employee,
    EmployeeLeaveBalance,
    EmployeeStatus,
    EmploymentGrade,
    LeaveRequest,
    LeaveRequestStatus,
    LeaveType,
    OvertimeEntry,
    OvertimePolicy,
    OvertimeRequestStatus,
    PayrollRun,
    PayrollRunStatus,
    SalaryStructure,
    ShiftAssignment,
    ShiftTemplate,
    WorkforceCapacityPlan,
)
from .serializers import (
    AttendanceSerializer,
    DepartmentSerializer,
    EmployeeLeaveBalanceSerializer,
    EmployeeSerializer,
    EmploymentGradeSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
    OvertimeApproveSerializer,
    OvertimeEntrySerializer,
    OvertimePolicySerializer,
    OvertimeRejectSerializer,
    PayrollFinalizeSerializer,
    PayrollRunSerializer,
    SalaryStructureSerializer,
    ShiftAssignmentSerializer,
    ShiftTemplateSerializer,
    WorkforceCapacityPlanSerializer,
)
from .services.payroll import PayrollService


def _ensure_company(request):
    company = getattr(request, "company", None)
    if not company:
        raise ValidationError("Active company context is required for HR operations.")
    return company


class CompanyScopedModelViewSet(viewsets.ModelViewSet):
    """Base viewset scoping all queries to the active company."""

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        queryset = super().get_queryset()
        if company is None:
            return queryset.none()
        return queryset.filter(company=company)

    def perform_create(self, serializer):
        _ensure_company(self.request)
        serializer.save()

    def perform_update(self, serializer):
        _ensure_company(self.request)
        serializer.save()


class DepartmentViewSet(CompanyScopedModelViewSet):
    queryset = Department.objects.select_related("head")
    serializer_class = DepartmentSerializer


class EmploymentGradeViewSet(CompanyScopedModelViewSet):
    queryset = EmploymentGrade.objects.all()
    serializer_class = EmploymentGradeSerializer


class SalaryStructureViewSet(CompanyScopedModelViewSet):
    queryset = SalaryStructure.objects.all()
    serializer_class = SalaryStructureSerializer


class ShiftTemplateViewSet(CompanyScopedModelViewSet):
    queryset = ShiftTemplate.objects.select_related("default_overtime_policy")
    serializer_class = ShiftTemplateSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        include_inactive = self.request.query_params.get("include_inactive")
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        return queryset.order_by("start_time")


class ShiftAssignmentViewSet(CompanyScopedModelViewSet):
    queryset = ShiftAssignment.objects.select_related(
        "employee",
        "shift",
        "overtime_policy",
        "cost_center",
    )
    serializer_class = ShiftAssignmentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        employee_id = params.get("employee")
        shift_id = params.get("shift")
        raw_date = params.get("date")
        target_date = parse_date(raw_date) if raw_date else None
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        if shift_id:
            queryset = queryset.filter(shift_id=shift_id)
        if target_date:
            queryset = queryset.filter(
                effective_from__lte=target_date,
            ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=target_date))
        return queryset.order_by("-effective_from")

    @action(detail=False, methods=["get"], url_path="active")
    def list_active(self, request):
        company = _ensure_company(request)
        raw_date = request.query_params.get("date")
        target_date = parse_date(raw_date) if raw_date else timezone.localdate()
        if target_date is None:
            target_date = timezone.localdate()
        assignments = (
            self.get_queryset()
            .filter(
                company=company,
                effective_from__lte=target_date,
            )
            .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=target_date))
        )
        page = self.paginate_queryset(assignments)
        serializer = self.get_serializer(page or assignments, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class EmployeeViewSet(CompanyScopedModelViewSet):
    queryset = (
        Employee.objects.select_related(
            "department",
            "grade",
            "manager",
            "salary_structure",
            "cost_center",
        )
    )
    serializer_class = EmployeeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        status_param = params.get("status")
        department = params.get("department")
        search = params.get("search")
        if status_param:
            queryset = queryset.filter(status=status_param)
        if department:
            queryset = queryset.filter(department_id=department)
        if search:
            queryset = queryset.filter(
                Q(employee_id__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )
        return queryset.order_by("employee_id")


class AttendanceViewSet(CompanyScopedModelViewSet):
    queryset = Attendance.objects.select_related("employee", "shift")
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        start_date = parse_date(params.get("start_date")) if params.get("start_date") else None
        end_date = parse_date(params.get("end_date")) if params.get("end_date") else None
        employee = params.get("employee")
        status_param = params.get("status")
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        if employee:
            queryset = queryset.filter(employee_id=employee)
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset.order_by("-date", "employee__employee_id")


class LeaveTypeViewSet(CompanyScopedModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer


class EmployeeLeaveBalanceViewSet(CompanyScopedModelViewSet):
    queryset = EmployeeLeaveBalance.objects.select_related("employee", "leave_type")
    serializer_class = EmployeeLeaveBalanceSerializer


class LeaveRequestViewSet(CompanyScopedModelViewSet):
    queryset = LeaveRequest.objects.select_related("employee", "leave_type", "approved_by")
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        status_param = params.get("status")
        employee = params.get("employee")
        if status_param:
            queryset = queryset.filter(status=status_param)
        if employee:
            queryset = queryset.filter(employee_id=employee)
        return queryset.order_by("-created_at")

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        record = self.get_object()
        if record.status != LeaveRequestStatus.SUBMITTED:
            raise ValidationError("Only submitted leave requests can be approved.")
        record.status = LeaveRequestStatus.APPROVED
        record.approved_by = getattr(request, "user", None)
        record.approved_at = timezone.now()
        record.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return Response(self.get_serializer(record).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        record = self.get_object()
        if record.status != LeaveRequestStatus.SUBMITTED:
            raise ValidationError("Only submitted leave requests can be rejected.")
        record.status = LeaveRequestStatus.REJECTED
        record.approved_by = getattr(request, "user", None)
        record.approved_at = timezone.now()
        record.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return Response(self.get_serializer(record).data, status=status.HTTP_200_OK)

class OvertimePolicyViewSet(CompanyScopedModelViewSet):
    queryset = OvertimePolicy.objects.select_related("department", "grade", "default_budget_line")
    serializer_class = OvertimePolicySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        active_only = params.get("active", "true").lower() in {"true", "1", "yes"}
        department = params.get("department")
        grade = params.get("grade")
        if active_only:
            queryset = queryset.filter(is_active=True)
        if department:
            queryset = queryset.filter(department_id=department)
        if grade:
            queryset = queryset.filter(grade_id=grade)
        return queryset.order_by("name")


class OvertimeEntryViewSet(CompanyScopedModelViewSet):
    queryset = OvertimeEntry.objects.select_related(
        "employee",
        "employee__department",
        "shift",
        "policy",
        "cost_center",
        "budget_line",
        "approved_by",
        "payroll_run",
    )
    serializer_class = OvertimeEntrySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        status_param = params.get("status")
        employee = params.get("employee")
        start_raw = params.get("start")
        end_raw = params.get("end")
        posted = params.get("posted")
        if status_param:
            queryset = queryset.filter(status=status_param)
        if employee:
            queryset = queryset.filter(employee_id=employee)
        if start_raw:
            start_date = parse_date(start_raw)
            if start_date:
                queryset = queryset.filter(date__gte=start_date)
        if end_raw:
            end_date = parse_date(end_raw)
            if end_date:
                queryset = queryset.filter(date__lte=end_date)
        if posted is not None:
            if posted.lower() in {"true", "1", "yes"}:
                queryset = queryset.filter(posted_to_payroll=True)
            else:
                queryset = queryset.filter(posted_to_payroll=False)
        return queryset.order_by("-date", "-created_at")

    def update(self, request, *args, **kwargs):
        entry = self.get_object()
        if entry.posted_to_payroll:
            raise ValidationError("Posted overtime entries cannot be modified.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        entry = self.get_object()
        if entry.posted_to_payroll:
            raise ValidationError("Posted overtime entries cannot be deleted.")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        entry = self.get_object()
        if entry.status not in {OvertimeRequestStatus.DRAFT, OvertimeRequestStatus.REJECTED}:
            raise ValidationError("Only draft or rejected entries can be submitted.")
        entry.status = OvertimeRequestStatus.SUBMITTED
        entry.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(entry).data)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve_entry(self, request, pk=None):
        entry = self.get_object()
        if entry.posted_to_payroll:
            raise ValidationError("Posted overtime entries cannot be re-approved.")
        if entry.status not in {OvertimeRequestStatus.SUBMITTED, OvertimeRequestStatus.DRAFT}:
            raise ValidationError("Only draft or submitted entries can be approved.")

        serializer = OvertimeApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        approved_hours = data.get("approved_hours") or entry.requested_hours
        budget_line = data.get("budget_line") or entry.budget_line

        if not budget_line and entry.policy and entry.policy.auto_apply_budget and entry.policy.default_budget_line:
            budget_line = entry.policy.default_budget_line

        entry.approved_hours = approved_hours
        entry.budget_line = budget_line
        entry.qa_flagged = data.get("qa_flagged", entry.qa_flagged)
        if "qa_notes" in data:
            entry.qa_notes = data.get("qa_notes") or ""
        entry.approved_by = getattr(request, "user", None)
        entry.approved_at = timezone.now()
        entry.status = OvertimeRequestStatus.APPROVED
        entry.full_clean()
        entry.save()

        self._record_budget_usage(entry)
        return Response(self.get_serializer(entry).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject_entry(self, request, pk=None):
        entry = self.get_object()
        if entry.posted_to_payroll:
            raise ValidationError("Posted overtime entries cannot be rejected.")
        if entry.status == OvertimeRequestStatus.CANCELLED:
            raise ValidationError("Cancelled entries cannot be rejected.")

        serializer = OvertimeRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entry.status = OvertimeRequestStatus.REJECTED
        entry.approved_by = getattr(request, "user", None)
        entry.approved_at = timezone.now()
        entry.qa_flagged = False
        if "qa_notes" in serializer.validated_data:
            entry.qa_notes = serializer.validated_data.get("qa_notes") or ""
        entry.save(update_fields=["status", "approved_by", "approved_at", "qa_flagged", "qa_notes", "updated_at"])
        return Response(self.get_serializer(entry).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_entry(self, request, pk=None):
        entry = self.get_object()
        if entry.posted_to_payroll:
            raise ValidationError("Posted overtime entries cannot be cancelled.")
        if entry.status == OvertimeRequestStatus.CANCELLED:
            return Response(self.get_serializer(entry).data)
        entry.status = OvertimeRequestStatus.CANCELLED
        entry.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(entry).data)

    def _record_budget_usage(self, entry: OvertimeEntry) -> None:
        if not entry.budget_line_id or entry.amount <= 0:
            return
        exists = BudgetUsage.objects.filter(
            reference_type="hr.OvertimeEntry",
            reference_id=str(entry.id),
        ).exists()
        if exists:
            return
        BudgetUsage.objects.create(
            budget_line=entry.budget_line,
            usage_date=entry.date,
            usage_type="overtime",
            quantity=entry.effective_hours,
            amount=entry.amount,
            reference_type="hr.OvertimeEntry",
            reference_id=str(entry.id),
            description=f"Overtime for {entry.employee.full_name} on {entry.date:%Y-%m-%d}",
            created_by=getattr(self.request, "user", None),
        )

class WorkforceCapacityPlanViewSet(CompanyScopedModelViewSet):
    queryset = WorkforceCapacityPlan.objects.select_related("shift", "cost_center", "qa_cost_center")
    serializer_class = WorkforceCapacityPlanSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        scenario = params.get("scenario")
        cost_center = params.get("cost_center")
        start_raw = params.get("start")
        end_raw = params.get("end")
        if scenario:
            queryset = queryset.filter(scenario=scenario)
        if cost_center:
            queryset = queryset.filter(cost_center_id=cost_center)
        if start_raw:
            start_date = parse_date(start_raw)
            if start_date:
                queryset = queryset.filter(date__gte=start_date)
        if end_raw:
            end_date = parse_date(end_raw)
            if end_date:
                queryset = queryset.filter(date__lte=end_date)
        return queryset.order_by("date", "shift__start_time")

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        company = _ensure_company(request)
        today = timezone.localdate()
        start_param = request.query_params.get("start")
        end_param = request.query_params.get("end")
        start = parse_date(start_param) if start_param else today
        end = parse_date(end_param) if end_param else start + timedelta(days=13)
        queryset = self.get_queryset().filter(company=company, date__gte=start, date__lte=end)

        plans = [plan.to_dashboard() for plan in queryset]
        totals = {
            "requiredHeadcount": sum(plan["requiredHeadcount"] for plan in plans),
            "actualHeadcount": sum(plan["actualHeadcount"] for plan in plans),
            "plannedOvertimeHours": float(sum(plan["plannedOvertimeHours"] for plan in plans)),
            "actualOvertimeHours": float(sum(plan["actualOvertimeHours"] for plan in plans)),
        }
        qa_required = [plan["qaRequiredHeadcount"] or 0 for plan in plans]
        qa_actual = [plan["qaActualHeadcount"] or 0 for plan in plans]
        totals["qaRequiredHeadcount"] = sum(qa_required)
        totals["qaActualHeadcount"] = sum(qa_actual)

        return Response(
            {
                "window": {
                    "start": start,
                    "end": end,
                    "days": (end - start).days + 1,
                },
                "plans": plans,
                "totals": totals,
            }
        )


class PayrollRunViewSet(CompanyScopedModelViewSet):
    queryset = PayrollRun.objects.select_related("expense_account", "liability_account")
    serializer_class = PayrollRunSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        status_param = params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset.order_by("-period_start")

    def create(self, request, *args, **kwargs):
        _ensure_company(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(self.get_serializer(run).data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post"], url_path="finalize")
    def finalize(self, request, pk=None):
        run = self.get_object()
        serializer = PayrollFinalizeSerializer(data=request.data, context={"run": run})
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        final_run = PayrollService.finalize_run(
            run=run,
            posted_by=getattr(request, "user", None),
            expense_account=validated.get("expense_account"),
            liability_account=validated.get("liability_account"),
            post_to_finance=validated.get("post_to_finance", True),
        )
        return Response(self.get_serializer(final_run).data)


class PayrollRunCancelView(APIView):
    def delete(self, request, *args, **kwargs):
        run_id = kwargs.get("pk")
        run = PayrollRun.objects.filter(pk=run_id, company=_ensure_company(request)).first()
        if not run:
            raise ValidationError("Payroll run not found.")
        if run.status == PayrollRunStatus.POSTED:
            raise ValidationError("Posted payroll runs cannot be cancelled.")
        run.status = PayrollRunStatus.CANCELLED
        run.save(update_fields=["status", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

class HROverviewView(APIView):
    def get(self, request):
        company = _ensure_company(request)
        today = timezone.localdate()
        thirty_days_ago = today - timedelta(days=30)

        kpis = {
            "totalHeadcount": Employee.objects.filter(company=company, is_active=True).count(),
            "openLeaveRequests": LeaveRequest.objects.filter(company=company, status=LeaveRequestStatus.SUBMITTED).count(),
            "payrollRuns": PayrollRun.objects.filter(company=company).count(),
            "pendingOnboarding": Employee.objects.filter(
                company=company,
                status__in=[EmployeeStatus.ONBOARDING, EmployeeStatus.PROBATION],
            ).count(),
        }

        headcount_trend = (
            Employee.objects.filter(company=company, is_active=True, date_of_joining__gte=thirty_days_ago)
            .extra(select={"join_day": "date(date_of_joining)"})
            .values("join_day")
            .annotate(count=Count("id"))
            .order_by("join_day")
        )

        pulse_results = [
            {"question": "How was your week?", "trend": [4, 4.2, 4.1, 4.4]},
            {"question": "Do you have the tools to perform?", "trend": [3.5, 3.7, 3.8, 3.9]},
        ]

        recent_hires = Employee.objects.filter(
            company=company,
            date_of_joining__gte=thirty_days_ago,
        ).order_by("-date_of_joining")
        pending_leave = LeaveRequest.objects.filter(company=company, status=LeaveRequestStatus.SUBMITTED).count()
        watchlist = Employee.objects.filter(company=company, status=EmployeeStatus.LEAVE)
        pending_reviews = Employee.objects.filter(
            company=company,
            status__in=[EmployeeStatus.PROBATION, EmployeeStatus.ONBOARDING],
        )

        people_board = {
            "columns": {
                "pipeline": {
                    "id": "pipeline",
                    "title": "Pending Leave Requests",
                    "description": "Awaiting manager approval",
                    "itemIds": [f"leave-{leave.id}" for leave in LeaveRequest.objects.filter(company=company, status=LeaveRequestStatus.SUBMITTED)[:6]],
                },
                "onboarding": {
                    "id": "onboarding",
                    "title": "New Joiners",
                    "description": "Rolling 30 days",
                    "itemIds": [f"hire-{emp.id}" for emp in recent_hires[:6]],
                },
                "performance": {
                    "id": "performance",
                    "title": "Probation Reviews",
                    "description": "Upcoming confirmations",
                    "itemIds": [f"review-{emp.id}" for emp in pending_reviews[:6]],
                },
                "retention": {
                    "id": "retention",
                    "title": "Leave Watchlist",
                    "description": "Currently on extended leave",
                    "itemIds": [f"watch-{emp.id}" for emp in watchlist[:6]],
                },
            },
            "items": {},
        }

        for leave in LeaveRequest.objects.filter(company=company, status=LeaveRequestStatus.SUBMITTED)[:6]:
            people_board["items"][f"leave-{leave.id}"] = {
                "id": f"leave-{leave.id}",
                "name": f"{leave.employee.full_name}",
                "stage": f"{leave.leave_type.name} {leave.start_date:%d %b}",
                "owner": leave.employee.manager.full_name if leave.employee.manager else "HR",
            }
        for emp in recent_hires[:6]:
            people_board["items"][f"hire-{emp.id}"] = {
                "id": f"hire-{emp.id}",
                "name": emp.full_name,
                "stage": emp.date_of_joining.strftime("Joined %d %b"),
                "owner": emp.department.name if emp.department else "",
            }
        for emp in pending_reviews[:6]:
            people_board["items"][f"review-{emp.id}"] = {
                "id": f"review-{emp.id}",
                "name": emp.full_name,
                "stage": "Probation review",
                "owner": emp.manager.full_name if emp.manager else "HRBP",
            }
        for emp in watchlist[:6]:
            people_board["items"][f"watch-{emp.id}"] = {
                "id": f"watch-{emp.id}",
                "name": emp.full_name,
                "stage": "On leave",
                "owner": emp.manager.full_name if emp.manager else "HR Services",
            }

        payroll_runs = [
            {
                "id": run.id,
                "period": run.label,
                "processedOn": run.updated_at.strftime("%d %b %Y  -  %H:%M") if run.updated_at else "",
                "amount": f"{run.net_total:,.2f}",
                "status": run.status.title(),
            }
            for run in PayrollRun.objects.filter(company=company).order_by("-period_start")[:5]
        ]

        alerts = []
        if pending_leave > 0:
            alerts.append(
                {
                    "id": "alert-pending-leave",
                    "title": "Pending leave approvals",
                    "level": "warning",
                    "detail": f"{pending_leave} request(s) awaiting action.",
                }
            )
        upcoming_payroll = PayrollRun.objects.filter(
            company=company,
            status__in=[PayrollRunStatus.DRAFT, PayrollRunStatus.COMPUTED],
        ).order_by("period_end").first()
        if upcoming_payroll:
            alerts.append(
                {
                    "id": "alert-payroll",
                    "title": "Payroll pending posting",
                    "level": "info",
                    "detail": f"Complete posting for {upcoming_payroll.label}.",
                }
            )

        automations = [
            {
                "id": "auto-1",
                "title": "Overtime to payroll",
                "status": "active",
                "detail": "Approved overtime auto-syncs with payroll calculations nightly.",
            },
            {
                "id": "auto-2",
                "title": "Leave to attendance",
                "status": "active",
                "detail": "Approved leave auto marks attendance calendar.",
            },
        ]

        horizon_start = timezone.localdate()
        horizon_end = horizon_start + timedelta(days=6)
        capacity_qs = (
            WorkforceCapacityPlan.objects.filter(
                company=company,
                date__gte=horizon_start,
                date__lte=horizon_end,
            ).select_related("shift", "cost_center", "qa_cost_center")
        )
        capacity_cards = [plan.to_dashboard() for plan in capacity_qs]
        scenario_breakdown = defaultdict(lambda: {"plans": 0, "required": 0, "actual": 0})
        qa_alerts = []
        for card in capacity_cards:
            scenario_breakdown[card["scenario"]]["plans"] += 1
            scenario_breakdown[card["scenario"]]["required"] += card["requiredHeadcount"]
            scenario_breakdown[card["scenario"]]["actual"] += card["actualHeadcount"]
            if card.get("qaVariance") is not None and card["qaVariance"] < 0:
                qa_alerts.append(card)

        totals_required = sum(card["requiredHeadcount"] for card in capacity_cards)
        totals_actual = sum(card["actualHeadcount"] for card in capacity_cards)
        totals_planned_ot = sum(card["plannedOvertimeHours"] for card in capacity_cards)
        totals_actual_ot = sum(card["actualOvertimeHours"] for card in capacity_cards)
        totals_qa_required = sum((card["qaRequiredHeadcount"] or 0) for card in capacity_cards)
        totals_qa_actual = sum((card["qaActualHeadcount"] or 0) for card in capacity_cards)

        capacity_overview = {
            "window": {
                "start": horizon_start,
                "end": horizon_end,
                "days": (horizon_end - horizon_start).days + 1,
            },
            "totals": {
                "requiredHeadcount": totals_required,
                "actualHeadcount": totals_actual,
                "plannedOvertimeHours": totals_planned_ot,
                "actualOvertimeHours": totals_actual_ot,
                "qaRequiredHeadcount": totals_qa_required,
                "qaActualHeadcount": totals_qa_actual,
                "qaVariance": totals_qa_actual - totals_qa_required,
            },
            "scenarios": [
                {
                    "scenario": scenario,
                    "plans": breakdown["plans"],
                    "requiredHeadcount": breakdown["required"],
                    "actualHeadcount": breakdown["actual"],
                }
                for scenario, breakdown in scenario_breakdown.items()
            ],
            "plans": capacity_cards[:10],
            "qaAlerts": qa_alerts[:5],
        }

        if qa_alerts:
            alerts.append(
                {
                    "id": "alert-qa-capacity",
                    "title": "QA coverage gaps",
                    "level": "danger",
                    "detail": f"{len(qa_alerts)} shift(s) short on QA coverage in the next week.",
                }
            )

        overtime_window_start = horizon_start - timedelta(days=30)
        approved_overtime_qs = OvertimeEntry.objects.filter(
            company=company,
            status=OvertimeRequestStatus.APPROVED,
            date__gte=overtime_window_start,
        )
        overtime_stats = approved_overtime_qs.aggregate(
            total_hours=Sum(
                Case(
                    When(approved_hours__isnull=False, then="approved_hours"),
                    default="requested_hours",
                    output_field=DecimalField(max_digits=7, decimal_places=2),
                )
            ),
            total_amount=Sum("amount"),
        )
        pending_overtime = OvertimeEntry.objects.filter(
            company=company,
            status__in=[OvertimeRequestStatus.SUBMITTED, OvertimeRequestStatus.DRAFT],
        ).count()

        overtime_dashboard = {
            "window": {
                "start": overtime_window_start,
                "end": horizon_start,
                "days": (horizon_start - overtime_window_start).days,
            },
            "approvedHours": float(overtime_stats.get("total_hours") or 0),
            "approvedAmount": float(overtime_stats.get("total_amount") or Decimal("0")),
            "pendingApprovals": pending_overtime,
            "recent": [
                {
                    "id": entry.id,
                    "employee": entry.employee.full_name,
                    "date": entry.date,
                    "hours": float(entry.effective_hours),
                    "amount": float(entry.amount),
                    "status": entry.get_status_display(),
                }
                for entry in OvertimeEntry.objects.filter(company=company)
                .select_related("employee")
                .order_by("-date", "-created_at")[:5]
            ],
        }

        if pending_overtime:
            alerts.append(
                {
                    "id": "alert-overtime-approvals",
                    "title": "Overtime approvals pending",
                    "level": "warning",
                    "detail": f"{pending_overtime} overtime request(s) awaiting decision.",
                }
            )

        payload = {
            "kpis": kpis,
            "headcount_trend": headcount_trend,
            "pulse_results": pulse_results,
            "people_board": people_board,
            "payroll_runs": payroll_runs,
            "capacity_overview": capacity_overview,
            "overtime_dashboard": overtime_dashboard,
            "alerts": alerts,
            "automations": automations,
        }
        return Response(payload, status=status.HTTP_200_OK)

