from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponseRedirect

from .models import ModuleFeatureToggle, FeatureAuditLog


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
                '<int:pk>/toggle/',
                self.admin_site.admin_view(self.quick_toggle_view),
                name='admin_settings_modulefeaturetoggle_toggle',
            ),
        ]
        return custom_urls + urls

    def feature_display(self, obj):
        """Display feature with icon and key."""
        icon_html = ''
        if obj.icon:
            icon_html = f'<i class="{obj.icon}" style="margin-right: 5px;"></i>'

        return format_html(
            '{}<strong>{}</strong><br/>'
            '<small style="color: #666;">{}.{}</small>',
            icon_html,
            obj.feature_name,
            obj.module_name,
            obj.feature_key,
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
            obj.get_status_display(),
        )
    status_badge.short_description = 'Status'

    def scope_display(self, obj):
        """Display scope information."""
        if obj.scope_type == 'GLOBAL':
            return format_html('<span style="color: #007bff;">Global</span>')
        if obj.scope_type == 'GROUP' and obj.company_group:
            return format_html('<span style="color: #6f42c1;">{}</span>', obj.company_group.name)
        if obj.scope_type == 'COMPANY' and obj.company:
            return format_html('<span style="color: #fd7e14;">{}</span>', obj.company.name)
        return '-'
    scope_display.short_description = 'Scope'

    def visibility_display(self, obj):
        """Display visibility status."""
        if obj.is_visible:
            return format_html('<span style="color: #28a745;">Visible</span>')
        return format_html('<span style="color: #6c757d;">Hidden</span>')
    visibility_display.short_description = 'Visibility'

    def quick_toggle(self, obj):
        """Quick enable/disable toggle button."""
        url = reverse('admin:admin_settings_modulefeaturetoggle_toggle', args=[obj.pk])
        if obj.is_enabled:
            return format_html(
                '<a class="button" href="{}" style="background-color: #28a745; color: white; '
                'padding: 5px 10px; text-decoration: none; border-radius: 3px;">Enabled</a>',
                url,
            )
        return format_html(
            '<a class="button" href="{}" style="background-color: #dc3545; color: white; '
            'padding: 5px 10px; text-decoration: none; border-radius: 3px;">Disabled</a>',
            url,
        )
    quick_toggle.short_description = 'Quick Toggle'

    def updated_display(self, obj):
        """Display last update information."""
        if obj.updated_by:
            return format_html(
                '<small>{}<br/>by {}</small>',
                obj.updated_at.strftime('%Y-%m-%d %H:%M'),
                obj.updated_by.username,
            )
        return format_html('<small>{}</small>', obj.updated_at.strftime('%Y-%m-%d %H:%M'))
    updated_display.short_description = 'Last Updated'

    def save_model(self, request, obj, form, change):
        """Track who created/updated the feature toggle and log changes."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user

        # Prepare old values for audit log
        old_value = None
        if change:
            try:
                old_obj = ModuleFeatureToggle.objects.get(pk=obj.pk)
                old_value = {
                    'is_enabled': old_obj.is_enabled,
                    'is_visible': old_obj.is_visible,
                    'status': old_obj.status,
                }
            except ModuleFeatureToggle.DoesNotExist:
                old_value = None

        super().save_model(request, obj, form, change)

        action = 'created' if not change else 'updated'
        if change and old_value and old_value.get('is_enabled') != obj.is_enabled:
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
        super().delete_model(request, obj)

    @staticmethod
    def get_client_ip(request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

    # Bulk Actions
    def enable_features(self, request, queryset):
        """Bulk enable features."""
        count = queryset.update(is_enabled=True, updated_by=request.user)
        for obj in queryset:
            FeatureAuditLog.objects.create(
                feature_toggle=obj,
                action='enabled',
                user=request.user,
                ip_address=self.get_client_ip(request),
            )
        self.message_user(request, f'{count} feature(s) enabled successfully.', messages.SUCCESS)
    enable_features.short_description = 'Enable selected features'

    def disable_features(self, request, queryset):
        """Bulk disable features."""
        count = queryset.update(is_enabled=False, updated_by=request.user)
        for obj in queryset:
            FeatureAuditLog.objects.create(
                feature_toggle=obj,
                action='disabled',
                user=request.user,
                ip_address=self.get_client_ip(request),
            )
        self.message_user(request, f'{count} feature(s) disabled successfully.', messages.WARNING)
    disable_features.short_description = 'Disable selected features'

    def make_visible(self, request, queryset):
        """Bulk make visible."""
        count = queryset.update(is_visible=True, updated_by=request.user)
        self.message_user(request, f'{count} feature(s) made visible.', messages.SUCCESS)
    make_visible.short_description = 'Make visible'

    def make_hidden(self, request, queryset):
        """Bulk hide features."""
        count = queryset.update(is_visible=False, updated_by=request.user)
        self.message_user(request, f'{count} feature(s) hidden.', messages.SUCCESS)
    make_hidden.short_description = 'Hide from menu'

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
                messages.SUCCESS if obj.is_enabled else messages.WARNING,
            )
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '../'))


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

