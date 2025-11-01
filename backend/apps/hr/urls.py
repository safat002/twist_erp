from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LeaveTypeViewSet,
    HolidayViewSet,
    LeaveRequestViewSet,
    EmployeeLeaveBalanceViewSet,
    AdvanceSalaryViewSet,
    EmployeeLoanViewSet,
    JobRequisitionViewSet,
    CandidateViewSet,
    InterviewViewSet,
    OnboardingChecklistItemViewSet,
    EmployeeOnboardingViewSet,
    OnboardingTaskViewSet,
    PerformanceReviewCycleViewSet,
    PerformanceGoalViewSet,
    CompetencyViewSet,
    CompetencyRatingViewSet,
    PerformanceReviewViewSet,
    DisciplinaryActionViewSet,
    ClearanceChecklistViewSet,
    EmployeeClearanceViewSet,
    ExitInterviewViewSet,
    FinalSettlementViewSet,
    EmployeeExitViewSet,
    PolicyDocumentViewSet,
    PolicyAcknowledgmentViewSet,
    ShiftTemplateViewSet,
    AttendanceViewSet
)

router = DefaultRouter()
router.register(r'leave-types', LeaveTypeViewSet)
router.register(r'holidays', HolidayViewSet)
router.register(r'leave-requests', LeaveRequestViewSet)
router.register(r'leave-balances', EmployeeLeaveBalanceViewSet)
router.register(r'salary-advances', AdvanceSalaryViewSet)
router.register(r'employee-loans', EmployeeLoanViewSet)
router.register(r'job-requisitions', JobRequisitionViewSet)
router.register(r'candidates', CandidateViewSet)
router.register(r'interviews', InterviewViewSet)
router.register(r'onboarding-checklist-items', OnboardingChecklistItemViewSet)
router.register(r'employee-onboarding', EmployeeOnboardingViewSet)
router.register(r'onboarding-tasks', OnboardingTaskViewSet)
router.register(r'performance-review-cycles', PerformanceReviewCycleViewSet)
router.register(r'performance-goals', PerformanceGoalViewSet)
router.register(r'competencies', CompetencyViewSet)
router.register(r'competency-ratings', CompetencyRatingViewSet)
router.register(r'performance-reviews', PerformanceReviewViewSet)
router.register(r'disciplinary-actions', DisciplinaryActionViewSet)
router.register(r'clearance-checklists', ClearanceChecklistViewSet)
router.register(r'employee-clearances', EmployeeClearanceViewSet)
router.register(r'exit-interviews', ExitInterviewViewSet)
router.register(r'final-settlements', FinalSettlementViewSet)
router.register(r'employee-exits', EmployeeExitViewSet)
router.register(r'policy-documents', PolicyDocumentViewSet)
router.register(r'policy-acknowledgments', PolicyAcknowledgmentViewSet)
router.register(r'shift-templates', ShiftTemplateViewSet)
router.register(r'attendance', AttendanceViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
