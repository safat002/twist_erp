from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.utils import timezone

from apps.companies.models import Company


class Asset(models.Model):
    METHOD_SL = "SL"
    METHOD_DB = "DB"
    DEPRECIATION_METHODS = [
        (METHOD_SL, "Straight-line"),
        (METHOD_DB, "Declining balance"),
    ]

    STATUS_ACTIVE = "ACTIVE"
    STATUS_MAINTENANCE = "MAINTENANCE"
    STATUS_RETIRED = "RETIRED"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_MAINTENANCE, "In Maintenance"),
        (STATUS_RETIRED, "Retired"),
    ]

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    barcode = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=120, blank=True)
    manufacturer = models.CharField(max_length=120, blank=True)
    model_number = models.CharField(max_length=120, blank=True)
    serial_number = models.CharField(max_length=120, blank=True)
    acquisition_date = models.DateField()
    cost = models.DecimalField(max_digits=14, decimal_places=2)
    residual_value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    depreciation_method = models.CharField(max_length=2, choices=DEPRECIATION_METHODS, default=METHOD_SL)
    useful_life_months = models.PositiveIntegerField(default=60)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="assets")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-acquisition_date", "code"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "category"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @staticmethod
    def _months_between(start_date, end_date) -> int:
        if not start_date or not end_date:
            return 0
        return max(0, (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month))

    def months_in_service(self, reference_date=None) -> int:
        reference = reference_date or timezone.now().date()
        return min(self.useful_life_months, self._months_between(self.acquisition_date, reference))

    def monthly_depreciation(self) -> Decimal:
        depreciable_base = (self.cost or Decimal("0")) - (self.residual_value or Decimal("0"))
        if depreciable_base <= 0 or self.useful_life_months <= 0:
            return Decimal("0.00")

        if self.depreciation_method == self.METHOD_DB:
            rate = Decimal("2") / Decimal(self.useful_life_months)
            return (depreciable_base * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return (depreciable_base / Decimal(self.useful_life_months)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def depreciation_to_date(self, reference_date=None) -> Decimal:
        months = self.months_in_service(reference_date=reference_date)
        depreciation = self.monthly_depreciation() * Decimal(months)
        max_depreciation = (self.cost or Decimal("0")) - (self.residual_value or Decimal("0"))
        if max_depreciation <= 0:
            return Decimal("0.00")
        if depreciation > max_depreciation:
            depreciation = max_depreciation
        return depreciation.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def book_value(self, reference_date=None) -> Decimal:
        depreciation = self.depreciation_to_date(reference_date=reference_date)
        value = (self.cost or Decimal("0")) - depreciation
        min_value = self.residual_value or Decimal("0")
        if value < min_value:
            value = min_value
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def next_maintenance(self):
        return (
            self.maintenance_tasks.filter(status__in=[AssetMaintenancePlan.STATUS_PLANNED, AssetMaintenancePlan.STATUS_IN_PROGRESS])
            .order_by("scheduled_date")
            .first()
        )


class AssetMaintenancePlan(models.Model):
    STATUS_PLANNED = "PLANNED"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_OVERDUE = "OVERDUE"

    STATUS_CHOICES = [
        (STATUS_PLANNED, "Planned"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_OVERDUE, "Overdue"),
    ]

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="maintenance_tasks")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="asset_maintenance")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    maintenance_type = models.CharField(max_length=120, blank=True)
    scheduled_date = models.DateField()
    due_date = models.DateField()
    completed_at = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED)
    assigned_to = models.CharField(max_length=255, blank=True)
    frequency_months = models.PositiveIntegerField(default=0)
    cost_estimate = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_date", "id"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "scheduled_date"]),
        ]

    def __str__(self):
        return f"{self.asset.code} - {self.title} ({self.scheduled_date})"

    @property
    def is_overdue(self) -> bool:
        if self.status == self.STATUS_COMPLETED:
            return False
        return self.due_date < timezone.now().date()
