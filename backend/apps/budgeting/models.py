from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from apps.companies.models import Company, CompanyGroup

User = settings.AUTH_USER_MODEL


class CostCenter(models.Model):
    class CostCenterType(models.TextChoices):
        DEPARTMENT = "department", "Department"
        BRANCH = "branch", "Branch"
        PROGRAM = "program", "Program / Grant"
        PROJECT = "project", "Project"
        PRODUCTION_LINE = "production_line", "Production Line"

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255, default="Untitled Budget", blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='children')
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='cost_centers')
    company_group = models.ForeignKey(CompanyGroup, on_delete=models.PROTECT, null=True, blank=True, related_name='cost_centers')
    cost_center_type = models.CharField(max_length=32, choices=CostCenterType.choices, default=CostCenterType.DEPARTMENT)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='primary_cost_centers')
    deputy_owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='backup_cost_centers')
    default_currency = models.CharField(max_length=3, default='USD')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    kpi_snapshot = models.JSONField(default=dict, blank=True)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["code"]
        indexes = [
            models.Index(fields=["company", "cost_center_type"], name="budgeting_c_company_b28430_idx"),
            models.Index(fields=["company", "is_active"], name="budgeting_c_company_964e12_idx"),
        ]

    def __str__(self):
        prefix = f"{self.company.code} · " if hasattr(self.company, "code") else ""
        return f"{prefix}{self.code} - {self.name}"

    @property
    def active_budget_periods(self):
        today = timezone.now().date()
        return self.budgets.filter(period_start__lte=today, period_end__gte=today, status=Budget.STATUS_ACTIVE)

    def update_kpi_snapshot(self, **metrics):
        snapshot = {**(self.kpi_snapshot or {}), **metrics}
        self.kpi_snapshot = snapshot
        self.save(update_fields=["kpi_snapshot", "updated_at"])


class Budget(models.Model):
    STATUS_DRAFT = "DRAFT"
    STATUS_PROPOSED = "PROPOSED"
    STATUS_UNDER_REVIEW = "UNDER_REVIEW"
    STATUS_ACTIVE = "ACTIVE"
    STATUS_LOCKED = "LOCKED"
    STATUS_CLOSED = "CLOSED"
    STATUS_ARCHIVED = "ARCHIVED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PROPOSED, "Proposed"),
        (STATUS_UNDER_REVIEW, "Under Review"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_LOCKED, "Locked"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    TYPE_OPERATIONAL = "operational"
    TYPE_OPEX = "opex"
    TYPE_CAPEX = "capex"
    TYPE_REVENUE = "revenue"

    TYPE_CHOICES = [
        (TYPE_OPERATIONAL, "Operational / Production"),
        (TYPE_OPEX, "Department OPEX"),
        (TYPE_CAPEX, "Capital Expenditure"),
        (TYPE_REVENUE, "Revenue Target"),
    ]

    cost_center = models.ForeignKey(CostCenter, on_delete=models.PROTECT, related_name='budgets')
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='budgets')
    name = models.CharField(max_length=255, default="Untitled Budget")
    budget_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_OPERATIONAL)
    period_start = models.DateField(default=timezone.now)
    period_end = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    consumed = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    threshold_percent = models.PositiveIntegerField(default=90)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    workflow_state = models.CharField(max_length=120, blank=True, default="")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_budgets')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_budgets')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_budgets')
    approved_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_start", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["cost_center", "budget_type", "period_start", "period_end"],
                name="unique_budget_period_per_type",
            ),
        ]
        indexes = [
            models.Index(
                fields=["company", "budget_type", "status"],
                name="budgeting_b_company_a6095c_idx",
            ),
            models.Index(
                fields=["period_start", "period_end"],
                name="budgeting_b_period__d9335e_idx",
            ),
        ]

    @property
    def available(self) -> Decimal:
        return self.amount - self.consumed

    @property
    def duration_days(self) -> int:
        return (self.period_end - self.period_start).days + 1

    @property
    def line_count(self) -> int:
        return self.lines.count()

    def recalculate_totals(self, commit: bool = True):
        totals = self.lines.aggregate(
            value_limit=models.Sum("value_limit"),
            consumed_value=models.Sum("consumed_value"),
        )
        total_limit = totals.get("value_limit") or Decimal("0.00")
        consumed = totals.get("consumed_value") or Decimal("0.00")
        self.amount = total_limit
        self.consumed = consumed
        if commit:
            self.save(update_fields=["amount", "consumed", "updated_at"])
        return total_limit, consumed

    def mark_active(self, user=None):
        self.status = self.STATUS_ACTIVE
        self.approved_at = timezone.now()
        if user:
            self.approved_by = user
        self.save(update_fields=["status", "approved_at", "approved_by", "updated_at"])

    def lock(self, user=None):
        self.status = self.STATUS_LOCKED
        self.locked_at = timezone.now()
        if user:
            self.updated_by = user
        self.save(update_fields=["status", "locked_at", "updated_by", "updated_at"])

    def close(self, user=None):
        self.status = self.STATUS_CLOSED
        if user:
            self.updated_by = user
        self.save(update_fields=["status", "updated_by", "updated_at"])


class BudgetLine(models.Model):
    class ProcurementClass(models.TextChoices):
        STOCK_ITEM = "stock_item", "Stock Item"
        SERVICE_ITEM = "service_item", "Service / Expense"
        CAPEX_ITEM = "capex_item", "Capex Item"

    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name="lines")
    sequence = models.PositiveIntegerField(default=1)
    procurement_class = models.CharField(max_length=20, choices=ProcurementClass.choices)
    item_code = models.CharField(max_length=64, blank=True)
    item_name = models.CharField(max_length=255)
    category = models.CharField(max_length=120, blank=True)
    project_code = models.CharField(max_length=64, blank=True)
    qty_limit = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0"))
    value_limit = models.DecimalField(max_digits=20, decimal_places=2)
    standard_price = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    tolerance_percent = models.PositiveIntegerField(default=5)
    consumed_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0"))
    consumed_value = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    committed_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0"))
    committed_value = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    budget_owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_budget_lines')
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sequence", "id"]
        constraints = [
            models.UniqueConstraint(fields=["budget", "sequence"], name="unique_budget_line_sequence"),
        ]
        indexes = [
            models.Index(fields=["budget", "procurement_class"], name="budgeting_b_budget__8d9b4c_idx"),
            models.Index(fields=["item_code"], name="budgeting_b_item_co_a819b1_idx"),
        ]

    def __str__(self):
        return f"{self.budget.name} · {self.item_name}"

    @property
    def remaining_value(self) -> Decimal:
        return (self.value_limit or Decimal("0")) - (self.consumed_value or Decimal("0"))

    @property
    def remaining_quantity(self) -> Decimal:
        return (self.qty_limit or Decimal("0")) - (self.consumed_quantity or Decimal("0"))

    @property
    def available_value(self) -> Decimal:
        return self.remaining_value - (self.committed_value or Decimal("0"))

    @property
    def available_quantity(self) -> Decimal:
        return self.remaining_quantity - (self.committed_quantity or Decimal("0"))

    def record_usage(self, quantity: Decimal, amount: Decimal, *, commit: bool = True):
        self.consumed_quantity = (self.consumed_quantity or Decimal("0")) + quantity
        self.consumed_value = (self.consumed_value or Decimal("0")) + amount
        if commit:
            self.save(update_fields=["consumed_quantity", "consumed_value", "updated_at"])
            self.budget.recalculate_totals(commit=True)
        return self.consumed_quantity, self.consumed_value

    def recalculate_commitments(self, commit: bool = True) -> tuple[Decimal, Decimal]:
        totals = self.commitments.filter(
            status__in=BudgetCommitment.ACTIVE_STATUSES  # type: ignore[name-defined]
        ).aggregate(
            committed_qty=Sum("committed_quantity") or Decimal("0"),
            committed_val=Sum("committed_value") or Decimal("0"),
            consumed_qty=Sum("consumed_quantity") or Decimal("0"),
            consumed_val=Sum("consumed_value") or Decimal("0"),
            released_qty=Sum("released_quantity") or Decimal("0"),
            released_val=Sum("released_value") or Decimal("0"),
        )

        committed_qty = totals.get("committed_qty") or Decimal("0")
        committed_val = totals.get("committed_val") or Decimal("0")
        consumed_qty = totals.get("consumed_qty") or Decimal("0")
        consumed_val = totals.get("consumed_val") or Decimal("0")
        released_qty = totals.get("released_qty") or Decimal("0")
        released_val = totals.get("released_val") or Decimal("0")

        outstanding_qty = committed_qty - consumed_qty - released_qty
        outstanding_val = committed_val - consumed_val - released_val

        self.committed_quantity = max(outstanding_qty, Decimal("0"))
        self.committed_value = max(outstanding_val, Decimal("0"))

        if commit:
            self.save(update_fields=["committed_quantity", "committed_value", "updated_at"])
        return self.committed_quantity, self.committed_value


class BudgetUsage(models.Model):
    USAGE_TYPE_CHOICES = [
        ("stock_issue", "Stock Issue"),
        ("service_receipt", "Service Delivery"),
        ("capex_receipt", "Capex Receipt"),
        ("journal", "Finance Journal"),
        ("manual_adjust", "Manual Adjustment"),
        ("procurement_receipt", "Procurement Receipt"),
        ("overtime", "Overtime"),
    ]

    budget_line = models.ForeignKey(BudgetLine, on_delete=models.CASCADE, related_name="usage_events")
    usage_date = models.DateField(default=timezone.now)
    usage_type = models.CharField(max_length=40, choices=USAGE_TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0"))
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    reference_type = models.CharField(max_length=64)
    reference_id = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='budget_usage_events')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-usage_date", "-created_at"]
        indexes = [
            models.Index(fields=["reference_type", "reference_id"], name="budgeting_b_referen_0454ab_idx"),
        ]

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        result = super().save(*args, **kwargs)
        if is_new:
            self.budget_line.record_usage(self.quantity, self.amount, commit=True)
        return result


class BudgetCommitment(models.Model):
    class Status(models.TextChoices):
        RESERVED = "reserved", "Reserved"
        CONVERTED = "converted", "Converted to Order"
        RELEASED = "released", "Released"
        CONSUMED = "consumed", "Consumed"

    ACTIVE_STATUSES = {Status.RESERVED, Status.CONVERTED}

    budget_line = models.ForeignKey(BudgetLine, on_delete=models.CASCADE, related_name="commitments")
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="budget_commitments")
    cost_center = models.ForeignKey(CostCenter, on_delete=models.PROTECT, related_name="budget_commitments")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RESERVED)
    source_type = models.CharField(max_length=32)
    source_reference = models.CharField(max_length=64)
    committed_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0"))
    committed_value = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    consumed_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0"))
    consumed_value = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    released_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0"))
    released_value = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_budget_commitments"
    )
    reserved_at = models.DateTimeField(auto_now_add=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("budget_line", "source_type", "source_reference")
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["source_type", "source_reference"]),
        ]

    def __str__(self) -> str:
        return f"{self.source_type}:{self.source_reference} -> {self.budget_line}"

    @property
    def remaining_quantity(self) -> Decimal:
        committed = self.committed_quantity or Decimal("0")
        consumed = self.consumed_quantity or Decimal("0")
        released = self.released_quantity or Decimal("0")
        return max(committed - consumed - released, Decimal("0"))

    @property
    def remaining_value(self) -> Decimal:
        committed = self.committed_value or Decimal("0")
        consumed = self.consumed_value or Decimal("0")
        released = self.released_value or Decimal("0")
        return max(committed - consumed - released, Decimal("0"))

    def save(self, *args, **kwargs):
        if not self.company_id and self.budget_line_id:
            self.company = self.budget_line.budget.company
        if not self.cost_center_id and self.budget_line_id:
            self.cost_center = self.budget_line.budget.cost_center
        super().save(*args, **kwargs)
        self.budget_line.recalculate_commitments(commit=True)

    def delete(self, *args, **kwargs):
        budget_line = self.budget_line
        super().delete(*args, **kwargs)
        budget_line.recalculate_commitments(commit=True)

    def mark_converted(self, *, timestamp=None):
        self.status = self.Status.CONVERTED
        self.converted_at = timestamp or timezone.now()
        self.save(update_fields=["status", "converted_at", "updated_at"])

    def release(self, quantity: Decimal, value: Decimal, *, timestamp=None):
        self.released_quantity = (self.released_quantity or Decimal("0")) + quantity
        self.released_value = (self.released_value or Decimal("0")) + value
        if self.remaining_quantity <= Decimal("0") and self.remaining_value <= Decimal("0"):
            self.status = self.Status.RELEASED
            self.released_at = timestamp or timezone.now()
        self.save(update_fields=["released_quantity", "released_value", "status", "released_at", "updated_at"])

    def consume(self, quantity: Decimal, value: Decimal, *, timestamp=None):
        self.consumed_quantity = (self.consumed_quantity or Decimal("0")) + quantity
        self.consumed_value = (self.consumed_value or Decimal("0")) + value
        if self.remaining_quantity <= Decimal("0") and self.remaining_value <= Decimal("0"):
            self.status = self.Status.CONSUMED
            self.consumed_at = timestamp or timezone.now()
        self.save(update_fields=["consumed_quantity", "consumed_value", "status", "consumed_at", "updated_at"])


class BudgetOverrideRequest(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    cost_center = models.ForeignKey(CostCenter, on_delete=models.PROTECT, related_name="override_requests")
    budget_line = models.ForeignKey(BudgetLine, on_delete=models.SET_NULL, null=True, blank=True, related_name="override_requests")
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="budget_override_requests")
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="budget_override_requests")
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="budget_override_decisions")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reason = models.TextField()
    requested_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0"))
    requested_amount = models.DecimalField(max_digits=20, decimal_places=2)
    decision_notes = models.TextField(blank=True)
    reference_type = models.CharField(max_length=64, blank=True)
    reference_id = models.CharField(max_length=64, blank=True)
    severity = models.CharField(max_length=32, blank=True, default="")
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"], name="budgeting_b_company_384006_idx"),
            models.Index(fields=["reference_type", "reference_id"], name="budgeting_b_referen_f62276_idx"),
        ]

    def mark(self, status: str, *, user=None, notes: str = ""):
        self.status = status
        self.decision_notes = notes
        self.approver = user
        self.approved_at = timezone.now()
        self.save(update_fields=["status", "decision_notes", "approver", "approved_at", "updated_at"])


class BudgetConsumptionSnapshot(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name="snapshots")
    snapshot_date = models.DateField(default=timezone.now)
    total_limit = models.DecimalField(max_digits=20, decimal_places=2)
    total_consumed = models.DecimalField(max_digits=20, decimal_places=2)
    total_remaining = models.DecimalField(max_digits=20, decimal_places=2)
    metrics = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-snapshot_date"]
        constraints = [
            models.UniqueConstraint(fields=["budget", "snapshot_date"], name="unique_budget_snapshot_per_day"),
        ]
