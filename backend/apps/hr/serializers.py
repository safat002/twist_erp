from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from apps.budgeting.models import BudgetLine, CostCenter

from .models import (
    Attendance,
    AttendanceStatus,
    CapacityPlanScenario,
    Department,
    Employee,
    EmployeeLeaveBalance,
    EmploymentGrade,
    LeaveRequest,
    LeaveRequestStatus,
    LeaveType,
    OvertimeEntry,
    OvertimePolicy,
    OvertimeRequestStatus,
    PayrollLine,
    PayrollRun,
    SalaryStructure,
    ShiftAssignment,
    ShiftTemplate,
    WorkforceCapacityPlan,
)


class CompanyBoundSerializer(serializers.ModelSerializer):
    """
    Base serializer that injects company (and created_by if available)
    from the request context.
    """

    def _get_request(self):
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request context is required.")
        return request

    def _get_company(self):
        request = self._get_request()
        company = getattr(request, "company", None)
        if company is None:
            raise serializers.ValidationError("Active company context is required.")
        return company

    def _inject_company(self, validated_data):
        company = self._get_company()
        validated_data["company"] = company
        model_fields = {field.name for field in self.Meta.model._meta.get_fields()}
        if "created_by" in model_fields and not validated_data.get("created_by"):
            validated_data["created_by"] = getattr(self._get_request(), "user", None)
        return validated_data

    def create(self, validated_data):
        validated_data = self._inject_company(validated_data)
        return super().create(validated_data)


class DepartmentSerializer(CompanyBoundSerializer):
    head_name = serializers.CharField(source="head.full_name", read_only=True)

    class Meta:
        model = Department
        fields = [
            "id",
            "code",
            "name",
            "description",
            "head",
            "head_name",
            "company",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company", "created_at", "updated_at", "head_name"]


class EmploymentGradeSerializer(CompanyBoundSerializer):
    class Meta:
        model = EmploymentGrade
        fields = [
            "id",
            "code",
            "name",
            "description",
            "salary_min",
            "salary_max",
            "company",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company", "created_at", "updated_at"]


class SalaryStructureSerializer(CompanyBoundSerializer):
    total_fixed_compensation = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = SalaryStructure
        fields = [
            "id",
            "code",
            "name",
            "description",
            "base_salary",
            "housing_allowance",
            "transport_allowance",
            "meal_allowance",
            "other_allowance",
            "overtime_rate",
            "tax_rate",
            "pension_rate",
            "metadata",
            "is_active",
            "company",
            "created_at",
            "updated_at",
            "total_fixed_compensation",
        ]
        read_only_fields = ["company", "created_at", "updated_at", "total_fixed_compensation"]


class EmployeeSerializer(CompanyBoundSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    grade_name = serializers.CharField(source="grade.name", read_only=True)
    manager_name = serializers.CharField(source="manager.full_name", read_only=True)
    cost_center_name = serializers.CharField(source="cost_center.name", read_only=True)
    salary_structure_name = serializers.CharField(
        source="salary_structure.name",
        read_only=True,
    )
    full_name = serializers.CharField(read_only=True)
    active_shift = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_id",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone_number",
            "emergency_contact",
            "job_title",
            "employment_type",
            "status",
            "date_of_birth",
            "date_of_joining",
            "date_of_exit",
            "payroll_currency",
            "bank_name",
            "bank_account_number",
            "tax_identification_number",
            "notes",
            "work_location",
            "department",
            "department_name",
            "grade",
            "grade_name",
            "manager",
            "manager_name",
            "salary_structure",
            "salary_structure_name",
            "cost_center",
            "cost_center_name",
            "active_shift",
            "company",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "company",
            "created_at",
            "updated_at",
            "department_name",
            "grade_name",
            "manager_name",
            "salary_structure_name",
            "full_name",
            "cost_center_name",
            "active_shift",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        company = self._get_company()
        related_fields = {
            "department": Department,
            "grade": EmploymentGrade,
            "manager": Employee,
            "salary_structure": SalaryStructure,
            "cost_center": CostCenter,
        }
        for field_name, model_cls in related_fields.items():
            instance = attrs.get(field_name)
            if instance and getattr(instance, "company_id", company.id) != company.id:
                raise serializers.ValidationError(
                    {field_name: "Selected value belongs to a different company."}
                )
        return attrs

    def get_active_shift(self, obj: Employee):
        today = timezone.localdate()
        assignment = (
            obj.shift_assignments.filter(
                effective_from__lte=today,
            )
            .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=today))
            .select_related("shift")
            .order_by("-effective_from")
            .first()
        )
        if not assignment or not assignment.shift:
            return None
        shift = assignment.shift
        return {
            "shiftId": shift.id,
            "code": shift.code,
            "name": shift.name,
            "effectiveFrom": assignment.effective_from,
            "effectiveTo": assignment.effective_to,
            "workLocation": assignment.work_location,
        }


class ShiftTemplateSerializer(CompanyBoundSerializer):
    default_overtime_policy_name = serializers.CharField(source="default_overtime_policy.name", read_only=True)

    class Meta:
        model = ShiftTemplate
        fields = [
            "id",
            "code",
            "name",
            "description",
            "category",
            "start_time",
            "end_time",
            "break_minutes",
            "location",
            "default_headcount",
            "allow_overtime",
            "default_overtime_policy",
            "default_overtime_policy_name",
            "color_hex",
            "is_night_shift",
            "is_active",
            "company",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company", "created_at", "updated_at", "default_overtime_policy_name"]


class ShiftAssignmentSerializer(CompanyBoundSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True)
    shift_code = serializers.CharField(source="shift.code", read_only=True)
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = ShiftAssignment
        fields = [
            "id",
            "employee",
            "employee_name",
            "shift",
            "shift_name",
            "shift_code",
            "effective_from",
            "effective_to",
            "work_location",
            "cost_center",
            "overtime_policy",
            "notes",
            "is_active",
            "company",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "company",
            "created_at",
            "updated_at",
            "employee_name",
            "shift_name",
            "shift_code",
            "is_active",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        company = self._get_company()
        employee = attrs.get("employee")
        shift = attrs.get("shift")
        cost_center = attrs.get("cost_center")
        overtime_policy = attrs.get("overtime_policy")

        if employee and employee.company_id != company.id:
            raise serializers.ValidationError({"employee": "Employee belongs to a different company."})
        if shift and shift.company_id != company.id:
            raise serializers.ValidationError({"shift": "Shift belongs to a different company."})
        if cost_center and cost_center.company_id != company.id:
            raise serializers.ValidationError({"cost_center": "Cost center belongs to a different company."})
        if overtime_policy and overtime_policy.company_id != company.id:
            raise serializers.ValidationError({"overtime_policy": "Overtime policy belongs to a different company."})
        return attrs

    def get_is_active(self, obj: ShiftAssignment) -> bool:
        return obj.is_active


class OvertimePolicySerializer(CompanyBoundSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    grade_name = serializers.CharField(source="grade.name", read_only=True)
    budget_line_name = serializers.CharField(source="default_budget_line.item_name", read_only=True)

    class Meta:
        model = OvertimePolicy
        fields = [
            "id",
            "code",
            "name",
            "description",
            "department",
            "department_name",
            "grade",
            "grade_name",
            "rate_multiplier",
            "fixed_hourly_rate",
            "requires_approval",
            "auto_apply_budget",
            "default_budget_line",
            "budget_line_name",
            "max_hours_per_day",
            "max_hours_per_week",
            "qa_review_required",
            "is_active",
            "company",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "company",
            "created_at",
            "updated_at",
            "department_name",
            "grade_name",
            "budget_line_name",
        ]


class OvertimeEntrySerializer(CompanyBoundSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    shift_code = serializers.CharField(source="shift.code", read_only=True)
    policy_name = serializers.CharField(source="policy.name", read_only=True)
    cost_center_name = serializers.CharField(source="cost_center.name", read_only=True)
    budget_line_name = serializers.CharField(source="budget_line.item_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    effective_hours = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)

    class Meta:
        model = OvertimeEntry
        fields = [
            "id",
            "employee",
            "employee_name",
            "shift",
            "shift_code",
            "policy",
            "policy_name",
            "date",
            "source",
            "status",
            "status_display",
            "requested_hours",
            "approved_hours",
            "effective_hours",
            "hourly_rate",
            "amount",
            "reason",
            "qa_flagged",
            "qa_notes",
            "cost_center",
            "cost_center_name",
            "budget_line",
            "budget_line_name",
            "approved_by",
            "approved_at",
            "posted_to_payroll",
            "payroll_run",
            "company",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "company",
            "created_at",
            "updated_at",
            "employee_name",
            "shift_code",
            "policy_name",
            "status_display",
            "effective_hours",
            "amount",
            "cost_center_name",
            "budget_line_name",
            "approved_by",
            "approved_at",
            "posted_to_payroll",
            "payroll_run",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        company = self._get_company()
        checks = {
            "shift": ShiftTemplate,
            "policy": OvertimePolicy,
            "cost_center": CostCenter,
            "budget_line": BudgetLine,
        }
        for field_name, model_cls in checks.items():
            instance = attrs.get(field_name)
            if instance and getattr(instance, "company_id", company.id) != company.id:
                raise serializers.ValidationError({field_name: "Selected value belongs to a different company."})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["effective_hours"] = str(instance.effective_hours)
        data["amount"] = str(instance.amount)
        return data


class OvertimeApproveSerializer(serializers.Serializer):
    approved_hours = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    budget_line = serializers.PrimaryKeyRelatedField(queryset=BudgetLine.objects.all(), allow_null=True, required=False)
    qa_flagged = serializers.BooleanField(required=False)
    qa_notes = serializers.CharField(required=False, allow_blank=True)

    def validate_approved_hours(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Approved hours must be non-negative.")
        return value


class OvertimeRejectSerializer(serializers.Serializer):
    qa_notes = serializers.CharField(required=False, allow_blank=True)


class WorkforceCapacityPlanSerializer(CompanyBoundSerializer):
    shift_code = serializers.CharField(source="shift.code", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True)
    cost_center_name = serializers.CharField(source="cost_center.name", read_only=True)
    qa_cost_center_name = serializers.CharField(source="qa_cost_center.name", read_only=True)
    dashboard = serializers.SerializerMethodField()

    class Meta:
        model = WorkforceCapacityPlan
        fields = [
            "id",
            "date",
            "shift",
            "shift_code",
            "shift_name",
            "cost_center",
            "cost_center_name",
            "qa_cost_center",
            "qa_cost_center_name",
            "scenario",
            "required_headcount",
            "qa_required_headcount",
            "planned_overtime_hours",
            "target_utilization_percent",
            "notes",
            "dashboard",
            "company",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "company",
            "created_at",
            "updated_at",
            "shift_code",
            "shift_name",
            "cost_center_name",
            "qa_cost_center_name",
            "dashboard",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        company = self._get_company()
        for field_name in ("shift", "cost_center", "qa_cost_center"):
            instance = attrs.get(field_name)
            if instance and getattr(instance, "company_id", company.id) != company.id:
                raise serializers.ValidationError({field_name: "Selected value belongs to a different company."})
        return attrs

    def get_dashboard(self, obj: WorkforceCapacityPlan):
        snapshot = obj.to_dashboard()
        snapshot["plannedOvertimeHours"] = float(obj.planned_overtime_hours)
        snapshot["targetUtilizationPercent"] = float(obj.target_utilization_percent)
        return snapshot

class AttendanceSerializer(CompanyBoundSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    shift_code = serializers.CharField(source="shift.code", read_only=True)

    class Meta:
        model = Attendance
        fields = [
            "id",
            "employee",
            "employee_name",
            "shift",
            "shift_code",
            "date",
            "status",
            "source",
            "check_in",
            "check_out",
            "worked_hours",
            "overtime_hours",
            "gps_latitude",
            "gps_longitude",
            "source_payload",
            "notes",
            "recorded_by",
            "company",
            "created_at",
        ]
        read_only_fields = [
            "company",
            "created_at",
            "recorded_by",
            "employee_name",
            "shift_code",
            "source_payload",
        ]

    def validate_employee(self, value):
        company = self._get_company()
        if value.company_id != company.id:
            raise serializers.ValidationError("Employee belongs to a different company.")
        return value

    def validate_shift(self, value):
        if value is None:
            return value
        company = self._get_company()
        if value.company_id != company.id:
            raise serializers.ValidationError("Shift belongs to a different company.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        check_in = attrs.get("check_in")
        check_out = attrs.get("check_out")
        status = attrs.get("status")

        if check_in and check_out and check_in > check_out:
            raise serializers.ValidationError({"check_out": "Check-out must be after check-in."})

        if status == AttendanceStatus.ABSENT and attrs.get("worked_hours", Decimal("0")) > 0:
            raise serializers.ValidationError(
                {"worked_hours": "Absent entries cannot record worked hours."}
            )

        if check_in and check_out:
            duration = (check_out - check_in).total_seconds() / 3600
            attrs["worked_hours"] = round(duration, 2)
        if "recorded_by" not in attrs:
            attrs["recorded_by"] = getattr(self._get_request(), "user", None)
        return attrs


class LeaveTypeSerializer(CompanyBoundSerializer):
    class Meta:
        model = LeaveType
        fields = [
            "id",
            "code",
            "name",
            "description",
            "is_paid",
            "default_allocation",
            "max_carry_forward",
            "requires_approval",
            "company",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company", "created_at", "updated_at"]


class EmployeeLeaveBalanceSerializer(CompanyBoundSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    balance = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)

    class Meta:
        model = EmployeeLeaveBalance
        fields = [
            "id",
            "employee",
            "employee_name",
            "leave_type",
            "leave_type_name",
            "year",
            "allocated",
            "used",
            "carry_forward",
            "balance",
            "company",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "company",
            "created_at",
            "updated_at",
            "employee_name",
            "leave_type_name",
            "balance",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        company = self._get_company()
        employee = attrs.get("employee")
        leave_type = attrs.get("leave_type")
        if employee and employee.company_id != company.id:
            raise serializers.ValidationError({"employee": "Employee belongs to a different company."})
        if leave_type and leave_type.company_id != company.id:
            raise serializers.ValidationError({"leave_type": "Leave type belongs to a different company."})
        return attrs


class LeaveRequestSerializer(CompanyBoundSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    approver_name = serializers.CharField(source="approved_by.get_full_name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee",
            "employee_name",
            "leave_type",
            "leave_type_name",
            "start_date",
            "end_date",
            "return_date",
            "days",
            "status",
            "reason",
            "manager_note",
            "approved_at",
            "approved_by",
            "approver_name",
            "company",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "company",
            "created_at",
            "updated_at",
            "approved_at",
            "approved_by",
            "approver_name",
            "employee_name",
            "leave_type_name",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        start_date = attrs.get("start_date") or getattr(self.instance, "start_date", None)
        end_date = attrs.get("end_date") or getattr(self.instance, "end_date", None)

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})

        employee = attrs.get("employee") or getattr(self.instance, "employee", None)
        if employee and employee.company_id != self._get_company().id:
            raise serializers.ValidationError({"employee": "Employee belongs to a different company."})

        leave_type = attrs.get("leave_type") or getattr(self.instance, "leave_type", None)
        if leave_type and leave_type.company_id != self._get_company().id:
            raise serializers.ValidationError({"leave_type": "Leave type belongs to a different company."})

        if start_date and end_date and not attrs.get("days"):
            total_days = (end_date - start_date).days + 1
            attrs["days"] = Decimal(str(total_days))

        return attrs


class PayrollLineSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)
    department_name = serializers.CharField(source="employee.department.name", read_only=True)

    class Meta:
        model = PayrollLine
        fields = [
            "id",
            "employee",
            "employee_code",
            "employee_name",
            "department_name",
            "attendance_days",
            "leave_days",
            "base_pay",
            "allowance_total",
            "overtime_hours",
            "overtime_pay",
            "gross_pay",
            "deduction_total",
            "net_pay",
            "remarks",
            "details",
        ]
        read_only_fields = [
            "attendance_days",
            "leave_days",
            "base_pay",
            "allowance_total",
            "overtime_hours",
            "overtime_pay",
            "gross_pay",
            "deduction_total",
            "net_pay",
        ]


class PayrollRunSerializer(CompanyBoundSerializer):
    lines = PayrollLineSerializer(many=True, read_only=True)

    class Meta:
        model = PayrollRun
        fields = [
            "id",
            "period_start",
            "period_end",
            "period_label",
            "status",
            "notes",
            "expense_account",
            "liability_account",
            "journal_voucher",
            "gross_total",
            "deduction_total",
            "net_total",
            "generated_by",
            "generated_at",
            "company",
            "created_at",
            "updated_at",
            "lines",
        ]
        read_only_fields = [
            "company",
            "created_at",
            "updated_at",
            "gross_total",
            "deduction_total",
            "net_total",
            "generated_by",
            "generated_at",
            "journal_voucher",
            "status",
            "lines",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        period_start = attrs.get("period_start")
        period_end = attrs.get("period_end")
        if period_start and period_end and period_end < period_start:
            raise serializers.ValidationError(
                {"period_end": "Period end must be on or after the period start date."}
            )
        return attrs

    def create(self, validated_data):
        from .services.payroll import PayrollService

        validated_data = self._inject_company(validated_data)
        company = validated_data["company"]
        created_by = getattr(self._get_request(), "user", None)
        return PayrollService.generate_payroll_run(
            company=company,
            created_by=created_by,
            **validated_data,
        )


class PayrollFinalizeSerializer(serializers.Serializer):
    expense_account = serializers.IntegerField(required=False)
    liability_account = serializers.IntegerField(required=False)
    post_to_finance = serializers.BooleanField(default=True)

    def validate(self, attrs):
        run: PayrollRun = self.context.get("run")
        if not run:
            raise serializers.ValidationError("Payroll run context missing.")

        if attrs.get("post_to_finance", True):
            if not (attrs.get("expense_account") or run.expense_account_id):
                raise serializers.ValidationError(
                    {"expense_account": "Expense account is required to post payroll."}
                )
            if not (attrs.get("liability_account") or run.liability_account_id):
                raise serializers.ValidationError(
                    {"liability_account": "Liability account is required to post payroll."}
                )
        return attrs
