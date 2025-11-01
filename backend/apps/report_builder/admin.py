from django.contrib import admin

from .models import ReportDefinition


@admin.register(ReportDefinition)
class ReportDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "scope_type", "status", "updated_at")
    search_fields = ("name", "slug", "description")
    list_filter = ("scope_type", "status", "layer")
