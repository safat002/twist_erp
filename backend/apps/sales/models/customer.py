from django.db import models
from django.conf import settings


class Customer(models.Model):
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
    customer_status = models.CharField(max_length=20, choices=[
        ('LEAD', 'Lead'),
        ('PROSPECT', 'Prospect'),
        ('ACTIVE', 'Active Customer'),
        ('INACTIVE', 'Inactive'),
    ], default='LEAD')
    customer_type = models.CharField(max_length=20, choices=CustomerType.choices, default=CustomerType.LOCAL)
    is_active = models.BooleanField(default=True)
    receivable_account = models.ForeignKey('finance.Account', on_delete=models.PROTECT)

    class Meta:
        unique_together = ('company', 'code')
        indexes = [
            models.Index(fields=['company', 'customer_status']),
        ]
