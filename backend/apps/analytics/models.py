from decimal import Decimal
from django.db import models


class WarehouseRunLog(models.Model):
    RUN_STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    run_at = models.DateTimeField(auto_now_add=True)
    company_id = models.IntegerField(null=True, blank=True)
    company_code = models.CharField(max_length=50, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    run_type = models.CharField(max_length=50, default='nightly')
    status = models.CharField(max_length=20, choices=RUN_STATUS_CHOICES)
    processed_records = models.IntegerField(default=0)
    message = models.TextField(blank=True)

    class Meta:
        app_label = 'analytics'
        db_table = 'dw_run_log'
        ordering = ['-run_at']

    def __str__(self):
        label = self.company_code or self.company_name or 'Global'
        return f"{label} @ {self.run_at:%Y-%m-%d %H:%M}"


class SalesPerformanceSnapshot(models.Model):
    snapshot_date = models.DateField()
    period = models.CharField(max_length=20, default='30d')
    company_id = models.IntegerField()
    company_code = models.CharField(max_length=50)
    company_name = models.CharField(max_length=255)
    timeframe_start = models.DateField()
    timeframe_end = models.DateField()
    total_orders = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    avg_order_value = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    sales_trend = models.JSONField(default=list, blank=True)
    top_customers = models.JSONField(default=list, blank=True)
    top_products = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'analytics'
        db_table = 'dw_sales_performance'
        unique_together = ('snapshot_date', 'period', 'company_id')
        indexes = [
            models.Index(fields=['company_id', 'period', 'snapshot_date']),
        ]
        ordering = ['-snapshot_date', '-created_at']

    def __str__(self):
        return f"Sales Snapshot {self.snapshot_date} ({self.period})"


class CashflowSnapshot(models.Model):
    snapshot_date = models.DateField()
    period = models.CharField(max_length=20, default='30d')
    company_id = models.IntegerField()
    company_code = models.CharField(max_length=50)
    company_name = models.CharField(max_length=255)
    timeframe_start = models.DateField()
    timeframe_end = models.DateField()
    cash_in = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    cash_out = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    net_cash = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    cash_trend = models.JSONField(default=list, blank=True)
    receivables_balance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    payables_balance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    bank_balances = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'analytics'
        db_table = 'dw_cashflow_snapshot'
        unique_together = ('snapshot_date', 'period', 'company_id')
        indexes = [
            models.Index(fields=['company_id', 'period', 'snapshot_date']),
        ]
        ordering = ['-snapshot_date', '-created_at']

    def __str__(self):
        return f"Cashflow Snapshot {self.snapshot_date} ({self.period})"
