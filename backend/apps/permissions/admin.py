from django.contrib import admin
from .models import Permission, Role


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "module"]
    list_filter = ["module"]
    search_fields = ["code", "name", "module"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "is_system_role"]
    list_filter = ["company", "is_system_role"]
    search_fields = ["name", "company__code"]
    filter_horizontal = ["permissions"]

