from django.contrib import admin

from .models import Notification, EmailAwarenessState


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "severity", "status", "company", "created_at")
    list_filter = ("severity", "status", "company")
    search_fields = ("title", "body", "user__username", "user__email")
    date_hierarchy = "created_at"


@admin.register(EmailAwarenessState)
class EmailAwarenessStateAdmin(admin.ModelAdmin):
    list_display = ("user", "unread_count", "company", "created_at")
    list_filter = ("company",)
    search_fields = ("user__username", "user__email")

