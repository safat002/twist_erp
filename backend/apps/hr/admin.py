from django.contrib import admin

from .models import (
    Attendance,
    Department,
    Employee,
    EmployeeLeaveBalance,
    EmploymentGrade,
    LeaveRequest,
    LeaveType,
    PayrollLine,
    PayrollRun,
    SalaryStructure,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "company", "head")
    list_filter = ("company",)
    search_fields = ("name", "code")


@admin.register(EmploymentGrade)
class EmploymentGradeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "company", "salary_min", "salary_max")
    list_filter = ("company",)
    search_fields = ("code", "name")


@admin.register(SalaryStructure)
class SalaryStructureAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "company", "base_salary", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("code", "name")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "employee_id",
        "first_name",
        "last_name",
        "department",
        "job_title",
        "employment_type",
        "company",
        "status",
        "is_active",
    )
    list_filter = ("company", "employment_type", "status", "department")
    search_fields = ("employee_id", "first_name", "last_name", "email")
    autocomplete_fields = ("department", "grade", "manager", "salary_structure")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "status", "worked_hours", "overtime_hours", "company")
    list_filter = ("company", "status", "date", "source")
    search_fields = ("employee__employee_id", "employee__first_name", "employee__last_name")
    date_hierarchy = "date"
    autocomplete_fields = ("employee",)


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "company", "is_paid", "default_allocation")
    list_filter = ("company", "is_paid")
    search_fields = ("code", "name")


@admin.register(EmployeeLeaveBalance)
class EmployeeLeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "year", "allocated", "used", "balance")
    list_filter = ("company", "year", "leave_type")
    search_fields = ("employee__employee_id", "employee__first_name", "employee__last_name")
    autocomplete_fields = ("employee", "leave_type")


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "start_date", "end_date", "status", "company")
    list_filter = ("company", "status", "leave_type")
    search_fields = ("employee__employee_id", "employee__first_name", "employee__last_name")
    autocomplete_fields = ("employee", "leave_type", "approved_by")


class PayrollLineInline(admin.TabularInline):
    model = PayrollLine
    extra = 0
    readonly_fields = ("employee", "gross_pay", "deduction_total", "net_pay")
    autocomplete_fields = ("employee",)


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ("label", "company", "period_start", "period_end", "status", "net_total")
    list_filter = ("company", "status")
    search_fields = ("period_label",)
    autocomplete_fields = ("expense_account", "liability_account", "journal_voucher")
    inlines = [PayrollLineInline]


@admin.register(PayrollLine)
class PayrollLineAdmin(admin.ModelAdmin):
    list_display = ("payroll_run", "employee", "gross_pay", "deduction_total", "net_pay")
    list_filter = ("company",)
    search_fields = ("employee__employee_id", "employee__first_name", "employee__last_name")
    autocomplete_fields = ("payroll_run", "employee")
