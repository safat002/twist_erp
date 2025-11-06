from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.companies.models import Company, CompanyGroup
from apps.users.models import User


class ModuleFeatureToggle(models.Model):
    """
    Feature toggle for controlling module and feature availability.

    Supports multi-tenant scoping (Global, Company Group, Company) with
    hierarchical resolution (Company overrides Group overrides Global).
    """

    # Feature Identification
    module_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Module identifier (e.g., 'finance', 'hr', 'inventory')"
    )
    feature_key = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Feature identifier (e.g., 'journal_vouchers', 'sales_orders'). Use 'module' for entire module."
    )
    feature_name = models.CharField(
        max_length=255,
        help_text="Human-readable feature name"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of what this feature does"
    )
    help_text = models.TextField(
        blank=True,
        help_text="Help text for end users"
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text="Icon identifier (e.g., 'mdi-finance', 'fa-users')"
    )

    # Status & Visibility
    STATUS_CHOICES = [
        ('enabled', 'Enabled'),
        ('disabled', 'Disabled'),
        ('beta', 'Beta'),
        ('deprecated', 'Deprecated'),
        ('coming_soon', 'Coming Soon'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='enabled',
        help_text="Feature status"
    )
    is_enabled = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether the feature is currently enabled"
    )
    is_visible = models.BooleanField(
        default=True,
        help_text="Whether the feature appears in menus (even if disabled)"
    )

    # Scoping (Multi-tenancy support)
    SCOPE_CHOICES = [
        ('GLOBAL', 'Global (All Companies)'),
        ('GROUP', 'Company Group'),
        ('COMPANY', 'Specific Company'),
    ]
    scope_type = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        default='GLOBAL',
        db_index=True,
        help_text="Scope of this feature toggle"
    )
    company_group = models.ForeignKey(
        CompanyGroup,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='feature_toggles',
        help_text="Company group (required if scope_type=GROUP)"
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='feature_toggles',
        help_text="Company (required if scope_type=COMPANY)"
    )

    # Configuration (Feature-specific settings)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Feature-specific configuration parameters (JSON)"
    )

    # Dependencies
    depends_on = models.JSONField(
        default=list,
        blank=True,
        help_text="List of required feature keys (e.g., ['finance.accounts', 'inventory.products'])"
    )

    # Priority & Ordering
    priority = models.IntegerField(
        default=0,
        help_text="Display priority (higher = shown first)"
    )

    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_feature_toggles'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_feature_toggles'
    )

    class Meta:
        db_table = 'admin_feature_toggles'
        verbose_name = 'Feature Toggle'
        verbose_name_plural = 'Feature Toggles'
        ordering = ['-priority', 'module_name', 'feature_key']
        unique_together = [
            ('module_name', 'feature_key', 'scope_type', 'company_group', 'company')
        ]
        indexes = [
            models.Index(fields=['module_name', 'feature_key', 'scope_type']),
            models.Index(fields=['is_enabled', 'scope_type']),
            models.Index(fields=['company_group', 'is_enabled']),
            models.Index(fields=['company', 'is_enabled']),
        ]

    def __str__(self):
        scope = f"{self.scope_type}"
        if self.company:
            scope = f"{self.company.code}"
        elif self.company_group:
            scope = f"Group:{self.company_group.name}"
        return f"{self.module_name}.{self.feature_key} ({scope})"

    def clean(self):
        """Validate model constraints."""
        # Validate scope relationships
        if self.scope_type == 'COMPANY' and not self.company:
            raise ValidationError("Company is required when scope_type is COMPANY")
        if self.scope_type == 'GROUP' and not self.company_group:
            raise ValidationError("Company Group is required when scope_type is GROUP")
        if self.scope_type == 'GLOBAL' and (self.company or self.company_group):
            raise ValidationError("Company and Company Group must be null when scope_type is GLOBAL")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def full_key(self):
        """Return the fully qualified feature key."""
        return f"{self.module_name}.{self.feature_key}"

    @property
    def is_module_toggle(self):
        """Check if this is a module-level toggle (not a specific feature)."""
        return self.feature_key == 'module'


class FeatureAuditLog(models.Model):
    """
    Audit log for feature toggle changes.
    """
    feature_toggle = models.ForeignKey(
        ModuleFeatureToggle,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )

    ACTION_CHOICES = [
        ('created', 'Created'),
        ('enabled', 'Enabled'),
        ('disabled', 'Disabled'),
        ('updated', 'Updated'),
        ('deleted', 'Deleted'),
    ]
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)

    # Change tracking
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    # Actor
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='feature_audit_logs'
    )

    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_feature_audit_logs'
        verbose_name = 'Feature Audit Log'
        verbose_name_plural = 'Feature Audit Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['feature_toggle', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.action} - {self.feature_toggle} by {self.user} at {self.timestamp}"
