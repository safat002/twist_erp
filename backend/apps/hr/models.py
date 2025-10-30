from __future__ import annotations

from decimal import Decimal
from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.companies.models import Company  # noqa: F401  # Imported for admin/typing
from apps.budgeting.models import BudgetLine, BudgetUsage, CostCenter
from shared.models import CompanyAwareModel


class Department(CompanyAwareModel):
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    head = models.ForeignKey(
        "Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="head_of_departments",
    )

    class Meta:
        unique_together = ("company", "code")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["company", "code"]),
            models.Index(fields=["company", "name"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class EmploymentGrade(CompanyAwareModel):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    salary_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    salary_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )

    class Meta:
        unique_together = ("company", "code")
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class SalaryStructure(CompanyAwareModel):
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    base_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    housing_allowance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    transport_allowance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    meal_allowance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    other_allowance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    overtime_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
        help_text="Default hourly overtime rate.",
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
        help_text="Percentage tax deduction applied on gross.",
    )
    pension_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"

    def total_fixed_compensation(self) -> Decimal:
        return (
            (self.base_salary or Decimal("0.00"))
            + (self.housing_allowance or Decimal("0.00"))
            + (self.transport_allowance or Decimal("0.00"))
            + (self.meal_allowance or Decimal("0.00"))
            + (self.other_allowance or Decimal("0.00"))
        )


class ShiftCategory(models.TextChoices):
    DAY = "DAY", "Day"
    NIGHT = "NIGHT", "Night"
    ROTATING = "ROTATING", "Rotating"
    FLEX = "FLEX", "Flexible"


class ShiftTemplate(CompanyAwareModel):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=ShiftCategory.choices, default=ShiftCategory.DAY)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_minutes = models.PositiveIntegerField(default=0)
    location = models.CharField(max_length=120, blank=True)
    default_headcount = models.PositiveIntegerField(
        default=0,
        help_text="Target crew size for this shift before overtime.",
    )
    allow_overtime = models.BooleanField(default=True)
    default_overtime_policy = models.ForeignKey(
        "OvertimePolicy",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_shifts",
    )
    color_hex = models.CharField(max_length=7, default="#1677ff")
    is_night_shift = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    @property
    def duration_hours(self) -> Decimal:
        today = timezone.now().date()
        start = datetime.combine(today, self.start_time)
        end = datetime.combine(today, self.end_time)
        if end <= start:
            end += timedelta(days=1)
        total_minutes = (end - start).total_seconds() / 60 - self.break_minutes
        return Decimal(total_minutes / 60).quantize(Decimal("0.01"))


class ShiftAssignment(CompanyAwareModel):
    employee = models.ForeignKey(
        "Employee",
        on_delete=models.CASCADE,
        related_name="shift_assignments",
    )
    shift = models.ForeignKey(
        ShiftTemplate,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    work_location = models.CharField(max_length=255, blank=True)
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shift_assignments",
    )
    overtime_policy = models.ForeignKey(
        "OvertimePolicy",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shift_assignments",
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_shift_assignments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-effective_from",)
        indexes = [
            models.Index(fields=["company", "employee", "effective_from"]),
            models.Index(fields=["company", "shift", "effective_from"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee.full_name} -> {self.shift.code}"

    @property
    def is_active(self) -> bool:
        today = timezone.localdate()
        return self.effective_from <= today and (self.effective_to is None or today <= self.effective_to)


class OvertimeRequestStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Pending Approval"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class OvertimeSource(models.TextChoices):
    MANUAL = "MANUAL", "Manual Entry"
    ATTENDANCE = "ATTENDANCE", "Attendance Sync"
    CAPACITY_PLAN = "CAPACITY_PLAN", "Capacity Planner"


class OvertimePolicy(CompanyAwareModel):
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="overtime_policies",
    )
    grade = models.ForeignKey(
        EmploymentGrade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="overtime_policies",
    )
    rate_multiplier = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("1.50"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Multiplier applied on employee base overtime rate.",
    )
    fixed_hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Override rate. If set, multiplier is ignored.",
    )
    requires_approval = models.BooleanField(default=True)
    auto_apply_budget = models.BooleanField(
        default=False,
        help_text="Automatically link approved entries to the default budget line.",
    )
    default_budget_line = models.ForeignKey(
        BudgetLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="overtime_policies",
    )
    max_hours_per_day = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("4.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    max_hours_per_week = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("24.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    qa_review_required = models.BooleanField(
        default=False,
        help_text="If true, QA team must flag completion before payroll uses the overtime.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["company", "department"]),
            models.Index(fields=["company", "grade"]),
            models.Index(fields=["company", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"

    @staticmethod
    def _quantize(value: Decimal) -> Decimal:
        if not isinstance(value, Decimal):
            value = Decimal(str(value or "0"))
        return value.quantize(Decimal("0.01"))

    def resolve_hourly_rate(self, employee: "Employee") -> Decimal:
        """
        Determine the effective overtime hourly rate for an employee.
        """
        if self.fixed_hourly_rate and self.fixed_hourly_rate > 0:
            return self._quantize(self.fixed_hourly_rate)

        structure = getattr(employee, "salary_structure", None)
        base_rate = getattr(structure, "overtime_rate", None) or Decimal("0.00")
        if not isinstance(base_rate, Decimal):
            base_rate = Decimal(str(base_rate or "0"))

        if base_rate <= 0:
            return Decimal("0.00")

        multiplier = self.rate_multiplier or Decimal("1.00")
        return self._quantize(base_rate * multiplier)


class OvertimeEntry(CompanyAwareModel):
    employee = models.ForeignKey(
        "Employee",
        on_delete=models.PROTECT,
        related_name="overtime_entries",
    )
    shift = models.ForeignKey(
        ShiftTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="overtime_entries",
    )
    policy = models.ForeignKey(
        OvertimePolicy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="overtime_entries",
    )
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="overtime_entries",
    )
    budget_line = models.ForeignKey(
        BudgetLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="overtime_entries",
    )
    date = models.DateField()
    source = models.CharField(
        max_length=20,
        choices=OvertimeSource.choices,
        default=OvertimeSource.MANUAL,
    )
    status = models.CharField(
        max_length=20,
        choices=OvertimeRequestStatus.choices,
        default=OvertimeRequestStatus.DRAFT,
    )
    requested_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    approved_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    reason = models.TextField(blank=True)
    qa_flagged = models.BooleanField(
        default=False,
        help_text="Marked when QA requires follow-up on this overtime session.",
    )
    qa_notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_overtime_entries",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    posted_to_payroll = models.BooleanField(default=False)
    payroll_run = models.ForeignKey(
        "PayrollRun",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="overtime_entries",
    )

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["company", "date"]),
            models.Index(fields=["company", "employee", "date"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "posted_to_payroll"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee.full_name} OT {self.date} ({self.effective_hours}h)"

    @staticmethod
    def _quantize(value: Decimal) -> Decimal:
        if value is None:
            value = Decimal("0")
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        return value.quantize(Decimal("0.01"))

    @property
    def effective_hours(self) -> Decimal:
        approved = self.approved_hours if self.approved_hours is not None else self.requested_hours
        if not isinstance(approved, Decimal):
            approved = Decimal(str(approved or "0"))
        return approved

    def _resolved_policy(self) -> OvertimePolicy | None:
        if self.policy:
            return self.policy
        if self.shift and self.shift.default_overtime_policy:
            return self.shift.default_overtime_policy
        assignment = (
            self.employee.shift_assignments.filter(
                company=self.company,
                effective_from__lte=self.date,
            )
            .order_by("-effective_from")
            .first()
        )
        if assignment and assignment.overtime_policy:
            return assignment.overtime_policy
        return None

    def _resolve_hourly_rate(self) -> Decimal:
        policy = self._resolved_policy()
        if policy:
            rate = policy.resolve_hourly_rate(self.employee)
            if rate > 0:
                return self._quantize(rate)

        structure = getattr(self.employee, "salary_structure", None)
        overtime_rate = getattr(structure, "overtime_rate", None) or Decimal("0.00")
        if not isinstance(overtime_rate, Decimal):
            overtime_rate = Decimal(str(overtime_rate or "0"))
        return self._quantize(overtime_rate)

    def clean(self):
        super().clean()
        if self.approved_hours and self.approved_hours > self.requested_hours:
            raise ValidationError("Approved hours cannot exceed requested hours.")

    def save(self, *args, **kwargs):
        if not self.company_id:
            self.company = self.employee.company
        if not self.cost_center_id and self.employee.cost_center_id:
            self.cost_center_id = self.employee.cost_center_id
        if not self.policy_id:
            policy = self._resolved_policy()
            if policy:
                self.policy = policy
        if not self.hourly_rate or self.hourly_rate <= 0:
            self.hourly_rate = self._resolve_hourly_rate()

        hours = self.effective_hours
        self.amount = self._quantize(self.hourly_rate * hours)
        super().save(*args, **kwargs)

    def mark_posted(self, payroll_run: "PayrollRun") -> None:
        """
        Flag the overtime entry as consumed by a payroll run.
        """
        self.payroll_run = payroll_run
        self.posted_to_payroll = True
        if self.status != OvertimeRequestStatus.APPROVED:
            self.status = OvertimeRequestStatus.APPROVED
        self.save(update_fields=["payroll_run", "posted_to_payroll", "status", "updated_at"])


class CapacityPlanScenario(models.TextChoices):
    PRODUCTION = "PRODUCTION", "Production"
    SERVICE = "SERVICE", "Service"
    SUPPORT = "SUPPORT", "Support"


class WorkforceCapacityPlan(CompanyAwareModel):
    date = models.DateField()
    shift = models.ForeignKey(
        ShiftTemplate,
        on_delete=models.CASCADE,
        related_name="capacity_plans",
    )
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.CASCADE,
        related_name="capacity_plans",
    )
    scenario = models.CharField(
        max_length=20,
        choices=CapacityPlanScenario.choices,
        default=CapacityPlanScenario.PRODUCTION,
    )
    required_headcount = models.PositiveIntegerField(default=0)
    qa_required_headcount = models.PositiveIntegerField(default=0)
    qa_cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="qa_capacity_plans",
    )
    planned_overtime_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    target_utilization_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("85.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("company", "date", "shift", "cost_center")
        ordering = ["-date", "shift__start_time"]
        indexes = [
            models.Index(fields=["company", "date"]),
            models.Index(fields=["company", "cost_center", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.date} {self.shift.code} plan"

    @staticmethod
    def _quantize(value: Decimal) -> Decimal:
        if value is None:
            value = Decimal("0")
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        return value.quantize(Decimal("0.01"))

    def compute_actuals(self) -> dict[str, Decimal | int | None]:
        from django.db.models import Q, Sum

        active_statuses = [
            AttendanceStatus.PRESENT,
            AttendanceStatus.REMOTE,
            AttendanceStatus.HALF_DAY,
        ]

        assignment_qs = ShiftAssignment.objects.filter(
            company=self.company,
            shift=self.shift,
            effective_from__lte=self.date,
        ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=self.date))

        if self.cost_center_id:
            assignment_qs = assignment_qs.filter(
                Q(cost_center_id=self.cost_center_id)
                | Q(cost_center__isnull=True, employee__cost_center_id=self.cost_center_id)
            )

        employee_ids = list(assignment_qs.values_list("employee_id", flat=True))
        if not employee_ids:
            employee_ids = []

        attendance_qs = Attendance.objects.filter(
            company=self.company,
            date=self.date,
            employee_id__in=employee_ids,
        )

        present_qs = attendance_qs.filter(status__in=active_statuses)
        actual_headcount = present_qs.values("employee_id").distinct().count()
        worked_hours = present_qs.aggregate(total=Sum("worked_hours")).get("total") or Decimal("0.00")

        overtime_entries = list(
            OvertimeEntry.objects.filter(
                company=self.company,
                date=self.date,
                employee_id__in=employee_ids,
                status=OvertimeRequestStatus.APPROVED,
            )
        )
        overtime_hours = sum(entry.effective_hours for entry in overtime_entries) if overtime_entries else Decimal("0.00")
        overtime_amount = sum(entry.amount for entry in overtime_entries) if overtime_entries else Decimal("0.00")

        qa_headcount = None
        if self.qa_cost_center_id:
            qa_headcount = (
                Attendance.objects.filter(
                    company=self.company,
                    date=self.date,
                    employee__cost_center_id=self.qa_cost_center_id,
                    status__in=active_statuses,
                )
                .values("employee_id")
                .distinct()
                .count()
            )

        return {
            "actual_headcount": actual_headcount,
            "worked_hours": self._quantize(worked_hours),
            "overtime_hours": self._quantize(overtime_hours),
            "overtime_amount": self._quantize(overtime_amount),
            "qa_actual_headcount": qa_headcount,
        }

    def to_dashboard(self) -> dict[str, object]:
        actuals = self.compute_actuals()
        headcount_variance = actuals["actual_headcount"] - self.required_headcount
        qa_variance = None
        if self.qa_required_headcount and actuals["qa_actual_headcount"] is not None:
            qa_variance = actuals["qa_actual_headcount"] - self.qa_required_headcount

        return {
            "id": self.id,
            "date": self.date,
            "shiftId": self.shift_id,
            "shiftCode": self.shift.code,
            "scenario": self.scenario,
            "costCenterId": self.cost_center_id,
            "requiredHeadcount": self.required_headcount,
            "actualHeadcount": actuals["actual_headcount"],
            "headcountVariance": headcount_variance,
            "plannedOvertimeHours": float(self.planned_overtime_hours),
            "actualOvertimeHours": float(actuals["overtime_hours"]),
            "overtimeAmount": float(actuals["overtime_amount"]),
            "targetUtilizationPercent": float(self.target_utilization_percent),
            "qaRequiredHeadcount": self.qa_required_headcount,
            "qaActualHeadcount": actuals["qa_actual_headcount"],
            "qaVariance": qa_variance,
            "notes": self.notes,
        }


class EmploymentType(models.TextChoices):
    FULL_TIME = "FULL_TIME", "Full-time"
    PART_TIME = "PART_TIME", "Part-time"
    CONTRACT = "CONTRACT", "Contract"
    INTERN = "INTERN", "Intern"
    CONSULTANT = "CONSULTANT", "Consultant"


class EmployeeStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    ONBOARDING = "ONBOARDING", "Onboarding"
    PROBATION = "PROBATION", "Probation"
    LEAVE = "LEAVE", "On Leave"
    TERMINATED = "TERMINATED", "Terminated"
    RESIGNED = "RESIGNED", "Resigned"


class Employee(models.Model):
    employee_id = models.CharField(max_length=30)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    emergency_contact = models.CharField(max_length=255, blank=True)
    job_title = models.CharField(max_length=150, blank=True)
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
    )
    status = models.CharField(
        max_length=20,
        choices=EmployeeStatus.choices,
        default=EmployeeStatus.ACTIVE,
    )
    date_of_birth = models.DateField(null=True, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    date_of_exit = models.DateField(null=True, blank=True)
    payroll_currency = models.CharField(max_length=3, default="BDT")
    bank_name = models.CharField(max_length=120, blank=True)
    bank_account_number = models.CharField(max_length=120, blank=True)
    tax_identification_number = models.CharField(max_length=60, blank=True)
    notes = models.TextField(blank=True)
    work_location = models.CharField(max_length=255, blank=True)

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    grade = models.ForeignKey(
        EmploymentGrade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
    )
    salary_structure = models.ForeignKey(
        SalaryStructure,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="employees",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("company", "employee_id")
        ordering = ["employee_id"]
        indexes = [
            models.Index(fields=["company", "employee_id"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "department"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee_id} - {self.first_name} {self.last_name}".strip()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def is_active_on(self, target_date) -> bool:
        if self.status in {EmployeeStatus.TERMINATED, EmployeeStatus.RESIGNED}:
            return False
        if self.date_of_joining and self.date_of_joining > target_date:
            return False
        if self.date_of_exit and self.date_of_exit < target_date:
            return False
        return self.is_active


class AttendanceStatus(models.TextChoices):
    PRESENT = "PRESENT", "Present"
    ABSENT = "ABSENT", "Absent"
    LEAVE = "LEAVE", "Leave"
    HALF_DAY = "HALF_DAY", "Half Day"
    REMOTE = "REMOTE", "Remote"


class AttendanceSource(models.TextChoices):
    MANUAL = "MANUAL", "Manual"
    BIOMETRIC = "BIOMETRIC", "Biometric"
    GEO_FENCED = "GEO_FENCED", "Geo-fenced Mobile"
    IMPORTED = "IMPORTED", "Imported"


class Attendance(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="attendances",
    )
    shift = models.ForeignKey(
        "ShiftTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendances",
    )
    date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
    )
    source = models.CharField(
        max_length=20,
        choices=AttendanceSource.choices,
        default=AttendanceSource.MANUAL,
    )
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    worked_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    overtime_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    notes = models.TextField(blank=True)
    gps_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    source_payload = models.JSONField(default=dict, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_attendance",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="attendances",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("employee", "date")
        ordering = ["-date", "employee__employee_id"]
        indexes = [
            models.Index(fields=["company", "date"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee.full_name} - {self.date} ({self.status})"


class LeaveType(CompanyAwareModel):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_paid = models.BooleanField(default=True)
    default_allocation = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    max_carry_forward = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    requires_approval = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class EmployeeLeaveBalance(CompanyAwareModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="leave_balances",
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name="leave_balances",
    )
    year = models.PositiveIntegerField()
    allocated = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    used = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    carry_forward = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )

    class Meta:
        unique_together = ("company", "employee", "leave_type", "year")
        indexes = [
            models.Index(fields=["company", "employee", "year"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee.full_name} - {self.leave_type.code} ({self.year})"

    @property
    def balance(self) -> Decimal:
        return (self.allocated + self.carry_forward) - self.used


class LeaveRequestStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class LeaveRequest(CompanyAwareModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="leave_requests",
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="leave_requests",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    status = models.CharField(
        max_length=20,
        choices=LeaveRequestStatus.choices,
        default=LeaveRequestStatus.DRAFT,
    )
    reason = models.TextField(blank=True)
    manager_note = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leave_requests",
    )

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "start_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee.full_name} {self.leave_type.code} {self.start_date} - {self.end_date}"


class PayrollRunStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    COMPUTED = "COMPUTED", "Computed"
    APPROVED = "APPROVED", "Approved"
    POSTED = "POSTED", "Posted"
    CANCELLED = "CANCELLED", "Cancelled"


class PayrollRun(CompanyAwareModel):
    period_start = models.DateField()
    period_end = models.DateField()
    period_label = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=20,
        choices=PayrollRunStatus.choices,
        default=PayrollRunStatus.DRAFT,
    )
    notes = models.TextField(blank=True)
    expense_account = models.ForeignKey(
        "finance.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payroll_expense_runs",
    )
    liability_account = models.ForeignKey(
        "finance.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payroll_liability_runs",
    )
    journal_voucher = models.ForeignKey(
        "finance.JournalVoucher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payroll_runs",
    )
    gross_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    deduction_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    net_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_payroll_runs",
    )
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-period_start"]
        indexes = [
            models.Index(fields=["company", "period_start"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.company.code} payroll {self.label}"

    @property
    def label(self) -> str:
        if self.period_label:
            return self.period_label
        if self.period_start and self.period_end:
            if self.period_start.month == self.period_end.month and self.period_start.year == self.period_end.year:
                return self.period_start.strftime("%b %Y")
            return f"{self.period_start.strftime('%d %b %Y')} - {self.period_end.strftime('%d %b %Y')}"
        return "Payroll Run"

    def recalculate_totals(self, save: bool = True) -> None:
        aggregates = self.lines.aggregate(
            gross=models.Sum("gross_pay"),
            deductions=models.Sum("deduction_total"),
            net=models.Sum("net_pay"),
        )
        self.gross_total = aggregates.get("gross") or Decimal("0.00")
        self.deduction_total = aggregates.get("deductions") or Decimal("0.00")
        self.net_total = aggregates.get("net") or Decimal("0.00")
        if save:
            self.save(
                update_fields=[
                    "gross_total",
                    "deduction_total",
                    "net_total",
                    "updated_at",
                ]
            )

    def mark_posted(self, voucher) -> None:
        self.status = PayrollRunStatus.POSTED
        self.journal_voucher = voucher
        self.save(update_fields=["status", "journal_voucher", "updated_at"])


class PayrollLine(CompanyAwareModel):
    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="payroll_lines",
    )
    attendance_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    leave_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    base_pay = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    allowance_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    overtime_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    overtime_pay = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    gross_pay = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    deduction_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    net_pay = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    remarks = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("payroll_run", "employee")
        ordering = ["employee__employee_id"]

    def __str__(self) -> str:
        return f"{self.payroll_run.label} - {self.employee.full_name}"

    def save(self, *args, **kwargs):
        if not self.company_id and self.payroll_run_id:
            self.company = self.payroll_run.company
        if not self.created_by and self.payroll_run.generated_by:
            self.created_by = self.payroll_run.generated_by
        super().save(*args, **kwargs)
