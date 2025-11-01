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
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=30, blank=True)
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
    probation_end_date = models.DateField(null=True, blank=True)
    confirmation_date = models.DateField(null=True, blank=True)
    last_promotion_date = models.DateField(null=True, blank=True)
    last_increment_date = models.DateField(null=True, blank=True)
    notice_period_days = models.PositiveIntegerField(default=30)
    payroll_currency = models.CharField(max_length=3, default="BDT")
    bank_name = models.CharField(max_length=120, blank=True)
    bank_account_number = models.CharField(max_length=120, blank=True)
    tax_identification_number = models.CharField(max_length=60, blank=True)
    photo = models.URLField(blank=True, help_text="URL to employee photo")
    blood_group = models.CharField(max_length=10, blank=True)
    work_location = models.CharField(max_length=255, blank=True)
    employee_type_tag = models.CharField(
        max_length=50,
        blank=True,
        help_text="Additional classification: management, executive, worker, etc."
    )
    rehire_eligible = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

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



class Holiday(CompanyAwareModel):
    name = models.CharField(max_length=100)
    date = models.DateField()
    is_optional = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ('company', 'date')
        ordering = ['date']
        indexes = [
            models.Index(fields=["company", "date"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.date})"


# ============================================================================
# 2.1 TIMESHEET MANAGEMENT & PROJECT COST ALLOCATION
# ============================================================================

class Project(CompanyAwareModel):
    """Project entity for timesheet tracking"""
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    client_name = models.CharField(max_length=200, blank=True)
    project_manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_projects"
    )
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects"
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    budget_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    is_billable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["-start_date", "name"]
        indexes = [
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["company", "project_manager"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class ProjectTask(CompanyAwareModel):
    """Tasks within projects for detailed time tracking"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks"
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks"
    )
    estimated_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    is_billable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "project", "code")
        ordering = ["project", "code"]
        indexes = [
            models.Index(fields=["company", "project"]),
            models.Index(fields=["company", "assigned_to"]),
        ]

    def __str__(self):
        return f"{self.project.code}/{self.code} - {self.name}"


class TimesheetStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class Timesheet(CompanyAwareModel):
    """Weekly/period timesheet header"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="timesheets"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=TimesheetStatus.choices,
        default=TimesheetStatus.DRAFT
    )
    total_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    billable_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_timesheets"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_timesheets"
    )
    approver_notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("company", "employee", "period_start")
        ordering = ["-period_start", "employee__employee_id"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "employee", "period_start"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.period_start} to {self.period_end}"

    def recalculate_totals(self):
        """Recalculate total and billable hours from lines"""
        aggregates = self.lines.aggregate(
            total=models.Sum("hours"),
            billable=models.Sum("hours", filter=models.Q(is_billable=True))
        )
        self.total_hours = aggregates.get("total") or Decimal("0.00")
        self.billable_hours = aggregates.get("billable") or Decimal("0.00")
        self.save(update_fields=["total_hours", "billable_hours", "updated_at"])


class TimesheetLine(CompanyAwareModel):
    """Individual time entries per day/task"""
    timesheet = models.ForeignKey(
        Timesheet,
        on_delete=models.CASCADE,
        related_name="lines"
    )
    date = models.DateField()
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="timesheet_lines"
    )
    task = models.ForeignKey(
        ProjectTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timesheet_lines"
    )
    hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(24)]
    )
    is_billable = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
        help_text="Rate for billing calculation"
    )

    class Meta:
        ordering = ["date", "project"]
        indexes = [
            models.Index(fields=["company", "timesheet"]),
            models.Index(fields=["company", "project", "date"]),
        ]

    def __str__(self):
        return f"{self.timesheet.employee.full_name} - {self.project.code} - {self.date}"

    @property
    def billing_amount(self):
        """Calculate billing amount for this line"""
        if self.is_billable and self.hourly_rate:
            return (self.hours or Decimal("0.00")) * (self.hourly_rate or Decimal("0.00"))
        return Decimal("0.00")


# ============================================================================
# 2.5 PERFORMANCE MANAGEMENT SYSTEM
# ============================================================================

class PerformanceReviewCycle(CompanyAwareModel):
    """Annual/periodic review cycle"""
    name = models.CharField(max_length=150)
    year = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    self_assessment_deadline = models.DateField(null=True, blank=True)
    manager_review_deadline = models.DateField(null=True, blank=True)
    calibration_deadline = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("company", "year", "name")
        ordering = ["-year", "-start_date"]
        indexes = [
            models.Index(fields=["company", "year"]),
            models.Index(fields=["company", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.year})"


class PerformanceGoal(CompanyAwareModel):
    """SMART goals for employees"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="performance_goals"
    )
    review_cycle = models.ForeignKey(
        PerformanceReviewCycle,
        on_delete=models.CASCADE,
        related_name="goals"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(
        max_length=50,
        choices=[
            ("BUSINESS", "Business Result"),
            ("COMPETENCY", "Competency Development"),
            ("PROJECT", "Project Delivery"),
            ("OTHER", "Other")
        ],
        default="BUSINESS"
    )
    target_value = models.CharField(max_length=255, blank=True)
    weight_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("NOT_STARTED", "Not Started"),
            ("IN_PROGRESS", "In Progress"),
            ("ACHIEVED", "Achieved"),
            ("PARTIALLY_ACHIEVED", "Partially Achieved"),
            ("NOT_ACHIEVED", "Not Achieved")
        ],
        default="NOT_STARTED"
    )
    achievement_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    employee_comments = models.TextField(blank=True)
    manager_comments = models.TextField(blank=True)

    class Meta:
        ordering = ["review_cycle", "-weight_percentage"]
        indexes = [
            models.Index(fields=["company", "employee", "review_cycle"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.title}"


class PerformanceReviewStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SELF_ASSESSMENT = "SELF_ASSESSMENT", "Self Assessment"
    MANAGER_REVIEW = "MANAGER_REVIEW", "Manager Review"
    CALIBRATION = "CALIBRATION", "Calibration"
    COMPLETED = "COMPLETED", "Completed"


class PerformanceReview(CompanyAwareModel):
    """Main performance review record"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="performance_reviews"
    )
    review_cycle = models.ForeignKey(
        PerformanceReviewCycle,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    reviewer = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conducted_reviews"
    )
    status = models.CharField(
        max_length=20,
        choices=PerformanceReviewStatus.choices,
        default=PerformanceReviewStatus.DRAFT
    )

    # Self assessment
    self_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    self_comments = models.TextField(blank=True)
    self_completed_at = models.DateTimeField(null=True, blank=True)

    # Manager assessment
    manager_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    manager_comments = models.TextField(blank=True)
    manager_completed_at = models.DateTimeField(null=True, blank=True)

    # Final rating
    final_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    final_comments = models.TextField(blank=True)
    calibration_notes = models.TextField(blank=True)

    # Recommendations
    promotion_recommended = models.BooleanField(default=False)
    increment_recommended_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    development_plan = models.TextField(blank=True)

    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("company", "employee", "review_cycle")
        ordering = ["-review_cycle__year", "employee__employee_id"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "employee"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.review_cycle.name}"


class CompetencyType(models.TextChoices):
    TECHNICAL = "TECHNICAL", "Technical"
    BEHAVIORAL = "BEHAVIORAL", "Behavioral"
    LEADERSHIP = "LEADERSHIP", "Leadership"


class Competency(CompanyAwareModel):
    """Competency framework"""
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    competency_type = models.CharField(
        max_length=20,
        choices=CompetencyType.choices,
        default=CompetencyType.BEHAVIORAL
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "name")
        ordering = ["competency_type", "name"]
        verbose_name_plural = "Competencies"

    def __str__(self):
        return self.name


class CompetencyRating(CompanyAwareModel):
    """Competency ratings within performance reviews"""
    performance_review = models.ForeignKey(
        PerformanceReview,
        on_delete=models.CASCADE,
        related_name="competency_ratings"
    )
    competency = models.ForeignKey(
        Competency,
        on_delete=models.CASCADE,
        related_name="ratings"
    )
    self_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    manager_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    comments = models.TextField(blank=True)

    class Meta:
        unique_together = ("performance_review", "competency")
        ordering = ["competency__competency_type", "competency__name"]

    def __str__(self):
        return f"{self.performance_review.employee.full_name} - {self.competency.name}"


# ============================================================================
# 2.6 RECRUITMENT & ONBOARDING
# ============================================================================

class JobRequisitionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    FILLED = "FILLED", "Filled"
    CANCELLED = "CANCELLED", "Cancelled"


class JobRequisition(CompanyAwareModel):
    """Job opening request"""
    requisition_number = models.CharField(max_length=50, unique=True)
    job_title = models.CharField(max_length=200)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="job_requisitions"
    )
    grade = models.ForeignKey(
        EmploymentGrade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_requisitions"
    )
    requested_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_job_requisitions"
    )
    number_of_positions = models.PositiveIntegerField(default=1)
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME
    )
    justification = models.TextField()
    job_description = models.TextField()
    required_qualifications = models.TextField()
    preferred_qualifications = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=JobRequisitionStatus.choices,
        default=JobRequisitionStatus.DRAFT
    )
    target_start_date = models.DateField(null=True, blank=True)
    budget_allocated = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_job_requisitions"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "department"]),
        ]

    def __str__(self):
        return f"{self.requisition_number} - {self.job_title}"


class CandidateStatus(models.TextChoices):
    NEW = "NEW", "New"
    SCREENING = "SCREENING", "Screening"
    INTERVIEW = "INTERVIEW", "Interview"
    OFFER = "OFFER", "Offer"
    HIRED = "HIRED", "Hired"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class Candidate(CompanyAwareModel):
    """Job applicant"""
    candidate_number = models.CharField(max_length=50)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    job_requisition = models.ForeignKey(
        JobRequisition,
        on_delete=models.CASCADE,
        related_name="candidates"
    )
    status = models.CharField(
        max_length=20,
        choices=CandidateStatus.choices,
        default=CandidateStatus.NEW
    )
    source = models.CharField(
        max_length=100,
        blank=True,
        help_text="Recruitment source (LinkedIn, Referral, Job Board, etc.)"
    )
    resume_url = models.URLField(blank=True)
    cover_letter = models.TextField(blank=True)
    current_employer = models.CharField(max_length=200, blank=True)
    current_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    expected_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    notice_period_days = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    class Meta:
        unique_together = ("company", "candidate_number")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "job_requisition"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.candidate_number}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class InterviewType(models.TextChoices):
    PHONE = "PHONE", "Phone Screening"
    VIDEO = "VIDEO", "Video Interview"
    ONSITE = "ONSITE", "Onsite Interview"
    TECHNICAL = "TECHNICAL", "Technical Assessment"
    HR = "HR", "HR Round"
    PANEL = "PANEL", "Panel Interview"


class InterviewStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    NO_SHOW = "NO_SHOW", "No Show"


class Interview(CompanyAwareModel):
    """Interview scheduling and feedback"""
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="interviews"
    )
    interview_type = models.CharField(
        max_length=20,
        choices=InterviewType.choices,
        default=InterviewType.PHONE
    )
    scheduled_date = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    interviewer = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conducted_interviews"
    )
    status = models.CharField(
        max_length=20,
        choices=InterviewStatus.choices,
        default=InterviewStatus.SCHEDULED
    )
    location = models.CharField(max_length=255, blank=True)
    meeting_link = models.URLField(blank=True)

    # Feedback
    feedback = models.TextField(blank=True)
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    recommendation = models.CharField(
        max_length=20,
        choices=[
            ("STRONG_HIRE", "Strong Hire"),
            ("HIRE", "Hire"),
            ("MAYBE", "Maybe"),
            ("NO_HIRE", "No Hire")
        ],
        blank=True
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["scheduled_date"]
        indexes = [
            models.Index(fields=["company", "candidate"]),
            models.Index(fields=["company", "scheduled_date"]),
        ]

    def __str__(self):
        return f"{self.candidate.full_name} - {self.interview_type} - {self.scheduled_date.date()}"


class OnboardingChecklistItem(CompanyAwareModel):
    """Template checklist items for onboarding"""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=50,
        choices=[
            ("DOCUMENTATION", "Documentation"),
            ("IT_SETUP", "IT Setup"),
            ("HR_ORIENTATION", "HR Orientation"),
            ("TRAINING", "Training"),
            ("INTRODUCTION", "Team Introduction"),
            ("OTHER", "Other")
        ],
        default="DOCUMENTATION"
    )
    responsible_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_items"
    )
    sequence = models.PositiveIntegerField(default=0)
    due_days_from_joining = models.PositiveIntegerField(
        default=0,
        help_text="Days from joining date"
    )
    is_mandatory = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sequence", "category"]
        indexes = [
            models.Index(fields=["company", "is_active"]),
        ]

    def __str__(self):
        return self.title


class OnboardingStatus(models.TextChoices):
    NOT_STARTED = "NOT_STARTED", "Not Started"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"


class EmployeeOnboarding(CompanyAwareModel):
    """Onboarding tracker for new hire"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="onboarding_tracker"
    )
    status = models.CharField(
        max_length=20,
        choices=OnboardingStatus.choices,
        default=OnboardingStatus.NOT_STARTED
    )
    buddy = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mentored_employees"
    )
    notes = models.TextField(blank=True)
    probation_end_date = models.DateField(null=True, blank=True)
    probation_review_scheduled = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("company", "employee")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employee.full_name} Onboarding"


class OnboardingTask(CompanyAwareModel):
    """Individual onboarding task instance"""
    onboarding = models.ForeignKey(
        EmployeeOnboarding,
        on_delete=models.CASCADE,
        related_name="tasks"
    )
    checklist_item = models.ForeignKey(
        OnboardingChecklistItem,
        on_delete=models.CASCADE,
        related_name="task_instances"
    )
    due_date = models.DateField()
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_onboarding_tasks"
    )
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("onboarding", "checklist_item")
        ordering = ["due_date", "checklist_item__sequence"]
        indexes = [
            models.Index(fields=["company", "onboarding"]),
            models.Index(fields=["company", "is_completed"]),
        ]

    def __str__(self):
        return f"{self.onboarding.employee.full_name} - {self.checklist_item.title}"


# ============================================================================
# 2.7 TRAINING & DEVELOPMENT
# ============================================================================

class TrainingCategory(CompanyAwareModel):
    """Training category/type"""
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_compliance_required = models.BooleanField(
        default=False,
        help_text="Mandatory compliance training (safety, harassment, etc.)"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "name")
        ordering = ["name"]
        verbose_name_plural = "Training Categories"

    def __str__(self):
        return self.name


class TrainingCourse(CompanyAwareModel):
    """Training course catalog"""
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        TrainingCategory,
        on_delete=models.CASCADE,
        related_name="courses"
    )
    duration_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    instructor_name = models.CharField(max_length=150, blank=True)
    external_vendor = models.CharField(max_length=200, blank=True)
    cost_per_participant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    is_online = models.BooleanField(default=False)
    is_certification_provided = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    prerequisites = models.TextField(blank=True)
    learning_objectives = models.TextField(blank=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["company", "category"]),
            models.Index(fields=["company", "is_active"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class TrainingSessionStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class TrainingSession(CompanyAwareModel):
    """Scheduled training session"""
    course = models.ForeignKey(
        TrainingCourse,
        on_delete=models.CASCADE,
        related_name="sessions"
    )
    session_number = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    meeting_link = models.URLField(blank=True)
    instructor = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conducted_training_sessions"
    )
    status = models.CharField(
        max_length=20,
        choices=TrainingSessionStatus.choices,
        default=TrainingSessionStatus.SCHEDULED
    )
    actual_participants = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("company", "session_number")
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["company", "course"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.course.name} - {self.session_number}"


class TrainingEnrollmentStatus(models.TextChoices):
    ENROLLED = "ENROLLED", "Enrolled"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class TrainingEnrollment(CompanyAwareModel):
    """Employee enrollment in training"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="training_enrollments"
    )
    session = models.ForeignKey(
        TrainingSession,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    status = models.CharField(
        max_length=20,
        choices=TrainingEnrollmentStatus.choices,
        default=TrainingEnrollmentStatus.ENROLLED
    )
    enrolled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrolled_trainees"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    assessment_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    feedback = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("employee", "session")
        ordering = ["-enrolled_at"]
        indexes = [
            models.Index(fields=["company", "employee"]),
            models.Index(fields=["company", "session"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.session.course.name}"


class Certification(CompanyAwareModel):
    """Professional certifications"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="certifications"
    )
    certification_name = models.CharField(max_length=200)
    issuing_organization = models.CharField(max_length=200)
    certification_number = models.CharField(max_length=100, blank=True)
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    document_url = models.URLField(blank=True)
    is_verified = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-issue_date"]
        indexes = [
            models.Index(fields=["company", "employee"]),
            models.Index(fields=["company", "expiry_date"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.certification_name}"

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def days_until_expiry(self):
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None


# ============================================================================
# 2.8 BENEFITS MANAGEMENT
# ============================================================================

class BenefitPlanType(models.TextChoices):
    HEALTH_INSURANCE = "HEALTH_INSURANCE", "Health Insurance"
    LIFE_INSURANCE = "LIFE_INSURANCE", "Life Insurance"
    PROVIDENT_FUND = "PROVIDENT_FUND", "Provident Fund"
    RETIREMENT = "RETIREMENT", "Retirement/401k"
    ESOP = "ESOP", "Employee Stock Option"
    GYM = "GYM", "Gym Membership"
    TRANSPORT = "TRANSPORT", "Transport Allowance"
    MEAL = "MEAL", "Meal Voucher"
    OTHER = "OTHER", "Other"


class BenefitsPlan(CompanyAwareModel):
    """Benefit plan definition"""
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    plan_type = models.CharField(
        max_length=30,
        choices=BenefitPlanType.choices
    )
    description = models.TextField(blank=True)
    provider_name = models.CharField(max_length=200, blank=True)
    employee_contribution_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    employer_contribution_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    is_percentage_based = models.BooleanField(
        default=False,
        help_text="If true, contributions are percentage of salary"
    )
    eligible_after_days = models.PositiveIntegerField(
        default=0,
        help_text="Eligibility after N days from joining"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["plan_type", "name"]
        indexes = [
            models.Index(fields=["company", "plan_type"]),
            models.Index(fields=["company", "is_active"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class BenefitsEnrollmentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    TERMINATED = "TERMINATED", "Terminated"


class BenefitsEnrollment(CompanyAwareModel):
    """Employee enrollment in benefits"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="benefits_enrollments"
    )
    benefit_plan = models.ForeignKey(
        BenefitsPlan,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    status = models.CharField(
        max_length=20,
        choices=BenefitsEnrollmentStatus.choices,
        default=BenefitsEnrollmentStatus.PENDING
    )
    enrollment_date = models.DateField()
    effective_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)
    employee_contribution = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    employer_contribution = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    dependents_covered = models.PositiveIntegerField(default=0)
    policy_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("employee", "benefit_plan", "enrollment_date")
        ordering = ["-enrollment_date"]
        indexes = [
            models.Index(fields=["company", "employee"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.benefit_plan.name}"


class BenefitsClaimStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    PAID = "PAID", "Paid"


class BenefitsClaim(CompanyAwareModel):
    """Claims against benefits"""
    enrollment = models.ForeignKey(
        BenefitsEnrollment,
        on_delete=models.CASCADE,
        related_name="claims"
    )
    claim_number = models.CharField(max_length=50)
    claim_date = models.DateField()
    claim_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    approved_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    status = models.CharField(
        max_length=20,
        choices=BenefitsClaimStatus.choices,
        default=BenefitsClaimStatus.SUBMITTED
    )
    description = models.TextField()
    supporting_documents_url = models.URLField(blank=True)
    reviewer_notes = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_benefit_claims"
    )

    class Meta:
        unique_together = ("company", "claim_number")
        ordering = ["-claim_date"]
        indexes = [
            models.Index(fields=["company", "enrollment"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.claim_number} - {self.enrollment.employee.full_name}"


# ============================================================================
# 2.9 COMPENSATION MANAGEMENT
# ============================================================================

class CompensationRevisionReason(models.TextChoices):
    ANNUAL = "ANNUAL", "Annual Increment"
    PROMOTION = "PROMOTION", "Promotion"
    MARKET_ADJUSTMENT = "MARKET_ADJUSTMENT", "Market Adjustment"
    PERFORMANCE = "PERFORMANCE", "Performance Based"
    RETENTION = "RETENTION", "Retention"
    OTHER = "OTHER", "Other"


class CompensationRevisionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    HR_REVIEW = "HR_REVIEW", "HR Review"
    FINANCE_REVIEW = "FINANCE_REVIEW", "Finance Review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    IMPLEMENTED = "IMPLEMENTED", "Implemented"


class CompensationRevision(CompanyAwareModel):
    """Salary revision history"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="compensation_revisions"
    )
    revision_number = models.CharField(max_length=50)
    effective_date = models.DateField()
    reason = models.CharField(
        max_length=30,
        choices=CompensationRevisionReason.choices
    )
    previous_salary_structure = models.ForeignKey(
        SalaryStructure,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="previous_revisions"
    )
    new_salary_structure = models.ForeignKey(
        SalaryStructure,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="new_revisions"
    )
    previous_base_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    new_base_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    increment_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    increment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    justification = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=CompensationRevisionStatus.choices,
        default=CompensationRevisionStatus.DRAFT
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_comp_revisions"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_comp_revisions"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    hr_notes = models.TextField(blank=True)
    finance_notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("company", "revision_number")
        ordering = ["-effective_date"]
        indexes = [
            models.Index(fields=["company", "employee"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.revision_number}"

    def save(self, *args, **kwargs):
        if self.new_base_salary and self.previous_base_salary:
            self.increment_amount = self.new_base_salary - self.previous_base_salary
            if self.previous_base_salary > 0:
                self.increment_percentage = (
                    (self.increment_amount / self.previous_base_salary) * Decimal("100")
                ).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)


class BonusType(models.TextChoices):
    PERFORMANCE = "PERFORMANCE", "Performance Bonus"
    ANNUAL = "ANNUAL", "Annual Bonus"
    SIGNING = "SIGNING", "Signing Bonus"
    RETENTION = "RETENTION", "Retention Bonus"
    PROJECT = "PROJECT", "Project Completion"
    COMMISSION = "COMMISSION", "Commission"
    OTHER = "OTHER", "Other"


class BonusStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    APPROVED = "APPROVED", "Approved"
    PAID = "PAID", "Paid"
    CANCELLED = "CANCELLED", "Cancelled"


class Bonus(CompanyAwareModel):
    """Variable pay/bonus tracking"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="bonuses"
    )
    bonus_number = models.CharField(max_length=50)
    bonus_type = models.CharField(
        max_length=20,
        choices=BonusType.choices
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    status = models.CharField(
        max_length=20,
        choices=BonusStatus.choices,
        default=BonusStatus.DRAFT
    )
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    payout_date = models.DateField(null=True, blank=True)
    description = models.TextField()
    performance_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_bonuses"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bonuses"
    )

    class Meta:
        unique_together = ("company", "bonus_number")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "employee"]),
            models.Index(fields=["company", "status"]),
        ]
        verbose_name_plural = "Bonuses"

    def __str__(self):
        return f"{self.employee.full_name} - {self.bonus_type} - {self.amount}"


# ============================================================================
# 2.10 EXIT MANAGEMENT & OFFBOARDING
# ============================================================================

class ExitReason(models.TextChoices):
    RESIGNATION = "RESIGNATION", "Resignation"
    TERMINATION = "TERMINATION", "Termination"
    RETIREMENT = "RETIREMENT", "Retirement"
    CONTRACT_END = "CONTRACT_END", "Contract End"
    MUTUAL = "MUTUAL", "Mutual Separation"
    OTHER = "OTHER", "Other"


class ExitStatus(models.TextChoices):
    INITIATED = "INITIATED", "Initiated"
    NOTICE_PERIOD = "NOTICE_PERIOD", "Notice Period"
    CLEARANCE = "CLEARANCE", "Clearance"
    COMPLETED = "COMPLETED", "Completed"


class EmployeeExit(CompanyAwareModel):
    """Exit/separation management"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="exit_records"
    )
    exit_number = models.CharField(max_length=50)
    exit_reason = models.CharField(
        max_length=20,
        choices=ExitReason.choices
    )
    resignation_date = models.DateField(null=True, blank=True)
    last_working_date = models.DateField()
    notice_period_days = models.PositiveIntegerField(default=0)
    notice_waived = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=ExitStatus.choices,
        default=ExitStatus.INITIATED
    )
    rehire_eligible = models.BooleanField(default=True)
    exit_interview_scheduled = models.BooleanField(default=False)
    exit_interview_date = models.DateField(null=True, blank=True)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="initiated_exits"
    )
    hr_notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("company", "exit_number")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "employee"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.exit_number}"


class ClearanceStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    CLEARED = "CLEARED", "Cleared"
    WITH_DUES = "WITH_DUES", "Cleared with Dues"


class ClearanceChecklist(CompanyAwareModel):
    """Exit clearance checklist template"""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    responsible_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clearance_items"
    )
    sequence = models.PositiveIntegerField(default=0)
    is_mandatory = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sequence"]
        indexes = [
            models.Index(fields=["company", "is_active"]),
        ]

    def __str__(self):
        return self.title


class EmployeeClearance(CompanyAwareModel):
    """Employee clearance tracker"""
    employee_exit = models.ForeignKey(
        EmployeeExit,
        on_delete=models.CASCADE,
        related_name="clearances"
    )
    checklist_item = models.ForeignKey(
        ClearanceChecklist,
        on_delete=models.CASCADE,
        related_name="clearance_instances"
    )
    status = models.CharField(
        max_length=20,
        choices=ClearanceStatus.choices,
        default=ClearanceStatus.PENDING
    )
    dues_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    cleared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cleared_items"
    )
    cleared_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("employee_exit", "checklist_item")
        ordering = ["checklist_item__sequence"]
        indexes = [
            models.Index(fields=["company", "employee_exit"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.employee_exit.employee.full_name} - {self.checklist_item.title}"


class ExitInterview(CompanyAwareModel):
    """Exit interview feedback"""
    employee_exit = models.OneToOneField(
        EmployeeExit,
        on_delete=models.CASCADE,
        related_name="exit_interview"
    )
    interview_date = models.DateField()
    interviewer = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conducted_exit_interviews"
    )

    # Feedback fields
    reason_for_leaving = models.TextField()
    liked_most = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    manager_feedback = models.TextField(blank=True)
    company_culture_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    work_environment_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    compensation_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    growth_opportunities_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    would_recommend_company = models.BooleanField(null=True)
    would_consider_returning = models.BooleanField(null=True)
    additional_comments = models.TextField(blank=True)

    class Meta:
        ordering = ["-interview_date"]
        indexes = [
            models.Index(fields=["company", "interview_date"]),
        ]

    def __str__(self):
        return f"Exit Interview - {self.employee_exit.employee.full_name}"


class FinalSettlement(CompanyAwareModel):
    """Final settlement calculation"""
    employee_exit = models.OneToOneField(
        EmployeeExit,
        on_delete=models.CASCADE,
        related_name="final_settlement"
    )
    settlement_date = models.DateField()

    # Dues TO employee
    pending_salary_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    pending_salary_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    leave_encashment_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    leave_encashment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    gratuity_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    other_dues_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # Dues BY employee
    notice_pay_recovery = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    advance_recovery = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    loan_recovery = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    other_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    gross_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    total_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    net_payable = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    payment_method = models.CharField(max_length=50, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-settlement_date"]
        indexes = [
            models.Index(fields=["company", "settlement_date"]),
            models.Index(fields=["company", "is_paid"]),
        ]

    def __str__(self):
        return f"Settlement - {self.employee_exit.employee.full_name}"

    def calculate_totals(self):
        """Calculate gross, deductions, and net"""
        self.gross_amount = (
            self.pending_salary_amount +
            self.leave_encashment_amount +
            self.gratuity_amount +
            self.other_dues_amount
        )
        self.total_deductions = (
            self.notice_pay_recovery +
            self.advance_recovery +
            self.loan_recovery +
            self.other_deductions
        )
        self.net_payable = self.gross_amount - self.total_deductions
        self.save(update_fields=["gross_amount", "total_deductions", "net_payable", "updated_at"])


# ============================================================================
# 2.11 DOCUMENT MANAGEMENT (HR-SPECIFIC)
# ============================================================================

class DocumentCategory(models.TextChoices):
    RESUME = "RESUME", "Resume/CV"
    ID_PROOF = "ID_PROOF", "ID Proof"
    EDUCATION = "EDUCATION", "Educational Certificate"
    OFFER_LETTER = "OFFER_LETTER", "Offer Letter"
    CONTRACT = "CONTRACT", "Employment Contract"
    SALARY_REVISION = "SALARY_REVISION", "Salary Revision Letter"
    PROMOTION = "PROMOTION", "Promotion Letter"
    PERFORMANCE = "PERFORMANCE", "Performance Review"
    DISCIPLINARY = "DISCIPLINARY", "Disciplinary Action"
    TRAINING = "TRAINING", "Training Certificate"
    VISA = "VISA", "Visa/Work Permit"
    OTHER = "OTHER", "Other"


class DocumentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Approval"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    EXPIRED = "EXPIRED", "Expired"


class EmployeeDocument(CompanyAwareModel):
    """Employee document repository"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="documents"
    )
    document_number = models.CharField(max_length=100, blank=True)
    category = models.CharField(
        max_length=20,
        choices=DocumentCategory.choices
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    document_url = models.URLField(
        help_text="URL to document storage (S3, cloud storage, etc.)"
    )
    file_name = models.CharField(max_length=255)
    file_size_kb = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING
    )
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_hr_documents"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_hr_documents"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    parent_document = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="versions"
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "employee"]),
            models.Index(fields=["company", "category"]),
            models.Index(fields=["company", "expiry_date"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.title}"

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def days_until_expiry(self):
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None


# ============================================================================
# 2.12 POLICY MANAGEMENT (HR INTEGRATION)
# ============================================================================

class PolicyCategory(models.TextChoices):
    LEAVE = "LEAVE", "Leave Policy"
    ATTENDANCE = "ATTENDANCE", "Attendance Policy"
    OVERTIME = "OVERTIME", "Overtime Policy"
    WFH = "WFH", "Work from Home"
    CODE_OF_CONDUCT = "CODE_OF_CONDUCT", "Code of Conduct"
    DRESS_CODE = "DRESS_CODE", "Dress Code"
    HARASSMENT = "HARASSMENT", "Anti-Harassment"
    DISCIPLINARY = "DISCIPLINARY", "Disciplinary"
    EXPENSE = "EXPENSE", "Expense Policy"
    OTHER = "OTHER", "Other"


class PolicyDocument(CompanyAwareModel):
    """HR policy library"""
    policy_code = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    category = models.CharField(
        max_length=30,
        choices=PolicyCategory.choices
    )
    description = models.TextField(blank=True)
    document_url = models.URLField(
        help_text="URL to policy document"
    )
    version = models.CharField(max_length=20, default="1.0")
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_policies"
    )
    is_active = models.BooleanField(default=True)
    requires_acknowledgment = models.BooleanField(default=True)
    content = models.TextField(
        blank=True,
        help_text="Policy content for AI/search indexing"
    )

    class Meta:
        unique_together = ("company", "policy_code", "version")
        ordering = ["-effective_date", "category"]
        indexes = [
            models.Index(fields=["company", "category"]),
            models.Index(fields=["company", "is_active"]),
        ]
        verbose_name_plural = "Policy Documents"

    def __str__(self):
        return f"{self.policy_code} - {self.title} (v{self.version})"


class PolicyAcknowledgment(CompanyAwareModel):
    """Employee policy acknowledgment tracking"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="policy_acknowledgments"
    )
    policy = models.ForeignKey(
        PolicyDocument,
        on_delete=models.CASCADE,
        related_name="acknowledgments"
    )
    acknowledged_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("employee", "policy")
        ordering = ["-acknowledged_at"]
        indexes = [
            models.Index(fields=["company", "employee"]),
            models.Index(fields=["company", "policy"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.policy.title}"


class DisciplinaryActionType(models.TextChoices):
    VERBAL_WARNING = "VERBAL_WARNING", "Verbal Warning"
    WRITTEN_WARNING = "WRITTEN_WARNING", "Written Warning"
    FINAL_WARNING = "FINAL_WARNING", "Final Warning"
    SUSPENSION = "SUSPENSION", "Suspension"
    TERMINATION = "TERMINATION", "Termination"
    OTHER = "OTHER", "Other"


class DisciplinaryAction(CompanyAwareModel):
    """Disciplinary action records"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="disciplinary_actions"
    )
    action_number = models.CharField(max_length=50)
    action_type = models.CharField(
        max_length=20,
        choices=DisciplinaryActionType.choices
    )
    violation_date = models.DateField()
    action_date = models.DateField()
    policy_violated = models.ForeignKey(
        PolicyDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="violations"
    )
    description = models.TextField()
    investigation_notes = models.TextField(blank=True)
    action_taken = models.TextField()
    is_appealed = models.BooleanField(default=False)
    appeal_notes = models.TextField(blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_disciplinary_actions"
    )
    witness_names = models.TextField(blank=True)
    supporting_documents_url = models.URLField(blank=True)

    class Meta:
        unique_together = ("company", "action_number")
        ordering = ["-action_date"]
        indexes = [
            models.Index(fields=["company", "employee"]),
            models.Index(fields=["company", "action_type"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.action_type} - {self.action_date}"


# ============================================================================
# 2.13 COMPLIANCE & REPORTING (Statutory)
# ============================================================================

class ComplianceReportType(models.TextChoices):
    PF_RETURN = "PF_RETURN", "PF Return"
    ESI_RETURN = "ESI_RETURN", "ESI Return"
    TDS_REPORT = "TDS_REPORT", "TDS Report"
    FORM_16 = "FORM_16", "Form 16"
    GRATUITY = "GRATUITY", "Gratuity Report"
    BONUS = "BONUS", "Bonus Report"
    LABOR_LAW = "LABOR_LAW", "Labor Law Compliance"
    EEO = "EEO", "EEO Report"
    SALARY_REGISTER = "SALARY_REGISTER", "Salary Register"
    OTHER = "OTHER", "Other"


class ComplianceReportStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    GENERATED = "GENERATED", "Generated"
    SUBMITTED = "SUBMITTED", "Submitted"
    FILED = "FILED", "Filed"


class ComplianceReport(CompanyAwareModel):
    """Statutory compliance reports"""
    report_number = models.CharField(max_length=50)
    report_type = models.CharField(
        max_length=30,
        choices=ComplianceReportType.choices
    )
    title = models.CharField(max_length=200)
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=ComplianceReportStatus.choices,
        default=ComplianceReportStatus.DRAFT
    )
    report_data = models.JSONField(
        default=dict,
        help_text="Computed report data"
    )
    report_url = models.URLField(blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_compliance_reports"
    )
    generated_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    filing_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("company", "report_number")
        ordering = ["-period_end"]
        indexes = [
            models.Index(fields=["company", "report_type"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.report_number} - {self.title}"


class ReimbursementCategory(models.TextChoices):
    TRAVEL = "TRAVEL", "Travel"
    MEAL = "MEAL", "Meal"
    ACCOMMODATION = "ACCOMMODATION", "Accommodation"
    COMMUNICATION = "COMMUNICATION", "Communication"
    MEDICAL = "MEDICAL", "Medical"
    EDUCATION = "EDUCATION", "Education"
    OTHER = "OTHER", "Other"


class ReimbursementStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    PAID = "PAID", "Paid"


class Reimbursement(CompanyAwareModel):
    """Employee expense reimbursement"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="reimbursements"
    )
    reimbursement_number = models.CharField(max_length=50)
    category = models.CharField(
        max_length=20,
        choices=ReimbursementCategory.choices
    )
    expense_date = models.DateField()
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    approved_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    status = models.CharField(
        max_length=20,
        choices=ReimbursementStatus.choices,
        default=ReimbursementStatus.DRAFT
    )
    description = models.TextField()
    receipt_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="List of receipt URLs"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_reimbursements"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reimbursements"
    )
    approver_notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("company", "reimbursement_number")
        ordering = ["-expense_date"]
        indexes = [
            models.Index(fields=["company", "employee"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.reimbursement_number}"


class AdvanceSalaryStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Requested"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    DISBURSED = "DISBURSED", "Disbursed"
    RECOVERED = "RECOVERED", "Fully Recovered"


class AdvanceSalary(CompanyAwareModel):
    """Salary advance tracking"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="salary_advances"
    )
    advance_number = models.CharField(max_length=50)
    request_date = models.DateField()
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    approved_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    status = models.CharField(
        max_length=20,
        choices=AdvanceSalaryStatus.choices,
        default=AdvanceSalaryStatus.REQUESTED
    )
    reason = models.TextField()
    disbursement_date = models.DateField(null=True, blank=True)
    recovery_installments = models.PositiveIntegerField(default=1)
    recovered_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_salary_advances"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("company", "advance_number")
        ordering = ["-request_date"]
        indexes = [
            models.Index(fields=["company", "employee"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.advance_number}"

    @property
    def balance(self):
        return (self.approved_amount or Decimal("0.00")) - (self.recovered_amount or Decimal("0.00"))


class EmployeeLoanStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    CLOSED = "CLOSED", "Closed"
    DEFAULTED = "DEFAULTED", "Defaulted"


class EmployeeLoan(CompanyAwareModel):
    """Employee loan tracking"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="loans"
    )
    loan_number = models.CharField(max_length=50)
    loan_type = models.CharField(max_length=100)
    principal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    disbursement_date = models.DateField()
    installment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    total_installments = models.PositiveIntegerField()
    paid_installments = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=EmployeeLoanStatus.choices,
        default=EmployeeLoanStatus.ACTIVE
    )
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("company", "loan_number")
        ordering = ["-disbursement_date"]
        indexes = [
            models.Index(fields=["company", "employee"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.loan_number}"

    @property
    def outstanding_amount(self):
        remaining = self.total_installments - self.paid_installments
        return self.installment_amount * remaining


# ============================================================================
# 2.4 ASSET ASSIGNMENT & TRACKING (HR Integration)
# ============================================================================

class AssetAssignmentStatus(models.TextChoices):
    ASSIGNED = "ASSIGNED", "Assigned"
    RETURNED = "RETURNED", "Returned"
    DAMAGED = "DAMAGED", "Damaged"
    LOST = "LOST", "Lost"


class EmployeeAssetAssignment(CompanyAwareModel):
    """Asset assignment to employees"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="asset_assignments"
    )
    asset_code = models.CharField(max_length=100)
    asset_name = models.CharField(max_length=200)
    asset_type = models.CharField(
        max_length=100,
        help_text="Laptop, Phone, Vehicle, etc."
    )
    serial_number = models.CharField(max_length=100, blank=True)
    assignment_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=AssetAssignmentStatus.choices,
        default=AssetAssignmentStatus.ASSIGNED
    )
    condition_at_assignment = models.TextField(blank=True)
    condition_at_return = models.TextField(blank=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_assets"
    )
    return_accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_asset_returns"
    )
    liability_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)]
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-assignment_date"]
        indexes = [
            models.Index(fields=["company", "employee"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.asset_name}"

