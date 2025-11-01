from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    AdvanceSalary,
    Attendance,
    Candidate,
    ClearanceChecklist,
    Competency,
    CompetencyRating,
    DisciplinaryAction,
    Employee,
    EmployeeClearance,
    EmployeeExit,
    EmployeeLoan,
    EmployeeOnboarding,
    EmployeeLeaveBalance,
    ExitInterview,
    FinalSettlement,
    Holiday,
    Interview,
    JobRequisition,
    LeaveRequest,
    LeaveType,
    OnboardingChecklistItem,
    OnboardingTask,
    PerformanceGoal,
    PerformanceReview,
    PerformanceReviewCycle,
    PolicyAcknowledgment,
    PolicyDocument,
    ShiftTemplate,
)
from .serializers import (
    AdvanceSalarySerializer,
    AttendanceSerializer,
    CandidateSerializer,
    ClearanceChecklistSerializer,
    CompetencyRatingSerializer,
    CompetencySerializer,
    DisciplinaryActionSerializer,
    EmployeeClearanceSerializer,
    EmployeeExitSerializer,
    EmployeeLeaveBalanceSerializer,
    EmployeeLoanSerializer,
    EmployeeOnboardingSerializer,
    ExitInterviewSerializer,
    FinalSettlementSerializer,
    HolidaySerializer,
    InterviewSerializer,
    JobRequisitionSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
    OnboardingChecklistItemSerializer,
    OnboardingTaskSerializer,
    PerformanceGoalSerializer,
    PerformanceReviewCycleSerializer,
    PerformanceReviewSerializer,
    PolicyAcknowledgmentSerializer,
    PolicyDocumentSerializer,
    ShiftTemplateSerializer,
)


from apps.security.permissions import HasERPPermission


class LeaveTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Leave Types. (Admin only)"""

    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [HasERPPermission('hr_manage_leave_types')]

    def get_queryset(self):
        return LeaveType.objects.filter(company=self.request.user.employee_profile.company)


class HolidayViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Holidays. (Admin only)"""

    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = [HasERPPermission('hr_manage_holidays')]

    def get_queryset(self):
        return Holiday.objects.filter(company=self.request.user.employee_profile.company)


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for employees to request leave and managers to approve them."""

    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        employee = get_object_or_404(Employee, user=self.request.user)
        if self.action == "team_requests":
            return LeaveRequest.objects.filter(employee__manager=employee)
        return LeaveRequest.objects.filter(employee=employee)

    def perform_create(self, serializer):
        employee = get_object_or_404(Employee, user=self.request.user)
        serializer.save(employee=employee)

    @action(detail=False, methods=["get"])
    def team_requests(self, request):
        """Returns leave requests for the current user's team."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a leave request."""
        leave_request = self.get_object()
        leave_request.status = "APPROVED"
        leave_request.approved_by = request.user
        leave_request.save()
        return Response({"status": "approved"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a leave request."""
        leave_request = self.get_object()
        leave_request.status = "REJECTED"
        leave_request.approved_by = request.user
        leave_request.comments = request.data.get("comments", "")
        leave_request.save()
        return Response({"status": "rejected"}, status=status.HTTP_200_OK)


class JobRequisitionViewSet(viewsets.ModelViewSet):
    """API endpoint for job requisitions."""

    queryset = JobRequisition.objects.all()
    serializer_class = JobRequisitionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return JobRequisition.objects.filter(company=self.request.user.employee_profile.company)

    def perform_create(self, serializer):
        serializer.save(
            company=self.request.user.employee_profile.company,
            requested_by=self.request.user.employee_profile,
        )


class CandidateViewSet(viewsets.ModelViewSet):
    """API endpoint for candidates."""

    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Candidate.objects.filter(company=self.request.user.employee_profile.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.employee_profile.company)


class InterviewViewSet(viewsets.ModelViewSet):
    """API endpoint for interviews."""

    queryset = Interview.objects.all()
    serializer_class = InterviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Interview.objects.filter(company=self.request.user.employee_profile.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.employee_profile.company)


class OnboardingChecklistItemViewSet(viewsets.ModelViewSet):
    """API endpoint for onboarding checklist items."""

    queryset = OnboardingChecklistItem.objects.all()
    serializer_class = OnboardingChecklistItemSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return OnboardingChecklistItem.objects.filter(company=self.request.user.employee_profile.company)


class EmployeeOnboardingViewSet(viewsets.ModelViewSet):
    """API endpoint for employee onboarding tracking."""

    queryset = EmployeeOnboarding.objects.all()
    serializer_class = EmployeeOnboardingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        employee = get_object_or_404(Employee, user=self.request.user)
        return EmployeeOnboarding.objects.filter(
            employee__in=Employee.objects.filter(manager=employee) | Employee.objects.filter(pk=employee.pk)
        )

    def perform_create(self, serializer):
        employee = get_object_or_404(Employee, user=self.request.user)
        serializer.save(company=employee.company)


class PolicyDocumentViewSet(viewsets.ModelViewSet):
    """API endpoint for HR policy documents."""

    queryset = PolicyDocument.objects.all()
    serializer_class = PolicyDocumentSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return PolicyDocument.objects.filter(company=self.request.user.employee_profile.company)


class PolicyAcknowledgmentViewSet(viewsets.ModelViewSet):
    """API endpoint for employee policy acknowledgments."""

    queryset = PolicyAcknowledgment.objects.all()
    serializer_class = PolicyAcknowledgmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        employee = get_object_or_404(Employee, user=self.request.user)
        return PolicyAcknowledgment.objects.filter(
            employee__in=Employee.objects.filter(manager=employee) | Employee.objects.filter(pk=employee.pk)
        )

    def perform_create(self, serializer):
        employee = get_object_or_404(Employee, user=self.request.user)
        serializer.save(employee=employee, company=employee.company)


class ShiftTemplateViewSet(viewsets.ModelViewSet):
    """API endpoint for managing shift templates."""

    queryset = ShiftTemplate.objects.all()
    serializer_class = ShiftTemplateSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return ShiftTemplate.objects.filter(company=self.request.user.employee_profile.company)


class AttendanceViewSet(viewsets.ModelViewSet):
    """API endpoint for managing attendance records."""

    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        employee = get_object_or_404(Employee, user=self.request.user)
        return Attendance.objects.filter(
            employee__in=Employee.objects.filter(manager=employee) | Employee.objects.filter(pk=employee.pk)
        )

    def perform_create(self, serializer):
        employee = get_object_or_404(Employee, user=self.request.user)
        serializer.save(company=employee.company)


class OnboardingTaskViewSet(viewsets.ModelViewSet):
    """API endpoint for individual onboarding tasks."""

    queryset = OnboardingTask.objects.all()
    serializer_class = OnboardingTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        employee = get_object_or_404(Employee, user=self.request.user)
        return OnboardingTask.objects.filter(
            onboarding__employee__in=Employee.objects.filter(manager=employee) | Employee.objects.filter(pk=employee.pk)
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.is_completed = True
        task.completed_by = request.user
        task.completed_at = timezone.now()
        task.save()
        return Response({"status": "completed"})


class PerformanceReviewCycleViewSet(viewsets.ModelViewSet):
    """API endpoint for performance review cycles."""

    queryset = PerformanceReviewCycle.objects.all()
    serializer_class = PerformanceReviewCycleSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return PerformanceReviewCycle.objects.filter(company=self.request.user.employee_profile.company)


class PerformanceGoalViewSet(viewsets.ModelViewSet):
    """API endpoint for performance goals."""

    queryset = PerformanceGoal.objects.all()
    serializer_class = PerformanceGoalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        employee = get_object_or_404(Employee, user=self.request.user)
        return PerformanceGoal.objects.filter(
            employee__in=Employee.objects.filter(manager=employee) | Employee.objects.filter(pk=employee.pk)
        )

    def perform_create(self, serializer):
        employee = get_object_or_404(Employee, user=self.request.user)
        serializer.save(employee=employee)


class DisciplinaryActionViewSet(viewsets.ModelViewSet):
    """API endpoint for disciplinary actions."""

    queryset = DisciplinaryAction.objects.all()
    serializer_class = DisciplinaryActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DisciplinaryAction.objects.filter(company=self.request.user.employee_profile.company)

    def perform_create(self, serializer):
        employee = get_object_or_404(Employee, user=self.request.user)
        serializer.save(company=employee.company)


class ClearanceChecklistViewSet(viewsets.ModelViewSet):
    """API endpoint for clearance checklist templates."""

    queryset = ClearanceChecklist.objects.all()
    serializer_class = ClearanceChecklistSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return ClearanceChecklist.objects.filter(company=self.request.user.employee_profile.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.employee_profile.company)


class EmployeeClearanceViewSet(viewsets.ModelViewSet):
    """API endpoint for employee clearance tracking."""

    queryset = EmployeeClearance.objects.all()
    serializer_class = EmployeeClearanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EmployeeClearance.objects.filter(
            employee_exit__employee__company=self.request.user.employee_profile.company
        )

    def perform_create(self, serializer):
        employee = get_object_or_404(Employee, user=self.request.user)
        serializer.save(company=employee.company)


class ExitInterviewViewSet(viewsets.ModelViewSet):
    """API endpoint for exit interviews."""

    queryset = ExitInterview.objects.all()
    serializer_class = ExitInterviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExitInterview.objects.filter(
            employee_exit__employee__company=self.request.user.employee_profile.company
        )

    def perform_create(self, serializer):
        employee = get_object_or_404(Employee, user=self.request.user)
        serializer.save(company=employee.company)


class FinalSettlementViewSet(viewsets.ModelViewSet):
    """API endpoint for final settlements."""

    queryset = FinalSettlement.objects.all()
    serializer_class = FinalSettlementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FinalSettlement.objects.filter(
            employee_exit__employee__company=self.request.user.employee_profile.company
        )

    def perform_create(self, serializer):
        employee = get_object_or_404(Employee, user=self.request.user)
        serializer.save(company=employee.company)


class EmployeeExitViewSet(viewsets.ModelViewSet):
    """API endpoint for employee exits."""

    queryset = EmployeeExit.objects.all()
    serializer_class = EmployeeExitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EmployeeExit.objects.filter(employee__company=self.request.user.employee_profile.company)

    def perform_create(self, serializer):
        employee = get_object_or_404(Employee, user=self.request.user)
        serializer.save(company=employee.company)


class CompetencyViewSet(viewsets.ModelViewSet):
    """API endpoint for competencies."""

    queryset = Competency.objects.all()
    serializer_class = CompetencySerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Competency.objects.filter(company=self.request.user.employee_profile.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.employee_profile.company)


class CompetencyRatingViewSet(viewsets.ModelViewSet):
    """API endpoint for competency ratings."""

    queryset = CompetencyRating.objects.all()
    serializer_class = CompetencyRatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        employee = get_object_or_404(Employee, user=self.request.user)
        return CompetencyRating.objects.filter(
            performance_review__employee__in=Employee.objects.filter(manager=employee)
            | Employee.objects.filter(pk=employee.pk)
        )


class PerformanceReviewViewSet(viewsets.ModelViewSet):
    """API endpoint for performance reviews."""

    queryset = PerformanceReview.objects.all()
    serializer_class = PerformanceReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        employee = get_object_or_404(Employee, user=self.request.user)
        return PerformanceReview.objects.filter(
            employee__in=Employee.objects.filter(manager=employee) | Employee.objects.filter(pk=employee.pk)
        )

    def perform_create(self, serializer):
        employee = get_object_or_404(Employee, user=self.request.user)
        serializer.save(employee=employee)


class EmployeeLeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for employees to view their leave balances."""

    queryset = EmployeeLeaveBalance.objects.all()
    serializer_class = EmployeeLeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        employee = get_object_or_404(Employee, user=self.request.user)
        return EmployeeLeaveBalance.objects.filter(employee=employee)


class AdvanceSalaryViewSet(viewsets.ModelViewSet):
    """API endpoint for salary advances."""

    queryset = AdvanceSalary.objects.all()
    serializer_class = AdvanceSalarySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        employee = get_object_or_404(Employee, user=self.request.user)
        return AdvanceSalary.objects.filter(
            employee__in=Employee.objects.filter(manager=employee) | Employee.objects.filter(pk=employee.pk)
        )

    def perform_create(self, serializer):
        employee = get_object_or_404(Employee, user=self.request.user)
        serializer.save(employee=employee, company=employee.company)


class EmployeeLoanViewSet(viewsets.ModelViewSet):
    """API endpoint for employee loans."""

    queryset = EmployeeLoan.objects.all()
    serializer_class = EmployeeLoanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        employee = get_object_or_404(Employee, user=self.request.user)
        return EmployeeLoan.objects.filter(
            employee__in=Employee.objects.filter(manager=employee) | Employee.objects.filter(pk=employee.pk)
        )

    def perform_create(self, serializer):
        employee = get_object_or_404(Employee, user=self.request.user)
        serializer.save(employee=employee, company=employee.company)
