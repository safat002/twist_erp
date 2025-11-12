from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.budgeting.models import BudgetCommitment, BudgetLine, CostCenter

User = settings.AUTH_USER_MODEL


class Supplier(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        BLACKLISTED = "blacklisted", "Blacklisted"

    class SupplierType(models.TextChoices):
        LOCAL = "local", "Local"
        IMPORT = "import", "Import"
        SERVICE = "service", "Service"
        SUB_CONTRACTOR = "sub_contractor", "Sub-Contractor"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        help_text="Company this record belongs to",
        related_name="suppliers",
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    payment_terms = models.IntegerField(default=30, help_text="Payment terms in days")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    supplier_type = models.CharField(max_length=20, choices=SupplierType.choices, default=SupplierType.LOCAL)
    is_blocked = models.BooleanField(default=False)
    block_reason = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    payable_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["company", "code"]

    def __str__(self) -> str:
        return f"{self.company.code if hasattr(self.company, 'code') else self.company_id}::{self.code}"


class SupplierBlackoutWindow(models.Model):
    """Supplier availability blackout periods (no deliveries)."""

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='blackout_windows')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_date']
        indexes = [
            models.Index(fields=['supplier', 'start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.supplier.code} blackout {self.start_date} - {self.end_date}"


class PurchaseRequisition(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        CONVERTED = "converted", "Converted to PO"

    class Priority(models.TextChoices):
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class RequestType(models.TextChoices):
        STOCK_ITEM = BudgetLine.ProcurementClass.STOCK_ITEM
        SERVICE_ITEM = BudgetLine.ProcurementClass.SERVICE_ITEM
        CAPEX_ITEM = BudgetLine.ProcurementClass.CAPEX_ITEM

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        related_name="purchase_requisitions",
        help_text="Company this record belongs to",
    )
    cost_center = models.ForeignKey(CostCenter, on_delete=models.PROTECT, related_name="purchase_requisitions")
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="raised_requisitions")
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_requisitions",
    )
    requisition_number = models.CharField(max_length=32, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    priority = models.CharField(max_length=12, choices=Priority.choices, default=Priority.NORMAL)
    request_type = models.CharField(max_length=20, choices=RequestType.choices)
    is_emergency = models.BooleanField(default=False)
    justification = models.TextField(blank=True)
    required_by = models.DateField(null=True, blank=True)
    total_estimated_value = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total_estimated_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0"))
    workflow_state = models.CharField(max_length=64, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "requisition_number"]),
        ]

    def __str__(self) -> str:
        number = self.requisition_number or f"PR-{self.pk}"
        return f"{number} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        from apps.metadata.services.doc_numbers import get_next_doc_no
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.requisition_number:
            generated = get_next_doc_no(company=self.company, doc_type="PR", prefix="PR", fy_format="YYYY", width=5)
            PurchaseRequisition.objects.filter(pk=self.pk).update(requisition_number=generated)
            self.requisition_number = generated

    def refresh_totals(self, commit: bool = True) -> tuple[Decimal, Decimal]:
        totals = self.lines.aggregate(
            qty=models.Sum("quantity"),
            value=models.Sum("estimated_total_cost"),
        )
        quantity = totals.get("qty") or Decimal("0")
        value = totals.get("value") or Decimal("0")
        self.total_estimated_quantity = quantity
        self.total_estimated_value = value
        if commit:
            self.save(update_fields=["total_estimated_quantity", "total_estimated_value", "updated_at"])
        return quantity, value

    def _ensure_can_transition(self, allowed_statuses: set[str]):
        if self.status not in allowed_statuses:
            raise ValueError(f"Requisition {self.requisition_number} cannot transition from {self.status}.")

    def submit(self, user):
        self._ensure_can_transition({self.Status.DRAFT})
        if not self.lines.exists():
            raise ValueError("Cannot submit requisition without at least one line.")
        self.refresh_totals(commit=False)
        self.status = self.Status.SUBMITTED
        self.submitted_at = timezone.now()
        self.workflow_state = "submitted"
        self.save(update_fields=["status", "submitted_at", "workflow_state", "updated_at"])

    def approve(self, user):
        self._ensure_can_transition({self.Status.SUBMITTED, self.Status.UNDER_REVIEW})
        self.status = self.Status.APPROVED
        self.workflow_state = "approved"
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save(update_fields=["status", "workflow_state", "approved_by", "approved_at", "updated_at"])
        for line in self.lines.all():
            line.reserve_commitment(user=user)

    def reject(self, user, *, reason: str = ""):
        self._ensure_can_transition({self.Status.SUBMITTED, self.Status.UNDER_REVIEW})
        self.status = self.Status.REJECTED
        self.workflow_state = "rejected"
        self.approved_by = user
        self.rejected_at = timezone.now()
        self.cancellation_reason = reason
        self.save(
            update_fields=[
                "status",
                "workflow_state",
                "approved_by",
                "rejected_at",
                "cancellation_reason",
                "updated_at",
            ]
        )
        for line in self.lines.all():
            line.release_commitment(timestamp=self.rejected_at)

    def mark_converted(self):
        self.status = self.Status.CONVERTED
        self.save(update_fields=["status", "updated_at"])
        for line in self.lines.all():
            line.release_commitment(timestamp=timezone.now())


class PurchaseRequisitionLine(models.Model):
    requisition = models.ForeignKey(PurchaseRequisition, on_delete=models.CASCADE, related_name="lines")
    line_number = models.PositiveIntegerField()
    budget_line = models.ForeignKey(BudgetLine, on_delete=models.PROTECT, related_name="requisition_lines")
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.PROTECT,
        related_name="requisition_lines",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        "inventory.Item",
        on_delete=models.PROTECT,
        related_name="purchase_requisition_lines",
        null=True,
        blank=True,
    )
    description = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    uom = models.ForeignKey(
        "inventory.UnitOfMeasure",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="purchase_requisition_lines",
    )
    estimated_unit_cost = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    estimated_total_cost = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    needed_by = models.DateField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("requisition", "line_number")
        ordering = ["line_number"]
        indexes = [
            models.Index(fields=["budget_line"]),
        ]

    def __str__(self) -> str:
        return f"{self.requisition.requisition_number}#{self.line_number}"

    @property
    def procurement_class(self) -> str:
        return self.budget_line.procurement_class

    def clean(self):
        if self.item and self.budget_line.procurement_class != BudgetLine.ProcurementClass.STOCK_ITEM:
            raise ValueError("Only stock item requisitions can reference an inventory item.")

    def save(self, *args, **kwargs):
        self.estimated_total_cost = (self.estimated_unit_cost or Decimal("0")) * (self.quantity or Decimal("0"))
        if not self.cost_center_id:
            self.cost_center = self.requisition.cost_center
        self.ensure_budget_capacity()
        super().save(*args, **kwargs)
        self.requisition.refresh_totals(commit=True)

    def ensure_budget_capacity(self):
        """Ensure the linked budget line still has capacity for this requisition line."""
        if self.estimated_total_cost and self.budget_line.available_value < self.estimated_total_cost:
            raise ValueError(f"Budget line {self.budget_line.id} does not have enough value remaining.")
        if (
            self.budget_line.procurement_class == BudgetLine.ProcurementClass.STOCK_ITEM
            and self.quantity
            and self.budget_line.available_quantity < self.quantity
        ):
            raise ValueError(f"Budget line {self.budget_line.id} does not have enough quantity remaining.")

    def reserve_commitment(self, user=None):
        """Reserve budget against this requisition line."""
        commitment, created = BudgetCommitment.objects.get_or_create(
            budget_line=self.budget_line,
            source_type="PR_LINE",
            source_reference=str(self.id),
            defaults={
                "committed_quantity": self.quantity or Decimal("0"),
                "committed_value": self.estimated_total_cost or Decimal("0"),
                "created_by": user,
                "metadata": {"requisition_id": self.requisition_id},
            },
        )
        if not created:
            commitment.committed_quantity = self.quantity or Decimal("0")
            commitment.committed_value = self.estimated_total_cost or Decimal("0")
            commitment.status = BudgetCommitment.Status.RESERVED
            commitment.metadata = {**(commitment.metadata or {}), "requisition_id": self.requisition_id}
            commitment.save(update_fields=["committed_quantity", "committed_value", "status", "metadata", "updated_at"])
        return commitment

    def release_commitment(self, *, timestamp=None):
        try:
            commitment = BudgetCommitment.objects.get(
                budget_line=self.budget_line,
                source_type="PR_LINE",
                source_reference=str(self.id),
            )
        except BudgetCommitment.DoesNotExist:
            return
        commitment.release(
            quantity=commitment.remaining_quantity,
            value=commitment.remaining_value,
            timestamp=timestamp or timezone.now(),
        )


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        ISSUED = "issued", "Issued"
        PARTIALLY_RECEIVED = "partially_received", "Partially Received"
        RECEIVED = "received", "Received"
        CANCELLED = "cancelled", "Cancelled"
        CLOSED = "closed", "Closed"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        help_text="Company this record belongs to",
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    requisition = models.ForeignKey(
        PurchaseRequisition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_orders",
    )
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="+")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    order_number = models.CharField(max_length=32, db_index=True, blank=True)
    external_reference = models.CharField(max_length=64, blank=True)
    order_date = models.DateField(default=timezone.now)
    expected_delivery_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=8, default="USD")
    subtotal = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    tax_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT)
    workflow_state = models.CharField(max_length=64, blank=True)
    is_emergency = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    delivery_address = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("company", "order_number")
        ordering = ["-order_date", "-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self) -> str:
        number = self.order_number or f"PO-{self.pk}"
        return f"{number} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        from core.doc_numbers import get_next_doc_no
        is_new = self._state.adding
        if self.cost_center is None and self.requisition_id:
            self.cost_center = self.requisition.cost_center
        if self.currency == "USD" and hasattr(self.company, "currency_code"):
            self.currency = self.company.currency_code or self.currency
        super().save(*args, **kwargs)
        if is_new and not self.order_number:
            generated = get_next_doc_no(company=self.company, doc_type="PO", prefix="PO", fy_format="YYYY", width=5)
            PurchaseOrder.objects.filter(pk=self.pk).update(order_number=generated)
            self.order_number = generated

    def refresh_totals(self, commit: bool = True) -> tuple[Decimal, Decimal, Decimal]:
        totals = self.lines.aggregate(
            subtotal=models.Sum("line_total"),
            tax=models.Sum("tax_value"),
        )
        subtotal = totals.get("subtotal") or Decimal("0")
        tax = totals.get("tax") or Decimal("0")
        total = subtotal + tax
        self.subtotal = subtotal
        self.tax_amount = tax
        self.total_amount = total
        if commit:
            self.save(update_fields=["subtotal", "tax_amount", "total_amount", "updated_at"])
        return subtotal, tax, total

    def mark_submitted(self):
        if self.status not in {self.Status.DRAFT}:
            raise ValueError("Only draft purchase orders can be submitted.")
        self.status = self.Status.PENDING_APPROVAL
        self.workflow_state = "submitted"
        self.save(update_fields=["status", "workflow_state", "updated_at"])

    def mark_approved(self, user):
        if self.status not in {self.Status.PENDING_APPROVAL}:
            raise ValueError("Only pending approval purchase orders can be approved.")
        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.workflow_state = "approved"
        self.save(update_fields=["status", "approved_by", "approved_at", "workflow_state", "updated_at"])

    def mark_issued(self):
        if self.status not in {self.Status.APPROVED}:
            raise ValueError("Only approved purchase orders can be issued.")
        self.status = self.Status.ISSUED
        self.issued_at = timezone.now()
        self.workflow_state = "issued"
        self.save(update_fields=["status", "issued_at", "workflow_state", "updated_at"])

    def update_receipt_status(self):
        total_lines = self.lines.count()
        if total_lines == 0:
            return
        fully_received = sum(
            1
            for line in self.lines.all()
            if line.remaining_quantity <= Decimal("0")
        )
        if fully_received == total_lines:
            self.status = self.Status.RECEIVED
            self.closed_at = timezone.now()
        elif fully_received > 0:
            self.status = self.Status.PARTIALLY_RECEIVED
        self.save(update_fields=["status", "closed_at", "updated_at"])

    def cancel(self, reason: str = ""):
        if self.status in {self.Status.RECEIVED, self.Status.CLOSED}:
            raise ValueError("Cannot cancel a completed purchase order.")
        self.status = self.Status.CANCELLED
        self.workflow_state = "cancelled"
        self.notes = f"{self.notes}\nCancelled: {reason}".strip()
        self.save(update_fields=["status", "workflow_state", "notes", "updated_at"])
        for line in self.lines.select_related("budget_commitment"):
            if line.budget_commitment:
                line.budget_commitment.release(
                    quantity=line.remaining_quantity,
                    value=line.remaining_value,
                    timestamp=timezone.now(),
                )


class PurchaseOrderLine(models.Model):
    class LineStatus(models.TextChoices):
        OPEN = "open", "Open"
        PARTIAL = "partial", "Partially Received"
        RECEIVED = "received", "Received"

    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    line_number = models.PositiveIntegerField()
    requisition_line = models.ForeignKey(
        PurchaseRequisitionLine,
        on_delete=models.SET_NULL,
        related_name="purchase_order_lines",
        null=True,
        blank=True,
    )
    budget_line = models.ForeignKey(
        BudgetLine,
        on_delete=models.PROTECT,
        related_name="purchase_order_lines",
        null=True,
        blank=True,
    )
    budget_commitment = models.ForeignKey(
        BudgetCommitment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_order_lines",
    )
    product = models.ForeignKey(
        "inventory.Item",
        on_delete=models.PROTECT,
        related_name="purchase_order_lines",
        null=True,
        blank=True,
    )
    description = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    expected_delivery_date = models.DateField(null=True, blank=True)
    unit_price = models.DecimalField(max_digits=20, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    line_total = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    tax_value = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    tolerance_percent = models.PositiveIntegerField(default=0)
    within_tolerance = models.BooleanField(default=True)
    received_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0"))
    status = models.CharField(max_length=20, choices=LineStatus.choices, default=LineStatus.OPEN)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("purchase_order", "line_number")
        ordering = ["line_number"]
        indexes = [
            models.Index(fields=["budget_line"]),
        ]

    def __str__(self) -> str:
        return f"{self.purchase_order.order_number}#{self.line_number}"

    @property
    def procurement_class(self) -> str:
        return self.budget_line.procurement_class if self.budget_line else ""

    @property
    def remaining_quantity(self) -> Decimal:
        ordered = self.quantity or Decimal("0")
        received = self.received_quantity or Decimal("0")
        return max(ordered - received, Decimal("0"))

    @property
    def remaining_value(self) -> Decimal:
        return self.remaining_quantity * (self.unit_price or Decimal("0"))

    def save(self, *args, **kwargs):
        if not self.budget_line:
            raise ValueError("Purchase order line requires an associated budget line.")
        if self.requisition_line and not self.description:
            self.description = self.requisition_line.description
        if not self.tolerance_percent and self.budget_line and self.budget_line.tolerance_percent:
            self.tolerance_percent = self.budget_line.tolerance_percent
        if self.item is None and self.requisition_line and self.requisition_line.item:
            self.item = self.requisition_line.item
        self.line_total = (self.unit_price or Decimal("0")) * (self.quantity or Decimal("0"))
        self.tax_value = (self.line_total * (self.tax_rate or Decimal("0"))) / Decimal("100")
        self.within_tolerance = self._check_price_tolerance()
        super().save(*args, **kwargs)
        self.purchase_order.refresh_totals(commit=True)
        self._ensure_commitment()

    def _check_price_tolerance(self) -> bool:
        standard_price = self.budget_line.standard_price or Decimal("0")
        if not standard_price:
            return True
        tolerance = Decimal(self.tolerance_percent or 0) / Decimal("100")
        upper_bound = standard_price * (Decimal("1") + tolerance)
        lower_bound = standard_price * (Decimal("1") - tolerance)
        return lower_bound <= (self.unit_price or Decimal("0")) <= upper_bound

    def _ensure_commitment(self):
        commitment, created = BudgetCommitment.objects.get_or_create(
            budget_line=self.budget_line,
            source_type="PO_LINE",
            source_reference=str(self.id),
            defaults={
                "committed_quantity": self.quantity or Decimal("0"),
                "committed_value": self.line_total,
                "created_by": self.purchase_order.created_by,
                "metadata": {"purchase_order_id": self.purchase_order_id},
            },
        )
        if not created:
            commitment.committed_quantity = self.quantity or Decimal("0")
            commitment.committed_value = self.line_total
            commitment.status = BudgetCommitment.Status.CONVERTED
            commitment.metadata = {**(commitment.metadata or {}), "purchase_order_id": self.purchase_order_id}
            commitment.save(update_fields=["committed_quantity", "committed_value", "status", "metadata", "updated_at"])
        else:
            commitment.mark_converted(timestamp=timezone.now())
        self.budget_commitment = commitment
        super().save(update_fields=["budget_commitment"])

    def register_receipt(self, quantity: Decimal, *, timestamp=None):
        quantity = quantity or Decimal("0")
        if quantity <= Decimal("0"):
            return
        self.received_quantity = (self.received_quantity or Decimal("0")) + quantity
        if self.remaining_quantity <= Decimal("0"):
            self.status = self.LineStatus.RECEIVED
        else:
            self.status = self.LineStatus.PARTIAL
        self.save(update_fields=["received_quantity", "status"])

        receipt_value = quantity * (self.unit_price or Decimal("0"))
        if self.budget_commitment:
            self.budget_commitment.consume(quantity, receipt_value, timestamp=timestamp or timezone.now())

class PurchaseRequisitionDraft(models.Model):
    """Lightweight PR draft to support simple UI flow before full budgeting integration."""
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='purchase_requisition_drafts')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    requisition_number = models.CharField(max_length=50, blank=True, db_index=True)
    request_date = models.DateField()
    needed_by = models.DateField(null=True, blank=True)
    purpose = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='SUBMITTED')

    # JSON lines: [{item_id, item_name, quantity, uom, notes}]
    lines = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'requisition_number']),
        ]

    def __str__(self) -> str:
        return self.requisition_number or f"PR-{self.pk}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.requisition_number:
            from core.doc_numbers import get_next_doc_no
            generated = get_next_doc_no(company=self.company, doc_type="PR", prefix="PR", fy_format="YYYY", width=5)
            PurchaseRequisitionDraft.objects.filter(pk=self.pk).update(requisition_number=generated)
            self.requisition_number = generated
