from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.workflows.services import WorkflowService
from apps.workflows.models import WorkflowTemplate, WorkflowInstance

class Product(models.Model):
    """LEGACY: This model will be migrated to Item + sales.Product. Do not use for new code."""
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to", related_name='legacy_inventory_products')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    product_type = models.CharField(max_length=20, choices=[
        ('GOODS', 'Goods'),
        ('SERVICE', 'Service'),
        ('CONSUMABLE', 'Consumable'),
    ], default='GOODS')
    track_inventory = models.BooleanField(default=True)
    track_serial = models.BooleanField(default=False)
    track_batch = models.BooleanField(default=False)
    prevent_expired_issuance = models.BooleanField(default=True, help_text="Block issuing expired stock (when expiry is tracked)")
    expiry_warning_days = models.PositiveIntegerField(default=0, help_text="Warn when stock will expire within N days")
    cost_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    reorder_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    # Default valuation method (aligns with migration 9999)
    valuation_method = models.CharField(
        max_length=20,
        choices=[
            ('FIFO', 'First In, First Out'),
            ('LIFO', 'Last In, First Out'),
            ('WEIGHTED_AVG', 'Weighted Average'),
            ('STANDARD_COST', 'Standard Cost'),
        ],
        default='FIFO',
        help_text='Default valuation method for this product'
    )
    standard_cost = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text='Standard cost for standard cost valuation method')
    is_active = models.BooleanField(default=True)
    category = models.ForeignKey('ProductCategory', on_delete=models.PROTECT, related_name='legacy_products')
    uom = models.ForeignKey('UnitOfMeasure', on_delete=models.PROTECT, related_name='legacy_products')
    expense_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT, related_name='expense_products')
    income_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT, related_name='income_products')
    inventory_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT, related_name='inventory_products')

    class Meta:
        unique_together = ('company', 'code')
        indexes = [
            models.Index(fields=['company', 'category']),
            models.Index(fields=['company', 'is_active']),
        ]

class StockMovement(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    movement_number = models.CharField(max_length=50)
    movement_date = models.DateField()
    movement_type = models.CharField(max_length=20, choices=[
        ('RECEIPT', 'Goods Receipt'),
        ('ISSUE', 'Goods Issue'),
        ('TRANSFER', 'Stock Transfer'),
        ('ADJUSTMENT', 'Stock Adjustment'),
    ])
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=[
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ], default='DRAFT')
    posted_at = models.DateTimeField(null=True, blank=True)
    from_warehouse = models.ForeignKey('Warehouse', on_delete=models.PROTECT, null=True, blank=True, related_name='movements_out')
    to_warehouse = models.ForeignKey('Warehouse', on_delete=models.PROTECT, related_name='movements_in')

    class Meta:
        unique_together = ('company', 'movement_number')

    def save(self, *args, **kwargs):
        is_new = self._state.adding and not self.movement_number
        super().save(*args, **kwargs)
        if is_new:
            from core.doc_numbers import get_next_doc_no
            generated = get_next_doc_no(company=self.company, doc_type="SM", prefix="SM", fy_format="YYYY", width=5)
            StockMovement.objects.filter(pk=self.pk).update(movement_number=generated)
            self.movement_number = generated

class Warehouse(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    warehouse_type = models.CharField(max_length=20, choices=[
        ('MAIN', 'Main Warehouse'),
        ('TRANSIT', 'Transit Location'),
        ('RETAIL', 'Retail Store'),
        ('VIRTUAL', 'Virtual Location'),
    ], default='MAIN')
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('company', 'code')

class UnitOfMeasure(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    company_group = models.ForeignKey('companies.CompanyGroup', on_delete=models.PROTECT, null=True, blank=True, help_text="Company group (for group-wide uniqueness)")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=20, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('company', 'code')
        verbose_name = 'Unit of Measure'
        verbose_name_plural = 'Units of Measure'

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        # Auto-derive company_group if not set
        if self.company_id and not self.company_group_id:
            try:
                self.company_group = self.company.company_group
            except Exception:
                pass
        super().save(*args, **kwargs)

class StockMovementLine(models.Model):
    movement = models.ForeignKey(StockMovement, on_delete=models.CASCADE, related_name='lines')
    line_number = models.IntegerField()
    item = models.ForeignKey('Item', on_delete=models.PROTECT, related_name='stock_movement_lines', help_text="Item being moved")
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    rate = models.DecimalField(max_digits=20, decimal_places=2)
    batch_no = models.CharField(max_length=50, blank=True)
    serial_no = models.CharField(max_length=50, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['movement', 'line_number']

class ProductCategory(models.Model):
    """LEGACY: This model will be migrated. Use sales.ProductCategory for new code."""
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to", related_name='legacy_product_categories')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    parent_category = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='legacy_sub_categories')

    class Meta:
        verbose_name_plural = 'Legacy Product Categories'
        unique_together = ('company', 'code')

class StockLedger(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    item = models.ForeignKey('Item', on_delete=models.PROTECT, related_name='stock_ledger_entries', help_text="Item for stock tracking")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    transaction_date = models.DateTimeField()
    transaction_type = models.CharField(max_length=20, choices=[
        ('RECEIPT', 'Stock Receipt'),
        ('ISSUE', 'Stock Issue'),
        ('TRANSFER', 'Transfer'),
        ('ADJUSTMENT', 'Adjustment'),
    ])
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    rate = models.DecimalField(max_digits=20, decimal_places=2)
    value = models.DecimalField(max_digits=20, decimal_places=2)
    balance_qty = models.DecimalField(max_digits=15, decimal_places=3)
    balance_value = models.DecimalField(max_digits=20, decimal_places=2)
    source_document_type = models.CharField(max_length=50)
    source_document_id = models.IntegerField()
    batch_no = models.CharField(max_length=50, blank=True)
    serial_no = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Valuation tracking (NEW fields for Phase 1)
    valuation_method_used = models.CharField(
        max_length=20,
        blank=True,
        help_text="Valuation method used for this transaction (FIFO/LIFO/AVG/STANDARD)"
    )
    layer_consumed_detail = models.JSONField(
        null=True,
        blank=True,
        help_text="Details of cost layers consumed: [{layer_id, qty_consumed, cost_per_unit}]"
    )

    class Meta:
        ordering = ['transaction_date', 'id']
        indexes = [
            models.Index(fields=['company', 'item', 'warehouse']),
            models.Index(fields=['transaction_date']),
        ]

class DeliveryOrder(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivery_number = models.CharField(max_length=50)
    delivery_date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('DRAFT', 'Draft'),
        ('POSTED', 'Posted'),
    ], default='DRAFT')
    notes = models.TextField(blank=True)
    customer = models.ForeignKey('sales.Customer', on_delete=models.PROTECT, related_name='delivery_orders')
    sales_order = models.ForeignKey('sales.SalesOrder', on_delete=models.PROTECT, related_name='delivery_orders')

    class Meta:
        unique_together = ('company', 'delivery_number')

    def save(self, *args, **kwargs):
        is_new = self._state.adding and not self.delivery_number
        previous_status = None
        if self.pk:
            previous_status = DeliveryOrder.objects.filter(pk=self.pk).values_list("status", flat=True).first()
        super().save(*args, **kwargs)
        if is_new:
            from core.doc_numbers import get_next_doc_no
            generated = get_next_doc_no(company=self.company, doc_type="DO", prefix="DO", fy_format="YYYY", width=5)
            DeliveryOrder.objects.filter(pk=self.pk).update(delivery_number=generated)
            self.delivery_number = generated
        # When moving to SUBMITTED, start workflow if template exists
        if previous_status != 'SUBMITTED' and self.status == 'SUBMITTED':
            try:
                if WorkflowTemplate.objects.filter(name__iexact='DO Approval', company=self.company, status='active').exists() or \
                   WorkflowTemplate.objects.filter(name__iexact='DO Approval', company__isnull=True, status='active').exists():
                    WorkflowService.start_workflow(self, 'DO Approval')
            except Exception:
                pass
        # Trigger posting side-effects when transitioning to POSTED
        if previous_status != 'POSTED' and self.status == 'POSTED':
            # Enforce workflow approval if a template exists
            if WorkflowTemplate.objects.filter(name__iexact='DO Approval', company=self.company, status='active').exists() or \
               WorkflowTemplate.objects.filter(name__iexact='DO Approval', company__isnull=True, status='active').exists():
                inst = WorkflowInstance.objects.filter(company=self.company, template__name__iexact='DO Approval', context__object_pk=self.pk).order_by('-created_at').first()
                if not inst:
                    raise ValueError("Cannot post Delivery Order: approval workflow not started.")
                if inst.state.lower() != 'approved':
                    raise ValueError("Cannot post Delivery Order until workflow state is 'approved'.")
            self._on_posted()

    def _on_posted(self):
        """When a Delivery Order is posted, ship goods and post to ledger/valuation."""
        try:
            from apps.inventory.services.stock_service import InventoryService
            InventoryService.ship_goods_against_so(self)
        except Exception as exc:
            # Re-raise to surface issues to the caller/transaction
            raise

class GoodsReceipt(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    receipt_number = models.CharField(max_length=50)
    receipt_date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('DRAFT', 'Draft'),
        ('POSTED', 'Posted'),
    ], default='DRAFT')
    notes = models.TextField(blank=True)
    supplier = models.ForeignKey('procurement.Supplier', on_delete=models.PROTECT, related_name='goods_receipts')
    purchase_order = models.ForeignKey('procurement.PurchaseOrder', on_delete=models.PROTECT, related_name='goods_receipts')
    quality_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('on_hold', 'On Hold'),
        ('passed', 'Passed'),
        ('rejected', 'Rejected'),
    ], default='pending')
    hold_reason = models.TextField(blank=True)
    quality_checked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    quality_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('company', 'receipt_number')

    def save(self, *args, **kwargs):
        is_new = self._state.adding and not self.receipt_number
        previous_status = None
        if self.pk:
            previous_status = GoodsReceipt.objects.filter(pk=self.pk).values_list("status", flat=True).first()
        super().save(*args, **kwargs)
        if is_new:
            from core.doc_numbers import get_next_doc_no
            generated = get_next_doc_no(company=self.company, doc_type="GRN", prefix="GRN", fy_format="YYYY", width=5)
            GoodsReceipt.objects.filter(pk=self.pk).update(receipt_number=generated)
            self.receipt_number = generated
        # When moving to SUBMITTED, start workflow if template exists
        if previous_status != 'SUBMITTED' and self.status == 'SUBMITTED':
            try:
                if WorkflowTemplate.objects.filter(name__iexact='GRN Approval', company=self.company, status='active').exists() or \
                   WorkflowTemplate.objects.filter(name__iexact='GRN Approval', company__isnull=True, status='active').exists():
                    WorkflowService.start_workflow(self, 'GRN Approval')
            except Exception:
                # If workflow not defined, continue silently
                pass

        if previous_status != 'POSTED' and self.status == 'POSTED':
            # Enforce workflow approval if a template exists
            if WorkflowTemplate.objects.filter(name__iexact='GRN Approval', company=self.company, status='active').exists() or \
               WorkflowTemplate.objects.filter(name__iexact='GRN Approval', company__isnull=True, status='active').exists():
                inst = WorkflowInstance.objects.filter(company=self.company, template__name__iexact='GRN Approval', context__object_pk=self.pk).order_by('-created_at').first()
                if not inst:
                    raise ValueError("Cannot post GRN: approval workflow not started.")
                if inst.state.lower() != 'approved':
                    raise ValueError("Cannot post GRN until workflow state is 'approved'.")
            self._on_posted()

    def _on_posted(self):
        from apps.budgeting.models import BudgetUsage
        timestamp = timezone.now()
        for line in self.lines.select_related('purchase_order_line__budget_line', 'purchase_order_line__budget_commitment'):
            po_line = line.purchase_order_line
            if not po_line:
                continue
            quantity = line.quantity_received or Decimal("0")
            po_line.register_receipt(quantity, timestamp=timestamp)
            budget_line = po_line.budget_line
            if not budget_line:
                continue
            usage_type_map = {
                'stock_item': 'procurement_receipt',
                'service_item': 'service_receipt',
                'capex_item': 'capex_receipt',
            }
            usage_type = usage_type_map.get(budget_line.procurement_class, 'procurement_receipt')
            BudgetUsage.objects.create(
                budget_line=budget_line,
                usage_date=self.receipt_date,
                usage_type=usage_type,
                quantity=quantity,
                amount=(po_line.unit_price or Decimal("0")) * quantity,
                reference_type="GoodsReceipt",
                reference_id=f"{self.id}:{po_line.id}",
                description=self.notes or "",
                created_by=self.created_by,
            )
        self.purchase_order.update_receipt_status()
        # Create stock movement, ledger entries and valuation layers
        try:
            from apps.inventory.services.stock_service import InventoryService
            InventoryService.receive_goods_against_po(self)
        except Exception:
            # Re-raise to avoid silently losing inventory postings
            raise

    def place_on_hold(self, *, reason: str, user=None):
        self.quality_status = 'on_hold'
        self.hold_reason = reason
        self.quality_checked_by = user
        self.quality_checked_at = timezone.now()
        self.save(update_fields=['quality_status', 'hold_reason', 'quality_checked_by', 'quality_checked_at', 'updated_at'])
        # Update related cost layers to ON_HOLD
        try:
            CostLayer.objects.filter(
                company=self.company,
                source_document_type='GoodsReceipt',
                source_document_id=self.id,
            ).update(stock_state='ON_HOLD')
        except Exception:
            pass

    def release_hold(self, *, user=None, passed: bool = True):
        self.quality_status = 'passed' if passed else 'rejected'
        self.quality_checked_by = user
        self.quality_checked_at = timezone.now()
        self.save(update_fields=['quality_status', 'quality_checked_by', 'quality_checked_at', 'updated_at'])
        # Update related cost layers to RELEASED or keep ON_HOLD if rejected
        try:
            new_state = 'RELEASED' if passed else 'ON_HOLD'
            CostLayer.objects.filter(
                company=self.company,
                source_document_type='GoodsReceipt',
                source_document_id=self.id,
            ).update(stock_state=new_state)
        except Exception:
            pass

class StockLevel(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    item = models.ForeignKey('Item', on_delete=models.PROTECT, related_name='stock_levels', help_text="Item with stock level")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=15, decimal_places=3, default=0)

    class Meta:
        unique_together = ('company', 'item', 'warehouse')
        indexes = [
            models.Index(fields=['company', 'item', 'warehouse']),
        ]


class InternalRequisition(models.Model):
    """Simple internal stock requisition for operational needs."""
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"
        CANCELLED = "CANCELLED", "Cancelled"

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    requisition_number = models.CharField(max_length=50, blank=True, db_index=True)
    request_date = models.DateField()
    needed_by = models.DateField(null=True, blank=True)
    warehouse = models.ForeignKey('Warehouse', on_delete=models.PROTECT, null=True, blank=True)
    purpose = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)

    # Store lines as JSON for MVP: [{item_id, item_name, quantity, uom, notes}]
    lines = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'requisition_number']),
        ]

    def __str__(self) -> str:
        return self.requisition_number or f"IR-{self.pk}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.requisition_number:
            from core.doc_numbers import get_next_doc_no
            generated = get_next_doc_no(company=self.company, doc_type="IR", prefix="IR", fy_format="YYYY", width=5)
            InternalRequisition.objects.filter(pk=self.pk).update(requisition_number=generated)
            self.requisition_number = generated

class GoodsReceiptLine(models.Model):
    goods_receipt = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name='lines')
    item = models.ForeignKey('Item', on_delete=models.PROTECT, related_name='goods_receipt_lines', help_text="Item being received")
    purchase_order_line = models.ForeignKey('procurement.PurchaseOrderLine', on_delete=models.PROTECT, related_name='receipt_lines')
    quantity_received = models.DecimalField(max_digits=15, decimal_places=3)
    batch_no = models.CharField(max_length=50, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('goods_receipt', 'purchase_order_line')

class DeliveryOrderLine(models.Model):
    delivery_order = models.ForeignKey(DeliveryOrder, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(
        'sales.Product',
        on_delete=models.PROTECT,
        related_name='delivery_order_lines',
        help_text="Saleable product being delivered to customer"
    )
    sales_order_line = models.ForeignKey('sales.SalesOrderLine', on_delete=models.PROTECT, related_name='delivery_lines')
    quantity_shipped = models.DecimalField(max_digits=15, decimal_places=3)

    class Meta:
        unique_together = ('delivery_order', 'sales_order_line')


# ========================================
# VALUATION & COST LAYER MODELS
# ========================================

class ItemValuationMethod(models.Model):
    """
    Defines the valuation method for a specific item/warehouse combination.
    Supports FIFO, LIFO, Weighted Average, and Standard Cost methods.
    """
    VALUATION_METHOD_CHOICES = [
        ('FIFO', 'First In, First Out'),
        ('LIFO', 'Last In, First Out'),
        ('WEIGHTED_AVG', 'Weighted Average'),
        ('STANDARD', 'Standard Cost'),
    ]

    AVERAGE_PERIOD_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('PERPETUAL', 'Perpetual (Moving Average)'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    product = models.ForeignKey('Item', on_delete=models.PROTECT, related_name='valuation_methods')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='valuation_methods')
    valuation_method = models.CharField(max_length=20, choices=VALUATION_METHOD_CHOICES, default='FIFO')

    # For weighted average only
    avg_period = models.CharField(
        max_length=20,
        choices=AVERAGE_PERIOD_CHOICES,
        default='PERPETUAL',
        help_text="Applicable only for Weighted Average method"
    )

    # Control flags
    allow_negative_inventory = models.BooleanField(
        default=False,
        help_text="Allow stock to go negative (backorders)"
    )
    prevent_cost_below_zero = models.BooleanField(
        default=True,
        help_text="Prevent cost per unit from going below zero"
    )

    effective_date = models.DateField(
        help_text="Date from which this valuation method is effective"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('company', 'product', 'warehouse', 'effective_date')
        ordering = ['-effective_date']
        indexes = [
            models.Index(fields=['company', 'product', 'warehouse', '-effective_date']),
            models.Index(fields=['company', 'product', 'is_active']),
        ]
        verbose_name = 'Item Valuation Method'
        verbose_name_plural = 'Item Valuation Methods'

    def __str__(self):
        return f"{self.product.code} @ {self.warehouse.code} - {self.get_valuation_method_display()}"


class CostLayer(models.Model):
    """
    Immutable record of inventory receipt costs for FIFO/LIFO tracking.
    Each receipt creates a new layer. Issues consume from layers based on valuation method.
    """
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_at = models.DateTimeField(auto_now_add=True)

    product = models.ForeignKey('Item', on_delete=models.PROTECT, related_name='cost_layers')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='cost_layers')

    # Receipt information
    receipt_date = models.DateTimeField(help_text="When this layer was created (receipt timestamp)")
    qty_received = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        help_text="Original quantity received in this layer"
    )
    cost_per_unit = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        help_text="Cost per unit at receipt (includes landed cost if already known)"
    )
    total_cost = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Total cost of layer (qty_received × cost_per_unit)"
    )

    # Current state
    qty_remaining = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        help_text="Quantity still available in this layer (updated on consumption)"
    )
    cost_remaining = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Cost remaining in this layer (qty_remaining × cost_per_unit)"
    )

    # FIFO sequencing
    fifo_sequence = models.IntegerField(
        help_text="Sequence number for FIFO ordering (auto-incremented per product+warehouse)"
    )

    # Batch tracking (optional)
    batch_no = models.CharField(max_length=50, blank=True, help_text="Batch number if tracked")
    serial_no = models.CharField(max_length=50, blank=True, help_text="Serial number if tracked")

    # Valuation type
    is_standard_cost = models.BooleanField(
        default=False,
        help_text="True if this is a standard cost layer (not actual receipt)"
    )

    # Stock state for QC and availability
    STOCK_STATE_CHOICES = [
        ('QUARANTINE', 'Quarantine'),
        ('ON_HOLD', 'On Hold'),
        ('RELEASED', 'Released'),
    ]
    stock_state = models.CharField(
        max_length=20,
        choices=STOCK_STATE_CHOICES,
        default='QUARANTINE',
        help_text="Stock availability state; only RELEASED layers are issuable"
    )

    # Landed cost adjustments
    landed_cost_adjustment = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=0,
        help_text="Additional cost per unit from landed cost (freight, duty, etc.)"
    )
    adjustment_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When landed cost adjustment was applied"
    )
    adjustment_reason = models.TextField(blank=True, help_text="Reason for cost adjustment")
    # Expiry for FEFO and compliance
    expiry_date = models.DateField(null=True, blank=True)

    # Source document tracking
    source_document_type = models.CharField(
        max_length=50,
        help_text="Type of source document (GoodsReceipt, StockMovement, etc.)"
    )
    source_document_id = models.IntegerField(
        help_text="ID of source document"
    )

    # Immutability control
    immutable_after_post = models.BooleanField(
        default=True,
        help_text="Once consumed, cost_per_unit cannot change (only qty_remaining updates)"
    )
    is_closed = models.BooleanField(
        default=False,
        help_text="True when qty_remaining = 0 (fully consumed)"
    )

    class Meta:
        ordering = ['fifo_sequence', 'receipt_date', 'id']
        indexes = [
            models.Index(fields=['company', 'product', 'warehouse', 'is_closed']),
            models.Index(fields=['company', 'product', 'warehouse', 'fifo_sequence']),
            models.Index(fields=['company', 'product', 'warehouse', 'stock_state']),
            models.Index(fields=['receipt_date']),
            models.Index(fields=['source_document_type', 'source_document_id']),
        ]
        verbose_name = 'Cost Layer'
        verbose_name_plural = 'Cost Layers'

    def __str__(self):
        return f"{self.product.code} Layer #{self.fifo_sequence} @ {self.cost_per_unit}"

    def save(self, *args, **kwargs):
        # Auto-calculate total_cost and cost_remaining
        if self.qty_received and self.cost_per_unit:
            self.total_cost = Decimal(str(self.qty_received)) * Decimal(str(self.cost_per_unit))

        if self.qty_remaining and self.cost_per_unit:
            self.cost_remaining = Decimal(str(self.qty_remaining)) * Decimal(str(self.cost_per_unit + self.landed_cost_adjustment))

        # Mark as closed if qty_remaining is zero
        if self.qty_remaining <= 0:
            self.is_closed = True

        super().save(*args, **kwargs)


class ValuationChangeLog(models.Model):
    """
    Audit trail for valuation method changes.
    Tracks who requested, who approved, and the financial impact.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('EFFECTIVE', 'Effective (Applied)'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    product = models.ForeignKey('Item', on_delete=models.PROTECT, related_name='valuation_changes')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='valuation_changes')

    # Change details
    old_method = models.CharField(max_length=20, choices=ItemValuationMethod.VALUATION_METHOD_CHOICES)
    new_method = models.CharField(max_length=20, choices=ItemValuationMethod.VALUATION_METHOD_CHOICES)
    effective_date = models.DateField(help_text="Date when change becomes effective")

    # Financial impact
    old_inventory_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Inventory value before change"
    )
    new_inventory_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Inventory value after change"
    )
    revaluation_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text="Adjustment amount (positive = increase, negative = decrease)"
    )

    # Approval workflow
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='valuation_changes_requested'
    )
    requested_date = models.DateTimeField(auto_now_add=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='valuation_changes_approved'
    )
    approval_date = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reason = models.TextField(help_text="Business reason for the change")
    rejection_reason = models.TextField(blank=True, help_text="Reason if rejected")

    # GL Integration
    revaluation_je_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Journal Entry ID for revaluation posting"
    )

    class Meta:
        ordering = ['-requested_date']
        indexes = [
            models.Index(fields=['company', 'product', 'warehouse']),
            models.Index(fields=['status', '-requested_date']),
            models.Index(fields=['effective_date']),
        ]
        verbose_name = 'Valuation Change Log'
        verbose_name_plural = 'Valuation Change Logs'

    def __str__(self):
        return f"{self.product.code} @ {self.warehouse.code}: {self.old_method} → {self.new_method}"


# ========================================
# NEW ITEM AND ITEMCATEGORY MODELS
# For Product-to-Item refactoring
# ========================================

class Item(models.Model):
    """
    Items are non-saleable inventory components used in operations:
    - Raw materials, Consumables, Components, Fixed assets, etc.
    Different from Product (in sales app) which represents saleable items.
    """

    ITEM_TYPE_CHOICES = [
        ('RAW_MATERIAL', 'Raw Material'),
        ('CONSUMABLE', 'Consumable'),
        ('COMPONENT', 'Component'),
        ('FIXED_ASSET', 'Fixed Asset'),
        ('SERVICE', 'Service'),
        ('SEMI_FINISHED', 'Semi-Finished Good'),
        ('PACKING_MATERIAL', 'Packing Material'),
        ('SPARE_PART', 'Spare Part'),
        ('TOOL', 'Tool'),
    ]

    VALUATION_METHOD_CHOICES = [
        ('FIFO', 'First In, First Out'),
        ('LIFO', 'Last In, First Out'),
        ('WEIGHTED_AVG', 'Weighted Average'),
        ('STANDARD_COST', 'Standard Cost'),
    ]

    # Base fields
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Identification
    code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Classification
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, default='RAW_MATERIAL', help_text="Type of item")
    is_tradable = models.BooleanField(default=False, help_text="If True, can be linked to a saleable Product")

    # Inventory tracking
    track_inventory = models.BooleanField(default=True)
    track_serial = models.BooleanField(default=False)
    track_batch = models.BooleanField(default=False)
    prevent_expired_issuance = models.BooleanField(default=True)
    expiry_warning_days = models.PositiveIntegerField(default=0)

    # Costing
    cost_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    standard_cost = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    valuation_method = models.CharField(max_length=20, choices=VALUATION_METHOD_CHOICES, default='FIFO')

    # Reordering
    reorder_level = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    reorder_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    lead_time_days = models.IntegerField(default=0)

    # Accounting
    inventory_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT, related_name='inventory_items', null=True, blank=True)
    expense_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT, related_name='expense_items', null=True, blank=True)

    # Master data
    category = models.ForeignKey('ItemCategory', on_delete=models.PROTECT, help_text="Item category")
    uom = models.ForeignKey('UnitOfMeasure', on_delete=models.PROTECT, related_name='items')

    # Status
    is_active = models.BooleanField(default=True)

    # Backward compatibility
    legacy_product_id = models.IntegerField(null=True, blank=True, help_text="Link to original Product record")

    class Meta:
        db_table = 'inventory_item'
        unique_together = ('company', 'code')
        indexes = [
            models.Index(fields=['company', 'category']),
            models.Index(fields=['company', 'item_type']),
            models.Index(fields=['company', 'is_active']),
        ]
        verbose_name = 'Item'
        verbose_name_plural = 'Items'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_available_stock(self, warehouse=None):
        """Get available stock quantity for this item"""
        if warehouse:
            try:
                stock_level = StockLevel.objects.get(company=self.company, item=self, warehouse=warehouse)
                return stock_level.quantity
            except StockLevel.DoesNotExist:
                return Decimal('0.00')
        else:
            total = StockLevel.objects.filter(company=self.company, item=self).aggregate(total=models.Sum('quantity'))['total'] or Decimal('0.00')
            return total


class ItemCategory(models.Model):
    """
    Hierarchical item categories with unlimited depth
    Supports: Category → Sub-Category → Sub-Sub-Category → ...
    """
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Hierarchical structure
    parent_category = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='sub_categories')
    hierarchy_path = models.CharField(max_length=500, editable=False, blank=True, db_index=True)
    level = models.IntegerField(default=0, editable=False)

    is_active = models.BooleanField(default=True)
    is_default_template = models.BooleanField(default=False, help_text="System default category")

    class Meta:
        db_table = 'inventory_item_category'
        unique_together = ('company', 'code')
        verbose_name_plural = 'Item Categories'
        ordering = ['hierarchy_path', 'code']
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['hierarchy_path']),
        ]

    def __str__(self):
        return self.get_full_path()

    def save(self, *args, **kwargs):
        # Calculate level and hierarchy path
        if self.parent_category:
            self.level = self.parent_category.level + 1
            parent_path = self.parent_category.hierarchy_path or str(self.parent_category.id)
            if not self.pk:
                self.hierarchy_path = f"{parent_path}/new"
            else:
                self.hierarchy_path = f"{parent_path}/{self.id}"
        else:
            self.level = 0
            if not self.pk:
                self.hierarchy_path = "new"
            else:
                self.hierarchy_path = str(self.id)

        super().save(*args, **kwargs)

        # Update hierarchy path if new record
        if 'new' in self.hierarchy_path:
            if self.parent_category:
                parent_path = self.parent_category.hierarchy_path or str(self.parent_category.id)
                new_path = f"{parent_path}/{self.id}"
            else:
                new_path = str(self.id)
            ItemCategory.objects.filter(pk=self.pk).update(hierarchy_path=new_path)
            self.hierarchy_path = new_path

    def get_ancestors(self):
        """Get all parent categories up to root"""
        ancestors = []
        current = self.parent_category
        while current:
            ancestors.insert(0, current)
            current = current.parent_category
        return ancestors

    def get_descendants(self):
        """Get all child categories (recursive)"""
        return ItemCategory.objects.filter(company=self.company, hierarchy_path__startswith=self.hierarchy_path + '/')

    def get_full_path(self):
        """Get full category path: 'Raw Materials / Metals / Steel'"""
        ancestors = self.get_ancestors()
        path_parts = [a.name for a in ancestors] + [self.name]
        return ' / '.join(path_parts)
