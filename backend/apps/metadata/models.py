from __future__ import annotations

import uuid
from django.conf import settings
from django.db import models

from apps.companies.models import Company, CompanyGroup


class MetadataDefinition(models.Model):
    """Versioned metadata container for entities, forms, workflows, dashboards, etc."""

    KIND_CHOICES = [
        ("ENTITY", "Entity Definition"),
        ("FORM", "Form Definition"),
        ("LIST", "List View Definition"),
        ("WORKFLOW", "Workflow Definition"),
        ("DASHBOARD", "Dashboard Definition"),
        ("WIDGET", "Dashboard Widget Definition"),
    ]

    LAYER_CHOICES = [
        ("CORE", "Core System"),
        ("INDUSTRY_PACK", "Industry Pack Baseline"),
        ("GROUP_CUSTOM", "Group Customization"),
        ("COMPANY_OVERRIDE", "Company Override"),
    ]

    SCOPE_CHOICES = [
        ("GLOBAL", "Global"),
        ("GROUP", "Company Group"),
        ("COMPANY", "Company"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(
        max_length=255,
        help_text="Stable identifier (e.g., 'entity.customer', 'form.purchase_order').",
        default=uuid.uuid4,
    )
    label = models.CharField(max_length=255, blank=True, default="")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="FORM")
    layer = models.CharField(max_length=20, choices=LAYER_CHOICES, default="COMPANY_OVERRIDE")
    scope_type = models.CharField(max_length=20, choices=SCOPE_CHOICES, default="COMPANY")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=False)
    definition = models.JSONField(default=dict, help_text="Versioned metadata payload.")
    summary = models.JSONField(default=dict, blank=True, help_text="Lightweight summary for UI listings.")
    description = models.TextField(blank=True)

    company_group = models.ForeignKey(
        CompanyGroup,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="metadata_definitions",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="metadata_definitions",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_metadata_definitions",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_metadata_definitions",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["key", "kind", "layer", "scope_type", "company_group", "company", "version"],
                name="uniq_metadata_version",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(scope_type="GLOBAL", company__isnull=True, company_group__isnull=True)
                    | models.Q(scope_type="GROUP", company_group__isnull=False)
                    | models.Q(scope_type="COMPANY", company__isnull=False)
                ),
                name="metadata_scope_consistency",
            ),
        ]
        indexes = [
            models.Index(fields=["kind", "key", "status"]),
            models.Index(fields=["scope_type", "company_group", "company"]),
        ]

    def __str__(self) -> str:
        scope = self.scope_type
        if self.scope_type == "GROUP" and self.company_group:
            scope = f"{scope}:{self.company_group.name}"
        elif self.scope_type == "COMPANY" and self.company:
            scope = f"{scope}:{self.company.code}"
        return f"{self.kind}:{self.key}@{scope} v{self.version} ({self.status})"

    def activate(self, *, user=None) -> None:
        """Mark this definition as active and archive older versions."""
        if self.status == "active" and self.is_active:
            return
        MetadataDefinition.objects.filter(
            key=self.key,
            kind=self.kind,
            scope_type=self.scope_type,
            company_group=self.company_group,
            company=self.company,
            status="active",
        ).update(status="archived", is_active=False)
        self.status = "active"
        self.is_active = True
        if user:
            self.updated_by = user
        self.save(update_fields=["status", "is_active", "updated_at", "updated_by"])

    @classmethod
    def next_version(cls, *, key: str, kind: str, layer: str, scope_type: str, company_group=None, company=None) -> int:
        """Determine the next version number for a metadata record."""
        latest = (
            cls.objects.filter(
                key=key,
                kind=kind,
                layer=layer,
                scope_type=scope_type,
                company_group=company_group,
                company=company,
            )
            .order_by("-version")
            .first()
        )
        return (latest.version + 1) if latest else 1
