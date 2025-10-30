from django.contrib import admin
from django.contrib import messages
from .models import WorkflowTemplate, WorkflowInstance
from .services import WorkflowService


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "status", "updated_at"]
    list_filter = ["company", "status"]
    search_fields = ["name", "description"]
    readonly_fields = ["updated_at", "created_at"]


@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(admin.ModelAdmin):
    list_display = ["template", "state", "company", "updated_at"]
    list_filter = ["company", "state"]
    search_fields = ["template__name", "state"]
    readonly_fields = ["created_at", "updated_at"]
    actions = [
        "transition_to_draft",
        "transition_to_approved",
        "transition_to_closed",
    ]

    def _bulk_transition(self, request, queryset, to_state: str):
        ok = 0
        err = 0
        for inst in queryset:
            try:
                WorkflowService.trigger_transition(inst, to_state)
                ok += 1
            except Exception as exc:
                err += 1
        if ok:
            self.message_user(request, f"{ok} workflow(s) moved to '{to_state}'.", level=messages.SUCCESS)
        if err:
            self.message_user(
                request,
                f"{err} workflow(s) could not transition to '{to_state}' (not allowed or error).",
                level=messages.WARNING,
            )

    def transition_to_draft(self, request, queryset):
        self._bulk_transition(request, queryset, "draft")

    transition_to_draft.short_description = "Transition selected to 'draft'"

    def transition_to_approved(self, request, queryset):
        self._bulk_transition(request, queryset, "approved")

    transition_to_approved.short_description = "Transition selected to 'approved'"

    def transition_to_closed(self, request, queryset):
        self._bulk_transition(request, queryset, "closed")

    transition_to_closed.short_description = "Transition selected to 'closed'"
