from django.contrib import admin
from .models import FormTemplate, FormSubmission


@admin.register(FormTemplate)
class FormTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "is_active", "created_by", "updated_at"]
    list_filter = ["company", "is_active"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ["template", "submitted_by", "company", "created_at"]
    list_filter = ["company", "template"]
    search_fields = ["template__name", "submitted_by__username"]
    readonly_fields = ["created_at"]

