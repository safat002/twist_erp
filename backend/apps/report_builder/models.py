from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from apps.companies.models import Company, CompanyGroup
from apps.metadata.models import MetadataDefinition


class ReportDefinition(models.Model):
    """Metadata-backed report definition for the visual report builder."""

    SCOPE_CHOICES = [
        ("COMPANY", "Company"),
        ("GROUP", "Company Group"),
        ("GLOBAL", "Global"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("archived", "Archived"),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True)
    layer = models.CharField(
        max_length=20,
        choices=MetadataDefinition.LAYER_CHOICES,
        default="COMPANY_OVERRIDE",
    )
    scope_type = models.CharField(max_length=15, choices=SCOPE_CHOICES, default="COMPANY")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="draft")
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    company_group = models.ForeignKey(
        CompanyGroup,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="report_definitions",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="report_definitions",
    )

    definition = models.JSONField(default=dict, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    required_permissions = models.JSONField(default=list, blank=True)

    metadata = models.ForeignKey(
        MetadataDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="report_definitions",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_report_definitions",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_report_definitions",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "company"],
                condition=Q(scope_type="COMPANY"),
                name="uniq_report_slug_company",
            ),
            models.UniqueConstraint(
                fields=["slug", "company_group"],
                condition=Q(scope_type="GROUP"),
                name="uniq_report_slug_group",
            ),
            models.UniqueConstraint(
                fields=["slug"],
                condition=Q(scope_type="GLOBAL"),
                name="uniq_report_slug_global",
            ),
        ]

    def __str__(self) -> str:
        scope = self.scope_type
        if self.scope_type == "COMPANY" and self.company:
            scope = self.company.code
        elif self.scope_type == "GROUP" and self.company_group:
            scope = self.company_group.name
        return f"{scope}:{self.slug or 'unpublished'}"

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            base_slug = slugify(self.name) or f"report-{self.pk or 'new'}"
            slug_candidate = base_slug
            counter = 1
            while ReportDefinition.objects.exclude(pk=self.pk).filter(
                slug=slug_candidate,
                scope_type=self.scope_type,
                company=self.company if self.scope_type == "COMPANY" else None,
                company_group=self.company_group if self.scope_type == "GROUP" else None,
            ).exists():
                counter += 1
                slug_candidate = f"{base_slug}-{counter}"
            self.slug = slug_candidate

        if self.scope_type == "COMPANY" and self.company and not self.company_group:
            self.company_group = self.company.company_group

        super().save(*args, **kwargs)

    @property
    def metadata_key(self) -> str:
        slug_value = self.slug or slugify(self.name) or f"report-{self.pk or 'new'}"
        return f"report:{slug_value}"

    def required_permission_codes(self) -> list[str]:
        return [code for code in self.required_permissions if isinstance(code, str)]
