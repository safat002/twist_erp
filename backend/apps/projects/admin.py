from django.contrib import admin
from .models import Project, Task


class TaskInline(admin.TabularInline):
    model = Task
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "start_date", "end_date", "company"]
    list_filter = ["company", "start_date"]
    search_fields = ["name"]
    inlines = [TaskInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["project", "name", "start_date", "end_date"]
    list_filter = ["project"]
    search_fields = ["name", "project__name"]
    date_hierarchy = "start_date"

