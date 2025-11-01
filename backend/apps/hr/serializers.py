from rest_framework import serializers
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


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = "__all__"


class EmployeeLeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeLeaveBalance
        fields = "__all__"


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = "__all__"

    def validate(self, data):
        start = data.get("start_date")
        end = data.get("end_date")
        if start and end and start > end:
            raise serializers.ValidationError("End date must be after start date.")
        return data


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = "__all__"


class JobRequisitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobRequisition
        fields = "__all__"


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = "__all__"


class InterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        fields = "__all__"


class OnboardingChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingChecklistItem
        fields = "__all__"


class OnboardingTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingTask
        fields = "__all__"


class EmployeeOnboardingSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeOnboarding
        fields = "__all__"


class PerformanceReviewCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceReviewCycle
        fields = "__all__"


class PerformanceGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceGoal
        fields = "__all__"


class CompetencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Competency
        fields = "__all__"


class CompetencyRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetencyRating
        fields = "__all__"


class PerformanceReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceReview
        fields = "__all__"


class DisciplinaryActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisciplinaryAction
        fields = "__all__"


class ClearanceChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClearanceChecklist
        fields = "__all__"


class EmployeeClearanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeClearance
        fields = "__all__"


class ExitInterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExitInterview
        fields = "__all__"


class FinalSettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinalSettlement
        fields = "__all__"


class EmployeeExitSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeExit
        fields = "__all__"


class PolicyDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyDocument
        fields = "__all__"


class PolicyAcknowledgmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyAcknowledgment
        fields = "__all__"


class ShiftTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftTemplate
        fields = "__all__"


class AdvanceSalarySerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvanceSalary
        fields = "__all__"
        read_only_fields = ("approved_by", "approved_at", "recovered_amount", "status")


class EmployeeLoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeLoan
        fields = "__all__"
        read_only_fields = ("paid_installments", "status")
