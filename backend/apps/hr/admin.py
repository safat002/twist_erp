from django.contrib import admin
from .models import *


# ========================================
# EXISTING CORE MODELS
# ========================================

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "company")
    list_filter = ("company",)
    search_fields = ("name", "code")


@admin.register(EmploymentGrade)
class EmploymentGradeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "company")
    list_filter = ("company",)
    search_fields = ("code", "name")


@admin.register(SalaryStructure)
class SalaryStructureAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "company", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("code", "name")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "first_name", "last_name", "department", "company", "is_active")
    list_filter = ("company", "department", "is_active")
    search_fields = ("employee_id", "first_name", "last_name", "email")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "status", "company")
    list_filter = ("company", "status", "date")
    search_fields = ("employee__employee_id",)
    date_hierarchy = "date"


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "is_paid")
    list_filter = ("company", "is_paid")
    search_fields = ("name",)


@admin.register(EmployeeLeaveBalance)
class EmployeeLeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "balance")
    list_filter = ("leave_type",)
    search_fields = ("employee__employee_id",)


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "start_date", "end_date", "status")
    list_filter = ("status", "leave_type")
    search_fields = ("employee__employee_id",)


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ("label", "company", "period_start", "period_end", "status")
    list_filter = ("company", "status")


@admin.register(PayrollLine)
class PayrollLineAdmin(admin.ModelAdmin):
    list_display = ("payroll_run", "employee", "company")
    list_filter = ("company",)


# ========================================
# NEW MODELS - SIMPLE REGISTRATIONS
# ========================================

# Timesheet Management
admin.site.register(Holiday)
admin.site.register(Project)
admin.site.register(ProjectTask)
admin.site.register(Timesheet)
admin.site.register(TimesheetLine)

# Shift Management
admin.site.register(ShiftTemplate)
admin.site.register(ShiftAssignment)

# Overtime
admin.site.register(OvertimePolicy)
admin.site.register(OvertimeEntry)

# Workforce Planning
admin.site.register(WorkforceCapacityPlan)

# Performance
admin.site.register(PerformanceReviewCycle)
admin.site.register(PerformanceGoal)
admin.site.register(PerformanceReview)
admin.site.register(Competency)
admin.site.register(CompetencyRating)

# Recruitment & Onboarding
admin.site.register(JobRequisition)
admin.site.register(Candidate)
admin.site.register(Interview)
admin.site.register(OnboardingChecklistItem)
admin.site.register(EmployeeOnboarding)
admin.site.register(OnboardingTask)

# Training
admin.site.register(TrainingCategory)
admin.site.register(TrainingCourse)
admin.site.register(TrainingSession)
admin.site.register(TrainingEnrollment)
admin.site.register(Certification)

# Benefits
admin.site.register(BenefitsPlan)
admin.site.register(BenefitsEnrollment)
admin.site.register(BenefitsClaim)

# Compensation
admin.site.register(CompensationRevision)
admin.site.register(Bonus)

# Exit Management
admin.site.register(EmployeeExit)
admin.site.register(ClearanceChecklist)
admin.site.register(EmployeeClearance)
admin.site.register(ExitInterview)
admin.site.register(FinalSettlement)

# Documents
admin.site.register(EmployeeDocument)
admin.site.register(PolicyDocument)
admin.site.register(PolicyAcknowledgment)

# Disciplinary
admin.site.register(DisciplinaryAction)

# Compliance
admin.site.register(ComplianceReport)
admin.site.register(Reimbursement)
admin.site.register(AdvanceSalary)
admin.site.register(EmployeeLoan)

# Assets
admin.site.register(EmployeeAssetAssignment)
