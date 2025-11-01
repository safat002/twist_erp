from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "company", "action", "entity_type", "entity_id")
    list_filter = ("action", "company")
    search_fields = ("entity_type", "entity_id", "description", "user__username", "user__email")
