from django.db import models
from .sales_order import SalesOrder

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
    product = models.ForeignKey(
        'sales.Product',
        on_delete=models.PROTECT,
        related_name='sales_order_lines',
        help_text="Saleable product being sold"
    )
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT)

    class Meta:
        ordering = ['order', 'line_number']
