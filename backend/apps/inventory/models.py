from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
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
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='stock_movements', help_text="Budget master item reference")
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
        ('IN_TRANSIT', 'In Transit'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ], default='DRAFT')
    posted_at = models.DateTimeField(null=True, blank=True)
    from_warehouse = models.ForeignKey('Warehouse', on_delete=models.PROTECT, null=True, blank=True, related_name='movements_out')
    to_warehouse = models.ForeignKey('Warehouse', on_delete=models.PROTECT, related_name='movements_in')
    cost_center = models.ForeignKey('budgeting.CostCenter', on_delete=models.PROTECT, null=True, blank=True, related_name='stock_movements')
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT, null=True, blank=True, related_name='stock_movements')
    cost_center = models.ForeignKey('budgeting.CostCenter', on_delete=models.PROTECT, null=True, blank=True, related_name='stock_movements')
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT, null=True, blank=True, related_name='stock_movements')

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
    code = models.CharField(max_length=20, blank=True)
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

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.code:
            # Auto-generate code: WH-001, WH-002, etc.
            last_warehouse = Warehouse.objects.filter(
                company=self.company
            ).order_by('-id').first()

            if last_warehouse and last_warehouse.code:
                try:
                    last_num = int(last_warehouse.code.split('-')[-1])
                    next_num = last_num + 1
                except (ValueError, IndexError):
                    next_num = 1
            else:
                next_num = 1

            self.code = f"WH-{next_num:03d}"

        super().save(*args, **kwargs)

class WarehouseBin(models.Model):
    """
    Logical sub-location inside a warehouse (rack, shelf, bin).
    Enables the item warehouse configuration model to store default bin routing.
    """
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='inventory_bins')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='bins')
    code = models.CharField(max_length=30, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('warehouse', 'code')
        indexes = [
            models.Index(fields=['company', 'warehouse']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = 'Warehouse Bin'
        verbose_name_plural = 'Warehouse Bins'

    def __str__(self):
        return f"{self.warehouse.code}-{self.code}"

    def save(self, *args, **kwargs):
        if not self.code:
            # Auto-generate code: BIN-001, BIN-002, etc.
            last_bin = WarehouseBin.objects.filter(
                warehouse=self.warehouse
            ).order_by('-id').first()

            if last_bin and last_bin.code:
                # Try to extract number from last code
                try:
                    last_num = int(last_bin.code.split('-')[-1])
                    next_num = last_num + 1
                except (ValueError, IndexError):
                    next_num = 1
            else:
                next_num = 1

            self.code = f"BIN-{next_num:03d}"

        super().save(*args, **kwargs)

class UnitOfMeasure(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    company_group = models.ForeignKey('companies.CompanyGroup', on_delete=models.PROTECT, null=True, blank=True, help_text="Company group (for group-wide uniqueness)")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    code = models.CharField(max_length=10, blank=True)
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
        # Auto-generate code if not set
        if not self.code:
            last_uom = UnitOfMeasure.objects.filter(
                company=self.company
            ).order_by('-id').first()

            if last_uom and last_uom.code:
                try:
                    last_num = int(last_uom.code.split('-')[-1])
                    next_num = last_num + 1
                except (ValueError, IndexError):
                    next_num = 1
            else:
                next_num = 1

            self.code = f"UOM-{next_num:03d}"

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
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='stock_movement_lines', help_text="Item being moved")
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    entered_quantity = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, help_text="Original quantity in entered UoM")
    entered_uom = models.ForeignKey('UnitOfMeasure', on_delete=models.PROTECT, null=True, blank=True, related_name='entered_stock_movement_lines')
    rate = models.DecimalField(max_digits=20, decimal_places=2)
    batch_no = models.CharField(max_length=50, blank=True)
    serial_no = models.CharField(max_length=50, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    cost_center = models.ForeignKey('budgeting.CostCenter', on_delete=models.PROTECT, null=True, blank=True, related_name='stock_movement_lines')
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT, null=True, blank=True, related_name='stock_movement_lines')
    cost_center = models.ForeignKey('budgeting.CostCenter', on_delete=models.PROTECT, null=True, blank=True, related_name='stock_movement_lines')
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT, null=True, blank=True, related_name='stock_movement_lines')

    class Meta:
        ordering = ['movement', 'line_number']

class InTransitShipmentLine(models.Model):
    """Tracks quantities currently in transit for a transfer movement."""

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='in_transit_lines')
    movement = models.ForeignKey(StockMovement, on_delete=models.CASCADE, related_name='in_transit_lines')
    movement_line = models.ForeignKey(StockMovementLine, on_delete=models.CASCADE, related_name='in_transit_entries')
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='in_transit_lines', help_text="Item in transit")
    from_warehouse = models.ForeignKey('Warehouse', on_delete=models.PROTECT, related_name='in_transit_out')
    to_warehouse = models.ForeignKey('Warehouse', on_delete=models.PROTECT, related_name='in_transit_in')
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    rate = models.DecimalField(max_digits=20, decimal_places=2)
    batch_no = models.CharField(max_length=50, blank=True)
    serial_no = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    cost_center = models.ForeignKey('budgeting.CostCenter', on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    movement_event = models.OneToOneField('inventory.MovementEvent', on_delete=models.SET_NULL, null=True, blank=True, related_name='in_transit_snapshot')

    class Meta:
        indexes = [
            models.Index(fields=['company', 'budget_item']),
            models.Index(fields=['company', 'from_warehouse']),
            models.Index(fields=['company', 'to_warehouse']),
        ]

    def __str__(self):
        return f"{self.budget_item.code} {self.quantity} in transit"

class ProductCategory(models.Model):
    """LEGACY: This model will be migrated. Use sales.ProductCategory for new code."""
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to", related_name='legacy_product_categories')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    code = models.CharField(max_length=20, blank=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    parent_category = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='legacy_sub_categories')

    class Meta:
        verbose_name_plural = 'Legacy Product Categories'
        unique_together = ('company', 'code')

    def save(self, *args, **kwargs):
        if not self.code:
            last_cat = ProductCategory.objects.filter(
                company=self.company
            ).order_by('-id').first()

            if last_cat and last_cat.code:
                try:
                    last_num = int(last_cat.code.split('-')[-1])
                    next_num = last_num + 1
                except (ValueError, IndexError):
                    next_num = 1
            else:
                next_num = 1

            self.code = f"CAT-{next_num:03d}"

        super().save(*args, **kwargs)

class StockLedger(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='stock_ledger_entries', help_text="Item for stock tracking")
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
    movement_event = models.OneToOneField('inventory.MovementEvent', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_ledger_entry')
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
    cost_center = models.ForeignKey('budgeting.CostCenter', on_delete=models.PROTECT, null=True, blank=True, related_name='stock_ledger_entries')
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT, null=True, blank=True, related_name='stock_ledger_entries')

    class Meta:
        ordering = ['transaction_date', 'id']
        indexes = [
            models.Index(fields=['company', 'budget_item', 'warehouse']),
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
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='stock_levels', help_text="Item with stock level")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=15, decimal_places=3, default=0)

    class Meta:
        unique_together = ('company', 'budget_item', 'warehouse')
        indexes = [
            models.Index(fields=['company', 'budget_item', 'warehouse']),
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
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='goods_receipt_lines', help_text="Item being received")
    purchase_order_line = models.ForeignKey('procurement.PurchaseOrderLine', on_delete=models.PROTECT, related_name='receipt_lines')
    quantity_received = models.DecimalField(max_digits=15, decimal_places=3)
    batch_no = models.CharField(max_length=50, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    serial_numbers = models.JSONField(default=list, blank=True, help_text="Array of serial numbers for serialized items")
    manufacturer_batch_no = models.CharField(max_length=100, blank=True, help_text="Manufacturer's batch/lot number")
    certificate_of_analysis = models.FileField(upload_to='qc/coa/', null=True, blank=True, help_text="Certificate of Analysis document")

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

    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='valuation_methods', help_text="Item for valuation tracking")
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
        unique_together = ('company', 'budget_item', 'warehouse', 'effective_date')
        ordering = ['-effective_date']
        indexes = [
            models.Index(fields=['company', 'budget_item', 'warehouse', '-effective_date']),
            models.Index(fields=['company', 'budget_item', 'is_active']),
        ]
        verbose_name = 'Item Valuation Method'
        verbose_name_plural = 'Item Valuation Methods'

    def __str__(self):
        return f"{self.budget_item.code} @ {self.warehouse.code} - {self.get_valuation_method_display()}"


class CostLayer(models.Model):
    """
    Immutable record of inventory receipt costs for FIFO/LIFO tracking.
    Each receipt creates a new layer. Issues consume from layers based on valuation method.
    """
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_at = models.DateTimeField(auto_now_add=True)

    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='cost_layers', help_text="Item for cost layer tracking")
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
            models.Index(fields=['company', 'budget_item', 'warehouse', 'is_closed']),
            models.Index(fields=['company', 'budget_item', 'warehouse', 'fifo_sequence']),
            models.Index(fields=['company', 'budget_item', 'warehouse', 'stock_state']),
            models.Index(fields=['receipt_date']),
            models.Index(fields=['source_document_type', 'source_document_id']),
        ]
        verbose_name = 'Cost Layer'
        verbose_name_plural = 'Cost Layers'

    def __str__(self):
        item_code = self.budget_item.code if self.budget_item else 'N/A'
        return f"{item_code} Layer #{self.fifo_sequence} @ {self.cost_per_unit}"

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

    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='valuation_changes', help_text="Item with valuation change")
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
            models.Index(fields=['company', 'budget_item', 'warehouse']),
            models.Index(fields=['status', '-requested_date']),
            models.Index(fields=['effective_date']),
        ]
        verbose_name = 'Valuation Change Log'
        verbose_name_plural = 'Valuation Change Logs'

    def __str__(self):
        return f"{self.budget_item.code} @ {self.warehouse.code}: {self.old_method} → {self.new_method}"


class StandardCostVariance(models.Model):
    """
    Tracks variances between standard cost and actual cost.
    Used when item is valued at STANDARD_COST method.
    """
    VARIANCE_TYPE_CHOICES = [
        ('FAVORABLE', 'Favorable (Actual < Standard)'),
        ('UNFAVORABLE', 'Unfavorable (Actual > Standard)'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Transaction reference
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='standard_variances', help_text="Item with standard cost variance")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='standard_variances')
    transaction_date = models.DateField()
    transaction_type = models.CharField(
        max_length=20,
        choices=[
            ('GRN', 'Goods Receipt'),
            ('ISSUE', 'Stock Issue'),
            ('ADJUSTMENT', 'Inventory Adjustment'),
        ]
    )
    reference_id = models.IntegerField(help_text="GRN ID or Stock Ledger ID")

    # Cost details
    standard_cost = models.DecimalField(max_digits=15, decimal_places=4, help_text="Standard cost per unit")
    actual_cost = models.DecimalField(max_digits=15, decimal_places=4, help_text="Actual cost per unit")
    quantity = models.DecimalField(max_digits=15, decimal_places=4, help_text="Quantity (stock UoM)")

    # Variance calculation
    variance_per_unit = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text="Actual - Standard (negative = favorable)"
    )
    total_variance_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="variance_per_unit × quantity"
    )
    variance_type = models.CharField(max_length=15, choices=VARIANCE_TYPE_CHOICES)

    # GL Integration
    variance_je_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Journal Entry ID for variance posting"
    )
    posted_to_gl = models.BooleanField(default=False)
    gl_posted_date = models.DateTimeField(null=True, blank=True)

    # Additional tracking
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['company', 'budget_item', 'warehouse']),
            models.Index(fields=['transaction_date', 'variance_type']),
            models.Index(fields=['posted_to_gl', 'transaction_date']),
        ]
        verbose_name = 'Standard Cost Variance'
        verbose_name_plural = 'Standard Cost Variances'

    def __str__(self):
        return f"{self.budget_item.code}: {self.variance_type} ${self.total_variance_amount}"

    def save(self, *args, **kwargs):
        # Calculate variance
        self.variance_per_unit = self.actual_cost - self.standard_cost
        self.total_variance_amount = self.variance_per_unit * self.quantity

        # Determine variance type
        if self.variance_per_unit < 0:
            self.variance_type = 'FAVORABLE'
        else:
            self.variance_type = 'UNFAVORABLE'

        super().save(*args, **kwargs)


class PurchasePriceVariance(models.Model):
    """
    Tracks variances between expected purchase price and actual invoice price.
    Captured at GRN time when PO price differs from invoice price.
    """
    VARIANCE_TYPE_CHOICES = [
        ('FAVORABLE', 'Favorable (Invoice < PO)'),
        ('UNFAVORABLE', 'Unfavorable (Invoice > PO)'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Transaction reference
    goods_receipt = models.ForeignKey('GoodsReceipt', on_delete=models.PROTECT, related_name='price_variances')
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='ppv_records', help_text="Item with purchase price variance")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='ppv_records')

    # Price details
    po_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text="Purchase Order unit price"
    )
    invoice_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text="Actual invoice unit price"
    )
    quantity = models.DecimalField(max_digits=15, decimal_places=4, help_text="Quantity received")

    # Variance calculation
    variance_per_unit = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text="Invoice - PO (negative = favorable)"
    )
    total_variance_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="variance_per_unit × quantity"
    )
    variance_type = models.CharField(max_length=15, choices=VARIANCE_TYPE_CHOICES)

    # GL Integration
    variance_je_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Journal Entry ID for PPV posting"
    )
    posted_to_gl = models.BooleanField(default=False)
    gl_posted_date = models.DateTimeField(null=True, blank=True)

    # Additional tracking
    supplier_id = models.IntegerField(null=True, blank=True, help_text="Supplier reference")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'budget_item', 'warehouse']),
            models.Index(fields=['goods_receipt', 'variance_type']),
            models.Index(fields=['posted_to_gl', '-created_at']),
        ]
        verbose_name = 'Purchase Price Variance'
        verbose_name_plural = 'Purchase Price Variances'

    def __str__(self):
        return f"PPV GRN#{self.goods_receipt_id}: {self.variance_type} ${self.total_variance_amount}"

    def save(self, *args, **kwargs):
        # Calculate variance
        self.variance_per_unit = self.invoice_price - self.po_price
        self.total_variance_amount = self.variance_per_unit * self.quantity

        # Determine variance type
        if self.variance_per_unit < 0:
            self.variance_type = 'FAVORABLE'
        else:
            self.variance_type = 'UNFAVORABLE'

        super().save(*args, **kwargs)


class LandedCostComponent(models.Model):
    """
    Individual components of landed cost (freight, duty, insurance, etc.)
    Enables detailed tracking and apportionment.
    """
    COMPONENT_TYPE_CHOICES = [
        ('FREIGHT', 'Freight / Shipping'),
        ('INSURANCE', 'Insurance'),
        ('CUSTOMS_DUTY', 'Customs Duty'),
        ('IMPORT_TAX', 'Import Tax'),
        ('BROKERAGE', 'Brokerage Fees'),
        ('PORT_HANDLING', 'Port Handling'),
        ('DEMURRAGE', 'Demurrage'),
        ('INSPECTION', 'Inspection Fees'),
        ('OTHER', 'Other Charges'),
    ]

    APPORTIONMENT_METHOD_CHOICES = [
        ('QUANTITY', 'By Quantity'),
        ('VALUE', 'By Line Value'),
        ('WEIGHT', 'By Weight'),
        ('VOLUME', 'By Volume'),
        ('MANUAL', 'Manual Allocation'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Link to GRN
    goods_receipt = models.ForeignKey('GoodsReceipt', on_delete=models.PROTECT, related_name='landed_cost_components')

    # Component details
    component_type = models.CharField(max_length=20, choices=COMPONENT_TYPE_CHOICES)
    description = models.CharField(max_length=255, blank=True)
    total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Total amount for this component"
    )
    currency = models.CharField(max_length=3, default='USD')

    # Apportionment
    apportionment_method = models.CharField(max_length=20, choices=APPORTIONMENT_METHOD_CHOICES)
    apportioned_to_inventory = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text="Amount applied to remaining inventory"
    )
    apportioned_to_cogs = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text="Amount applied to consumed goods"
    )

    # Invoice reference
    invoice_number = models.CharField(max_length=100, blank=True)
    invoice_date = models.DateField(null=True, blank=True)
    supplier_id = models.IntegerField(null=True, blank=True)

    # GL Integration
    je_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Journal Entry ID for landed cost posting"
    )
    posted_to_gl = models.BooleanField(default=False)
    gl_posted_date = models.DateTimeField(null=True, blank=True)

    # Audit
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='applied_landed_costs'
    )
    applied_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'goods_receipt']),
            models.Index(fields=['component_type', '-created_at']),
            models.Index(fields=['posted_to_gl']),
        ]
        verbose_name = 'Landed Cost Component'
        verbose_name_plural = 'Landed Cost Components'

    def __str__(self):
        return f"{self.get_component_type_display()} - GRN#{self.goods_receipt_id}: ${self.total_amount}"


class LandedCostLineApportionment(models.Model):
    """
    Per-line apportionment detail for landed cost components.
    Shows how much of each component was allocated to each GRN line.
    """
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    # References
    landed_cost_component = models.ForeignKey(
        LandedCostComponent,
        on_delete=models.CASCADE,
        related_name='line_apportionments'
    )
    goods_receipt_line = models.ForeignKey(
        'GoodsReceiptLine',
        on_delete=models.PROTECT,
        related_name='landed_cost_apportionments'
    )
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='landed_cost_components', help_text="Item receiving landed cost allocation")

    # Apportionment calculation
    basis_value = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        help_text="Quantity, value, weight, or volume used for apportionment"
    )
    allocation_percentage = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        help_text="% of total component allocated to this line"
    )
    apportioned_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Amount allocated to this line"
    )
    cost_per_unit_adjustment = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text="Per-unit cost increase from this component"
    )

    class Meta:
        ordering = ['landed_cost_component', 'goods_receipt_line']
        indexes = [
            models.Index(fields=['company', 'budget_item']),
            models.Index(fields=['landed_cost_component']),
        ]
        verbose_name = 'Landed Cost Line Apportionment'
        verbose_name_plural = 'Landed Cost Line Apportionments'

    def __str__(self):
        return f"{self.budget_item.code}: +${self.cost_per_unit_adjustment}/unit"


class LandedCostVoucher(models.Model):
    """
    Voucher for managing landed cost allocation to multiple GRNs.
    Acts as a container for multiple cost allocations.
    """
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('ALLOCATED', 'Allocated to Cost Layers'),
        ('POSTED', 'Posted to GL'),
        ('CANCELLED', 'Cancelled'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Voucher identification
    voucher_number = models.CharField(max_length=50, unique=True, db_index=True)
    voucher_date = models.DateField()
    description = models.TextField(blank=True)

    # References
    supplier_id = models.IntegerField(null=True, blank=True, help_text="Supplier providing the service")
    invoice_number = models.CharField(max_length=100, blank=True)
    invoice_date = models.DateField(null=True, blank=True)

    # Status and workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    # Totals
    total_cost = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text="Total landed cost to be allocated"
    )
    allocated_cost = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text="Amount already allocated to cost layers"
    )

    # Workflow tracking
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_landed_cost_vouchers'
    )
    submitted_date = models.DateTimeField(null=True, blank=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_landed_cost_vouchers'
    )
    approval_date = models.DateTimeField(null=True, blank=True)

    # GL Integration
    je_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Journal Entry ID when posted to GL"
    )
    posted_to_gl = models.BooleanField(default=False)
    gl_posted_date = models.DateTimeField(null=True, blank=True)

    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_landed_cost_vouchers'
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-voucher_date', '-created_at']
        indexes = [
            models.Index(fields=['company', 'voucher_number']),
            models.Index(fields=['status', '-voucher_date']),
            models.Index(fields=['posted_to_gl', '-voucher_date']),
        ]
        verbose_name = 'Landed Cost Voucher'
        verbose_name_plural = 'Landed Cost Vouchers'

    def __str__(self):
        return f"LCV#{self.voucher_number} - ${self.total_cost}"

    def can_edit(self):
        """Check if voucher can be edited"""
        return self.status in ['DRAFT', 'SUBMITTED']

    def can_submit(self):
        """Check if voucher can be submitted"""
        return self.status == 'DRAFT' and self.total_cost > 0

    def can_approve(self):
        """Check if voucher can be approved"""
        return self.status == 'SUBMITTED'

    def can_allocate(self):
        """Check if voucher can be allocated"""
        return self.status == 'APPROVED' and self.allocated_cost < self.total_cost

    @property
    def unallocated_cost(self):
        """Calculate unallocated amount"""
        return self.total_cost - self.allocated_cost


class LandedCostAllocation(models.Model):
    """
    Allocation of landed cost from voucher to specific cost layers.
    Links voucher to GRN lines and updates cost layers.
    """
    ALLOCATION_STATUS_CHOICES = [
        ('PENDING', 'Pending Allocation'),
        ('ALLOCATED', 'Allocated to Cost Layers'),
        ('REVERSED', 'Reversed'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # References
    voucher = models.ForeignKey(
        LandedCostVoucher,
        on_delete=models.PROTECT,
        related_name='allocations'
    )
    goods_receipt = models.ForeignKey(
        'GoodsReceipt',
        on_delete=models.PROTECT,
        related_name='landed_cost_allocations'
    )
    goods_receipt_line = models.ForeignKey(
        'GoodsReceiptLine',
        on_delete=models.PROTECT,
        related_name='landed_cost_allocations'
    )
    cost_layer = models.ForeignKey(
        'CostLayer',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='landed_cost_allocations'
    )

    # Allocation details
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='landed_cost_voucher_lines', help_text="Item for landed cost voucher line")
    warehouse = models.ForeignKey('Warehouse', on_delete=models.PROTECT)

    allocated_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Amount allocated to this line"
    )
    allocation_basis = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        help_text="Basis value used for allocation (qty, value, weight, etc.)"
    )
    allocation_percentage = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        help_text="Percentage of total cost allocated"
    )

    # Cost impact
    original_cost_per_unit = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text="Cost per unit before allocation"
    )
    cost_per_unit_adjustment = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text="Per-unit cost increase from this allocation"
    )
    new_cost_per_unit = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text="Cost per unit after allocation"
    )

    # Split between inventory and COGS
    to_inventory = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text="Amount allocated to remaining inventory"
    )
    to_cogs = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text="Amount allocated to consumed goods (COGS)"
    )

    # Status
    status = models.CharField(max_length=20, choices=ALLOCATION_STATUS_CHOICES, default='PENDING')
    allocated_date = models.DateTimeField(null=True, blank=True)
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='landed_cost_allocations'
    )

    # Reversal tracking
    reversed_date = models.DateTimeField(null=True, blank=True)
    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reversed_landed_cost_allocations'
    )
    reversal_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['voucher', 'goods_receipt', 'goods_receipt_line']
        indexes = [
            models.Index(fields=['company', 'voucher']),
            models.Index(fields=['goods_receipt', 'status']),
            models.Index(fields=['cost_layer']),
        ]
        verbose_name = 'Landed Cost Allocation'
        verbose_name_plural = 'Landed Cost Allocations'

    def __str__(self):
        return f"Allocation: LCV#{self.voucher.voucher_number} → GRN#{self.goods_receipt.grn_number} (${self.allocated_amount})"


class ReturnToVendor(models.Model):
    """
    Return To Vendor (RTV) model for handling supplier returns.
    Creates negative movement events and reverses budget usage.
    """
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted for Approval'),
        ('APPROVED', 'Approved'),
        ('IN_TRANSIT', 'In Transit to Vendor'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    REASON_CHOICES = [
        ('DEFECTIVE', 'Defective/Damaged Goods'),
        ('WRONG_ITEM', 'Wrong Item Received'),
        ('EXCESS_QUANTITY', 'Excess Quantity'),
        ('QUALITY_ISSUE', 'Quality Issue'),
        ('EXPIRED', 'Expired/Near Expiry'),
        ('NOT_ORDERED', 'Not Ordered'),
        ('OTHER', 'Other'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # RTV identification
    rtv_number = models.CharField(max_length=50, unique=True, db_index=True)
    rtv_date = models.DateField()

    # Original GRN reference
    goods_receipt = models.ForeignKey(
        'GoodsReceipt',
        on_delete=models.PROTECT,
        related_name='vendor_returns'
    )

    # Supplier information
    supplier_id = models.IntegerField(help_text="Supplier to return to")
    warehouse = models.ForeignKey('Warehouse', on_delete=models.PROTECT)

    # Return details
    return_reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    return_reason_detail = models.TextField(help_text="Detailed explanation")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    # Financial impact
    total_return_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text="Total value being returned"
    )
    refund_expected = models.BooleanField(default=True)
    refund_received = models.BooleanField(default=False)
    refund_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True
    )
    refund_date = models.DateField(null=True, blank=True)

    # Workflow
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_vendor_returns'
    )
    requested_date = models.DateTimeField(auto_now_add=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_vendor_returns'
    )
    approval_date = models.DateTimeField(null=True, blank=True)

    shipped_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)

    # GL Integration
    je_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Journal Entry ID for return posting"
    )
    posted_to_gl = models.BooleanField(default=False)
    gl_posted_date = models.DateTimeField(null=True, blank=True)

    # Documents
    debit_note_number = models.CharField(max_length=100, blank=True)
    debit_note_date = models.DateField(null=True, blank=True)

    # Additional info
    notes = models.TextField(blank=True)
    attachments = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-rtv_date', '-created_at']
        indexes = [
            models.Index(fields=['company', 'rtv_number']),
            models.Index(fields=['goods_receipt', 'status']),
            models.Index(fields=['status', '-rtv_date']),
            models.Index(fields=['posted_to_gl', '-rtv_date']),
        ]
        verbose_name = 'Return To Vendor'
        verbose_name_plural = 'Returns To Vendor'

    def __str__(self):
        return f"RTV#{self.rtv_number} - {self.get_return_reason_display()}"

    def can_edit(self):
        """Check if RTV can be edited"""
        return self.status in ['DRAFT', 'SUBMITTED']

    def can_submit(self):
        """Check if RTV can be submitted"""
        return self.status == 'DRAFT' and self.total_return_value > 0

    def can_approve(self):
        """Check if RTV can be approved"""
        return self.status == 'SUBMITTED'

    def can_ship(self):
        """Check if RTV can be marked as shipped"""
        return self.status == 'APPROVED'

    def can_complete(self):
        """Check if RTV can be completed"""
        return self.status in ['APPROVED', 'IN_TRANSIT']

    @property
    def refund_status(self):
        """Get refund status"""
        if self.refund_received:
            return 'RECEIVED'
        elif self.refund_expected:
            return 'PENDING'
        else:
            return 'NOT_APPLICABLE'


class ReturnToVendorLine(models.Model):
    """
    Individual line items for Return To Vendor.
    """
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # References
    rtv = models.ForeignKey(
        ReturnToVendor,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    goods_receipt_line = models.ForeignKey(
        'GoodsReceiptLine',
        on_delete=models.PROTECT,
        related_name='vendor_return_lines'
    )
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='rtv_lines', help_text="Item being returned to vendor")

    # Description
    description = models.TextField(blank=True, help_text="Description of items being returned")

    # Return quantities
    quantity_to_return = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text="Quantity being returned (in stock UoM)"
    )
    uom = models.ForeignKey('UnitOfMeasure', on_delete=models.PROTECT, null=True, blank=True)
    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text="Original unit cost from GRN"
    )
    line_total = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Total value of this line"
    )

    # Return reason and notes
    reason = models.CharField(max_length=200, blank=True, null=True, help_text="Specific reason for this line")
    quality_notes = models.TextField(blank=True, null=True, help_text="Quality inspection notes")

    # Batch/Serial tracking
    batch_lot_id = models.IntegerField(null=True, blank=True)
    serial_numbers = models.JSONField(default=list, blank=True)

    # Budget reversal
    budget_item = models.ForeignKey(
        'budgeting.BudgetLine',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rtv_reversals'
    )
    budget_reversed = models.BooleanField(default=False)
    budget_reversal_date = models.DateTimeField(null=True, blank=True)

    # Movement event reference
    movement_event = models.ForeignKey(
        'MovementEvent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Negative movement event created for this return",
        related_name='rtv_lines'
    )

    # Additional info
    line_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['rtv', 'id']
        indexes = [
            models.Index(fields=['company', 'rtv']),
            models.Index(fields=['budget_item']),
            models.Index(fields=['goods_receipt_line']),
        ]
        verbose_name = 'Return To Vendor Line'
        verbose_name_plural = 'Return To Vendor Lines'

    def __str__(self):
        return f"RTV Line: {self.budget_item.code} x {self.quantity_to_return}"

    def save(self, *args, **kwargs):
        # Calculate line total
        self.line_total = self.quantity_to_return * self.unit_cost
        super().save(*args, **kwargs)


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
    budget_item = models.OneToOneField(
        'budgeting.BudgetItemCode',
        on_delete=models.PROTECT,
        related_name='inventory_extension',
        help_text="Budget master item reference"
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Identification
    code = models.CharField(max_length=50, db_index=True, blank=True)
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

    def clean(self):
        super().clean()
        if self.budget_item_id:
            self._validate_budget_scope(self.budget_item)

    def _validate_budget_scope(self, budget):
        if not budget:
            return
        if self.company_id and budget.company_id and self.company_id != budget.company_id:
            raise ValidationError({'budget_item': 'Selected budget item belongs to a different company.'})
        if self.company_id and not budget.company_id:
            company = getattr(self, 'company', None)
            company_group_id = getattr(company, 'company_group_id', None) if company else None
            budget_group_id = getattr(budget, 'company_group_id', None)
            if company_group_id and budget_group_id and company_group_id != budget_group_id:
                raise ValidationError({'budget_item': 'Selected budget item belongs to a different company group.'})

    def _sync_budget_master_fields(self):
        if not self.budget_item_id:
            return
        budget = getattr(self, 'budget_item', None)
        if not budget:
            return
        self._validate_budget_scope(budget)
        if not self.company_id and budget.company_id:
            self.company_id = budget.company_id
        if budget.code and self.code != budget.code:
            self.code = budget.code
        if budget.name and self.name != budget.name:
            self.name = budget.name
        if budget.uom_id and self.uom_id != budget.uom_id:
            self.uom_id = budget.uom_id
        if budget.standard_price and (self.standard_cost is None or self.standard_cost == 0):
            self.standard_cost = budget.standard_price

    def save(self, *args, **kwargs):
        # Auto-generate code if not set
        if not self.code:
            last_item = Item.objects.filter(
                company=self.company
            ).order_by('-id').first()

            if last_item and last_item.code:
                try:
                    last_num = int(last_item.code.split('-')[-1])
                    next_num = last_num + 1
                except (ValueError, IndexError):
                    next_num = 1
            else:
                next_num = 1

            self.code = f"ITEM-{next_num:03d}"

        self._sync_budget_master_fields()
        super().save(*args, **kwargs)

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

    def get_operational_profile(self):
        """Return the operational extension, creating one on-demand if missing."""
        from django.utils import timezone as _tz
        try:
            return self.operational_profile
        except ItemOperationalExtension.DoesNotExist:
            return ItemOperationalExtension.objects.create(
                company=self.company,
                item=self,
                stock_uom=self.uom,
                created_at=_tz.now(),
            )

    def get_default_config(self, warehouse=None):
        """Fetch the warehouse config matching the provided warehouse or the global fallback."""
        qs = self.warehouse_configs.all()
        if warehouse:
            cfg = qs.filter(warehouse=warehouse).order_by('-updated_at').first()
            if cfg:
                return cfg
        return qs.filter(warehouse__isnull=True).order_by('-updated_at').first()

    def get_fefo_config(self, warehouse=None):
        """Return FEFO configuration for a warehouse or global default."""
        qs = self.fefo_configs.all()
        if warehouse:
            cfg = qs.filter(warehouse=warehouse).order_by('-updated_at').first()
            if cfg:
                return cfg
        return qs.filter(warehouse__isnull=True).order_by('-updated_at').first()


class ItemCategory(models.Model):
    """
    Hierarchical item categories with unlimited depth
    Supports: Category → Sub-Category → Sub-Sub-Category → ...
    """
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    code = models.CharField(max_length=50, blank=True)
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
        # Auto-generate code if not set
        if not self.code:
            last_cat = ItemCategory.objects.filter(
                company=self.company
            ).order_by('-id').first()

            if last_cat and last_cat.code:
                try:
                    last_num = int(last_cat.code.split('-')[-1])
                    next_num = last_num + 1
                except (ValueError, IndexError):
                    next_num = 1
            else:
                next_num = 1

            self.code = f"ICAT-{next_num:03d}"

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


class ItemOperationalExtension(models.Model):
    """Operational attributes that live in Inventory (separate from Budget-controlled master data)."""

    SIGNAL_WORD_CHOICES = [
        ('DANGER', 'Danger'),
        ('WARNING', 'Warning'),
        ('CAUTION', 'Caution'),
    ]

    STORAGE_CLASS_CHOICES = [
        ('DRY', 'Dry'),
        ('FROZEN', 'Frozen'),
        ('CLIMATE', 'Climate Controlled'),
        ('HAZMAT', 'Hazardous Material'),
        ('OUTDOOR', 'Outdoor'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='item_operational_profiles')
    budget_item = models.OneToOneField(
        'budgeting.BudgetItemCode',
        on_delete=models.PROTECT,
        related_name='operational_extension',
        help_text='Budget master item reference'
    )
    barcode = models.CharField(max_length=64, blank=True)
    qr_code = models.CharField(max_length=64, blank=True)
    hazmat_class = models.CharField(max_length=30, blank=True)
    hazmat_signal_word = models.CharField(max_length=20, choices=SIGNAL_WORD_CHOICES, blank=True)
    storage_class = models.CharField(max_length=20, choices=STORAGE_CLASS_CHOICES, blank=True)
    handling_instructions = models.TextField(blank=True)
    requires_batch_tracking = models.BooleanField(default=False)
    requires_serial_tracking = models.BooleanField(default=False)
    requires_expiry_tracking = models.BooleanField(default=False)
    expiry_warning_days = models.PositiveIntegerField(default=0)
    allow_negative_inventory = models.BooleanField(default=False)
    purchase_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, null=True, blank=True, related_name='purchase_items')
    stock_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='stock_items')
    sales_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, null=True, blank=True, related_name='sales_items')
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_item_operational_extension'
        indexes = [
            models.Index(fields=['company', 'hazmat_class']),
            models.Index(fields=['company', 'storage_class']),
            models.Index(fields=['requires_batch_tracking', 'requires_serial_tracking']),
        ]
        verbose_name = 'Item Operational Extension'

    def __str__(self):
        code = getattr(self.budget_item, 'code', 'UNLINKED') if self.budget_item_id else 'UNLINKED'
        return f"{code} operational profile"

    def save(self, *args, **kwargs):
        if not self.company_id and getattr(self.budget_item, 'company_id', None):
            self.company_id = self.budget_item.company_id
        base_uom = None
        if getattr(self.budget_item, 'uom_id', None):
            base_uom = self.budget_item.uom
        if not self.stock_uom_id and base_uom:
            self.stock_uom = base_uom
        if not self.purchase_uom_id and self.stock_uom_id:
            self.purchase_uom = self.stock_uom
        super().save(*args, **kwargs)


class ItemWarehouseConfig(models.Model):
    """Warehouse (or global) level operational configuration per item."""

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='item_warehouse_configs')
    item = models.ForeignKey(
        'Item',
        on_delete=models.CASCADE,
        related_name='warehouse_configs',
        null=True,
        blank=True,
        help_text='Deprecated linkage; use budget_item instead'
    )
    budget_item = models.ForeignKey(
        'budgeting.BudgetItemCode',
        on_delete=models.PROTECT,
        related_name='warehouse_configs',
        help_text='Budget master item reference'
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True, related_name='item_configs')
    default_bin = models.ForeignKey(WarehouseBin, on_delete=models.SET_NULL, null=True, blank=True, related_name='default_for_items')
    pack_size_qty = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal('0.000'))
    pack_size_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, null=True, blank=True, related_name='pack_size_items')
    min_stock_level = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal('0.000'))
    max_stock_level = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal('0.000'))
    reorder_point = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal('0.000'))
    economic_order_qty = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal('0.000'), help_text="EOQ (economic order quantity)")
    avg_daily_demand = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal('0.000'), help_text="Average daily demand")
    lead_time_days = models.IntegerField(default=0)
    lead_time_std_dev = models.IntegerField(default=0)
    demand_std_dev = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal('0.000'))
    service_level_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('95.00'))
    allow_negative_inventory = models.BooleanField(default=False)
    allow_backorder_generation = models.BooleanField(default=False)
    auto_replenish = models.BooleanField(default=False, help_text="Enable automated replenishment logic")
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_item_warehouse_config'
        unique_together = ('budget_item', 'warehouse', 'is_active')
        indexes = [
            models.Index(fields=['company', 'warehouse', 'is_active']),
            models.Index(fields=['company', 'budget_item', 'reorder_point']),
        ]
        verbose_name = 'Item Warehouse Configuration'

    def __str__(self):
        wh = self.warehouse.code if self.warehouse else 'GLOBAL'
        code = getattr(self.budget_item, 'code', None) or getattr(self.item, 'code', 'UNLINKED')
        return f"{code} @ {wh}"

    def save(self, *args, **kwargs):
        if not self.item_id and self.budget_item_id:
            try:
                self.item = Item.objects.get(budget_item_id=self.budget_item_id)
            except Item.DoesNotExist:
                self.item = None
        if not self.budget_item_id and getattr(self.item, 'budget_item_id', None):
            self.budget_item_id = self.item.budget_item_id
        if not self.company_id:
            if self.item_id:
                self.company = self.item.company
            elif getattr(self.budget_item, 'company_id', None):
                self.company_id = self.budget_item.company_id
        base_uom = None
        if self.item_id:
            base_uom = self.item.uom
        if not base_uom and getattr(self.budget_item, 'uom_id', None):
            base_uom = self.budget_item.uom
        if not self.pack_size_uom_id and base_uom:
            self.pack_size_uom = base_uom
        super().save(*args, **kwargs)


class ItemUOMConversion(models.Model):
    """Conversion configuration between purchase/stock/sales units per item."""

    ROUNDING_RULE_CHOICES = [
        ('ROUND_UP', 'Round Up'),
        ('ROUND_DOWN', 'Round Down'),
        ('ROUND_NEAREST', 'Round Nearest'),
        ('TRUNCATE', 'Truncate'),
        ('NO_ROUNDING', 'No Rounding'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='item_uom_conversions')
    item = models.ForeignKey(
        'Item',
        on_delete=models.CASCADE,
        related_name='uom_conversions',
        null=True,
        blank=True,
        help_text='Deprecated linkage; use budget_item instead'
    )
    budget_item = models.ForeignKey(
        'budgeting.BudgetItemCode',
        on_delete=models.PROTECT,
        related_name='uom_conversions',
        help_text='Budget master item reference'
    )
    from_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='conversion_from_uom')
    to_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='conversion_to_uom')
    conversion_factor = models.DecimalField(max_digits=20, decimal_places=6, help_text="Quantity of to_uom in one from_uom")
    rounding_rule = models.CharField(max_length=20, choices=ROUNDING_RULE_CHOICES, default='NO_ROUNDING')
    is_purchase_conversion = models.BooleanField(default=False)
    is_sales_conversion = models.BooleanField(default=False)
    is_stock_conversion = models.BooleanField(default=False)
    effective_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    precedence = models.IntegerField(default=100)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_item_uom_conversion'
        indexes = [
            models.Index(fields=['company', 'budget_item', 'effective_date']),
            models.Index(fields=['company', 'budget_item', 'from_uom', 'to_uom']),
        ]
        unique_together = ('budget_item', 'from_uom', 'to_uom', 'effective_date', 'precedence')

    def __str__(self):
        code = getattr(self.budget_item, 'code', None) or getattr(self.item, 'code', 'UNLINKED')
        return f"{code}: {self.from_uom.code} -> {self.to_uom.code}"

    def save(self, *args, **kwargs):
        if not self.item_id and self.budget_item_id:
            try:
                self.item = Item.objects.get(budget_item_id=self.budget_item_id)
            except Item.DoesNotExist:
                self.item = None
        if not self.budget_item_id and getattr(self.item, 'budget_item_id', None):
            self.budget_item_id = self.item.budget_item_id
        if not self.company_id:
            if self.item_id:
                self.company = self.item.company
            elif getattr(self.budget_item, 'company_id', None):
                self.company_id = self.budget_item.company_id
        if not self.end_date:
            self.end_date = None
        super().save(*args, **kwargs)


class MovementEvent(models.Model):
    """Immutable event-sourced ledger for every quantity movement."""

    EVENT_TYPES = [
        ('RECEIPT', 'Receipt'),
        ('ISSUE', 'Issue'),
        ('TRANSFER_OUT', 'Transfer Out'),
        ('TRANSFER_IN', 'Transfer In'),
        ('ADJUSTMENT', 'Adjustment'),
        ('SCRAP', 'Scrap / Loss'),
        ('CYCLE_COUNT', 'Cycle Count Adjustment'),
        ('REVERSAL', 'Reversal'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='inventory_events')
    movement = models.ForeignKey('StockMovement', on_delete=models.CASCADE, null=True, blank=True, related_name='movement_events')
    movement_line = models.ForeignKey('StockMovementLine', on_delete=models.CASCADE, null=True, blank=True, related_name='movement_events')
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='movement_events', help_text="Item for movement event")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='movement_events')
    bin = models.ForeignKey(WarehouseBin, on_delete=models.SET_NULL, null=True, blank=True, related_name='movement_events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    qty_change = models.DecimalField(max_digits=18, decimal_places=6, help_text="Positive for receipts, negative for issues")
    stock_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='movement_events')
    source_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, null=True, blank=True, related_name='movement_events_source')
    source_quantity = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    event_date = models.DateField()
    event_timestamp = models.DateTimeField(auto_now_add=True)
    reference_document_type = models.CharField(max_length=50, blank=True)
    reference_document_id = models.IntegerField(null=True, blank=True)
    reference_number = models.CharField(max_length=50, blank=True)
    cost_per_unit_at_event = models.DecimalField(max_digits=20, decimal_places=4, default=Decimal('0.0000'))
    valuation_method_used = models.CharField(max_length=20, blank=True)
    event_metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    immutable_after_posting = models.BooleanField(default=True, help_text="If true, record cannot be edited once persisted")

    class Meta:
        db_table = 'inventory_movement_event'
        ordering = ['-event_timestamp']
        indexes = [
            models.Index(fields=['company', 'budget_item', 'warehouse']),
            models.Index(fields=['event_date']),
            models.Index(fields=['reference_document_type', 'reference_document_id']),
        ]

    def __str__(self):
        return f"{self.event_type} {self.budget_item.code} {self.qty_change}"

    def save(self, *args, **kwargs):
        if self.pk and self.immutable_after_posting:
            raise ValueError("Movement events are immutable and cannot be updated once saved.")
        if not self.company_id:
            self.company = self.item.company
        if not self.stock_uom_id:
            self.stock_uom = self.item.uom
        if not self.event_date:
            self.event_date = timezone.now().date()
        super().save(*args, **kwargs)


class ItemSupplier(models.Model):
    """Per-item supplier configuration (MOQ, multiples, lead time, pack size)."""

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='item_suppliers')
    item = models.ForeignKey(
        'Item',
        on_delete=models.CASCADE,
        related_name='supplier_links',
        null=True,
        blank=True,
        help_text='Deprecated linkage; use budget_item instead'
    )
    budget_item = models.ForeignKey(
        'budgeting.BudgetItemCode',
        on_delete=models.PROTECT,
        related_name='supplier_links',
        help_text='Budget master item reference'
    )
    supplier = models.ForeignKey('procurement.Supplier', on_delete=models.PROTECT, related_name='item_links')
    supplier_item_code = models.CharField(max_length=100, blank=True)
    supplier_pack_size = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal('0.000'))
    supplier_pack_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, null=True, blank=True, related_name='supplier_pack_items')
    moq_qty = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal('0.000'), help_text="Minimum order quantity")
    multiple_qty = models.DecimalField(max_digits=15, decimal_places=3, default=Decimal('0.000'), help_text="Order multiples")
    lead_time_days = models.IntegerField(default=0)
    lead_time_variability = models.IntegerField(default=0, help_text="Std dev of lead time in days")
    preferred_rank = models.IntegerField(default=1, help_text="1 = preferred supplier")
    last_purchase_price = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    last_purchase_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_item_supplier'
        unique_together = ('budget_item', 'supplier')
        indexes = [
            models.Index(fields=['company', 'budget_item']),
            models.Index(fields=['company', 'supplier']),
            models.Index(fields=['item', 'preferred_rank']),
        ]
        ordering = ['preferred_rank', 'supplier_id']

    def __str__(self):
        code = getattr(self.budget_item, 'code', None) or getattr(self.item, 'code', 'UNLINKED')
        return f"{code} ↔ {self.supplier.name}"

    def save(self, *args, **kwargs):
        if not self.item_id and self.budget_item_id:
            try:
                self.item = Item.objects.get(budget_item_id=self.budget_item_id)
            except Item.DoesNotExist:
                self.item = None
        if not self.budget_item_id and getattr(self.item, 'budget_item_id', None):
            self.budget_item_id = self.item.budget_item_id
        if not self.company_id:
            if self.item_id:
                self.company = self.item.company
            elif getattr(self.budget_item, 'company_id', None):
                self.company_id = self.budget_item.company_id
        if not self.supplier_pack_uom_id:
            base_uom = None
            if self.item_id:
                base_uom = self.item.uom
            if not base_uom and getattr(self.budget_item, 'uom_id', None):
                base_uom = self.budget_item.uom
            if base_uom:
                self.supplier_pack_uom = base_uom
        super().save(*args, **kwargs)


class ItemFEFOConfig(models.Model):
    """FEFO enforcement configuration per item/warehouse."""

    EXPIRY_RULE_CHOICES = [
        ('FIXED_DATE', 'Fixed Date'),
        ('DAYS_FROM_MFG', 'Days from Manufacture'),
        ('DAYS_FROM_RECEIPT', 'Days from Receipt'),
        ('CUSTOM', 'Custom Formula'),
    ]
    DISPOSAL_CHOICES = [
        ('SCRAP', 'Scrap'),
        ('DONATE', 'Donate'),
        ('RETURN_TO_SUPPLIER', 'Return to Supplier'),
        ('REWORK', 'Rework'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='item_fefo_configs')
    item = models.ForeignKey(
        'Item',
        on_delete=models.CASCADE,
        related_name='fefo_configs',
        null=True,
        blank=True,
        help_text='Deprecated linkage; use budget_item instead'
    )
    budget_item = models.ForeignKey(
        'budgeting.BudgetItemCode',
        on_delete=models.PROTECT,
        related_name='fefo_configs',
        help_text='Budget master item reference'
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True, related_name='fefo_configs')
    enforce_fefo = models.BooleanField(default=False)
    warn_days_before_expiry = models.PositiveIntegerField(default=0)
    block_issue_if_expired = models.BooleanField(default=True)
    disposal_method = models.CharField(max_length=30, choices=DISPOSAL_CHOICES, default='SCRAP')
    expiry_calculation_rule = models.CharField(max_length=30, choices=EXPIRY_RULE_CHOICES, default='FIXED_DATE')
    shelf_life_days = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_item_fefo_config'
        unique_together = ('budget_item', 'warehouse')
        indexes = [
            models.Index(fields=['company', 'budget_item']),
            models.Index(fields=['company', 'warehouse']),
        ]

    def __str__(self):
        target = self.warehouse.code if self.warehouse else 'GLOBAL'
        code = getattr(self.budget_item, 'code', None) or getattr(self.item, 'code', 'UNLINKED')
        return f"{code} FEFO @ {target}"

    def save(self, *args, **kwargs):
        if not self.item_id and self.budget_item_id:
            try:
                self.item = Item.objects.get(budget_item_id=self.budget_item_id)
            except Item.DoesNotExist:
                self.item = None
        if not self.budget_item_id and getattr(self.item, 'budget_item_id', None):
            self.budget_item_id = self.item.budget_item_id
        if not self.company_id:
            if self.item_id:
                self.company = self.item.company
            elif getattr(self.budget_item, 'company_id', None):
                self.company_id = self.budget_item.company_id
        super().save(*args, **kwargs)


# ============================================================================
# PHASE 3: QUALITY CONTROL & COMPLIANCE MODELS
# ============================================================================

class StockHold(models.Model):
    """Stock hold for QC inspection, pending approval, or other reasons"""
    HOLD_TYPE_CHOICES = [
        ('QC_INSPECTION', 'QC Inspection'),
        ('DOCUMENT_HOLD', 'Document Hold'),
        ('APPROVAL_PENDING', 'Approval Pending'),
        ('CUSTOMER_RETURN', 'Customer Return'),
        ('DEFECT', 'Defect'),
        ('OTHER', 'Other'),
    ]

    QC_RESULT_CHOICES = [
        ('PASS', 'Pass'),
        ('FAIL', 'Fail'),
        ('PENDING', 'Pending'),
        ('CONDITIONAL', 'Conditional'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('RELEASED', 'Released'),
        ('SCRAPPED', 'Scrapped'),
        ('RETURNED', 'Returned'),
    ]

    DISPOSITION_CHOICES = [
        ('TO_WAREHOUSE', 'Move to Warehouse'),
        ('SCRAP', 'Scrap'),
        ('RETURN', 'Return to Supplier'),
        ('REWORK', 'Rework'),
        ('REJECT', 'Reject'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='stock_holds')
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='stock_holds', help_text="Master item record")
    warehouse = models.ForeignKey('Warehouse', on_delete=models.PROTECT, related_name='stock_holds')
    bin = models.ForeignKey('WarehouseBin', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_holds')
    batch_lot = models.ForeignKey('BatchLot', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_holds')

    hold_type = models.CharField(max_length=30, choices=HOLD_TYPE_CHOICES)
    qty_held = models.DecimalField(max_digits=15, decimal_places=3, help_text="Quantity held in stock UoM")
    hold_reason = models.TextField(help_text="Detailed reason for hold")
    hold_date = models.DateField(default=timezone.now)
    hold_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='holds_created')

    expected_release_date = models.DateField(null=True, blank=True)
    actual_release_date = models.DateField(null=True, blank=True)
    released_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='holds_released')

    qc_pass_result = models.CharField(max_length=20, choices=QC_RESULT_CHOICES, default='PENDING')
    qc_notes = models.TextField(blank=True)
    escalation_flag = models.BooleanField(default=False, help_text="Set if hold is overdue")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    disposition = models.CharField(max_length=30, choices=DISPOSITION_CHOICES, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_stock_hold'
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['warehouse', 'status']),
            models.Index(fields=['hold_date']),
        ]

    def __str__(self):
        item_ref = self.budget_item.code if self.budget_item_id else 'UNLINKED'
        return f"Hold {self.id}: {item_ref} - {self.qty_held} units ({self.status})"


class QCCheckpoint(models.Model):
    """Quality control checkpoint configuration for warehouses"""
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='qc_checkpoints')
    warehouse = models.ForeignKey('Warehouse', on_delete=models.CASCADE, related_name='qc_checkpoints')
    checkpoint_name = models.CharField(max_length=200, help_text="e.g., Receiving Dock Inspection")
    checkpoint_order = models.PositiveIntegerField(default=1, help_text="Sequence order")
    automatic_after = models.BooleanField(default=False, help_text="Auto-run without user intervention")
    inspection_criteria = models.TextField(help_text="What to check during inspection")
    inspection_template = models.CharField(max_length=200, blank=True, help_text="SOP document ID or URL")
    acceptance_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=95.0, help_text="AQL level (percentage)")
    escalation_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=5.0, help_text="Reject % to escalate")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='qc_checkpoints_assigned')
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_qc_checkpoint'
        unique_together = ('warehouse', 'checkpoint_name')
        ordering = ['checkpoint_order']
        indexes = [
            models.Index(fields=['company', 'warehouse']),
        ]

    def __str__(self):
        return f"{self.checkpoint_name} (#{self.checkpoint_order}) @ {self.warehouse.code}"


class QCResult(models.Model):
    """Quality control inspection result"""
    REJECTION_REASON_CHOICES = [
        ('DAMAGE', 'Damage'),
        ('INCOMPLETE_DOC', 'Incomplete Documentation'),
        ('WRONG_ITEM', 'Wrong Item'),
        ('QUANTITY_DISCREPANCY', 'Quantity Discrepancy'),
        ('QUALITY_ISSUE', 'Quality Issue'),
        ('EXPIRY_ISSUE', 'Expiry/Date Issue'),
        ('OTHER', 'Other'),
    ]

    QC_STATUS_CHOICES = [
        ('PASS', 'Pass'),
        ('FAIL', 'Fail'),
        ('CONDITIONAL_PASS', 'Conditional Pass'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='qc_results')
    grn = models.ForeignKey('GoodsReceipt', on_delete=models.CASCADE, related_name='qc_results')
    checkpoint = models.ForeignKey('QCCheckpoint', on_delete=models.PROTECT, related_name='qc_results')

    inspected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='qc_inspections')
    inspected_date = models.DateField(default=timezone.now)

    qty_inspected = models.DecimalField(max_digits=15, decimal_places=3)
    qty_accepted = models.DecimalField(max_digits=15, decimal_places=3)
    qty_rejected = models.DecimalField(max_digits=15, decimal_places=3)

    rejection_reason = models.CharField(max_length=30, choices=REJECTION_REASON_CHOICES, null=True, blank=True)
    qc_status = models.CharField(max_length=20, choices=QC_STATUS_CHOICES)
    notes = models.TextField(blank=True)
    rework_instruction = models.TextField(blank=True, help_text="Instructions if conditional pass")

    # Attachment for COA, photos, etc.
    attachment = models.FileField(upload_to='qc_attachments/', null=True, blank=True)
    hold_created = models.BooleanField(default=False, help_text="Whether this result created a stock hold")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_qc_result'
        indexes = [
            models.Index(fields=['company', 'inspected_date']),
            models.Index(fields=['grn']),
            models.Index(fields=['qc_status']),
        ]

    def __str__(self):
        return f"QC {self.id}: GRN#{self.grn_id} - {self.qc_status}"


class BatchLot(models.Model):
    """Batch/Lot tracking for items with expiry dates or supplier lots"""
    HOLD_STATUS_CHOICES = [
        ('QUARANTINE', 'Quarantine'),
        ('ON_HOLD', 'On Hold'),
        ('RELEASED', 'Released'),
        ('SCRAP', 'Scrap'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='batch_lots')
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='batch_lots', help_text="Master item record")

    supplier_lot_number = models.CharField(max_length=100, blank=True, help_text="Supplier's batch/lot ID")
    internal_batch_code = models.CharField(max_length=100, unique=True, help_text="Auto-generated or manual internal code")

    grn = models.ForeignKey('GoodsReceipt', on_delete=models.SET_NULL, null=True, blank=True, related_name='batch_lots')

    mfg_date = models.DateField(null=True, blank=True, help_text="Manufacture date")
    exp_date = models.DateField(null=True, blank=True, help_text="Expiration/use-by date")
    received_date = models.DateField(default=timezone.now)

    received_qty = models.DecimalField(max_digits=15, decimal_places=3, help_text="Original received quantity in stock UoM")
    current_qty = models.DecimalField(max_digits=15, decimal_places=3, help_text="Remaining quantity after issuances")

    cost_per_unit = models.DecimalField(max_digits=20, decimal_places=2, default=0, help_text="Cost of this batch")

    # Certificate of Analysis
    certificate_of_analysis = models.FileField(upload_to='coa/', null=True, blank=True)
    coa_upload_date = models.DateField(null=True, blank=True)

    storage_location = models.CharField(max_length=200, blank=True)
    hazmat_classification = models.CharField(max_length=50, blank=True)

    hold_status = models.CharField(max_length=20, choices=HOLD_STATUS_CHOICES, default='QUARANTINE')
    fefo_sequence = models.IntegerField(default=0, help_text="For FEFO sorting (lower = pick first)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_batch_lot'
        indexes = [
            models.Index(fields=['company', 'hold_status']),
            models.Index(fields=['budget_item', 'exp_date']),
            models.Index(fields=['internal_batch_code']),
            models.Index(fields=['fefo_sequence']),
        ]

    def __str__(self):
        item_ref = self.budget_item.code if self.budget_item_id else 'UNLINKED'
        return f"Batch {self.internal_batch_code}: {item_ref} - {self.current_qty} units"

    def is_expired(self):
        """Check if batch is expired"""
        if not self.exp_date:
            return False
        return self.exp_date < timezone.now().date()

    def days_until_expiry(self):
        """Days until expiry (negative if expired)"""
        if not self.exp_date:
            return None
        return (self.exp_date - timezone.now().date()).days


class SerialNumber(models.Model):
    """Serial number tracking for individual items"""
    STATUS_CHOICES = [
        ('IN_STOCK', 'In Stock'),
        ('ASSIGNED', 'Assigned to Order'),
        ('ISSUED', 'Issued'),
        ('RETURNED', 'Returned'),
        ('SCRAPPED', 'Scrapped'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='serial_numbers')
    budget_item = models.ForeignKey('budgeting.BudgetItemCode', on_delete=models.PROTECT, null=True, blank=True, related_name='serial_numbers', help_text="Master item record")

    serial_number = models.CharField(max_length=200, help_text="Unique serial number per item")
    batch_lot = models.ForeignKey('BatchLot', on_delete=models.SET_NULL, null=True, blank=True, related_name='serial_numbers')

    warranty_start = models.DateField(null=True, blank=True)
    warranty_end = models.DateField(null=True, blank=True)
    asset_tag = models.CharField(max_length=100, blank=True, help_text="Fixed asset tag if applicable")

    # Assignment tracking
    assigned_to_customer_order = models.ForeignKey('sales.SalesOrder', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_serials')
    issued_date = models.DateField(null=True, blank=True)
    issued_to = models.CharField(max_length=200, blank=True, help_text="Customer/Department")

    received_back_date = models.DateField(null=True, blank=True)
    inspection_date = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_STOCK')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_serial_number'
        unique_together = ('budget_item', 'serial_number')
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['serial_number']),
        ]

    def __str__(self):
        item_ref = self.budget_item.code if self.budget_item_id else 'UNLINKED'
        return f"{item_ref} - SN: {self.serial_number}"


# ============================================================================
# MATERIAL ISSUE MANAGEMENT
# ============================================================================

class MaterialIssue(models.Model):
    """
    Material Issue/Dispatch from warehouse to departments, production, or sales.
    """
    ISSUE_TYPE_CHOICES = [
        ('PRODUCTION', 'Issue to Production'),
        ('DEPARTMENT', 'Issue to Department'),
        ('SALES_ORDER', 'Issue to Sales Order'),
        ('PROJECT', 'Issue to Project'),
        ('COST_CENTER', 'Issue to Cost Center'),
        ('SAMPLE', 'Sample Issue'),
        ('OTHER', 'Other'),
    ]

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('ISSUED', 'Issued'),
        ('PARTIALLY_RETURNED', 'Partially Returned'),
        ('CLOSED', 'Closed'),
        ('CANCELLED', 'Cancelled'),
    ]

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    issue_number = models.CharField(max_length=50, unique=True)
    issue_type = models.CharField(max_length=30, choices=ISSUE_TYPE_CHOICES, default='DEPARTMENT')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='DRAFT')

    # Source
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='material_issues')

    # Destination
    cost_center = models.ForeignKey(
        'budgeting.CostCenter',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='material_issues'
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='material_issues'
    )
    department = models.CharField(max_length=200, blank=True, help_text="Department name if not linked to cost center")

    # Requisition reference
    requisition = models.ForeignKey(
        InternalRequisition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='material_issues'
    )

    # Issue details
    issue_date = models.DateField()
    requested_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='material_issues_requested'
    )
    issued_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='material_issues_issued',
        help_text="Store keeper who issued the materials"
    )
    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='material_issues_approved'
    )

    # Purpose and notes
    purpose = models.TextField(help_text="Purpose/reason for material issue")
    notes = models.TextField(blank=True)

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Stock movement reference (created when issued)
    stock_movement = models.ForeignKey(
        StockMovement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='material_issue_ref'
    )

    class Meta:
        db_table = 'inventory_material_issue'
        ordering = ['-issue_date', '-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['warehouse', 'issue_date']),
            models.Index(fields=['cost_center', 'issue_date']),
            models.Index(fields=['issue_number']),
        ]

    def __str__(self):
        return f"{self.issue_number} - {self.get_issue_type_display()}"

    def save(self, *args, **kwargs):
        if not self.issue_number:
            # Generate issue number: MI-YYYY-XXXX
            from django.db.models import Max
            today = timezone.now()
            prefix = f"MI-{today.year}-"
            last_issue = MaterialIssue.objects.filter(
                issue_number__startswith=prefix
            ).aggregate(Max('issue_number'))

            if last_issue['issue_number__max']:
                last_num = int(last_issue['issue_number__max'].split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1

            self.issue_number = f"{prefix}{new_num:05d}"

        super().save(*args, **kwargs)


class MaterialIssueLine(models.Model):
    """
    Line items for Material Issue
    """
    material_issue = models.ForeignKey(
        MaterialIssue,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)

    # Item details
    budget_item = models.ForeignKey(
        'budgeting.BudgetItemCode',
        on_delete=models.PROTECT,
        related_name='inventory_issue_lines'
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='inventory_issue_lines'
    )

    # Quantities
    quantity_requested = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    quantity_issued = models.DecimalField(max_digits=15, decimal_places=3)
    uom = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.PROTECT,
        related_name='material_issue_lines'
    )

    # Batch/Serial tracking
    batch_lot = models.ForeignKey(
        BatchLot,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='material_issue_lines',
        help_text="Batch allocated for this issue"
    )
    serial_numbers = models.JSONField(
        default=list,
        blank=True,
        help_text="Serial numbers issued (for serialized items)"
    )

    # Costing
    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Cost per unit at time of issue"
    )
    total_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total cost of this line"
    )

    # Cost allocation
    cost_center = models.ForeignKey(
        'budgeting.CostCenter',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='material_issue_lines'
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='material_issue_lines'
    )

    notes = models.TextField(blank=True)

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Movement event reference
    movement_event = models.ForeignKey(
        MovementEvent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='material_issue_line_ref'
    )

    class Meta:
        db_table = 'inventory_material_issue_line'
        ordering = ['id']
        indexes = [
            models.Index(fields=['material_issue', 'budget_item']),
            models.Index(fields=['company', 'budget_item']),
        ]

    def __str__(self):
        return f"{self.material_issue.issue_number} - {self.budget_item.code}"

    def save(self, *args, **kwargs):
        # Calculate total cost
        self.total_cost = self.quantity_issued * self.unit_cost
        super().save(*args, **kwargs)


# ========================================
# WAREHOUSE CATEGORY MAPPING
# ========================================

class WarehouseCategoryMapping(models.Model):
    """
    Maps item categories/subcategories to warehouses for intelligent warehouse selection.
    Provides auto-suggestion with override capability.
    """
    WARNING_LEVEL_CHOICES = [
        ('INFO', 'Informational - can proceed without reason'),
        ('WARNING', 'Warning - requires reason'),
        ('CRITICAL', 'Critical - requires supervisor approval'),
    ]

    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='warehouse_category_mappings',
        help_text="Company this mapping belongs to"
    )
    warehouse = models.ForeignKey(
        'Warehouse',
        on_delete=models.CASCADE,
        related_name='category_mappings',
        help_text="Warehouse for this category"
    )
    category = models.ForeignKey(
        'ItemCategory',
        on_delete=models.CASCADE,
        related_name='warehouse_mappings',
        help_text="Item category (required)"
    )
    subcategory = models.ForeignKey(
        'ItemCategory',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='warehouse_subcategory_mappings',
        help_text="Specific subcategory (optional - leave blank for all subcategories)"
    )

    # Behavior configuration
    is_default = models.BooleanField(
        default=False,
        help_text="Auto-select this warehouse for items in this category"
    )
    priority = models.IntegerField(
        default=1,
        help_text="Priority when multiple warehouses match (higher = preferred)"
    )
    allow_multi_warehouse = models.BooleanField(
        default=False,
        help_text="Items in this category can be stored in multiple warehouses without warnings"
    )
    warning_level = models.CharField(
        max_length=20,
        choices=WARNING_LEVEL_CHOICES,
        default='WARNING',
        help_text="Warning level when user selects different warehouse"
    )

    # Metadata
    notes = models.TextField(blank=True, help_text="Notes about this mapping")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_warehouse_category_mapping'
        unique_together = ['company', 'warehouse', 'category', 'subcategory']
        ordering = ['-priority', 'warehouse__name']
        indexes = [
            models.Index(fields=['company', 'category', 'subcategory']),
            models.Index(fields=['warehouse', 'is_default']),
            models.Index(fields=['category', 'is_default']),
        ]
        verbose_name = 'Warehouse Category Mapping'
        verbose_name_plural = 'Warehouse Category Mappings'

    def __str__(self):
        if self.subcategory:
            return f"{self.warehouse.name} → {self.category.name} / {self.subcategory.name}"
        return f"{self.warehouse.name} → {self.category.name} (All)"

    def clean(self):
        from django.core.exceptions import ValidationError

        # Validation: subcategory must be child of category
        if self.subcategory:
            if self.subcategory.parent_category_id != self.category_id:
                raise ValidationError({
                    'subcategory': 'Subcategory must be a child of the selected category'
                })

        # Validation: company consistency
        if self.warehouse.company_id != self.company_id:
            raise ValidationError({
                'warehouse': 'Warehouse must belong to the same company'
            })

        if self.category.company_id != self.company_id:
            raise ValidationError({
                'category': 'Category must belong to the same company'
            })

    @staticmethod
    def get_allowed_warehouses_for_item(item):
        """
        Get list of warehouses allowed for a specific item based on its category.
        Returns: QuerySet of Warehouse objects
        """
        from django.db.models import Q

        # Get mappings for this item's category
        mappings = WarehouseCategoryMapping.objects.filter(
            company=item.company,
            category=item.category
        ).filter(
            Q(subcategory__isnull=True) |  # Category-level mapping
            Q(subcategory=item.subcategory)  # Specific subcategory
        ).select_related('warehouse')

        if mappings.exists():
            warehouse_ids = mappings.values_list('warehouse_id', flat=True)
            return Warehouse.objects.filter(id__in=warehouse_ids, is_active=True)

        # If no mappings, return all active warehouses (fallback)
        return Warehouse.objects.filter(is_active=True, company=item.company)

    @staticmethod
    def get_default_warehouse_for_item(item):
        """
        Get the default warehouse for an item based on category mappings.
        Returns: Warehouse object or None
        """
        from django.db.models import Q

        # First try: Exact subcategory match with default flag
        if item.subcategory:
            mapping = WarehouseCategoryMapping.objects.filter(
                company=item.company,
                category=item.category,
                subcategory=item.subcategory,
                is_default=True
            ).select_related('warehouse').first()

            if mapping:
                return mapping.warehouse

        # Second try: Category-level match with default flag
        mapping = WarehouseCategoryMapping.objects.filter(
            company=item.company,
            category=item.category,
            subcategory__isnull=True,
            is_default=True
        ).select_related('warehouse').first()

        if mapping:
            return mapping.warehouse

        # Third try: Highest priority warehouse for this category
        mapping = WarehouseCategoryMapping.objects.filter(
            company=item.company,
            category=item.category
        ).filter(
            Q(subcategory__isnull=True) |
            Q(subcategory=item.subcategory)
        ).order_by('-priority').select_related('warehouse').first()

        if mapping:
            return mapping.warehouse

        return None

    @staticmethod
    def validate_warehouse_selection(item, selected_warehouse, user=None):
        """
        Validates if the selected warehouse is appropriate for the item.
        Returns dictionary with validation results.
        """
        from django.db.models import Q

        # Get suggested warehouse
        suggested_warehouse = WarehouseCategoryMapping.get_default_warehouse_for_item(item)

        # If no suggestion or selected matches suggested, all good
        if not suggested_warehouse or suggested_warehouse.id == selected_warehouse.id:
            return {
                'is_valid': True,
                'warning_level': None,
                'message': None,
                'suggested_warehouse': None,
                'requires_reason': False,
                'requires_approval': False,
                'allowed_warehouses': WarehouseCategoryMapping.get_allowed_warehouses_for_item(item),
            }

        # Get mapping for warning level
        mapping = WarehouseCategoryMapping.objects.filter(
            company=item.company,
            category=item.category,
            warehouse=suggested_warehouse
        ).filter(
            Q(subcategory__isnull=True) | Q(subcategory=item.subcategory)
        ).first()

        warning_level = mapping.warning_level if mapping else 'WARNING'

        # Check if selected warehouse is in allowed list
        allowed_warehouses = WarehouseCategoryMapping.get_allowed_warehouses_for_item(item)
        is_allowed = selected_warehouse in allowed_warehouses

        # Check if multi-warehouse is allowed
        allow_multi = mapping.allow_multi_warehouse if mapping else False

        return {
            'is_valid': False,
            'warning_level': warning_level,
            'message': f"This item ({item.category.name}) is configured for {suggested_warehouse.name}. "
                       f"You are selecting {selected_warehouse.name}.",
            'suggested_warehouse': suggested_warehouse,
            'selected_warehouse': selected_warehouse,
            'requires_reason': warning_level in ['WARNING', 'CRITICAL'] and not (allow_multi and is_allowed),
            'requires_approval': warning_level == 'CRITICAL',
            'is_allowed': is_allowed,
            'allow_multi_warehouse': allow_multi,
            'allowed_warehouses': allowed_warehouses,
        }


class WarehouseOverrideLog(models.Model):
    """
    Audit trail for warehouse overrides.
    Tracks when users select different warehouse than configured.
    """
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='warehouse_overrides',
        help_text="Company this override belongs to"
    )

    # Transaction context
    transaction_type = models.CharField(
        max_length=50,
        help_text="Type of transaction (GRN, Material Issue, Transfer, etc.)"
    )
    transaction_id = models.IntegerField(
        help_text="ID of the related transaction"
    )
    transaction_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Transaction number for easy reference"
    )

    # Item and warehouse details
    budget_item = models.ForeignKey(
        'budgeting.BudgetItemCode',
        on_delete=models.CASCADE,
        related_name='warehouse_overrides'
    )
    item_category = models.ForeignKey(
        'ItemCategory',
        on_delete=models.CASCADE,
        related_name='+',
        help_text="Category at time of override"
    )
    suggested_warehouse = models.ForeignKey(
        'Warehouse',
        on_delete=models.CASCADE,
        related_name='suggested_overrides',
        help_text="System-suggested warehouse"
    )
    actual_warehouse = models.ForeignKey(
        'Warehouse',
        on_delete=models.CASCADE,
        related_name='actual_overrides',
        help_text="User-selected warehouse"
    )

    # Override details
    override_reason = models.TextField(help_text="Reason provided by user")
    warning_level = models.CharField(
        max_length=20,
        help_text="Warning level at time of override"
    )
    was_approved = models.BooleanField(
        default=False,
        help_text="Whether supervisor approval was obtained"
    )

    # Audit fields
    overridden_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='warehouse_overrides'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='approved_warehouse_overrides'
    )
    overridden_at = models.DateTimeField(auto_now_add=True)

    # Review fields (for post-analysis)
    was_valid_override = models.BooleanField(
        null=True,
        blank=True,
        help_text="Reviewed by manager - was this a valid override?"
    )
    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reviewed_warehouse_overrides'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'inventory_warehouse_override_log'
        ordering = ['-overridden_at']
        indexes = [
            models.Index(fields=['company', 'overridden_at']),
            models.Index(fields=['overridden_by', 'overridden_at']),
            models.Index(fields=['budget_item', 'overridden_at']),
            models.Index(fields=['transaction_type', 'transaction_id']),
            models.Index(fields=['was_valid_override']),
        ]
        verbose_name = 'Warehouse Override Log'
        verbose_name_plural = 'Warehouse Override Logs'

    def __str__(self):
        return f"{self.transaction_type} #{self.transaction_number}: {self.suggested_warehouse.name} → {self.actual_warehouse.name}"
