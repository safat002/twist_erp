from django.contrib import admin

from .models import TaskItem


@admin.register(TaskItem)
class TaskItemAdmin(admin.ModelAdmin):
    list_display = ("title", "assigned_to", "priority", "status", "due_date", "company")
    list_filter = ("priority", "status", "company")
    search_fields = ("title", "description", "assigned_to__username", "assigned_to__email")
    date_hierarchy = "due_date"

