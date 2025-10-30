from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from apps.companies.models import Company, CompanyGroup
from apps.metadata.models import MetadataDefinition


class DashboardLayout(models.Model):
    """
    Stores a user's customised dashboard layout per company.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dashboard_layouts',
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='dashboard_layouts',
    )
    layout = models.JSONField(default=dict, blank=True)
    widgets = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'dashboard'
        db_table = 'dashboard_layout'
        unique_together = ('user', 'company')
        ordering = ['-updated_at']

    def __str__(self):
        return f"Dashboard layout for {self.user} ({self.company})"


class DashboardDefinition(models.Model):
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
    layout = models.JSONField(default=dict, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    scope_type = models.CharField(max_length=15, choices=SCOPE_CHOICES, default="COMPANY")
    layer = models.CharField(max_length=20, choices=MetadataDefinition.LAYER_CHOICES, default="COMPANY_OVERRIDE")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="draft")
    version = models.PositiveIntegerField(default=1)
    metadata = models.ForeignKey(
        MetadataDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dashboard_versions",
    )
    company_group = models.ForeignKey(
        CompanyGroup,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dashboard_definitions",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dashboard_definitions",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_dashboards",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_dashboards",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "company"],
                condition=Q(scope_type="COMPANY"),
                name="uniq_dashboard_company_slug",
            ),
            models.UniqueConstraint(
                fields=["slug", "company_group"],
                condition=Q(scope_type="GROUP"),
                name="uniq_dashboard_group_slug",
            ),
            models.UniqueConstraint(
                fields=["slug"],
                condition=Q(scope_type="GLOBAL"),
                name="uniq_dashboard_global_slug",
            ),
        ]

    def __str__(self):
        return f"{self.name} v{self.version}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or f"dashboard-{self.pk or 'new'}"
            slug_candidate = base_slug
            counter = 1
            qs = DashboardDefinition.objects.exclude(pk=self.pk)
            while qs.filter(slug=slug_candidate).exists():
                counter += 1
                slug_candidate = f"{base_slug}-{counter}"
            self.slug = slug_candidate
        if self.metadata and self.metadata.version != self.version:
            self.version = self.metadata.version
        super().save(*args, **kwargs)


class DashboardWidgetDefinition(models.Model):
    dashboard = models.ForeignKey(
        DashboardDefinition,
        on_delete=models.CASCADE,
        related_name="widgets",
    )
    key = models.CharField(max_length=255)
    widget_type = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    config = models.JSONField(default=dict, blank=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position', 'created_at']
        unique_together = [('dashboard', 'key')]

    def __str__(self):
        return f"{self.dashboard.slug}:{self.key}"
