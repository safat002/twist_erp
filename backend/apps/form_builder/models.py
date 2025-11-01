from django.db import models
from django.conf import settings
from django.db.models import Q
from django.utils.text import slugify

from apps.companies.models import Company, CompanyGroup
from apps.metadata.models import MetadataDefinition


class FormTemplate(models.Model):
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
    slug = models.SlugField(max_length=255, help_text="Stable identifier for the form.", blank=True, default="")
    description = models.TextField(blank=True)
    schema = models.JSONField(default=list, help_text="Ordered list of field definitions.")
    layer = models.CharField(
        max_length=20,
        choices=MetadataDefinition.LAYER_CHOICES,
        default="COMPANY_OVERRIDE",
    )
    scope_type = models.CharField(max_length=15, choices=SCOPE_CHOICES, default="COMPANY")
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="draft")
    company_group = models.ForeignKey(
        CompanyGroup,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="form_templates",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="form_templates",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_form_templates"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "company"],
                condition=Q(scope_type="COMPANY"),
                name="uniq_form_slug_company",
            ),
            models.UniqueConstraint(
                fields=["slug", "company_group"],
                condition=Q(scope_type="GROUP"),
                name="uniq_form_slug_group",
            ),
            models.UniqueConstraint(
                fields=["slug"],
                condition=Q(scope_type="GLOBAL"),
                name="uniq_form_slug_global",
            ),
        ]

    def __str__(self):
        scope = self.scope_type
        if self.scope_type == "COMPANY" and self.company:
            scope = f"{self.company.code}"
        elif self.scope_type == "GROUP" and self.company_group:
            scope = f"{self.company_group.name}"
        return f"{self.name} ({scope}) v{self.version}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or f"form-{self.pk or 'new'}"
            slug_candidate = base_slug
            counter = 1
            while FormTemplate.objects.exclude(pk=self.pk).filter(
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


class FormSubmission(models.Model):
    template = models.ForeignKey(FormTemplate, on_delete=models.PROTECT, related_name="submissions")
    data = models.JSONField(default=dict)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="form_submissions"
    )
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="form_submissions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class DynamicEntity(models.Model):
    SCOPE_CHOICES = FormTemplate.SCOPE_CHOICES

    template = models.OneToOneField(
        FormTemplate,
        on_delete=models.CASCADE,
        related_name="entity",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="dynamic_entities",
        null=True,
        blank=True,
    )
    company_group = models.ForeignKey(
        CompanyGroup,
        on_delete=models.PROTECT,
        related_name="dynamic_entities",
        null=True,
        blank=True,
    )
    scope_type = models.CharField(max_length=15, choices=SCOPE_CHOICES, default="COMPANY")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)
    fields = models.JSONField(default=list, blank=True)
    model_name = models.CharField(max_length=255)
    table_name = models.CharField(max_length=255)
    api_path = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_dynamic_entities",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "company"],
                condition=Q(scope_type="COMPANY"),
                name="uniq_dynamic_slug_company",
            ),
            models.UniqueConstraint(
                fields=["slug", "company_group"],
                condition=Q(scope_type="GROUP"),
                name="uniq_dynamic_slug_group",
            ),
            models.UniqueConstraint(
                fields=["slug"],
                condition=Q(scope_type="GLOBAL"),
                name="uniq_dynamic_slug_global",
            ),
        ]

    def __str__(self):
        scope = self.scope_type
        if self.scope_type == "COMPANY" and self.company:
            scope = self.company.code
        elif self.scope_type == "GROUP" and self.company_group:
            scope = self.company_group.name
        return f"{scope}:{self.slug}"

    def save(self, *args, **kwargs):
        if self.scope_type == "COMPANY" and self.company and not self.company_group:
            self.company_group = self.company.company_group
        super().save(*args, **kwargs)
