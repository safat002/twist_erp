from django.db import models
from django.conf import settings
from .customer import Customer

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
