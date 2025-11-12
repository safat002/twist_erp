from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.finance.models import Journal
from apps.inventory.models import StockLevel, StockMovement, StockMovementLine
from core.doc_numbers import get_next_doc_no

TWOPLACES = Decimal("0.01")


def _ensure_company_group(instance):
    if instance.company_id and not instance.company_group_id:
        instance.company_group = instance.company.company_group
    return instance


class BillOfMaterialStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"


class WorkOrderStatus(models.TextChoices):
    PLANNED = "PLANNED", "Planned"
    RELEASED = "RELEASED", "Released"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class WorkOrderPriority(models.TextChoices):
    LOW = "LOW", "Low"
    NORMAL = "NORMAL", "Normal"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class BillOfMaterial(models.Model):
    company_group = models.ForeignKey("companies.CompanyGroup", on_delete=models.PROTECT)
    company = models.ForeignKey("companies.Company", on_delete=models.PROTECT)
    product = models.ForeignKey("budgeting.BudgetItemCode", on_delete=models.PROTECT, related_name="boms")
    code = models.CharField(max_length=32, blank=True)
    version = models.CharField(max_length=16, default="1.0")
    name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=BillOfMaterialStatus.choices, default=BillOfMaterialStatus.DRAFT)
    is_primary = models.BooleanField(default=False)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    revision_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ("product", "version")

    def save(self, *args, **kwargs):
        _ensure_company_group(self)
        is_new = self._state.adding and not self.code
        super().save(*args, **kwargs)
        if is_new:
            generated = f"BOM-{self.product.code}-{self.pk:04d}"
            BillOfMaterial.objects.filter(pk=self.pk).update(code=generated)
            self.code = generated

    def __str__(self) -> str:
        return f"{self.code} · {self.product.name}"


class BillOfMaterialComponent(models.Model):
    bom = models.ForeignKey(BillOfMaterial, on_delete=models.CASCADE, related_name="components")
    sequence = models.PositiveIntegerField(default=1)
    component = models.ForeignKey("budgeting.BudgetItemCode", on_delete=models.PROTECT, related_name="bom_components")
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    uom = models.ForeignKey("inventory.UnitOfMeasure", on_delete=models.PROTECT, null=True, blank=True)
    scrap_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Preferred warehouse to issue from",
    )

    class Meta:
        ordering = ("sequence", "component__code")

    def __str__(self) -> str:
        return f"{self.component.name} ({self.quantity})"


class WorkOrder(models.Model):
    company_group = models.ForeignKey("companies.CompanyGroup", on_delete=models.PROTECT)
    company = models.ForeignKey("companies.Company", on_delete=models.PROTECT)
    number = models.CharField(max_length=40, blank=True)
    product = models.ForeignKey("budgeting.BudgetItemCode", on_delete=models.PROTECT, related_name="work_orders")
    bom = models.ForeignKey(BillOfMaterial, on_delete=models.SET_NULL, null=True, blank=True, related_name="work_orders")
    quantity_planned = models.DecimalField(max_digits=15, decimal_places=3)
    quantity_completed = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0.000"))
    status = models.CharField(max_length=16, choices=WorkOrderStatus.choices, default=WorkOrderStatus.PLANNED)
    priority = models.CharField(max_length=12, choices=WorkOrderPriority.choices, default=WorkOrderPriority.NORMAL)
    scheduled_start = models.DateField(null=True, blank=True)
    scheduled_end = models.DateField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("company", "number")
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        _ensure_company_group(self)
        is_new = self._state.adding and not self.number
        super().save(*args, **kwargs)
        if is_new:
            generated = get_next_doc_no(company=self.company, doc_type="WO", prefix="WO", fy_format="YYYY", width=5)
            WorkOrder.objects.filter(pk=self.pk).update(number=generated)
            self.number = generated
            self.refresh_from_db()
            self._initialize_requirements()

    def _initialize_requirements(self):
        if not self.bom_id:
            return
        components = []
        for component in self.bom.components.all():
            quantity = (component.quantity or Decimal("0")) * (self.quantity_planned or Decimal("0"))
            WorkOrderComponent.objects.create(
                work_order=self,
                component=component.component,
                required_quantity=quantity,
                issued_quantity=Decimal("0.000"),
                uom=component.uom,
                scrap_percent=component.scrap_percent or Decimal("0.00"),
                preferred_warehouse=component.warehouse,
            )

    def release(self):
        if self.status not in {WorkOrderStatus.PLANNED}:
            raise ValueError("Only planned work orders can be released.")
        self.status = WorkOrderStatus.RELEASED
        self.save(update_fields=["status", "updated_at"])

    def start(self):
        if self.status not in {WorkOrderStatus.RELEASED, WorkOrderStatus.PLANNED}:
            raise ValueError("Work order must be released before starting.")
        self.status = WorkOrderStatus.IN_PROGRESS
        self.actual_start = timezone.now()
        self.save(update_fields=["status", "actual_start", "updated_at"])

    def complete(self, quantity_completed: Decimal):
        if self.status != WorkOrderStatus.IN_PROGRESS:
            raise ValueError("Only in-progress work orders can be completed.")
        self.quantity_completed = Decimal(quantity_completed or 0)
        self.status = WorkOrderStatus.COMPLETED
        self.actual_end = timezone.now()
        self.save(update_fields=["quantity_completed", "status", "actual_end", "updated_at"])

    @transaction.atomic
    def record_material_issue(self, *, user, lines: list[dict], issue_date=None, notes: str = ""):
        issue = MaterialIssue.objects.create(
            work_order=self,
            issue_date=issue_date or timezone.now().date(),
            notes=notes,
            created_by=user,
        )
        company = self.company
        movement = StockMovement.objects.create(
            company=company,
            movement_number="",
            movement_date=issue.issue_date,
            movement_type="ISSUE",
            reference=self.number,
            notes=notes,
            status="COMPLETED",
            created_by=user,
        )
        for idx, line in enumerate(lines, start=1):
            component = WorkOrderComponent.objects.select_for_update().get(pk=line["component"])
            quantity = Decimal(line.get("quantity") or 0)
            warehouse_id = line.get("warehouse")
            MaterialIssueLine.objects.create(
                issue=issue,
                component=component,
                product=component.component,
                quantity=quantity,
                warehouse_id=warehouse_id,
            )
            component.issued_quantity = (component.issued_quantity or Decimal("0")) + quantity
            component.save(update_fields=["issued_quantity"])
            if warehouse_id and movement.from_warehouse_id is None:
                movement.from_warehouse_id = warehouse_id
                movement.save(update_fields=["from_warehouse"])
            StockMovementLine.objects.create(
                movement=movement,
                line_number=idx,
                item=component.component,
                quantity=quantity,
                rate=component.component.cost_price or Decimal("0.00"),
            )
            stock_level, _ = StockLevel.objects.select_for_update().get_or_create(
                company=company,
                product=component.component,
                warehouse_id=warehouse_id or component.preferred_warehouse_id or self.warehouse_id,
                defaults={"created_by": user},
            )
            stock_level.quantity = (stock_level.quantity or Decimal("0")) - quantity
            stock_level.save(update_fields=["quantity"])
        StockMovement.objects.filter(pk=movement.pk).update(
            movement_number=f"MI-{self.number}-{issue.pk:04d}"
        )
        self._post_material_issue_voucher(issue, user)
        return issue

    @transaction.atomic
    def record_receipt(self, *, user, quantity_good: Decimal, quantity_scrap: Decimal = Decimal("0"), receipt_date=None, notes: str = ""):
        receipt = ProductionReceipt.objects.create(
            work_order=self,
            receipt_date=receipt_date or timezone.now().date(),
            quantity_good=Decimal(quantity_good or 0),
            quantity_scrap=Decimal(quantity_scrap or 0),
            warehouse=self.warehouse,
            notes=notes,
            created_by=user,
        )
        self.quantity_completed = receipt.quantity_good
        self.status = WorkOrderStatus.COMPLETED
        self.actual_end = timezone.now()
        self.save(update_fields=["quantity_completed", "status", "actual_end", "updated_at"])
        warehouse = receipt.warehouse or self.warehouse
        movement = StockMovement.objects.create(
            company=self.company,
            movement_number="",
            movement_date=receipt.receipt_date,
            movement_type="RECEIPT",
            reference=self.number,
            notes=notes,
            status="COMPLETED",
            to_warehouse=warehouse,
            created_by=user,
        )
        StockMovementLine.objects.create(
            movement=movement,
            line_number=1,
            item=self.product,
            quantity=receipt.quantity_good,
            rate=self.product.cost_price or Decimal("0.00"),
        )
        StockMovement.objects.filter(pk=movement.pk).update(
            movement_number=f"PR-{self.number}-{receipt.pk:04d}"
        )
        stock_level, _ = StockLevel.objects.select_for_update().get_or_create(
            company=self.company,
            item=self.product,
            warehouse=warehouse,
            defaults={"created_by": user},
        )
        stock_level.quantity = (stock_level.quantity or Decimal("0")) + receipt.quantity_good
        stock_level.save(update_fields=["quantity"])
        self._post_receipt_voucher(receipt, user)
        return receipt

    def _get_default_journal(self, user=None):
        journal = (
            Journal.objects.filter(company=self.company, code__in=["PRODUCTION", "GENERAL"])
            .order_by("code")
            .first()
        )
        if journal:
            return journal
        return Journal.objects.create(
            company=self.company,
            company_group=self.company_group,
            created_by=user,
            code="GENERAL",
            name="General Journal",
            type="GENERAL",
        )

    def _post_material_issue_voucher(self, issue: MaterialIssue, user):
        from apps.finance.services.journal_service import JournalService
        debit_totals = defaultdict(Decimal)
        credit_totals = defaultdict(Decimal)
        for line in issue.lines.select_related("product"):
            product = line.product
            unit_cost = Decimal(product.cost_price or 0)
            line_value = (unit_cost * Decimal(line.quantity or 0)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
            if line_value <= 0 or not product.expense_account_id or not product.inventory_account_id:
                continue
            debit_totals[product.expense_account] += line_value
            credit_totals[product.inventory_account] += line_value
        if not debit_totals:
            return
        journal = self._get_default_journal(user)
        entries_data = []
        for account, amount in debit_totals.items():
            entries_data.append(
                {
                    "account": account,
                    "debit": amount,
                    "credit": Decimal("0.00"),
                    "description": f"Materials issued for {self.number}",
                }
            )
        for account, amount in credit_totals.items():
            entries_data.append(
                {
                    "account": account,
                    "debit": Decimal("0.00"),
                    "credit": amount,
                    "description": f"Materials issued for {self.number}",
                }
            )
        voucher = JournalService.create_journal_voucher(
            company=self.company,
            journal=journal,
            entry_date=issue.issue_date,
            description=f"Material issue for work order {self.number}",
            entries_data=entries_data,
            reference=self.number,
            source_document_type="MaterialIssue",
            source_document_id=issue.id,
            created_by=user,
        )
        JournalService.post_journal_voucher(voucher, user)

    def _post_receipt_voucher(self, receipt: ProductionReceipt, user):
        from apps.finance.services.journal_service import JournalService
        unit_cost = Decimal(self.product.cost_price or 0)
        line_value = (unit_cost * Decimal(receipt.quantity_good or 0)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        if line_value <= 0 or not self.product.inventory_account_id or not self.product.expense_account_id:
            return
        journal = self._get_default_journal(user)
        entries_data = [
            {
                "account": self.product.inventory_account,
                "debit": line_value,
                "credit": Decimal("0.00"),
                "description": f"Receipt for work order {self.number}",
            },
            {
                "account": self.product.expense_account,
                "debit": Decimal("0.00"),
                "credit": line_value,
                "description": f"Receipt for work order {self.number}",
            },
        ]
        voucher = JournalService.create_journal_voucher(
            company=self.company,
            journal=journal,
            entry_date=receipt.receipt_date,
            description=f"Production receipt for work order {self.number}",
            entries_data=entries_data,
            reference=self.number,
            source_document_type="ProductionReceipt",
            source_document_id=receipt.id,
            created_by=user,
        )
        JournalService.post_journal_voucher(voucher, user)


class WorkOrderComponent(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="components")
    component = models.ForeignKey(
        "budgeting.BudgetItemCode",
        on_delete=models.PROTECT,
        related_name="work_order_components",
        help_text="Component item required for production"
    )
    required_quantity = models.DecimalField(max_digits=15, decimal_places=3)
    issued_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0.000"))
    uom = models.ForeignKey("inventory.UnitOfMeasure", on_delete=models.PROTECT, null=True, blank=True)
    scrap_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    preferred_warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ("component__code",)

    @property
    def remaining_quantity(self) -> Decimal:
        return max(Decimal(self.required_quantity or 0) - Decimal(self.issued_quantity or 0), Decimal("0.000"))


class MaterialIssue(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="issues")
    issue_number = models.CharField(max_length=40, blank=True)
    issue_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-issue_date", "-created_at")

    def save(self, *args, **kwargs):
        is_new = self._state.adding and not self.issue_number
        super().save(*args, **kwargs)
        if is_new:
            generated = f"MI-{self.work_order.number}-{self.pk:04d}"
            MaterialIssue.objects.filter(pk=self.pk).update(issue_number=generated)
            self.issue_number = generated


class MaterialIssueLine(models.Model):
    issue = models.ForeignKey(MaterialIssue, on_delete=models.CASCADE, related_name="lines")
    component = models.ForeignKey(WorkOrderComponent, on_delete=models.CASCADE, related_name="issues")
    item = models.ForeignKey(
        "budgeting.BudgetItemCode",
        on_delete=models.PROTECT,
        related_name="material_issue_lines",
        help_text="Item being issued for production"
    )
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ("issue", "item__code")


class ProductionReceipt(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="receipts")
    receipt_number = models.CharField(max_length=40, blank=True)
    receipt_date = models.DateField(default=timezone.now)
    quantity_good = models.DecimalField(max_digits=15, decimal_places=3)
    quantity_scrap = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal("0.000"))
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.PROTECT, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-receipt_date", "-created_at")

    def save(self, *args, **kwargs):
        is_new = self._state.adding and not self.receipt_number
        super().save(*args, **kwargs)
        if is_new:
            generated = f"PR-{self.work_order.number}-{self.pk:04d}"
            ProductionReceipt.objects.filter(pk=self.pk).update(receipt_number=generated)
            self.receipt_number = generated
