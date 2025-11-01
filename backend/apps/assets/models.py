from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.utils import timezone

from django.conf import settings
from apps.companies.models import Company
from apps.finance.models import Account, Journal, JournalVoucher, JournalEntry


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
    # Optional finance mappings for depreciation posting
    depreciation_expense_account = models.ForeignKey(
        Account, on_delete=models.PROTECT, null=True, blank=True, related_name="depreciation_assets",
        help_text="Expense account to debit for monthly depreciation"
    )
    accumulated_depreciation_account = models.ForeignKey(
        Account, on_delete=models.PROTECT, null=True, blank=True, related_name="accumulated_depreciation_assets",
        help_text="Balance sheet account to credit (accumulated depreciation)"
    )

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


class DepreciationRun(models.Model):
    """Tracks monthly depreciation postings per company."""

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="asset_depreciation_runs")
    period = models.CharField(max_length=7, help_text="YYYY-MM")
    total_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    voucher = models.ForeignKey(JournalVoucher, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "period")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.company.code} {self.period} ({self.total_amount})"

    @staticmethod
    def _ensure_journal(company) -> Journal:
        journal, _ = Journal.objects.get_or_create(
            company=company,
            company_group=company.company_group,
            code="DEP",
            defaults={
                "name": "Depreciation Journal",
                "type": "GENERAL",
            },
        )
        return journal

    @classmethod
    def run_for_month(cls, *, company: Company, year: int, month: int, user=None) -> "DepreciationRun":
        period = f"{year:04d}-{month:02d}"
        run, created = cls.objects.get_or_create(company=company, period=period)
        if not created and run.voucher_id:
            return run  # already posted

        assets = Asset.objects.filter(company=company, status=Asset.STATUS_ACTIVE)
        entries = []
        line = 1
        total = Decimal("0.00")
        for asset in assets:
            amount = asset.monthly_depreciation()
            if amount <= 0:
                continue
            if not asset.depreciation_expense_account_id or not asset.accumulated_depreciation_account_id:
                continue  # skip assets without mappings
            entries.append({
                "line_number": line,
                "account_id": asset.depreciation_expense_account_id,
                "debit_amount": amount,
                "credit_amount": Decimal("0.00"),
                "description": f"Depreciation {period} - {asset.code}",
            })
            line += 1
            entries.append({
                "line_number": line,
                "account_id": asset.accumulated_depreciation_account_id,
                "debit_amount": Decimal("0.00"),
                "credit_amount": amount,
                "description": f"Accum. Depreciation {period} - {asset.code}",
            })
            line += 1
            total += amount

        if not entries:
            run.total_amount = Decimal("0.00")
            run.save(update_fields=["total_amount", "created_at"])
            return run

        journal = cls._ensure_journal(company)
        voucher = JournalVoucher.objects.create(
            company_group=company.company_group,
            company=company,
            created_by=user,
            entry_date=timezone.now().date(),
            period=period,
            reference=f"ASSET-DEP-{period}",
            description=f"Monthly depreciation batch for {period}",
            journal=journal,
            status="POSTED",
            posted_at=timezone.now(),
            posted_by=user,
        )
        # Create entries
        for e in entries:
            JournalEntry.objects.create(voucher=voucher, **e)
        run.total_amount = total
        run.voucher = voucher
        run.save(update_fields=["total_amount", "voucher", "created_at"])
        return run


class DowntimeLog(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="downtimes")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="asset_downtimes")
    reason = models.CharField(max_length=255)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    impact_percent = models.PositiveIntegerField(default=0, help_text="Estimated productivity impact 0-100%")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["company", "started_at"]),
            models.Index(fields=["company", "asset"]),
        ]

    @property
    def duration_minutes(self) -> int:
        end = self.ended_at or timezone.now()
        delta = end - self.started_at
        return int(delta.total_seconds() // 60)


class DisposalMethod(models.TextChoices):
    SALE = "SALE", "Sale"
    SCRAP = "SCRAP", "Scrap"
    WRITE_OFF = "WRITE_OFF", "Write Off"


class DisposalStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    POSTED = "POSTED", "Posted"


class AssetDisposal(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="disposals")
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="asset_disposals")
    method = models.CharField(max_length=20, choices=DisposalMethod.choices)
    disposal_date = models.DateField()
    reason = models.TextField(blank=True)
    proceeds_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    nbv_at_disposal = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=DisposalStatus.choices, default=DisposalStatus.DRAFT)
    voucher = models.ForeignKey(JournalVoucher, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    # Posting accounts (required to post)
    asset_cost_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='+', null=True, blank=True,
                                           help_text="Fixed asset cost account to credit on disposal")
    accumulated_dep_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='+', null=True, blank=True,
                                               help_text="Accumulated depreciation account to debit on disposal")
    proceeds_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='+', null=True, blank=True,
                                         help_text="Cash/Bank or Receivable account to debit for proceeds")
    gain_loss_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='+', null=True, blank=True,
                                          help_text="Gain/Loss on disposal account")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.asset.code} disposal {self.disposal_date} ({self.method})"

    @staticmethod
    def _ensure_gj(company) -> Journal:
        journal, _ = Journal.objects.get_or_create(
            company=company,
            company_group=company.company_group,
            code="GJ",
            defaults={"name": "General Journal", "type": "GENERAL"},
        )
        return journal

    def post_to_finance(self, *, user=None) -> JournalVoucher:
        if self.status == DisposalStatus.POSTED and self.voucher_id:
            return self.voucher

        if not (self.asset_cost_account_id and (self.accumulated_dep_account_id or self.asset.accumulated_depreciation_account_id)
                and self.proceeds_account_id and self.gain_loss_account_id):
            raise ValueError("All posting accounts must be provided to post disposal.")

        company = self.company
        journal = self._ensure_gj(company)

        # Compute NBV if not set
        if not self.nbv_at_disposal or self.nbv_at_disposal <= 0:
            self.nbv_at_disposal = self.asset.book_value(reference_date=self.disposal_date)

        depreciation_to_date = self.asset.depreciation_to_date(reference_date=self.disposal_date)
        cost = self.asset.cost or Decimal("0.00")
        proceeds = self.proceeds_amount or Decimal("0.00")
        nbv = self.nbv_at_disposal or (cost - depreciation_to_date)
        gain_loss = proceeds - nbv

        voucher = JournalVoucher.objects.create(
            company_group=company.company_group,
            company=company,
            created_by=user,
            entry_date=self.disposal_date,
            period=f"{self.disposal_date:%Y-%m}",
            reference=f"ASSET-DISP-{self.asset.code}",
            description=f"Asset disposal {self.asset.code} - {self.method}",
            journal=journal,
            status="POSTED",
            posted_at=timezone.now(),
            posted_by=user,
        )

        line = 1
        # Debit accumulated depreciation
        acc_dep_acct_id = self.accumulated_dep_account_id or self.asset.accumulated_depreciation_account_id
        if depreciation_to_date > 0 and acc_dep_acct_id:
            JournalEntry.objects.create(
                voucher=voucher,
                line_number=line,
                account_id=acc_dep_acct_id,
                debit_amount=depreciation_to_date,
                credit_amount=Decimal("0.00"),
                description=f"Remove accumulated depreciation {self.asset.code}",
            )
            line += 1
        # Credit asset cost
        if cost > 0:
            JournalEntry.objects.create(
                voucher=voucher,
                line_number=line,
                account_id=self.asset_cost_account_id,
                debit_amount=Decimal("0.00"),
                credit_amount=cost,
                description=f"Remove asset cost {self.asset.code}",
            )
            line += 1
        # Debit proceeds
        if proceeds > 0 and self.proceeds_account_id:
            JournalEntry.objects.create(
                voucher=voucher,
                line_number=line,
                account_id=self.proceeds_account_id,
                debit_amount=proceeds,
                credit_amount=Decimal("0.00"),
                description=f"Proceeds from disposal {self.asset.code}",
            )
            line += 1
        # Gain or loss line
        if gain_loss != 0:
            if gain_loss > 0:
                JournalEntry.objects.create(
                    voucher=voucher,
                    line_number=line,
                    account_id=self.gain_loss_account_id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=gain_loss,
                    description=f"Gain on disposal {self.asset.code}",
                )
            else:
                JournalEntry.objects.create(
                    voucher=voucher,
                    line_number=line,
                    account_id=self.gain_loss_account_id,
                    debit_amount=abs(gain_loss),
                    credit_amount=Decimal("0.00"),
                    description=f"Loss on disposal {self.asset.code}",
                )

        self.voucher = voucher
        self.status = DisposalStatus.POSTED
        self.approved_by = user
        self.save(update_fields=["voucher", "status", "approved_by", "nbv_at_disposal", "created_at"])
        return voucher
