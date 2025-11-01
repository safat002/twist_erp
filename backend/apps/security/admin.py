from django.contrib import admin
from .models import (
    SecPermission,
    SecRole,
    SecRolePermission,
    SecScope,
    SecUserRole,
    SecUserRoleScope,
    SecSoDRule,
    SecUserDirectPermission
)

@admin.register(SecPermission)
class SecPermissionAdmin(admin.ModelAdmin):
    list_display = ('code', 'description', 'category', 'scope_required', 'is_sensitive', 'is_assignable')
    list_filter = ('category', 'scope_required', 'is_sensitive', 'is_assignable')
    search_fields = ('code', 'description')
    ordering = ('category', 'code')

@admin.register(SecRole)
class SecRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'company_group', 'is_system')
    list_filter = ('is_system', 'company_group')
    search_fields = ('name', 'code')
    ordering = ('name',)

@admin.register(SecRolePermission)
class SecRolePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'permission', 'amount_limit', 'percent_limit')
    list_filter = ('role__name', 'permission__category')
    search_fields = ('role__name', 'permission__code')
    autocomplete_fields = ('role', 'permission')

@admin.register(SecScope)
class SecScopeAdmin(admin.ModelAdmin):
    list_display = ('name', 'scope_type', 'object_id', 'company_group')
    list_filter = ('scope_type', 'company_group')
    search_fields = ('name', 'object_id')
    ordering = ('scope_type', 'name')

@admin.register(SecUserRole)
class SecUserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'valid_from', 'valid_to', 'is_delegated')
    list_filter = ('role__name', 'is_delegated', 'valid_from', 'valid_to')
    search_fields = ('user__username', 'role__name')
    autocomplete_fields = ('user', 'role', 'delegated_by_user')

@admin.register(SecUserRoleScope)
class SecUserRoleScopeAdmin(admin.ModelAdmin):
    list_display = ('user_role', 'scope')
    list_filter = ('scope__scope_type', 'scope__name')
    search_fields = ('user_role__user__username', 'scope__name')
    autocomplete_fields = ('user_role', 'scope')

@admin.register(SecSoDRule)
class SecSoDRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'first_action_code', 'second_action_code', 'enforcement', 'is_active')
    list_filter = ('enforcement', 'is_active')
    search_fields = ('name', 'first_action_code', 'second_action_code')

@admin.register(SecUserDirectPermission)
class SecUserDirectPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'permission', 'scope', 'valid_from', 'valid_to')
    list_filter = ('permission__category', 'scope__scope_type')
    search_fields = ('user__username', 'permission__code')
    autocomplete_fields = ('user', 'permission', 'scope')
