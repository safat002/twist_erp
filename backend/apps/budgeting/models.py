from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models import Sum
from django.utils import timezone

from apps.companies.models import Company, CompanyGroup, Branch, Department

User = settings.AUTH_USER_MODEL


class CostCenter(models.Model):
    """
    Cost tracking entity. Each cost center belongs to a department.
    One department may have multiple cost centers.
    """
    class CostCenterType(models.TextChoices):
        DEPARTMENT = "department", "Department"
        BRANCH = "branch", "Branch"
        PROGRAM = "program", "Program / Grant"
        PROJECT = "project", "Project"
        PRODUCTION_LINE = "production_line", "Production Line"

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255, default="Untitled Budget", blank=True, null=True)

    # Hierarchy - Main requirement: Cost center belongs to department
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        null=True,  # Temporarily nullable for migration
        blank=True,
        related_name='cost_centers',
        help_text='Department this cost center belongs to (required for new records)'
    )

    # Legacy/backward compatibility fields
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='children')
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='cost_centers')
    company_group = models.ForeignKey(CompanyGroup, on_delete=models.PROTECT, null=True, blank=True, related_name='cost_centers')

    # Optional: For additional context
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cost_centers',
        help_text='Branch (optional, derived from department if not set)'
    )

    cost_center_type = models.CharField(max_length=32, choices=CostCenterType.choices, default=CostCenterType.DEPARTMENT)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='primary_cost_centers')
    deputy_owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='backup_cost_centers')
    budget_entry_users = models.ManyToManyField(User, blank=True, related_name='budget_entry_cost_centers', help_text="Users who can enter budget lines for this cost center")
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
            models.Index(fields=["department", "is_active"]),
        ]

    def __str__(self):
        prefix = f"{self.company.code} · " if hasattr(self.company, "code") else ""
        return f"{prefix}{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        # Auto-populate company and branch from department if not set
        if self.department_id:
            if not self.company_id:
                self.company = self.department.company
            if not self.branch_id and self.department.branch:
                self.branch = self.department.branch
        super().save(*args, **kwargs)

    @property
    def active_budget_periods(self):
        today = timezone.now().date()
        return self.budgets.filter(period_start__lte=today, period_end__gte=today, status=Budget.STATUS_ACTIVE)

    def update_kpi_snapshot(self, **metrics):
        snapshot = {**(self.kpi_snapshot or {}), **metrics}
        self.kpi_snapshot = snapshot
        self.save(update_fields=["kpi_snapshot", "updated_at"])


class Budget(models.Model):
    # Revised workflow statuses aligned with Budget-Module-Final-Requirements.md
    STATUS_PENDING_NAME_APPROVAL = "pending_name_approval"
    STATUS_DRAFT = "draft"
    STATUS_ENTRY_OPEN = "ENTRY_OPEN"
    STATUS_ENTRY_CLOSED_REVIEW_PENDING = "ENTRY_CLOSED_REVIEW_PENDING"
    STATUS_REVIEW_OPEN = "REVIEW_OPEN"
    STATUS_PENDING_CC_APPROVAL = "PENDING_CC_APPROVAL"
    STATUS_CC_APPROVED = "CC_APPROVED"
    STATUS_PENDING_MODERATOR_REVIEW = "PENDING_MODERATOR_REVIEW"
    STATUS_MODERATOR_REVIEWED = "MODERATOR_REVIEWED"
    STATUS_PENDING_FINAL_APPROVAL = "PENDING_FINAL_APPROVAL"
    STATUS_APPROVED = "APPROVED"
    STATUS_AUTO_APPROVED = "AUTO_APPROVED"
    STATUS_ACTIVE = "ACTIVE"
    STATUS_EXPIRED = "EXPIRED"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ENTRY_OPEN, "Entry Open"),
        (STATUS_ENTRY_CLOSED_REVIEW_PENDING, "Entry Closed - Review Pending"),
        (STATUS_REVIEW_OPEN, "Review Period Open"),
        (STATUS_PENDING_CC_APPROVAL, "Pending CC Approval"),
        (STATUS_CC_APPROVED, "CC Approved"),
        (STATUS_PENDING_MODERATOR_REVIEW, "Pending Moderator Review"),
        (STATUS_MODERATOR_REVIEWED, "Moderator Reviewed"),
        (STATUS_PENDING_FINAL_APPROVAL, "Pending Final Approval"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_AUTO_APPROVED, "Auto Approved"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CLOSED, "Closed"),
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

    # Duration Types (NEW - Section 2.1)
    DURATION_MONTHLY = "monthly"
    DURATION_QUARTERLY = "quarterly"
    DURATION_HALF_YEARLY = "half_yearly"
    DURATION_YEARLY = "yearly"
    DURATION_CUSTOM = "custom"

    DURATION_CHOICES = [
        (DURATION_MONTHLY, "Monthly"),
        (DURATION_QUARTERLY, "Quarterly"),
        (DURATION_HALF_YEARLY, "Half Yearly"),
        (DURATION_YEARLY, "Yearly"),
        (DURATION_CUSTOM, "Custom"),
    ]

    # Optional: when null, budget is company-wide (no cost center)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.PROTECT, null=True, blank=True, related_name='budgets')
    # Optional: restrict which CCs can enter lines against this budget (company-wide cases)
    applicable_cost_centers = models.ManyToManyField(CostCenter, blank=True, related_name='applicable_budgets')
    # For CC budgets derived from a declared budget
    parent_declared = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='cc_budgets')
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='budgets')
    name = models.CharField(max_length=255, default="Untitled Budget")
    budget_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_OPERATIONAL)
    description = models.TextField(blank=True)

    # Budget Name approval status (separate from workflow of lines)
    NAME_STATUS_DRAFT = "DRAFT"
    NAME_STATUS_APPROVED = "APPROVED"
    NAME_STATUS_REJECTED = "REJECTED"
    NAME_STATUS_CHOICES = [
        (NAME_STATUS_DRAFT, "Draft"),
        (NAME_STATUS_APPROVED, "Approved"),
        (NAME_STATUS_REJECTED, "Rejected"),
    ]
    name_status = models.CharField(max_length=16, choices=NAME_STATUS_CHOICES, default=NAME_STATUS_DRAFT)
    name_approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='name_approved_budgets')
    name_approved_at = models.DateTimeField(null=True, blank=True)
    auto_activate = models.BooleanField(default=False, help_text="If ON, auto-activate on period start (excludes held lines)")

    # CUSTOM DURATION SETTINGS (NEW - Section 2.1)
    duration_type = models.CharField(
        max_length=50,
        choices=DURATION_CHOICES,
        default=DURATION_YEARLY,
        help_text="Budget duration type"
    )
    custom_duration_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Days if duration_type=custom"
    )

    # Budget Period (actual effective dates)
    period_start = models.DateField(
        default=timezone.now,
        help_text="When budget becomes effective"
    )
    period_end = models.DateField(
        default=timezone.now,
        help_text="When budget expires"
    )

    # ENTRY PERIOD (Section 2.2)
    entry_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="When department users can start entering budget lines"
    )
    entry_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Deadline for department users to submit budget"
    )
    entry_enabled = models.BooleanField(
        default=True,
        help_text="Toggle to enable/disable entry period"
    )

    # GRACE PERIOD (NEW - Section 8)
    grace_period_days = models.IntegerField(
        default=3,
        help_text="Days after entry period ends before review starts"
    )

    # REVIEW PERIOD (NEW - Section 3)
    review_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="When review period starts (auto-calculated from entry_end + grace)"
    )
    review_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="When review period ends"
    )
    review_enabled = models.BooleanField(
        default=False,
        help_text="Auto-enabled when first item sent back for review"
    )

    # BUDGET IMPACT PERIOD (Section 2.5)
    budget_impact_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="When consumption tracking begins"
    )
    budget_impact_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="When consumption tracking stops"
    )
    budget_impact_enabled = models.BooleanField(
        default=False,
        help_text="Toggle to enable/disable consumption tracking"
    )

    # Legacy active window fields (keep for backward compatibility)
    budget_active_date = models.DateField(null=True, blank=True)
    budget_expire_date = models.DateField(null=True, blank=True)

    # AUTO-APPROVAL SETTINGS (NEW - Section 6)
    auto_approve_if_not_approved = models.BooleanField(
        default=False,
        help_text="Auto-approve budget at budget start date if not approved yet"
    )
    auto_approve_by_role = models.CharField(
        max_length=50,
        blank=True,
        default="Module Owner (System)",
        help_text="Which role should be recorded as auto-approver"
    )
    auto_approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When budget was auto-approved"
    )

    # Amount Tracking (Denormalized)
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total allocated budget amount"
    )
    consumed = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total consumed amount"
    )
    committed = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total committed amount"
    )
    remaining = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total remaining amount"
    )

    # VARIANCE TRACKING (NEW - Section 4)
    total_variance_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Sum of all line modifications (original vs modified)"
    )
    total_variance_count = models.IntegerField(
        default=0,
        help_text="Number of lines with modifications"
    )

    # Status & Workflow
    threshold_percent = models.PositiveIntegerField(default=90)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    workflow_state = models.CharField(max_length=120, blank=True, default="")

    # Approval Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_budgets')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_budgets')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_budgets')
    approved_at = models.DateTimeField(null=True, blank=True)

    # Moderator tracking (NEW)
    moderator_reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderator_reviewed_budgets',
        help_text="Moderator who reviewed this budget"
    )
    moderator_reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When moderator completed review"
    )

    # Final approval tracking
    final_approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='final_approved_budgets',
        help_text="Module owner who gave final approval"
    )
    final_approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When budget was finally approved"
    )

    # Activation tracking
    activated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activated_budgets',
        help_text="User who activated budget (turned on impact tracking)"
    )
    activated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When budget was activated"
    )

    locked_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Revision number for CC budgets (allows multiple submissions per declared budget per CC)
    revision_no = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_start", "-created_at"]
        constraints = [
            # Only one declared budget (company-wide) per type/period
            models.UniqueConstraint(
                fields=["company", "budget_type", "period_start", "period_end"],
                condition=Q(cost_center__isnull=True),
                name="uniq_declared_company_type_period",
            ),
            # CC budgets unique per CC/type/period and revision
            models.UniqueConstraint(
                fields=["company", "budget_type", "period_start", "period_end", "cost_center", "revision_no"],
                condition=Q(cost_center__isnull=False),
                name="uniq_cc_company_type_period_revision",
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

    def __str__(self) -> str:
        try:
            nm = (self.name or "").strip()
        except Exception:
            nm = ""
        if nm:
            return nm
        try:
            comp = getattr(self.company, 'code', None) or getattr(self.company, 'name', '') or ''
        except Exception:
            comp = ''
        try:
            ps = self.period_start.strftime('%Y-%m-%d') if self.period_start else ''
            pe = self.period_end.strftime('%Y-%m-%d') if self.period_end else ''
        except Exception:
            ps = pe = ''
        bt = ''
        try:
            bt = self.get_budget_type_display()
        except Exception:
            pass
        return f"{comp} {bt} {ps}-{pe}".strip()

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
        # If not explicitly set, start active from today
        if not self.budget_active_date:
            self.budget_active_date = timezone.now().date()
        if not self.approved_at:
            self.approved_at = timezone.now()
        if user:
            self.approved_by = user
        self.save(update_fields=[
            "status",
            "approved_at",
            "approved_by",
            "budget_active_date",
            "updated_at",
        ])

    def open_entry(self, *, start_date=None, end_date=None, user=None):
        self.status = self.STATUS_ENTRY_OPEN
        self.entry_enabled = True
        if start_date:
            self.entry_start_date = start_date
        elif not self.entry_start_date:
            self.entry_start_date = timezone.now().date()
        if end_date:
            self.entry_end_date = end_date
        self.updated_by = user or self.updated_by
        self.save(update_fields=["status", "entry_enabled", "entry_start_date", "entry_end_date", "updated_by", "updated_at"])

    def is_entry_period_active(self) -> bool:
        """Check if entry period is active and entry is enabled"""
        today = timezone.now().date()
        if not self.entry_enabled:
            return False
        if self.status not in {self.STATUS_DRAFT, self.STATUS_ENTRY_OPEN}:
            return False
        if self.entry_start_date and today < self.entry_start_date:
            return False
        if self.entry_end_date and today > self.entry_end_date:
            return False
        return True

    def is_review_period_active(self) -> bool:
        """Check if review period is active"""
        if not self.review_start_date or not self.review_end_date:
            return False
        if not self.review_enabled:
            return False
        today = timezone.now().date()
        return self.review_start_date <= today <= self.review_end_date

    def is_budget_impact_active(self) -> bool:
        """Check if budget impact (consumption tracking) is active"""
        if not self.budget_impact_enabled:
            return False
        if not self.budget_impact_start_date or not self.budget_impact_end_date:
            return False
        today = timezone.now().date()
        return self.budget_impact_start_date <= today <= self.budget_impact_end_date

    def calculate_review_start_date(self):
        """Auto-calculate review start date from entry end date + grace period"""
        if self.entry_end_date and self.grace_period_days is not None:
            from datetime import timedelta
            return self.entry_end_date + timedelta(days=self.grace_period_days)
        return None

    def should_auto_approve(self) -> bool:
        """Check if budget should auto-approve at budget start date"""
        from datetime import date
        today = date.today()
        return (
            self.auto_approve_if_not_approved and
            today >= self.period_start and
            self.status not in {self.STATUS_APPROVED, self.STATUS_AUTO_APPROVED, self.STATUS_ACTIVE}
        )

    def get_duration_display(self) -> str:
        """Get human-readable duration"""
        if self.duration_type == self.DURATION_CUSTOM:
            return f"Custom ({self.custom_duration_days} days)"
        return self.get_duration_type_display()

    def can_user_enter_budget(self, user, cost_center=None) -> bool:
        # Authentication
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        # Superusers/system admins can always enter
        if getattr(user, 'is_superuser', False) or getattr(user, 'is_system_admin', False):
            return True
        # Must be within entry period
        if not self.is_entry_period_active():
            return False
        # Determine applicable cost center
        cc = cost_center or getattr(self, 'cost_center', None)
        if cc is None:
            # Company-wide budget: require company‑level permission
            try:
                from apps.permissions.permissions import has_permission
                return has_permission(user, 'budgeting_manage_budget_plan', self.company)
            except Exception:
                return False
        # Cost center budget: owner, deputy, or explicitly granted entry users
        try:
            return bool(
                (getattr(cc, 'owner_id', None) and user.id == cc.owner_id)
                or (getattr(cc, 'deputy_owner_id', None) and user.id == cc.deputy_owner_id)
                or cc.budget_entry_users.filter(id=user.id).exists()
            )
        except Exception:
            return False

    def submit_for_approval(self, user=None):
        # Move budget to pending cc approval
        self.status = self.STATUS_PENDING_CC_APPROVAL
        self.updated_by = user or self.updated_by
        self.save(update_fields=["status", "updated_by", "updated_at"])

    def get_pending_cost_center_approvals(self):
        return getattr(self, "approvals", None).filter(
            approver_type="cost_center_owner", status=BudgetApproval.Status.PENDING
        ) if hasattr(self, "approvals") else []

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
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='budget_lines')

    # REFACTORED: Split product field into sales.Product and inventory.Item
    # For revenue budgets only - links to saleable products
    product = models.ForeignKey(
        'sales.Product',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='budget_lines',
        help_text='For revenue budgets only - saleable product'
    )

    # For expense/capex/operational budgets - links to inventory items
    item = models.ForeignKey(
        'inventory.Item',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='budget_lines',
        help_text='For expense/capex/operational budgets - inventory item'
    )

    # Sub-category for hierarchical classification
    sub_category = models.ForeignKey(
        'inventory.ItemCategory',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='budget_lines',
        help_text='Sub-category for budget classification'
    )

    item_name = models.CharField(max_length=255)
    category = models.CharField(max_length=120, blank=True)
    project_code = models.CharField(max_length=64, blank=True)

    # ORIGINAL VALUES (for variance tracking - Section 4)
    original_qty_limit = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=Decimal("0"),
        help_text="Original quantity at submission"
    )
    original_unit_price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Original price at submission"
    )
    original_value_limit = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Original value at submission"
    )

    # CURRENT VALUES (may be modified)
    qty_limit = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0"))
    value_limit = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    standard_price = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    manual_unit_price = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    # VARIANCE DETAILS (NEW - Section 4)
    qty_variance = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=Decimal("0"),
        help_text="Current Qty - Original Qty"
    )
    price_variance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Current Price - Original Price"
    )
    value_variance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Current Value - Original Value"
    )
    variance_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        help_text="% change from original"
    )

    # Who modified this line (NEW - Section 4)
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modified_budget_lines',
        help_text="User who last modified this line"
    )
    modified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When line was last modified"
    )
    modification_reason = models.TextField(
        blank=True,
        help_text="Justification for modification"
    )

    # HELD ITEMS LOGIC (NEW - Section 3)
    is_held_for_review = models.BooleanField(
        default=False,
        help_text="Marked as held for further review by owner/moderator"
    )
    held_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='held_budget_lines',
        help_text="User who marked this line as held"
    )
    held_reason = models.TextField(
        blank=True,
        help_text="Reason for holding this line"
    )
    held_until_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Hold expires on this date"
    )

    # REVIEW LOGIC (NEW - Section 3)
    sent_back_for_review = models.BooleanField(
        default=False,
        help_text="Sent back to CC owner/entry user for review"
    )

    # MODERATOR REMARKS (NEW - Section 2.4)
    moderator_remarks = models.TextField(
        blank=True,
        help_text="Moderator comments on this line"
    )
    moderator_remarks_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='budget_line_remarks',
        help_text="Moderator who added remarks"
    )
    moderator_remarks_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When moderator added remarks"
    )

    # CC Owner modification notes
    cc_owner_modification_notes = models.TextField(
        blank=True,
        help_text="CC Owner notes for modifications"
    )

    # Consumption Tracking
    tolerance_percent = models.PositiveIntegerField(default=5)
    consumed_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0"))
    consumed_value = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    committed_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0"))
    committed_value = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))

    # Projected Consumption (AI-powered - Section 12)
    projected_consumption_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="AI-predicted consumption based on trends"
    )
    projected_consumption_confidence = models.DecimalField(
        max_digits=3,
        decimal_places=0,
        null=True,
        blank=True,
        help_text="Confidence level (0-100) for projection"
    )
    will_exceed_budget = models.BooleanField(
        default=False,
        help_text="True if projected consumption > allocated"
    )

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
            models.Index(fields=["budget", "is_active"]),
            models.Index(fields=["is_held_for_review"]),
            models.Index(fields=["sent_back_for_review"]),
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

    def clean(self):
        """
        Validation for Product vs Item split:
        - Revenue budgets must use product (not item)
        - Other budgets must use item (not product)
        - Cannot have both product and item set
        """
        from django.core.exceptions import ValidationError

        # Check if both are set
        if self.product_id and self.item_id:
            raise ValidationError({
                'product': 'Cannot specify both product and item. Use product for revenue budgets, item for others.',
                'item': 'Cannot specify both product and item. Use product for revenue budgets, item for others.'
            })

        # Revenue budgets should use product
        if self.budget and self.budget.budget_type == Budget.TYPE_REVENUE:
            if self.item_id and not self.product_id:
                raise ValidationError({
                    'item': 'Revenue budgets must use product field, not item field.'
                })

        # Non-revenue budgets should use item
        if self.budget and self.budget.budget_type != Budget.TYPE_REVENUE:
            if self.product_id and not self.item_id:
                raise ValidationError({
                    'product': 'Non-revenue budgets (expense/capex/operational) must use item field, not product field.'
                })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


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


class BudgetApproval(models.Model):
    class ApproverType(models.TextChoices):
        BUDGET_NAME_APPROVER = "budget_name_approver", "Budget Name Approver"
        COST_CENTER_OWNER = "cost_center_owner", "Cost Center Owner"
        BUDGET_MODULE_OWNER = "budget_module_owner", "Budget Module Owner"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SENT_BACK = "sent_back", "Sent Back for Review"

    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name="approvals")
    approver_type = models.CharField(max_length=32, choices=ApproverType.choices)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.PROTECT, null=True, blank=True, related_name="budget_approvals")
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="budget_approvals")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    decision_date = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)
    modifications_made = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["budget", "approver_type", "status"]),
            models.Index(fields=["approver", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.budget_id}:{self.approver_type}:{self.status}"


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


class BudgetItemCategory(models.Model):
    """Top-level item category for budgeting, shared within a company group."""
    company = models.ForeignKey(Company, on_delete=models.PROTECT, null=True, blank=True, related_name='budget_item_categories')
    company_group = models.ForeignKey(CompanyGroup, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["company_group", "code"], name="uniq_budget_cat_group_code"),
        ]
        indexes = [
            models.Index(fields=["company", "code"]),
            # models.Index(fields=["company", "is_active"]),
        ]

    def save(self, *args, **kwargs):
        if self.company_id and not self.company_group_id:
            try:
                self.company_group = self.company.company_group
            except Exception:
                pass
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class BudgetItemSubCategory(models.Model):
    """Second-level item category. Must have a parent category."""
    company = models.ForeignKey(Company, on_delete=models.PROTECT, null=True, blank=True, related_name='budget_item_subcategories')
    company_group = models.ForeignKey(CompanyGroup, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    category = models.ForeignKey(BudgetItemCategory, on_delete=models.PROTECT, related_name='subcategories')
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category_id", "code"]
        constraints = [
            models.UniqueConstraint(fields=["category", "code"], name="uniq_budget_subcat_category_code"),
        ]
        indexes = [
            models.Index(fields=["company", "category"]),
            models.Index(fields=["category", "code"]),
        ]

    def save(self, *args, **kwargs):
        if self.company_id and not self.company_group_id:
            try:
                self.company_group = self.company.company_group
            except Exception:
                pass
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.category.code}:{self.code} - {self.name}"

class BudgetItemCode(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, null=True, blank=True, related_name='budget_item_codes')
    company_group = models.ForeignKey(CompanyGroup, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    # Back-compat free-text field (kept); prefer category_ref/sub_category_ref
    category = models.CharField(max_length=120, blank=True)
    category_ref = models.ForeignKey('budgeting.BudgetItemCategory', on_delete=models.PROTECT, null=True, blank=True, related_name='item_codes')
    sub_category_ref = models.ForeignKey('budgeting.BudgetItemSubCategory', on_delete=models.PROTECT, null=True, blank=True, related_name='item_codes')
    uom = models.ForeignKey('inventory.UnitOfMeasure', on_delete=models.PROTECT, related_name='budget_item_codes')
    standard_price = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ("company_group", "code")
        ordering = ["code"]
        indexes = [
            # models.Index(fields=["company", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        if self.company_id and not self.company_group_id:
            try:
                self.company_group = self.company.company_group
            except Exception:
                pass
        super().save(*args, **kwargs)


class BudgetPricePolicy(models.Model):
    SOURCE_STANDARD = "standard"
    SOURCE_LAST_PO = "last_po"
    SOURCE_AVG = "avg"
    SOURCE_MANUAL_ONLY = "manual_only"

    SOURCE_CHOICES = [
        (SOURCE_STANDARD, "Standard"),
        (SOURCE_LAST_PO, "Last PO"),
        (SOURCE_AVG, "Average"),
        (SOURCE_MANUAL_ONLY, "Manual Only"),
    ]

    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name="budget_price_policy")
    primary_source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_STANDARD)
    secondary_source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_LAST_PO)
    tertiary_source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_AVG)
    avg_lookback_days = models.IntegerField(default=365)
    fallback_on_zero = models.BooleanField(default=True)

    class Meta:
        ordering = ["company_id"]

    def __str__(self) -> str:
        return f"Policy {self.company_id}: {self.primary_source} > {self.secondary_source} > {self.tertiary_source}"


class BudgetRemarkTemplate(models.Model):
    """
    Pre-defined and custom remark templates for moderators
    Section 10: Remark Templates System
    """
    class RemarkType(models.TextChoices):
        SUGGESTION = "suggestion", "Suggestion"
        CONCERN = "concern", "Concern"
        APPROVAL_NOTE = "approval_note", "Approval Note"
        CLARIFICATION_NEEDED = "clarification_needed", "Clarification Needed"
        DATA_ISSUE = "data_issue", "Data Issue"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='budget_remark_templates'
    )

    # Template Details
    name = models.CharField(
        max_length=255,
        help_text='e.g., "Qty Exceeds Standard"'
    )
    description = models.TextField(blank=True)

    template_text = models.TextField(
        help_text='Remark text (can include placeholders like {item_name}, {qty})'
    )

    remark_type = models.CharField(
        max_length=50,
        choices=RemarkType.choices
    )

    is_predefined = models.BooleanField(
        default=False,
        help_text='True if predefined by system; False if custom'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_budget_templates'
    )

    usage_count = models.IntegerField(
        default=0,
        help_text='How many times used'
    )

    is_shared = models.BooleanField(
        default=True,
        help_text='Visible to all moderators if True'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'budget_remark_template'
        ordering = ['name']
        indexes = [
            models.Index(fields=['company', 'is_predefined']),
            models.Index(fields=['company', 'is_shared']),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_remark_type_display()})"


class BudgetVarianceAudit(models.Model):
    """
    Complete audit trail of all modifications (original vs. current)
    Section 4: Variance Tracking & Audit
    """
    class ChangeType(models.TextChoices):
        QTY_CHANGE = "qty_change", "Quantity Changed"
        PRICE_CHANGE = "price_change", "Price Changed"
        BOTH_CHANGE = "both_change", "Qty & Price Changed"

    class ModifierRole(models.TextChoices):
        CC_OWNER = "cc_owner", "CC Owner"
        MODERATOR = "moderator", "Moderator"
        MODULE_OWNER = "module_owner", "Module Owner"

    budget_line = models.ForeignKey(
        BudgetLine,
        on_delete=models.CASCADE,
        related_name='variance_audit_trail'
    )

    # Who made the change
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='budget_modifications'
    )
    modified_at = models.DateTimeField(auto_now_add=True)

    # What changed
    change_type = models.CharField(
        max_length=50,
        choices=ChangeType.choices
    )

    # Quantity changes
    original_qty = models.DecimalField(max_digits=15, decimal_places=3)
    new_qty = models.DecimalField(max_digits=15, decimal_places=3)
    qty_change_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))

    # Price changes
    original_price = models.DecimalField(max_digits=20, decimal_places=2)
    new_price = models.DecimalField(max_digits=20, decimal_places=2)
    price_change_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))

    # Value changes
    original_value = models.DecimalField(max_digits=20, decimal_places=2)
    new_value = models.DecimalField(max_digits=20, decimal_places=2)
    value_variance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))

    # Justification
    justification = models.TextField(
        blank=True,
        help_text='Why this change was made'
    )

    role_of_modifier = models.CharField(
        max_length=50,
        choices=ModifierRole.choices
    )

    class Meta:
        db_table = 'budget_variance_audit'
        ordering = ['-modified_at']
        indexes = [
            models.Index(fields=['budget_line']),
            models.Index(fields=['modified_at']),
            models.Index(fields=['modified_by']),
        ]

    def __str__(self) -> str:
        return f"{self.budget_line.item_name} - {self.get_change_type_display()} by {self.modified_by}"
