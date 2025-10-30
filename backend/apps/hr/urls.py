from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AttendanceViewSet,
    DepartmentViewSet,
    EmployeeLeaveBalanceViewSet,
    EmployeeViewSet,
    EmploymentGradeViewSet,
    HROverviewView,
    LeaveRequestViewSet,
    LeaveTypeViewSet,
    OvertimeEntryViewSet,
    OvertimePolicyViewSet,
    PayrollRunViewSet,
    SalaryStructureViewSet,
    ShiftAssignmentViewSet,
    ShiftTemplateViewSet,
    WorkforceCapacityPlanViewSet,
)

router = DefaultRouter()
router.register(r"departments", DepartmentViewSet, basename="hr-department")
router.register(r"shift-templates", ShiftTemplateViewSet, basename="hr-shift-template")
router.register(r"shift-assignments", ShiftAssignmentViewSet, basename="hr-shift-assignment")
router.register(r"overtime-policies", OvertimePolicyViewSet, basename="hr-overtime-policy")
router.register(r"overtime-entries", OvertimeEntryViewSet, basename="hr-overtime-entry")
router.register(r"capacity-plans", WorkforceCapacityPlanViewSet, basename="hr-capacity-plan")
router.register(r"grades", EmploymentGradeViewSet, basename="hr-grade")
router.register(r"salary-structures", SalaryStructureViewSet, basename="hr-salary-structure")
router.register(r"employees", EmployeeViewSet, basename="hr-employee")
router.register(r"attendance", AttendanceViewSet, basename="hr-attendance")
router.register(r"leave-types", LeaveTypeViewSet, basename="hr-leave-type")
router.register(r"leave-balances", EmployeeLeaveBalanceViewSet, basename="hr-leave-balance")
router.register(r"leave-requests", LeaveRequestViewSet, basename="hr-leave-request")
router.register(r"payroll-runs", PayrollRunViewSet, basename="hr-payroll-run")

urlpatterns = [
    path("overview/", HROverviewView.as_view(), name="hr-overview"),
    path("", include(router.urls)),
]
