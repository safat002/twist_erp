from django.db import models
from django.conf import settings

class Customer(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        BLACKLISTED = "blacklisted", "Blacklisted"

    class CustomerType(models.TextChoices):
        LOCAL = "local", "Local"
        EXPORT = "export", "Export"
        INTERCOMPANY = "intercompany", "Intercompany"

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    billing_address = models.TextField(blank=True)
    shipping_address = models.TextField(blank=True)
    credit_limit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    payment_terms = models.IntegerField(default=30, help_text="Payment terms in days")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    customer_type = models.CharField(max_length=20, choices=CustomerType.choices, default=CustomerType.LOCAL)
    is_blocked = models.BooleanField(default=False)
    block_reason = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    receivable_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT)

    class Meta:
        unique_together = ('company', 'code')
        indexes = [
            models.Index(fields=['company', 'customer_status']),
        ]

class SalesOrder(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, help_text="Company this record belongs to")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order_number = models.CharField(max_length=50)
    order_date = models.DateField()
    delivery_date = models.DateField()
    shipping_address = models.TextField()
    subtotal = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=20, decimal_places=2)
    status = models.CharField(max_length=20, choices=[
        ('DRAFT', 'Draft'),
        ('CONFIRMED', 'Confirmed'),
        ('PARTIAL', 'Partially Delivered'),
        ('DELIVERED', 'Delivered'),
        ('INVOICED', 'Invoiced'),
        ('CANCELLED', 'Cancelled'),
    ], default='DRAFT')
    notes = models.TextField(blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)

    class Meta:
        unique_together = ('company', 'order_number')
        indexes = [
            models.Index(fields=['company', 'order_date']),
            models.Index(fields=['company', 'customer', 'status']),
        ]

class SalesOrderLine(models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='lines')
    line_number = models.IntegerField()
    description = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    unit_price = models.DecimalField(max_digits=20, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=20, decimal_places=2)
    delivered_qty = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    product = models.ForeignKey('inventory.Item', on_delete=models.PROTECT)
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT)

    class Meta:
        ordering = ['order', 'line_number']
