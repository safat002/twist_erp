from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from core.id_factory import IDFactory


class Donor(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='donors')
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)

    class Meta:
        unique_together = ('company', 'code')
        ordering = ['name']

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Program(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        CLOSED = 'closed', 'Closed'

    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='programs')
    donor = models.ForeignKey(Donor, on_delete=models.PROTECT, related_name='programs')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    code = models.CharField(max_length=30)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    total_budget = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=8, default='USD')
    objectives = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    compliance_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        unique_together = ('company', 'code')
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        is_new = self._state.adding and not self.code
        super().save(*args, **kwargs)
        if is_new:
            generated = IDFactory.make_master_code('PRG', self.company, Program, width=5)
            Program.objects.filter(pk=self.pk).update(code=generated)
            self.code = generated


class ComplianceRequirement(models.Model):
    class Frequency(models.TextChoices):
        ONCE = 'once', 'Once'
        MONTHLY = 'monthly', 'Monthly'
        QUARTERLY = 'quarterly', 'Quarterly'
        ANNUAL = 'annual', 'Annual'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        CLOSED = 'closed', 'Closed'

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='requirements')
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    frequency = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.QUARTERLY)
    next_due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        unique_together = ('program', 'code')


class ComplianceSubmission(models.Model):
    requirement = models.ForeignKey(ComplianceRequirement, on_delete=models.CASCADE, related_name='submissions')
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('submitted', 'Submitted'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='submitted')
    notes = models.TextField(blank=True)
    file = models.FileField(upload_to='ngo/compliance/', null=True, blank=True)

