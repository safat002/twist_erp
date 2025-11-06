# Feature Toggle System - Implementation Plan

## Document Information
- **Created:** 2025-11-01
- **Version:** 1.0
- **Author:** System Architecture Team
- **Status:** Implementation Ready

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Database Schema](#database-schema)
4. [Backend Implementation](#backend-implementation)
5. [Frontend Implementation](#frontend-implementation)
6. [API Specification](#api-specification)
7. [Integration Points](#integration-points)
8. [Migration Strategy](#migration-strategy)
9. [Testing Strategy](#testing-strategy)
10. [Deployment Plan](#deployment-plan)
11. [Rollback Plan](#rollback-plan)

---

## Executive Summary

### Objective
Implement a centralized feature toggle system that allows administrators to enable/disable modules and features through the Django admin panel, with real-time propagation to the frontend.

### Key Benefits
- **Control:** Fine-grained control over feature availability
- **Multi-tenancy:** Support for Global, Company Group, and Company-level toggles
- **Performance:** Cached feature flags for optimal performance
- **Security:** Integration with existing permission system
- **Flexibility:** Phased rollout and beta testing capabilities

### Implementation Phases
- **Phase 1 (MVP):** 2-3 weeks - Module-level toggles, global scope
- **Phase 2 (Enhanced):** 2-3 weeks - Feature-level toggles, multi-tenant scoping
- **Phase 3 (Advanced):** 3-4 weeks - Dependencies, audit trail, advanced UX

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Django Admin Panel                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ModuleFeatureToggle Admin                          │   │
│  │  - Create/Edit/Delete toggles                       │   │
│  │  - Bulk enable/disable                              │   │
│  │  - Scope management                                 │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend Services                          │
│  ┌──────────────────────┐  ┌──────────────────────────┐    │
│  │ FeatureService       │  │ Cache Layer (Redis)      │    │
│  │ - get_features()     │◄─┤ - Feature cache          │    │
│  │ - is_enabled()       │  │ - Invalidation           │    │
│  │ - resolve_scope()    │  │ - TTL: 5 minutes         │    │
│  └──────────────────────┘  └──────────────────────────┘    │
│  ┌──────────────────────┐  ┌──────────────────────────┐    │
│  │ Database (Postgres)  │  │ Permission Integration   │    │
│  │ - ModuleFeatureToggle│  │ - Feature + Permission   │    │
│  │ - Audit trail        │  │ - Combined checks        │    │
│  └──────────────────────┘  └──────────────────────────┘    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼ REST API
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                          │
│  ┌──────────────────────┐  ┌──────────────────────────┐    │
│  │ FeatureContext       │  │ Route Guards             │    │
│  │ - Load on auth       │  │ - Conditional rendering  │    │
│  │ - Cache in memory    │  │ - 404 for disabled       │    │
│  │ - useFeatures()      │  │                          │    │
│  └──────────────────────┘  └──────────────────────────┘    │
│  ┌──────────────────────┐  ┌──────────────────────────┐    │
│  │ Dynamic Menu         │  │ Feature-aware Components │    │
│  │ - Filter by features │  │ - Conditional UI         │    │
│  │ - Hide disabled      │  │ - Degraded states        │    │
│  └──────────────────────┘  └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. Admin changes feature toggle in Django Admin
   ↓
2. Signal triggers cache invalidation
   ↓
3. Next frontend request fetches updated features via API
   ↓
4. FeatureContext updates state
   ↓
5. React components re-render with new feature availability
```

---

## Database Schema

### Models Overview

```
ModuleFeatureToggle (Primary model)
├── Feature Identification (module, key, name)
├── Status & Visibility (is_enabled, is_visible, status)
├── Scoping (scope_type, company_group, company)
├── Configuration (config JSON)
├── Dependencies (depends_on JSON)
├── Metadata (description, help_text, icon)
└── Audit (created_at, updated_at, updated_by)

FeatureAuditLog (Audit trail)
├── Toggle reference
├── Action (enabled, disabled, created, deleted)
├── Actor (user)
├── Context (old_value, new_value)
└── Timestamp
```

### Detailed Model Code

#### 1. ModuleFeatureToggle Model

**File:** `backend/apps/admin_settings/models.py`

```python
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

        # Validate dependencies
        if self.is_enabled and self.depends_on:
            # Check that all dependencies are enabled
            # Note: This is a simplified check; real implementation needs context
            pass

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
```

#### 2. Database Migration

**File:** `backend/apps/admin_settings/migrations/0001_initial.py`

```python
# Generated migration - run: python manage.py makemigrations admin_settings

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('companies', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ModuleFeatureToggle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('module_name', models.CharField(db_index=True, help_text="Module identifier (e.g., 'finance', 'hr', 'inventory')", max_length=100)),
                ('feature_key', models.CharField(db_index=True, help_text="Feature identifier (e.g., 'journal_vouchers', 'sales_orders'). Use 'module' for entire module.", max_length=100)),
                ('feature_name', models.CharField(help_text='Human-readable feature name', max_length=255)),
                ('description', models.TextField(blank=True, help_text='Detailed description of what this feature does')),
                ('help_text', models.TextField(blank=True, help_text='Help text for end users')),
                ('icon', models.CharField(blank=True, help_text="Icon identifier (e.g., 'mdi-finance', 'fa-users')", max_length=100)),
                ('status', models.CharField(choices=[('enabled', 'Enabled'), ('disabled', 'Disabled'), ('beta', 'Beta'), ('deprecated', 'Deprecated'), ('coming_soon', 'Coming Soon')], default='enabled', help_text='Feature status', max_length=20)),
                ('is_enabled', models.BooleanField(db_index=True, default=True, help_text='Whether the feature is currently enabled')),
                ('is_visible', models.BooleanField(default=True, help_text='Whether the feature appears in menus (even if disabled)')),
                ('scope_type', models.CharField(choices=[('GLOBAL', 'Global (All Companies)'), ('GROUP', 'Company Group'), ('COMPANY', 'Specific Company')], db_index=True, default='GLOBAL', help_text='Scope of this feature toggle', max_length=20)),
                ('config', models.JSONField(blank=True, default=dict, help_text='Feature-specific configuration parameters (JSON)')),
                ('depends_on', models.JSONField(blank=True, default=list, help_text="List of required feature keys (e.g., ['finance.accounts', 'inventory.products'])")),
                ('priority', models.IntegerField(default=0, help_text='Display priority (higher = shown first)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(blank=True, help_text='Company (required if scope_type=COMPANY)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='feature_toggles', to='companies.company')),
                ('company_group', models.ForeignKey(blank=True, help_text='Company group (required if scope_type=GROUP)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='feature_toggles', to='companies.companygroup')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_feature_toggles', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_feature_toggles', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Feature Toggle',
                'verbose_name_plural': 'Feature Toggles',
                'db_table': 'admin_feature_toggles',
                'ordering': ['-priority', 'module_name', 'feature_key'],
            },
        ),
        migrations.CreateModel(
            name='FeatureAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('created', 'Created'), ('enabled', 'Enabled'), ('disabled', 'Disabled'), ('updated', 'Updated'), ('deleted', 'Deleted')], max_length=20)),
                ('old_value', models.JSONField(blank=True, null=True)),
                ('new_value', models.JSONField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('feature_toggle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='admin_settings.modulefeaturetoggle')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='feature_audit_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Feature Audit Log',
                'verbose_name_plural': 'Feature Audit Logs',
                'db_table': 'admin_feature_audit_logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddConstraint(
            model_name='modulefeaturetoggle',
            constraint=models.UniqueConstraint(fields=('module_name', 'feature_key', 'scope_type', 'company_group', 'company'), name='unique_feature_scope'),
        ),
        migrations.AddIndex(
            model_name='modulefeaturetoggle',
            index=models.Index(fields=['module_name', 'feature_key', 'scope_type'], name='admin_featu_module__idx'),
        ),
        migrations.AddIndex(
            model_name='modulefeaturetoggle',
            index=models.Index(fields=['is_enabled', 'scope_type'], name='admin_featu_is_enab_idx'),
        ),
        migrations.AddIndex(
            model_name='featureauditlog',
            index=models.Index(fields=['feature_toggle', '-timestamp'], name='admin_featu_feature_idx'),
        ),
    ]
```

---

## Backend Implementation

### 1. Django Admin Configuration

**File:** `backend/apps/admin_settings/admin.py`

```python
from django.contrib import admin, messages
from django.db.models import Q, Count
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from .models import ModuleFeatureToggle, FeatureAuditLog
from .services import FeatureService


class FeatureAuditLogInline(admin.TabularInline):
    model = FeatureAuditLog
    extra = 0
    can_delete = False
    readonly_fields = ['action', 'old_value', 'new_value', 'user', 'timestamp', 'ip_address']
    fields = ['timestamp', 'action', 'user', 'old_value', 'new_value']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ModuleFeatureToggle)
class ModuleFeatureToggleAdmin(admin.ModelAdmin):
    list_display = [
        'feature_display',
        'status_badge',
        'scope_display',
        'visibility_display',
        'quick_toggle',
        'updated_display'
    ]
    list_filter = [
        'scope_type',
        'is_enabled',
        'is_visible',
        'status',
        'module_name',
        'company_group',
    ]
    search_fields = [
        'module_name',
        'feature_key',
        'feature_name',
        'description',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'created_by',
        'updated_by',
        'full_key',
    ]

    fieldsets = (
        ('Feature Identification', {
            'fields': (
                'module_name',
                'feature_key',
                'feature_name',
                'full_key',
                'description',
                'help_text',
                'icon',
            )
        }),
        ('Status & Visibility', {
            'fields': (
                'status',
                'is_enabled',
                'is_visible',
            ),
            'classes': ('wide',),
        }),
        ('Scope (Multi-tenancy)', {
            'fields': (
                'scope_type',
                'company_group',
                'company',
            ),
            'description': 'Define where this feature toggle applies. Company-level settings override Group-level, which override Global.',
        }),
        ('Configuration & Dependencies', {
            'fields': (
                'config',
                'depends_on',
                'priority',
            ),
            'classes': ('collapse',),
        }),
        ('Audit Information', {
            'fields': (
                'created_at',
                'created_by',
                'updated_at',
                'updated_by',
            ),
            'classes': ('collapse',),
        }),
    )

    inlines = [FeatureAuditLogInline]

    actions = [
        'enable_features',
        'disable_features',
        'make_visible',
        'make_hidden',
    ]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'bulk-create/',
                self.admin_site.admin_view(self.bulk_create_view),
                name='admin_settings_modulefeaturetoggle_bulk_create',
            ),
            path(
                '<int:pk>/toggle/',
                self.admin_site.admin_view(self.quick_toggle_view),
                name='admin_settings_modulefeaturetoggle_toggle',
            ),
        ]
        return custom_urls + urls

    def feature_display(self, obj):
        """Display feature with icon."""
        icon_html = ""
        if obj.icon:
            icon_html = f'<i class="{obj.icon}" style="margin-right: 5px;"></i>'

        return format_html(
            '{}<strong>{}</strong><br/>'
            '<small style="color: #666;">{}.{}</small>',
            icon_html,
            obj.feature_name,
            obj.module_name,
            obj.feature_key
        )
    feature_display.short_description = 'Feature'

    def status_badge(self, obj):
        """Display status as a colored badge."""
        colors = {
            'enabled': '#28a745',
            'disabled': '#dc3545',
            'beta': '#ffc107',
            'deprecated': '#6c757d',
            'coming_soon': '#17a2b8',
        }
        color = colors.get(obj.status, '#6c757d')

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def scope_display(self, obj):
        """Display scope information."""
        if obj.scope_type == 'GLOBAL':
            return format_html('<span style="color: #007bff;">🌐 Global</span>')
        elif obj.scope_type == 'GROUP' and obj.company_group:
            return format_html(
                '<span style="color: #6f42c1;">👥 {}</span>',
                obj.company_group.name
            )
        elif obj.scope_type == 'COMPANY' and obj.company:
            return format_html(
                '<span style="color: #fd7e14;">🏢 {}</span>',
                obj.company.name
            )
        return '—'
    scope_display.short_description = 'Scope'

    def visibility_display(self, obj):
        """Display visibility status."""
        if obj.is_visible:
            return format_html('<span style="color: #28a745;">👁️ Visible</span>')
        else:
            return format_html('<span style="color: #6c757d;">🚫 Hidden</span>')
    visibility_display.short_description = 'Visibility'

    def quick_toggle(self, obj):
        """Quick enable/disable toggle button."""
        url = reverse('admin:admin_settings_modulefeaturetoggle_toggle', args=[obj.pk])
        if obj.is_enabled:
            return format_html(
                '<a class="button" href="{}" style="background-color: #28a745; color: white; '
                'padding: 5px 10px; text-decoration: none; border-radius: 3px;">✓ Enabled</a>',
                url
            )
        else:
            return format_html(
                '<a class="button" href="{}" style="background-color: #dc3545; color: white; '
                'padding: 5px 10px; text-decoration: none; border-radius: 3px;">✗ Disabled</a>',
                url
            )
    quick_toggle.short_description = 'Quick Toggle'

    def updated_display(self, obj):
        """Display last update information."""
        if obj.updated_by:
            return format_html(
                '<small>{}<br/>by {}</small>',
                obj.updated_at.strftime('%Y-%m-%d %H:%M'),
                obj.updated_by.username
            )
        return format_html('<small>{}</small>', obj.updated_at.strftime('%Y-%m-%d %H:%M'))
    updated_display.short_description = 'Last Updated'

    def save_model(self, request, obj, form, change):
        """Track who created/updated the feature toggle."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user

        # Create audit log
        old_value = None
        if change:
            old_obj = ModuleFeatureToggle.objects.get(pk=obj.pk)
            old_value = {
                'is_enabled': old_obj.is_enabled,
                'is_visible': old_obj.is_visible,
                'status': old_obj.status,
            }

        super().save_model(request, obj, form, change)

        # Log the change
        action = 'created' if not change else 'updated'
        if change and old_value and old_value['is_enabled'] != obj.is_enabled:
            action = 'enabled' if obj.is_enabled else 'disabled'

        FeatureAuditLog.objects.create(
            feature_toggle=obj,
            action=action,
            old_value=old_value,
            new_value={
                'is_enabled': obj.is_enabled,
                'is_visible': obj.is_visible,
                'status': obj.status,
            },
            user=request.user,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
        )

        # Invalidate cache
        FeatureService.invalidate_cache(obj.scope_type, obj.company_group, obj.company)

    def delete_model(self, request, obj):
        """Log deletion."""
        FeatureAuditLog.objects.create(
            feature_toggle=obj,
            action='deleted',
            old_value={
                'is_enabled': obj.is_enabled,
                'full_key': obj.full_key,
            },
            user=request.user,
            ip_address=self.get_client_ip(request),
        )

        # Invalidate cache
        FeatureService.invalidate_cache(obj.scope_type, obj.company_group, obj.company)

        super().delete_model(request, obj)

    @staticmethod
    def get_client_ip(request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    # Bulk Actions
    def enable_features(self, request, queryset):
        """Bulk enable features."""
        count = queryset.update(is_enabled=True, updated_by=request.user)

        # Log and invalidate cache
        for obj in queryset:
            FeatureAuditLog.objects.create(
                feature_toggle=obj,
                action='enabled',
                user=request.user,
                ip_address=self.get_client_ip(request),
            )
            FeatureService.invalidate_cache(obj.scope_type, obj.company_group, obj.company)

        self.message_user(request, f'{count} feature(s) enabled successfully.', messages.SUCCESS)
    enable_features.short_description = '✓ Enable selected features'

    def disable_features(self, request, queryset):
        """Bulk disable features."""
        count = queryset.update(is_enabled=False, updated_by=request.user)

        # Log and invalidate cache
        for obj in queryset:
            FeatureAuditLog.objects.create(
                feature_toggle=obj,
                action='disabled',
                user=request.user,
                ip_address=self.get_client_ip(request),
            )
            FeatureService.invalidate_cache(obj.scope_type, obj.company_group, obj.company)

        self.message_user(request, f'{count} feature(s) disabled successfully.', messages.WARNING)
    disable_features.short_description = '✗ Disable selected features'

    def make_visible(self, request, queryset):
        """Bulk make visible."""
        count = queryset.update(is_visible=True, updated_by=request.user)
        self.message_user(request, f'{count} feature(s) made visible.', messages.SUCCESS)
    make_visible.short_description = '👁️ Make visible'

    def make_hidden(self, request, queryset):
        """Bulk hide features."""
        count = queryset.update(is_visible=False, updated_by=request.user)
        self.message_user(request, f'{count} feature(s) hidden.', messages.SUCCESS)
    make_hidden.short_description = '🚫 Hide from menu'

    # Custom Views
    def quick_toggle_view(self, request, pk):
        """Quick toggle feature enabled/disabled."""
        obj = self.get_object(request, pk)
        if obj:
            obj.is_enabled = not obj.is_enabled
            obj.updated_by = request.user
            obj.save()

            action = 'enabled' if obj.is_enabled else 'disabled'
            self.message_user(
                request,
                f'Feature "{obj.feature_name}" {action} successfully.',
                messages.SUCCESS if obj.is_enabled else messages.WARNING
            )

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '../'))

    def bulk_create_view(self, request):
        """View for bulk creating default feature toggles."""
        if request.method == 'POST':
            # Import default features
            from .default_features import DEFAULT_FEATURES

            scope_type = request.POST.get('scope_type', 'GLOBAL')
            company_group_id = request.POST.get('company_group')
            company_id = request.POST.get('company')

            created_count = 0
            for feature_data in DEFAULT_FEATURES:
                defaults = {
                    'feature_name': feature_data['name'],
                    'description': feature_data.get('description', ''),
                    'icon': feature_data.get('icon', ''),
                    'is_enabled': feature_data.get('enabled', True),
                    'is_visible': feature_data.get('visible', True),
                    'status': feature_data.get('status', 'enabled'),
                    'depends_on': feature_data.get('depends_on', []),
                    'priority': feature_data.get('priority', 0),
                    'scope_type': scope_type,
                    'created_by': request.user,
                    'updated_by': request.user,
                }

                if scope_type == 'GROUP' and company_group_id:
                    defaults['company_group_id'] = company_group_id
                elif scope_type == 'COMPANY' and company_id:
                    defaults['company_id'] = company_id

                obj, created = ModuleFeatureToggle.objects.get_or_create(
                    module_name=feature_data['module'],
                    feature_key=feature_data['key'],
                    scope_type=scope_type,
                    company_group_id=company_group_id if scope_type == 'GROUP' else None,
                    company_id=company_id if scope_type == 'COMPANY' else None,
                    defaults=defaults
                )

                if created:
                    created_count += 1

            self.message_user(
                request,
                f'{created_count} feature toggle(s) created successfully.',
                messages.SUCCESS
            )
            return redirect('..')

        # GET request - show form
        from apps.companies.models import CompanyGroup, Company

        context = {
            **self.admin_site.each_context(request),
            'title': 'Bulk Create Feature Toggles',
            'company_groups': CompanyGroup.objects.all(),
            'companies': Company.objects.all(),
        }

        return render(request, 'admin/admin_settings/bulk_create_features.html', context)


@admin.register(FeatureAuditLog)
class FeatureAuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'feature_toggle', 'action', 'user', 'ip_address']
    list_filter = ['action', 'timestamp', 'user']
    search_fields = ['feature_toggle__feature_name', 'feature_toggle__module_name', 'user__username']
    readonly_fields = ['feature_toggle', 'action', 'old_value', 'new_value', 'user', 'ip_address', 'user_agent', 'timestamp']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
```

### 2. Feature Service Layer

**File:** `backend/apps/admin_settings/services.py`

```python
from typing import Dict, Optional, List, Set
from django.core.cache import cache
from django.db.models import Q
from apps.companies.models import Company, CompanyGroup
from .models import ModuleFeatureToggle


class FeatureService:
    """
    Service layer for feature toggle operations.

    Handles feature resolution, caching, and scope hierarchy.
    """

    CACHE_TTL = 300  # 5 minutes
    CACHE_PREFIX = 'features'

    @classmethod
    def get_cache_key(cls, scope_type: str, company_group_id: Optional[int] = None,
                     company_id: Optional[int] = None) -> str:
        """Generate cache key for feature toggles."""
        if scope_type == 'COMPANY' and company_id:
            return f"{cls.CACHE_PREFIX}:company:{company_id}"
        elif scope_type == 'GROUP' and company_group_id:
            return f"{cls.CACHE_PREFIX}:group:{company_group_id}"
        else:
            return f"{cls.CACHE_PREFIX}:global"

    @classmethod
    def invalidate_cache(cls, scope_type: str = None, company_group=None, company=None):
        """Invalidate feature cache for specific scope."""
        if scope_type == 'COMPANY' and company:
            cache.delete(cls.get_cache_key('COMPANY', company_id=company.id))
            # Also invalidate group and global caches as they may be used in resolution
            if company.company_group:
                cache.delete(cls.get_cache_key('GROUP', company_group_id=company.company_group.id))
        elif scope_type == 'GROUP' and company_group:
            cache.delete(cls.get_cache_key('GROUP', company_group_id=company_group.id))

        # Always invalidate global cache
        cache.delete(cls.get_cache_key('GLOBAL'))

    @classmethod
    def get_features_for_company(cls, company: Company) -> Dict[str, Dict]:
        """
        Get all resolved features for a company.

        Resolution order (later overrides earlier):
        1. Global features
        2. Company Group features
        3. Company-specific features

        Returns:
            Dict with feature keys as keys and feature data as values
            Example: {
                'finance.module': {'enabled': True, 'visible': True, 'status': 'enabled', ...},
                'finance.journal_vouchers': {'enabled': True, ...},
            }
        """
        cache_key = cls.get_cache_key('COMPANY', company_id=company.id)
        cached = cache.get(cache_key)

        if cached is not None:
            return cached

        # Build feature map with hierarchical resolution
        features = {}

        # 1. Global features
        global_features = ModuleFeatureToggle.objects.filter(
            scope_type='GLOBAL',
            is_enabled=True
        ).select_related('created_by', 'updated_by')

        for feature in global_features:
            features[feature.full_key] = cls._serialize_feature(feature)

        # 2. Company Group features (override global)
        if company.company_group:
            group_features = ModuleFeatureToggle.objects.filter(
                scope_type='GROUP',
                company_group=company.company_group,
            ).select_related('created_by', 'updated_by')

            for feature in group_features:
                # Group feature overrides global
                if feature.is_enabled:
                    features[feature.full_key] = cls._serialize_feature(feature)
                else:
                    # If explicitly disabled at group level, remove it
                    features.pop(feature.full_key, None)

        # 3. Company-specific features (override all)
        company_features = ModuleFeatureToggle.objects.filter(
            scope_type='COMPANY',
            company=company,
        ).select_related('created_by', 'updated_by')

        for feature in company_features:
            if feature.is_enabled:
                features[feature.full_key] = cls._serialize_feature(feature)
            else:
                # If explicitly disabled at company level, remove it
                features.pop(feature.full_key, None)

        # Cache the result
        cache.set(cache_key, features, cls.CACHE_TTL)

        return features

    @classmethod
    def get_global_features(cls) -> Dict[str, Dict]:
        """Get all global features."""
        cache_key = cls.get_cache_key('GLOBAL')
        cached = cache.get(cache_key)

        if cached is not None:
            return cached

        features = {}
        global_features = ModuleFeatureToggle.objects.filter(
            scope_type='GLOBAL',
            is_enabled=True
        ).select_related('created_by', 'updated_by')

        for feature in global_features:
            features[feature.full_key] = cls._serialize_feature(feature)

        cache.set(cache_key, features, cls.CACHE_TTL)
        return features

    @classmethod
    def is_feature_enabled(cls, feature_key: str, company: Optional[Company] = None) -> bool:
        """
        Check if a specific feature is enabled.

        Args:
            feature_key: Full feature key (e.g., 'finance.journal_vouchers')
            company: Company context (optional)

        Returns:
            True if feature is enabled, False otherwise
        """
        if company:
            features = cls.get_features_for_company(company)
        else:
            features = cls.get_global_features()

        return feature_key in features and features[feature_key].get('enabled', False)

    @classmethod
    def is_feature_visible(cls, feature_key: str, company: Optional[Company] = None) -> bool:
        """Check if a feature is visible in menus."""
        if company:
            features = cls.get_features_for_company(company)
        else:
            features = cls.get_global_features()

        return feature_key in features and features[feature_key].get('visible', False)

    @classmethod
    def get_enabled_modules(cls, company: Optional[Company] = None) -> Set[str]:
        """Get set of enabled module names."""
        if company:
            features = cls.get_features_for_company(company)
        else:
            features = cls.get_global_features()

        modules = set()
        for key, data in features.items():
            if data.get('enabled') and '.module' in key:
                module_name = key.split('.')[0]
                modules.add(module_name)

        return modules

    @classmethod
    def check_dependencies(cls, feature_key: str, company: Optional[Company] = None) -> Dict[str, bool]:
        """
        Check if all dependencies for a feature are met.

        Returns:
            Dict with dependency keys as keys and their status as values
        """
        if company:
            features = cls.get_features_for_company(company)
        else:
            features = cls.get_global_features()

        feature_data = features.get(feature_key)
        if not feature_data:
            return {}

        dependencies = feature_data.get('depends_on', [])
        result = {}

        for dep_key in dependencies:
            result[dep_key] = cls.is_feature_enabled(dep_key, company)

        return result

    @classmethod
    def _serialize_feature(cls, feature: ModuleFeatureToggle) -> Dict:
        """Serialize feature toggle to dictionary."""
        return {
            'enabled': feature.is_enabled,
            'visible': feature.is_visible,
            'status': feature.status,
            'name': feature.feature_name,
            'description': feature.description,
            'help_text': feature.help_text,
            'icon': feature.icon,
            'config': feature.config,
            'depends_on': feature.depends_on,
            'priority': feature.priority,
            'scope_type': feature.scope_type,
        }
```

### 3. API Serializers

**File:** `backend/apps/admin_settings/serializers.py`

```python
from rest_framework import serializers
from .models import ModuleFeatureToggle, FeatureAuditLog


class ModuleFeatureToggleSerializer(serializers.ModelSerializer):
    """Serializer for feature toggles."""

    full_key = serializers.ReadOnlyField()
    is_module_toggle = serializers.ReadOnlyField()

    class Meta:
        model = ModuleFeatureToggle
        fields = [
            'id',
            'module_name',
            'feature_key',
            'full_key',
            'feature_name',
            'description',
            'help_text',
            'icon',
            'status',
            'is_enabled',
            'is_visible',
            'is_module_toggle',
            'scope_type',
            'config',
            'depends_on',
            'priority',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class FeatureMapSerializer(serializers.Serializer):
    """Serializer for feature map (frontend consumption)."""

    features = serializers.DictField(
        child=serializers.DictField(),
        help_text="Map of feature keys to feature data"
    )
    modules = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of enabled module names"
    )
    scope = serializers.CharField(help_text="Scope type applied")
    cached = serializers.BooleanField(help_text="Whether data came from cache")


class FeatureAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit logs."""

    feature_name = serializers.CharField(source='feature_toggle.feature_name', read_only=True)
    feature_key = serializers.CharField(source='feature_toggle.full_key', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = FeatureAuditLog
        fields = [
            'id',
            'feature_name',
            'feature_key',
            'action',
            'old_value',
            'new_value',
            'username',
            'ip_address',
            'timestamp',
        ]
```

### 4. API Views

**File:** `backend/apps/admin_settings/views.py`

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.core.cache import cache
from .services import FeatureService
from .serializers import FeatureMapSerializer, ModuleFeatureToggleSerializer, FeatureAuditLogSerializer
from .models import ModuleFeatureToggle, FeatureAuditLog


class FeatureFlagsView(APIView):
    """
    API endpoint for fetching feature flags.

    GET /api/v1/admin-settings/features/
    Returns all enabled features for the current user's company.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get feature flags for current company."""
        company = getattr(request, 'company', None)

        if not company:
            # No company context - return global features only
            features = FeatureService.get_global_features()
            scope = 'GLOBAL'
        else:
            # Get resolved features for company
            features = FeatureService.get_features_for_company(company)
            scope = f'COMPANY:{company.code}'

        # Get enabled modules
        modules = list(FeatureService.get_enabled_modules(company))

        # Check if from cache
        cache_key = FeatureService.get_cache_key(
            'COMPANY' if company else 'GLOBAL',
            company_id=company.id if company else None
        )
        cached = cache.get(cache_key) is not None

        data = {
            'features': features,
            'modules': modules,
            'scope': scope,
            'cached': cached,
        }

        serializer = FeatureMapSerializer(data)
        return Response(serializer.data)


class FeatureCheckView(APIView):
    """
    Check if a specific feature is enabled.

    GET /api/v1/admin-settings/features/check/?key=finance.journal_vouchers
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Check feature status."""
        feature_key = request.query_params.get('key')

        if not feature_key:
            return Response(
                {'error': 'Feature key is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        company = getattr(request, 'company', None)

        enabled = FeatureService.is_feature_enabled(feature_key, company)
        visible = FeatureService.is_feature_visible(feature_key, company)
        dependencies = FeatureService.check_dependencies(feature_key, company)

        return Response({
            'feature_key': feature_key,
            'enabled': enabled,
            'visible': visible,
            'dependencies': dependencies,
            'dependencies_met': all(dependencies.values()) if dependencies else True,
        })


class FeatureListView(APIView):
    """
    List all feature toggles (admin only).

    GET /api/v1/admin-settings/features/list/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List all feature toggles."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = ModuleFeatureToggle.objects.all().order_by('-priority', 'module_name', 'feature_key')

        # Apply filters
        module = request.query_params.get('module')
        if module:
            queryset = queryset.filter(module_name=module)

        scope_type = request.query_params.get('scope')
        if scope_type:
            queryset = queryset.filter(scope_type=scope_type)

        enabled = request.query_params.get('enabled')
        if enabled is not None:
            queryset = queryset.filter(is_enabled=enabled.lower() == 'true')

        serializer = ModuleFeatureToggleSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'features': serializer.data
        })


class FeatureAuditLogView(APIView):
    """
    View feature audit logs.

    GET /api/v1/admin-settings/features/audit/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get audit logs."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = FeatureAuditLog.objects.select_related(
            'feature_toggle', 'user'
        ).order_by('-timestamp')[:100]  # Last 100 entries

        serializer = FeatureAuditLogSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'logs': serializer.data
        })


class CacheInvalidationView(APIView):
    """
    Invalidate feature cache (admin only).

    POST /api/v1/admin-settings/features/invalidate-cache/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Invalidate cache."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Invalidate all caches
        cache.delete_pattern(f"{FeatureService.CACHE_PREFIX}:*")

        return Response({
            'message': 'Feature cache invalidated successfully'
        })
```

### 5. URL Configuration

**File:** `backend/apps/admin_settings/urls.py`

```python
from django.urls import path
from .views import (
    FeatureFlagsView,
    FeatureCheckView,
    FeatureListView,
    FeatureAuditLogView,
    CacheInvalidationView,
)

app_name = 'admin_settings'

urlpatterns = [
    # Public endpoints (authenticated users)
    path('features/', FeatureFlagsView.as_view(), name='feature_flags'),
    path('features/check/', FeatureCheckView.as_view(), name='feature_check'),

    # Admin-only endpoints
    path('features/list/', FeatureListView.as_view(), name='feature_list'),
    path('features/audit/', FeatureAuditLogView.as_view(), name='feature_audit'),
    path('features/invalidate-cache/', CacheInvalidationView.as_view(), name='invalidate_cache'),
]
```

**Register in API Gateway:** `backend/apps/api_gateway/urls.py`

```python
# Add to existing urlpatterns
path('v1/admin-settings/', include('apps.admin_settings.urls')),
```

### 6. Default Features Configuration

**File:** `backend/apps/admin_settings/default_features.py`

```python
"""
Default feature toggles to be created during initial setup.

This file defines all available features across all modules.
"""

DEFAULT_FEATURES = [
    # ========== CORE MODULES ==========

    # Dashboard Module
    {
        'module': 'dashboard',
        'key': 'module',
        'name': 'Dashboard Module',
        'description': 'Main dashboard and analytics overview',
        'icon': 'mdi-view-dashboard',
        'enabled': True,
        'visible': True,
        'status': 'enabled',
        'priority': 100,
    },

    # ========== FINANCE MODULE ==========

    {
        'module': 'finance',
        'key': 'module',
        'name': 'Finance Module',
        'description': 'Complete finance and accounting module',
        'icon': 'mdi-finance',
        'enabled': True,
        'visible': True,
        'status': 'enabled',
        'priority': 90,
    },
    {
        'module': 'finance',
        'key': 'chart_of_accounts',
        'name': 'Chart of Accounts',
        'description': 'Manage chart of accounts and account structure',
        'icon': 'mdi-file-tree',
        'enabled': True,
        'visible': True,
        'depends_on': ['finance.module'],
        'priority': 85,
    },
    {
        'module': 'finance',
        'key': 'journal_vouchers',
        'name': 'Journal Vouchers',
        'description': 'Create and manage journal vouchers',
        'icon': 'mdi-book-open-variant',
        'enabled': True,
        'visible': True,
        'depends_on': ['finance.module', 'finance.chart_of_accounts'],
        'priority': 84,
    },
    {
        'module': 'finance',
        'key': 'invoicing',
        'name': 'Invoicing',
        'description': 'Customer and vendor invoicing',
        'icon': 'mdi-receipt',
        'enabled': True,
        'visible': True,
        'depends_on': ['finance.module'],
        'priority': 83,
    },
    {
        'module': 'finance',
        'key': 'payments',
        'name': 'Payments',
        'description': 'Manage payments and receipts',
        'icon': 'mdi-cash-multiple',
        'enabled': True,
        'visible': True,
        'depends_on': ['finance.module'],
        'priority': 82,
    },

    # ========== INVENTORY MODULE ==========

    {
        'module': 'inventory',
        'key': 'module',
        'name': 'Inventory Module',
        'description': 'Inventory and warehouse management',
        'icon': 'mdi-warehouse',
        'enabled': True,
        'visible': True,
        'status': 'enabled',
        'priority': 80,
    },
    {
        'module': 'inventory',
        'key': 'products',
        'name': 'Products',
        'description': 'Product master data management',
        'icon': 'mdi-package-variant',
        'enabled': True,
        'visible': True,
        'depends_on': ['inventory.module'],
        'priority': 75,
    },
    {
        'module': 'inventory',
        'key': 'warehouses',
        'name': 'Warehouses',
        'description': 'Warehouse and location management',
        'icon': 'mdi-home-city',
        'enabled': True,
        'visible': True,
        'depends_on': ['inventory.module'],
        'priority': 74,
    },
    {
        'module': 'inventory',
        'key': 'stock_movements',
        'name': 'Stock Movements',
        'description': 'Track stock transfers and adjustments',
        'icon': 'mdi-swap-horizontal',
        'enabled': True,
        'visible': True,
        'depends_on': ['inventory.module', 'inventory.products'],
        'priority': 73,
    },

    # ========== SALES MODULE ==========

    {
        'module': 'sales',
        'key': 'module',
        'name': 'Sales Module',
        'description': 'Sales and CRM functionality',
        'icon': 'mdi-cart',
        'enabled': True,
        'visible': True,
        'status': 'enabled',
        'priority': 70,
    },
    {
        'module': 'sales',
        'key': 'customers',
        'name': 'Customers',
        'description': 'Customer relationship management',
        'icon': 'mdi-account-group',
        'enabled': True,
        'visible': True,
        'depends_on': ['sales.module'],
        'priority': 65,
    },
    {
        'module': 'sales',
        'key': 'sales_orders',
        'name': 'Sales Orders',
        'description': 'Manage sales orders and quotations',
        'icon': 'mdi-file-document',
        'enabled': True,
        'visible': True,
        'depends_on': ['sales.module', 'sales.customers', 'inventory.products'],
        'priority': 64,
    },

    # ========== PROCUREMENT MODULE ==========

    {
        'module': 'procurement',
        'key': 'module',
        'name': 'Procurement Module',
        'description': 'Purchase and vendor management',
        'icon': 'mdi-shopping',
        'enabled': True,
        'visible': True,
        'status': 'enabled',
        'priority': 60,
    },
    {
        'module': 'procurement',
        'key': 'vendors',
        'name': 'Vendors',
        'description': 'Vendor master data',
        'icon': 'mdi-truck',
        'enabled': True,
        'visible': True,
        'depends_on': ['procurement.module'],
        'priority': 55,
    },
    {
        'module': 'procurement',
        'key': 'purchase_orders',
        'name': 'Purchase Orders',
        'description': 'Create and manage purchase orders',
        'icon': 'mdi-clipboard-text',
        'enabled': True,
        'visible': True,
        'depends_on': ['procurement.module', 'procurement.vendors', 'inventory.products'],
        'priority': 54,
    },

    # ========== HR MODULE ==========

    {
        'module': 'hr',
        'key': 'module',
        'name': 'HR Module',
        'description': 'Human resources management',
        'icon': 'mdi-account-multiple',
        'enabled': True,
        'visible': True,
        'status': 'enabled',
        'priority': 50,
    },
    {
        'module': 'hr',
        'key': 'employees',
        'name': 'Employees',
        'description': 'Employee master data and profiles',
        'icon': 'mdi-account-tie',
        'enabled': True,
        'visible': True,
        'depends_on': ['hr.module'],
        'priority': 45,
    },
    {
        'module': 'hr',
        'key': 'attendance',
        'name': 'Attendance',
        'description': 'Time and attendance tracking',
        'icon': 'mdi-calendar-check',
        'enabled': True,
        'visible': True,
        'depends_on': ['hr.module', 'hr.employees'],
        'priority': 44,
    },
    {
        'module': 'hr',
        'key': 'leave',
        'name': 'Leave Management',
        'description': 'Leave requests and approvals',
        'icon': 'mdi-beach',
        'enabled': True,
        'visible': True,
        'depends_on': ['hr.module', 'hr.employees'],
        'priority': 43,
    },
    {
        'module': 'hr',
        'key': 'payroll',
        'name': 'Payroll',
        'description': 'Payroll processing and management',
        'icon': 'mdi-currency-usd',
        'enabled': True,
        'visible': True,
        'depends_on': ['hr.module', 'hr.employees', 'finance.module'],
        'priority': 42,
    },

    # ========== PRODUCTION MODULE ==========

    {
        'module': 'production',
        'key': 'module',
        'name': 'Production Module',
        'description': 'Manufacturing and production management',
        'icon': 'mdi-factory',
        'enabled': True,
        'visible': True,
        'status': 'enabled',
        'priority': 40,
    },
    {
        'module': 'production',
        'key': 'bom',
        'name': 'Bill of Materials',
        'description': 'Define product BOMs and recipes',
        'icon': 'mdi-format-list-bulleted',
        'enabled': True,
        'visible': True,
        'depends_on': ['production.module', 'inventory.products'],
        'priority': 35,
    },
    {
        'module': 'production',
        'key': 'work_orders',
        'name': 'Work Orders',
        'description': 'Create and track work orders',
        'icon': 'mdi-clipboard-list',
        'enabled': True,
        'visible': True,
        'depends_on': ['production.module', 'production.bom'],
        'priority': 34,
    },

    # ========== ASSETS MODULE ==========

    {
        'module': 'assets',
        'key': 'module',
        'name': 'Assets Module',
        'description': 'Fixed asset management',
        'icon': 'mdi-office-building',
        'enabled': True,
        'visible': True,
        'status': 'enabled',
        'priority': 30,
    },

    # ========== BUDGETING MODULE ==========

    {
        'module': 'budgeting',
        'key': 'module',
        'name': 'Budgeting Module',
        'description': 'Budget planning and control',
        'icon': 'mdi-chart-line',
        'enabled': True,
        'visible': True,
        'status': 'enabled',
        'priority': 25,
    },

    # ========== PROJECTS MODULE ==========

    {
        'module': 'projects',
        'key': 'module',
        'name': 'Projects Module',
        'description': 'Project management and tracking',
        'icon': 'mdi-briefcase',
        'enabled': True,
        'visible': True,
        'status': 'enabled',
        'priority': 20,
    },

    # ========== AI & AUTOMATION ==========

    {
        'module': 'ai_companion',
        'key': 'module',
        'name': 'AI Assistant',
        'description': 'AI-powered assistance and automation',
        'icon': 'mdi-robot',
        'enabled': True,
        'visible': True,
        'status': 'beta',
        'priority': 15,
    },

    # ========== FORM BUILDER ==========

    {
        'module': 'form_builder',
        'key': 'module',
        'name': 'Form Builder',
        'description': 'Dynamic form creation and management',
        'icon': 'mdi-form-select',
        'enabled': True,
        'visible': True,
        'status': 'enabled',
        'priority': 10,
    },

    # ========== WORKFLOWS ==========

    {
        'module': 'workflows',
        'key': 'module',
        'name': 'Workflows',
        'description': 'Workflow automation and approvals',
        'icon': 'mdi-chart-timeline',
        'enabled': True,
        'visible': True,
        'status': 'enabled',
        'priority': 9,
    },

    # ========== REPORT BUILDER ==========

    {
        'module': 'report_builder',
        'key': 'module',
        'name': 'Report Builder',
        'description': 'Custom report creation',
        'icon': 'mdi-file-chart',
        'enabled': True,
        'visible': True,
        'status': 'enabled',
        'priority': 8,
    },

    # ========== TASKS ==========

    {
        'module': 'tasks',
        'key': 'module',
        'name': 'Tasks',
        'description': 'Task management and to-do lists',
        'icon': 'mdi-checkbox-marked',
        'enabled': True,
        'visible': True,
        'status': 'enabled',
        'priority': 7,
    },

    # ========== NOTIFICATIONS ==========

    {
        'module': 'notifications',
        'key': 'module',
        'name': 'Notifications',
        'description': 'System notifications and alerts',
        'icon': 'mdi-bell',
        'enabled': True,
        'visible': True,
        'status': 'enabled',
        'priority': 6,
    },
]
```

---

## Frontend Implementation

### 1. Feature Context

**File:** `frontend/src/contexts/FeatureContext.jsx`

```javascript
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { useCompany } from './CompanyContext';
import api from '../services/api';

const FeatureContext = createContext();

export const FeatureProvider = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const { currentCompany } = useCompany();

  const [features, setFeatures] = useState({});
  const [modules, setModules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastFetched, setLastFetched] = useState(null);

  const fetchFeatures = useCallback(async () => {
    if (!isAuthenticated) {
      setFeatures({});
      setModules([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.get('/admin-settings/features/');

      setFeatures(response.data.features || {});
      setModules(response.data.modules || []);
      setLastFetched(new Date());

      // Cache in localStorage with TTL
      const cacheData = {
        features: response.data.features,
        modules: response.data.modules,
        timestamp: Date.now(),
        company: currentCompany?.id,
      };
      localStorage.setItem('feature_cache', JSON.stringify(cacheData));

      console.log('Features loaded:', {
        count: Object.keys(response.data.features).length,
        modules: response.data.modules,
        scope: response.data.scope,
        cached: response.data.cached,
      });
    } catch (err) {
      console.error('Failed to fetch features:', err);
      setError(err.message);

      // Try to load from cache on error
      try {
        const cached = localStorage.getItem('feature_cache');
        if (cached) {
          const cacheData = JSON.parse(cached);
          const age = Date.now() - cacheData.timestamp;
          const maxAge = 10 * 60 * 1000; // 10 minutes

          if (age < maxAge && cacheData.company === currentCompany?.id) {
            setFeatures(cacheData.features || {});
            setModules(cacheData.modules || []);
            console.log('Using cached features (API failed)');
          }
        }
      } catch (cacheErr) {
        console.error('Failed to load cached features:', cacheErr);
      }
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, currentCompany]);

  // Fetch on auth or company change
  useEffect(() => {
    fetchFeatures();
  }, [fetchFeatures]);

  // Auto-refresh every 5 minutes
  useEffect(() => {
    if (!isAuthenticated) return;

    const interval = setInterval(() => {
      console.log('Auto-refreshing features...');
      fetchFeatures();
    }, 5 * 60 * 1000); // 5 minutes

    return () => clearInterval(interval);
  }, [isAuthenticated, fetchFeatures]);

  /**
   * Check if a feature is enabled
   * @param {string} moduleKey - Module name (e.g., 'finance')
   * @param {string} featureKey - Feature key (e.g., 'journal_vouchers')
   * @returns {boolean}
   */
  const isFeatureEnabled = useCallback((moduleKey, featureKey = 'module') => {
    if (loading) return false; // Deny access while loading

    const key = `${moduleKey}.${featureKey}`;
    const feature = features[key];

    return feature?.enabled ?? false;
  }, [features, loading]);

  /**
   * Check if a feature is visible in menus
   * @param {string} moduleKey - Module name
   * @param {string} featureKey - Feature key
   * @returns {boolean}
   */
  const isFeatureVisible = useCallback((moduleKey, featureKey = 'module') => {
    if (loading) return false;

    const key = `${moduleKey}.${featureKey}`;
    const feature = features[key];

    return feature?.visible ?? false;
  }, [features, loading]);

  /**
   * Check if an entire module is enabled
   * @param {string} moduleKey - Module name
   * @returns {boolean}
   */
  const isModuleEnabled = useCallback((moduleKey) => {
    return isFeatureEnabled(moduleKey, 'module');
  }, [isFeatureEnabled]);

  /**
   * Get feature metadata
   * @param {string} moduleKey - Module name
   * @param {string} featureKey - Feature key
   * @returns {object|null}
   */
  const getFeature = useCallback((moduleKey, featureKey = 'module') => {
    const key = `${moduleKey}.${featureKey}`;
    return features[key] || null;
  }, [features]);

  /**
   * Check if all dependencies are met for a feature
   * @param {string} moduleKey - Module name
   * @param {string} featureKey - Feature key
   * @returns {boolean}
   */
  const areDependenciesMet = useCallback((moduleKey, featureKey = 'module') => {
    const feature = getFeature(moduleKey, featureKey);

    if (!feature || !feature.depends_on || feature.depends_on.length === 0) {
      return true; // No dependencies
    }

    return feature.depends_on.every(depKey => {
      const [depModule, depFeature] = depKey.split('.');
      return isFeatureEnabled(depModule, depFeature || 'module');
    });
  }, [getFeature, isFeatureEnabled]);

  /**
   * Get list of enabled module names
   * @returns {string[]}
   */
  const getEnabledModules = useCallback(() => {
    return modules;
  }, [modules]);

  /**
   * Manually refresh features (e.g., after admin changes)
   */
  const refreshFeatures = useCallback(() => {
    return fetchFeatures();
  }, [fetchFeatures]);

  const value = {
    // State
    features,
    modules,
    loading,
    error,
    lastFetched,

    // Functions
    isFeatureEnabled,
    isFeatureVisible,
    isModuleEnabled,
    getFeature,
    areDependenciesMet,
    getEnabledModules,
    refreshFeatures,
  };

  return (
    <FeatureContext.Provider value={value}>
      {children}
    </FeatureContext.Provider>
  );
};

/**
 * Hook to access feature context
 * @returns {object}
 */
export const useFeatures = () => {
  const context = useContext(FeatureContext);

  if (!context) {
    throw new Error('useFeatures must be used within a FeatureProvider');
  }

  return context;
};

/**
 * Hook to check if a feature is enabled (convenience hook)
 * @param {string} moduleKey - Module name
 * @param {string} featureKey - Feature key (default: 'module')
 * @returns {boolean}
 */
export const useFeatureEnabled = (moduleKey, featureKey = 'module') => {
  const { isFeatureEnabled } = useFeatures();
  return isFeatureEnabled(moduleKey, featureKey);
};

/**
 * Hook to check if a module is enabled (convenience hook)
 * @param {string} moduleKey - Module name
 * @returns {boolean}
 */
export const useModuleEnabled = (moduleKey) => {
  const { isModuleEnabled } = useFeatures();
  return isModuleEnabled(moduleKey);
};

export default FeatureContext;
```

### 2. Route Guard Component

**File:** `frontend/src/components/FeatureGuard/FeatureGuard.jsx`

```javascript
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useFeatures } from '../../contexts/FeatureContext';
import { Alert, CircularProgress, Box } from '@mui/material';

/**
 * Component to guard routes based on feature toggles
 */
export const FeatureGuard = ({
  module,
  feature = 'module',
  children,
  fallback = null,
  redirectTo = '/dashboard',
  showLoading = true,
  showError = true,
}) => {
  const { isFeatureEnabled, loading, error } = useFeatures();

  // Show loading state
  if (loading && showLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  // Show error state
  if (error && showError) {
    return (
      <Alert severity="error">
        Failed to load feature configuration. Please refresh the page.
      </Alert>
    );
  }

  // Check if feature is enabled
  const enabled = isFeatureEnabled(module, feature);

  if (!enabled) {
    if (fallback) {
      return fallback;
    }

    // Redirect to dashboard or specified route
    return <Navigate to={redirectTo} replace />;
  }

  // Feature is enabled - render children
  return <>{children}</>;
};

export default FeatureGuard;
```

### 3. Feature-Aware Route Configuration

**File:** `frontend/src/App.jsx` (Updated)

```javascript
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { CompanyProvider } from './contexts/CompanyContext';
import { PermissionProvider } from './contexts/PermissionContext';
import { FeatureProvider } from './contexts/FeatureContext';
import { FeatureGuard } from './components/FeatureGuard/FeatureGuard';
import MainLayout from './layouts/MainLayout';

// Import pages
import Dashboard from './pages/Dashboard/Dashboard';
import Login from './pages/Auth/Login';

// Finance
import FinanceWorkspace from './pages/Finance/FinanceWorkspace';
import JournalVouchers from './pages/Finance/Journals/JournalVouchers';
import AccountsList from './pages/Finance/Accounts/AccountsList';

// Inventory
import InventoryWorkspace from './pages/Inventory/InventoryWorkspace';
import ProductsList from './pages/Inventory/Products/ProductsList';

// Sales
import SalesWorkspace from './pages/Sales/SalesWorkspace';
import CustomersList from './pages/Sales/Customers/CustomersList';
import SalesOrdersList from './pages/Sales/Orders/SalesOrdersList';

// ... import other pages

function App() {
  return (
    <Router>
      <AuthProvider>
        <CompanyProvider>
          <PermissionProvider>
            <FeatureProvider>
              <Routes>
                {/* Public routes */}
                <Route path="/login" element={<Login />} />

                {/* Protected routes */}
                <Route element={<MainLayout />}>
                  {/* Dashboard - always available */}
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/dashboard" element={<Dashboard />} />

                  {/* Finance Module */}
                  <Route
                    path="/finance"
                    element={
                      <FeatureGuard module="finance">
                        <FinanceWorkspace />
                      </FeatureGuard>
                    }
                  />
                  <Route
                    path="/finance/accounts"
                    element={
                      <FeatureGuard module="finance" feature="chart_of_accounts">
                        <AccountsList />
                      </FeatureGuard>
                    }
                  />
                  <Route
                    path="/finance/journals"
                    element={
                      <FeatureGuard module="finance" feature="journal_vouchers">
                        <JournalVouchers />
                      </FeatureGuard>
                    }
                  />

                  {/* Inventory Module */}
                  <Route
                    path="/inventory"
                    element={
                      <FeatureGuard module="inventory">
                        <InventoryWorkspace />
                      </FeatureGuard>
                    }
                  />
                  <Route
                    path="/inventory/products"
                    element={
                      <FeatureGuard module="inventory" feature="products">
                        <ProductsList />
                      </FeatureGuard>
                    }
                  />

                  {/* Sales Module */}
                  <Route
                    path="/sales"
                    element={
                      <FeatureGuard module="sales">
                        <SalesWorkspace />
                      </FeatureGuard>
                    }
                  />
                  <Route
                    path="/sales/customers"
                    element={
                      <FeatureGuard module="sales" feature="customers">
                        <CustomersList />
                      </FeatureGuard>
                    }
                  />
                  <Route
                    path="/sales/orders"
                    element={
                      <FeatureGuard module="sales" feature="sales_orders">
                        <SalesOrdersList />
                      </FeatureGuard>
                    }
                  />

                  {/* Add more feature-guarded routes... */}

                  {/* 404 - Catch all */}
                  <Route path="*" element={<Navigate to="/dashboard" replace />} />
                </Route>
              </Routes>
            </FeatureProvider>
          </PermissionProvider>
        </CompanyProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
```

### 4. Dynamic Menu System

**File:** `frontend/src/layouts/MainLayout.jsx` (Updated)

```javascript
import React, { useMemo } from 'react';
import { useFeatures } from '../contexts/FeatureContext';
import { usePermissions } from '../contexts/PermissionContext';

const MainLayout = () => {
  const { isFeatureEnabled, isFeatureVisible, getFeature } = useFeatures();
  const { can } = usePermissions();

  /**
   * Define all possible menu items
   * Items will be filtered based on features and permissions
   */
  const allMenuItems = useMemo(() => [
    {
      title: 'Dashboard',
      icon: 'mdi-view-dashboard',
      path: '/dashboard',
      module: 'dashboard',
      feature: 'module',
      permission: null, // Always visible if feature enabled
    },
    {
      title: 'Finance',
      icon: 'mdi-finance',
      path: '/finance',
      module: 'finance',
      feature: 'module',
      permission: 'finance_view_dashboard',
      children: [
        {
          title: 'Chart of Accounts',
          icon: 'mdi-file-tree',
          path: '/finance/accounts',
          module: 'finance',
          feature: 'chart_of_accounts',
          permission: 'finance_view_accounts',
        },
        {
          title: 'Journal Vouchers',
          icon: 'mdi-book-open-variant',
          path: '/finance/journals',
          module: 'finance',
          feature: 'journal_vouchers',
          permission: 'finance_view_journals',
        },
        {
          title: 'Invoicing',
          icon: 'mdi-receipt',
          path: '/finance/invoices',
          module: 'finance',
          feature: 'invoicing',
          permission: 'finance_view_invoices',
        },
        {
          title: 'Payments',
          icon: 'mdi-cash-multiple',
          path: '/finance/payments',
          module: 'finance',
          feature: 'payments',
          permission: 'finance_view_payments',
        },
      ],
    },
    {
      title: 'Inventory',
      icon: 'mdi-warehouse',
      path: '/inventory',
      module: 'inventory',
      feature: 'module',
      permission: 'inventory_view_dashboard',
      children: [
        {
          title: 'Products',
          icon: 'mdi-package-variant',
          path: '/inventory/products',
          module: 'inventory',
          feature: 'products',
          permission: 'inventory_view_products',
        },
        {
          title: 'Warehouses',
          icon: 'mdi-home-city',
          path: '/inventory/warehouses',
          module: 'inventory',
          feature: 'warehouses',
          permission: 'inventory_view_warehouses',
        },
      ],
    },
    {
      title: 'Sales',
      icon: 'mdi-cart',
      path: '/sales',
      module: 'sales',
      feature: 'module',
      permission: 'sales_view_dashboard',
      children: [
        {
          title: 'Customers',
          icon: 'mdi-account-group',
          path: '/sales/customers',
          module: 'sales',
          feature: 'customers',
          permission: 'sales_view_customers',
        },
        {
          title: 'Sales Orders',
          icon: 'mdi-file-document',
          path: '/sales/orders',
          module: 'sales',
          feature: 'sales_orders',
          permission: 'sales_view_orders',
        },
      ],
    },
    {
      title: 'Procurement',
      icon: 'mdi-shopping',
      path: '/procurement',
      module: 'procurement',
      feature: 'module',
      permission: 'procurement_view_dashboard',
      children: [
        {
          title: 'Vendors',
          icon: 'mdi-truck',
          path: '/procurement/vendors',
          module: 'procurement',
          feature: 'vendors',
          permission: 'procurement_view_vendors',
        },
        {
          title: 'Purchase Orders',
          icon: 'mdi-clipboard-text',
          path: '/procurement/orders',
          module: 'procurement',
          feature: 'purchase_orders',
          permission: 'procurement_view_orders',
        },
      ],
    },
    {
      title: 'HR',
      icon: 'mdi-account-multiple',
      path: '/hr',
      module: 'hr',
      feature: 'module',
      permission: 'hr_view_dashboard',
      children: [
        {
          title: 'Employees',
          icon: 'mdi-account-tie',
          path: '/hr/employees',
          module: 'hr',
          feature: 'employees',
          permission: 'hr_view_employees',
        },
        {
          title: 'Attendance',
          icon: 'mdi-calendar-check',
          path: '/hr/attendance',
          module: 'hr',
          feature: 'attendance',
          permission: 'hr_view_attendance',
        },
        {
          title: 'Leave',
          icon: 'mdi-beach',
          path: '/hr/leave',
          module: 'hr',
          feature: 'leave',
          permission: 'hr_view_leave',
        },
        {
          title: 'Payroll',
          icon: 'mdi-currency-usd',
          path: '/hr/payroll',
          module: 'hr',
          feature: 'payroll',
          permission: 'hr_view_payroll',
        },
      ],
    },
    {
      title: 'Production',
      icon: 'mdi-factory',
      path: '/production',
      module: 'production',
      feature: 'module',
      permission: 'production_view_dashboard',
      children: [
        {
          title: 'Bill of Materials',
          icon: 'mdi-format-list-bulleted',
          path: '/production/bom',
          module: 'production',
          feature: 'bom',
          permission: 'production_view_bom',
        },
        {
          title: 'Work Orders',
          icon: 'mdi-clipboard-list',
          path: '/production/work-orders',
          module: 'production',
          feature: 'work_orders',
          permission: 'production_view_work_orders',
        },
      ],
    },
    {
      title: 'Assets',
      icon: 'mdi-office-building',
      path: '/assets',
      module: 'assets',
      feature: 'module',
      permission: 'assets_view_dashboard',
    },
    {
      title: 'Budgeting',
      icon: 'mdi-chart-line',
      path: '/budgeting',
      module: 'budgeting',
      feature: 'module',
      permission: 'budgeting_view_dashboard',
    },
    {
      title: 'Projects',
      icon: 'mdi-briefcase',
      path: '/projects',
      module: 'projects',
      feature: 'module',
      permission: 'projects_view_dashboard',
    },
    {
      title: 'AI Assistant',
      icon: 'mdi-robot',
      path: '/ai',
      module: 'ai_companion',
      feature: 'module',
      permission: null,
      badge: 'BETA',
      badgeColor: 'warning',
    },
    {
      title: 'Form Builder',
      icon: 'mdi-form-select',
      path: '/forms',
      module: 'form_builder',
      feature: 'module',
      permission: 'forms_view_dashboard',
    },
    {
      title: 'Workflows',
      icon: 'mdi-chart-timeline',
      path: '/workflows',
      module: 'workflows',
      feature: 'module',
      permission: 'workflows_view_dashboard',
    },
    {
      title: 'Reports',
      icon: 'mdi-file-chart',
      path: '/reports',
      module: 'report_builder',
      feature: 'module',
      permission: 'reports_view_dashboard',
    },
    {
      title: 'Tasks',
      icon: 'mdi-checkbox-marked',
      path: '/tasks',
      module: 'tasks',
      feature: 'module',
      permission: null,
    },
    {
      title: 'Notifications',
      icon: 'mdi-bell',
      path: '/notifications',
      module: 'notifications',
      feature: 'module',
      permission: null,
    },
  ], []);

  /**
   * Filter menu items based on features and permissions
   */
  const visibleMenuItems = useMemo(() => {
    const filterItem = (item) => {
      // Check feature toggle
      const featureEnabled = isFeatureEnabled(item.module, item.feature);
      const featureVisible = isFeatureVisible(item.module, item.feature);

      if (!featureVisible) {
        return null; // Hide if feature is not visible
      }

      // Check permission (if specified)
      const hasPermission = !item.permission || can(item.permission);

      if (!hasPermission) {
        return null; // Hide if user doesn't have permission
      }

      // Get feature metadata for badge/status
      const featureMeta = getFeature(item.module, item.feature);

      // Create filtered item
      const filteredItem = {
        ...item,
        disabled: !featureEnabled, // Disable but show if feature is disabled
        status: featureMeta?.status,
      };

      // Recursively filter children
      if (item.children) {
        const filteredChildren = item.children
          .map(filterItem)
          .filter(Boolean); // Remove null items

        if (filteredChildren.length === 0) {
          return null; // Hide parent if all children are hidden
        }

        filteredItem.children = filteredChildren;
      }

      return filteredItem;
    };

    return allMenuItems
      .map(filterItem)
      .filter(Boolean);
  }, [allMenuItems, isFeatureEnabled, isFeatureVisible, can, getFeature]);

  // Rest of MainLayout implementation...
  return (
    <div>
      {/* Render menu with visibleMenuItems */}
      {/* ... */}
    </div>
  );
};

export default MainLayout;
```

### 5. Feature Status Badge Component

**File:** `frontend/src/components/FeatureBadge/FeatureBadge.jsx`

```javascript
import React from 'react';
import { Chip, Tooltip } from '@mui/material';

/**
 * Display feature status badge (Beta, Coming Soon, etc.)
 */
export const FeatureBadge = ({ status, size = 'small' }) => {
  const config = {
    beta: {
      label: 'BETA',
      color: 'warning',
      tooltip: 'This feature is in beta testing',
    },
    deprecated: {
      label: 'DEPRECATED',
      color: 'error',
      tooltip: 'This feature will be removed in a future version',
    },
    coming_soon: {
      label: 'COMING SOON',
      color: 'info',
      tooltip: 'This feature is coming soon',
    },
    new: {
      label: 'NEW',
      color: 'success',
      tooltip: 'This is a new feature',
    },
  };

  const statusConfig = config[status];

  if (!statusConfig) {
    return null;
  }

  return (
    <Tooltip title={statusConfig.tooltip} arrow>
      <Chip
        label={statusConfig.label}
        color={statusConfig.color}
        size={size}
        sx={{ ml: 1, fontSize: '0.7rem', height: '20px' }}
      />
    </Tooltip>
  );
};

export default FeatureBadge;
```

---

## Integration Points

### 1. App Configuration

**Update:** `backend/core/settings.py`

```python
INSTALLED_APPS = [
    # ... existing apps
    'apps.admin_settings',  # ADD THIS
]

# Cache configuration (if not already present)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'twist_erp',
        'TIMEOUT': 300,  # 5 minutes default
    }
}
```

### 2. Create App Structure

```bash
# Backend
cd backend
python manage.py startapp admin_settings apps/admin_settings

# Create necessary files
mkdir -p apps/admin_settings/templates/admin/admin_settings
mkdir -p apps/admin_settings/migrations
touch apps/admin_settings/__init__.py
touch apps/admin_settings/models.py
touch apps/admin_settings/admin.py
touch apps/admin_settings/serializers.py
touch apps/admin_settings/views.py
touch apps/admin_settings/urls.py
touch apps/admin_settings/services.py
touch apps/admin_settings/default_features.py
```

### 3. Frontend Provider Integration

**Update:** `frontend/src/main.jsx`

```javascript
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { FeatureProvider } from './contexts/FeatureContext';

// Wrap App with FeatureProvider
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

---

## Migration Strategy

### Phase 1: Backend Setup (Week 1)

**Day 1-2: Models & Migrations**
```bash
# Create models
# Run migrations
cd backend
python manage.py makemigrations admin_settings
python manage.py migrate admin_settings
```

**Day 3-4: Admin Interface**
- Implement admin.py with all customizations
- Test admin UI
- Create bulk create template

**Day 5: Services & API**
- Implement FeatureService
- Create API endpoints
- Test caching

**Day 6-7: Default Features**
- Define DEFAULT_FEATURES
- Create management command for bulk import
- Run initial feature creation

```bash
# Management command to create default features
python manage.py create_default_features --scope=GLOBAL
```

### Phase 2: Frontend Integration (Week 2)

**Day 1-2: Context & Hooks**
- Implement FeatureContext
- Create custom hooks
- Test in DevTools

**Day 3-4: Route Guards**
- Implement FeatureGuard component
- Test loading states
- Test error handling

**Day 5: Menu System**
- Update MainLayout
- Implement dynamic filtering
- Add feature badges

**Day 6-7: Testing & Polish**
- Test all modules
- Fix edge cases
- Performance optimization

### Phase 3: Rollout (Week 3)

**Day 1: Staging Deployment**
```bash
# Deploy to staging
# Test with real data
# Verify cache performance
```

**Day 2-3: User Testing**
- Internal testing
- Collect feedback
- Fix bugs

**Day 4-5: Production Deployment**
```bash
# Deploy to production
python manage.py migrate
python manage.py create_default_features --scope=GLOBAL
# Monitor performance
```

**Day 6-7: Monitoring & Documentation**
- Monitor cache hit rates
- Document for users
- Training materials

---

## Testing Strategy

### 1. Backend Unit Tests

**File:** `backend/apps/admin_settings/tests/test_models.py`

```python
from django.test import TestCase
from apps.companies.models import Company, CompanyGroup
from apps.users.models import User
from apps.admin_settings.models import ModuleFeatureToggle


class ModuleFeatureToggleTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.company_group = CompanyGroup.objects.create(name='Test Group', db_name='test_db')
        self.company = Company.objects.create(
            company_group=self.company_group,
            code='TEST',
            name='Test Company',
            legal_name='Test Company Ltd',
            tax_id='12345',
            registration_number='REG123',
            fiscal_year_start='2024-01-01',
        )

    def test_create_global_feature(self):
        """Test creating a global feature toggle."""
        feature = ModuleFeatureToggle.objects.create(
            module_name='finance',
            feature_key='module',
            feature_name='Finance Module',
            scope_type='GLOBAL',
            is_enabled=True,
            created_by=self.user,
        )

        self.assertEqual(feature.full_key, 'finance.module')
        self.assertTrue(feature.is_module_toggle)
        self.assertTrue(feature.is_enabled)

    def test_create_company_feature(self):
        """Test creating a company-specific feature."""
        feature = ModuleFeatureToggle.objects.create(
            module_name='hr',
            feature_key='payroll',
            feature_name='Payroll',
            scope_type='COMPANY',
            company=self.company,
            is_enabled=True,
            created_by=self.user,
        )

        self.assertEqual(feature.scope_type, 'COMPANY')
        self.assertEqual(feature.company, self.company)

    def test_unique_constraint(self):
        """Test unique constraint on feature toggles."""
        ModuleFeatureToggle.objects.create(
            module_name='sales',
            feature_key='module',
            feature_name='Sales Module',
            scope_type='GLOBAL',
            is_enabled=True,
        )

        # Should raise IntegrityError for duplicate
        with self.assertRaises(Exception):
            ModuleFeatureToggle.objects.create(
                module_name='sales',
                feature_key='module',
                feature_name='Sales Module',
                scope_type='GLOBAL',
                is_enabled=False,
            )
```

**File:** `backend/apps/admin_settings/tests/test_services.py`

```python
from django.test import TestCase
from django.core.cache import cache
from apps.admin_settings.services import FeatureService
from apps.admin_settings.models import ModuleFeatureToggle
from apps.companies.models import Company, CompanyGroup


class FeatureServiceTestCase(TestCase):
    def setUp(self):
        cache.clear()

        self.company_group = CompanyGroup.objects.create(name='Test Group', db_name='test_db')
        self.company = Company.objects.create(
            company_group=self.company_group,
            code='TEST',
            name='Test Company',
            legal_name='Test Company Ltd',
            tax_id='12345',
            registration_number='REG123',
            fiscal_year_start='2024-01-01',
        )

    def test_get_global_features(self):
        """Test fetching global features."""
        ModuleFeatureToggle.objects.create(
            module_name='finance',
            feature_key='module',
            feature_name='Finance Module',
            scope_type='GLOBAL',
            is_enabled=True,
        )

        features = FeatureService.get_global_features()

        self.assertIn('finance.module', features)
        self.assertTrue(features['finance.module']['enabled'])

    def test_hierarchical_resolution(self):
        """Test that company features override global features."""
        # Global: enabled
        ModuleFeatureToggle.objects.create(
            module_name='hr',
            feature_key='module',
            feature_name='HR Module',
            scope_type='GLOBAL',
            is_enabled=True,
        )

        # Company: disabled (should override)
        ModuleFeatureToggle.objects.create(
            module_name='hr',
            feature_key='module',
            feature_name='HR Module',
            scope_type='COMPANY',
            company=self.company,
            is_enabled=False,
        )

        features = FeatureService.get_features_for_company(self.company)

        # Should not contain hr.module (disabled at company level)
        self.assertNotIn('hr.module', features)

    def test_caching(self):
        """Test that features are cached."""
        ModuleFeatureToggle.objects.create(
            module_name='sales',
            feature_key='module',
            feature_name='Sales Module',
            scope_type='GLOBAL',
            is_enabled=True,
        )

        # First call - should hit database
        features1 = FeatureService.get_global_features()

        # Second call - should hit cache
        features2 = FeatureService.get_global_features()

        self.assertEqual(features1, features2)

        # Verify cache is populated
        cache_key = FeatureService.get_cache_key('GLOBAL')
        cached = cache.get(cache_key)
        self.assertIsNotNone(cached)
```

### 2. Frontend Tests

**File:** `frontend/src/contexts/__tests__/FeatureContext.test.jsx`

```javascript
import { renderHook, waitFor } from '@testing-library/react';
import { FeatureProvider, useFeatures } from '../FeatureContext';
import api from '../../services/api';

jest.mock('../../services/api');
jest.mock('../AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: true }),
}));
jest.mock('../CompanyContext', () => ({
  useCompany: () => ({ currentCompany: { id: 1, code: 'TEST' } }),
}));

describe('FeatureContext', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  it('should fetch features on mount', async () => {
    const mockData = {
      features: {
        'finance.module': { enabled: true, visible: true },
        'hr.module': { enabled: false, visible: true },
      },
      modules: ['finance'],
      scope: 'COMPANY:TEST',
    };

    api.get.mockResolvedValue({ data: mockData });

    const { result } = renderHook(() => useFeatures(), {
      wrapper: FeatureProvider,
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(api.get).toHaveBeenCalledWith('/admin-settings/features/');
    expect(result.current.features).toEqual(mockData.features);
    expect(result.current.modules).toEqual(mockData.modules);
  });

  it('should check if feature is enabled', async () => {
    const mockData = {
      features: {
        'finance.module': { enabled: true, visible: true },
      },
      modules: ['finance'],
    };

    api.get.mockResolvedValue({ data: mockData });

    const { result } = renderHook(() => useFeatures(), {
      wrapper: FeatureProvider,
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.isFeatureEnabled('finance', 'module')).toBe(true);
    expect(result.current.isFeatureEnabled('hr', 'module')).toBe(false);
  });
});
```

---

## Deployment Plan

### Pre-Deployment Checklist

- [ ] All tests passing (backend + frontend)
- [ ] Database migrations created
- [ ] Redis cache configured
- [ ] Default features defined
- [ ] Admin interface tested
- [ ] API endpoints tested
- [ ] Frontend components tested
- [ ] Documentation complete
- [ ] Rollback plan ready

### Deployment Steps

#### 1. Database Migration

```bash
# Staging
cd backend
python manage.py makemigrations admin_settings
python manage.py migrate admin_settings

# Verify migration
python manage.py showmigrations admin_settings
```

#### 2. Create Default Features

```bash
# Create management command
# File: backend/apps/admin_settings/management/commands/create_default_features.py

python manage.py create_default_features --scope=GLOBAL
```

#### 3. Backend Deployment

```bash
# Collect static files
python manage.py collectstatic --noinput

# Restart application server
systemctl restart gunicorn  # or your app server
```

#### 4. Frontend Deployment

```bash
cd frontend
npm run build
# Deploy build artifacts
```

#### 5. Verify Deployment

```bash
# Check admin interface
# Navigate to /admin/admin_settings/modulefeaturetoggle/

# Check API endpoint
curl -H "Authorization: Bearer <token>" https://your-domain/api/v1/admin-settings/features/

# Check frontend
# Login and verify features load
```

### Monitoring

**Metrics to Track:**
- Feature API response time
- Cache hit rate
- Feature toggle change frequency
- User feature adoption
- Error rates

**Logging:**
```python
# Add to settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/features.log',
        },
    },
    'loggers': {
        'apps.admin_settings': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

---

## Rollback Plan

### If Issues Arise

**Option 1: Disable Feature System (Safe)**
```python
# In settings.py
FEATURES_ENABLED = False

# Update FeatureService to check this flag
class FeatureService:
    @classmethod
    def is_feature_enabled(cls, feature_key, company=None):
        if not settings.FEATURES_ENABLED:
            return True  # Allow all features
        # ... normal logic
```

**Option 2: Database Rollback**
```bash
# Rollback migration
python manage.py migrate admin_settings <previous_migration_number>

# Example:
python manage.py migrate admin_settings zero  # Remove all
```

**Option 3: Enable All Features**
```bash
# Quick SQL to enable everything
python manage.py dbshell
> UPDATE admin_feature_toggles SET is_enabled = true;
```

### Recovery Checklist

- [ ] Identify issue
- [ ] Check logs
- [ ] Disable problematic features
- [ ] Clear cache
- [ ] Notify users
- [ ] Fix issue
- [ ] Re-enable features
- [ ] Monitor closely

---

## Success Criteria

### MVP Success (Phase 1)

- ✅ Admin can create/edit feature toggles
- ✅ Features cached for performance
- ✅ API returns features correctly
- ✅ Module-level toggles working
- ✅ All existing features enabled by default

### Full Implementation Success (Phase 3)

- ✅ Feature-level toggles working
- ✅ Multi-tenant scoping functional
- ✅ Frontend menu dynamically filters
- ✅ Routes protected by feature guards
- ✅ Audit trail complete
- ✅ Performance metrics acceptable (<100ms API response)
- ✅ Cache hit rate >80%
- ✅ User documentation complete

---

## Next Steps After Implementation

### 1. Create Feature Presets

**File:** `backend/apps/admin_settings/presets.py`

```python
FEATURE_PRESETS = {
    'manufacturing': {
        'name': 'Manufacturing Company',
        'features': {
            'production': True,
            'inventory': True,
            'procurement': True,
            'finance': True,
            'sales': False,
            'hr': True,
        },
    },
    'service_company': {
        'name': 'Service Company',
        'features': {
            'production': False,
            'inventory': False,
            'procurement': False,
            'finance': True,
            'sales': True,
            'hr': True,
            'projects': True,
        },
    },
    'retail': {
        'name': 'Retail Company',
        'features': {
            'production': False,
            'inventory': True,
            'procurement': True,
            'finance': True,
            'sales': True,
            'hr': True,
        },
    },
}
```

### 2. Add Analytics

- Track feature usage
- Identify unused features
- Measure adoption rates
- A/B testing capabilities

### 3. Self-Service Feature Management

- Allow company admins to enable/disable their own features
- Request new features
- Beta program enrollment

---

## Appendix

### A. Complete File Structure

```
backend/
└── apps/
    └── admin_settings/
        ├── __init__.py
        ├── apps.py
        ├── models.py
        ├── admin.py
        ├── serializers.py
        ├── views.py
        ├── urls.py
        ├── services.py
        ├── default_features.py
        ├── presets.py
        ├── migrations/
        │   ├── __init__.py
        │   └── 0001_initial.py
        ├── management/
        │   └── commands/
        │       └── create_default_features.py
        ├── templates/
        │   └── admin/
        │       └── admin_settings/
        │           └── bulk_create_features.html
        └── tests/
            ├── __init__.py
            ├── test_models.py
            ├── test_services.py
            └── test_views.py

frontend/
└── src/
    ├── contexts/
    │   └── FeatureContext.jsx
    ├── components/
    │   ├── FeatureGuard/
    │   │   └── FeatureGuard.jsx
    │   └── FeatureBadge/
    │       └── FeatureBadge.jsx
    ├── hooks/
    │   └── useFeatureEnabled.js
    └── App.jsx (updated)
```

### B. API Documentation

**Base URL:** `/api/v1/admin-settings/`

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/features/` | GET | Required | Get all features for current company |
| `/features/check/?key=<key>` | GET | Required | Check specific feature status |
| `/features/list/` | GET | Admin | List all feature toggles |
| `/features/audit/` | GET | Admin | View audit logs |
| `/features/invalidate-cache/` | POST | Admin | Clear feature cache |

### C. Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Features not loading | API error | Check network tab, verify authentication |
| Stale features | Cache not invalidating | Clear cache or reduce TTL |
| Route still accessible | Missing FeatureGuard | Add guard to route |
| Menu item visible when disabled | Permission check missing | Update menu filtering logic |
| Performance slow | Too many DB queries | Verify caching is working |

---

## Conclusion

This implementation plan provides a complete, production-ready feature toggle system for Twist ERP. Follow the phases sequentially, test thoroughly at each stage, and monitor performance metrics post-deployment.

**Estimated Total Effort:** 8-10 weeks for complete implementation including testing and documentation.

**Key Success Factors:**
1. Start with MVP (module-level toggles)
2. Test extensively before adding complexity
3. Monitor cache performance
4. Document everything
5. Train users effectively

Good luck with the implementation! 🚀
