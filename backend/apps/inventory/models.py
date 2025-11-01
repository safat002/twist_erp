from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.budgeting.models import BudgetUsage

class Product(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
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
    cost_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    reorder_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    is_active = models.BooleanField(default=True)
    category = models.ForeignKey('ProductCategory', on_delete=models.PROTECT)
    uom = models.ForeignKey('UnitOfMeasure', on_delete=models.PROTECT, related_name='products')
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
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('company', 'code')

class StockMovementLine(models.Model):
    movement = models.ForeignKey(StockMovement, on_delete=models.CASCADE, related_name='lines')
    line_number = models.IntegerField()
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    rate = models.DecimalField(max_digits=20, decimal_places=2)
    batch_no = models.CharField(max_length=50, blank=True)
    serial_no = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['movement', 'line_number']

class ProductCategory(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    parent_category = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Product Categories'
        unique_together = ('company', 'code')

class StockLedger(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
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

    class Meta:
        ordering = ['transaction_date', 'id']
        indexes = [
            models.Index(fields=['company', 'product', 'warehouse']),
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
        previous_status = None
        if self.pk:
            previous_status = GoodsReceipt.objects.filter(pk=self.pk).values_list("status", flat=True).first()
        super().save(*args, **kwargs)
        if previous_status != 'POSTED' and self.status == 'POSTED':
            self._on_posted()

    def _on_posted(self):
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

    def place_on_hold(self, *, reason: str, user=None):
        self.quality_status = 'on_hold'
        self.hold_reason = reason
        self.quality_checked_by = user
        self.quality_checked_at = timezone.now()
        self.save(update_fields=['quality_status', 'hold_reason', 'quality_checked_by', 'quality_checked_at', 'updated_at'])

    def release_hold(self, *, user=None, passed: bool = True):
        self.quality_status = 'passed' if passed else 'rejected'
        self.quality_checked_by = user
        self.quality_checked_at = timezone.now()
        self.save(update_fields=['quality_status', 'quality_checked_by', 'quality_checked_at', 'updated_at'])

class StockLevel(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=15, decimal_places=3, default=0)

    class Meta:
        unique_together = ('company', 'product', 'warehouse')
        indexes = [
            models.Index(fields=['company', 'product', 'warehouse']),
        ]

class GoodsReceiptLine(models.Model):
    goods_receipt = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='receipt_lines')
    purchase_order_line = models.ForeignKey('procurement.PurchaseOrderLine', on_delete=models.PROTECT, related_name='receipt_lines')
    quantity_received = models.DecimalField(max_digits=15, decimal_places=3)

    class Meta:
        unique_together = ('goods_receipt', 'purchase_order_line')

class DeliveryOrderLine(models.Model):
    delivery_order = models.ForeignKey(DeliveryOrder, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='delivery_lines')
    sales_order_line = models.ForeignKey('sales.SalesOrderLine', on_delete=models.PROTECT, related_name='delivery_lines')
    quantity_shipped = models.DecimalField(max_digits=15, decimal_places=3)

    class Meta:
        unique_together = ('delivery_order', 'sales_order_line')
