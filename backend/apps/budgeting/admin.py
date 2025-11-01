from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from .models import (
    Budget,
    BudgetConsumptionSnapshot,
    BudgetLine,
    BudgetOverrideRequest,
    CostCenter,
    BudgetItemCode,
)


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "cost_center_type", "owner", "company", "is_active"]
    list_filter = ["company", "cost_center_type", "is_active"]
    search_fields = ["code", "name", "owner__username", "owner__email"]
    ordering = ["code"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("company", "company_group", "code", "name", "cost_center_type", "parent")}),
        ("Ownership", {"fields": ("owner", "deputy_owner", "default_currency", "tags")}),
        ("Status", {"fields": ("is_active", "description", "kpi_snapshot", "created_at", "updated_at")}),
    )


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ["name", "cost_center", "budget_type", "period_start", "period_end", "amount", "consumed", "status", "company"]
    list_filter = ["company", "budget_type", "status", "period_start"]
    search_fields = ["name", "cost_center__code", "cost_center__name"]
    readonly_fields = ["amount", "consumed", "created_at", "updated_at", "approved_by", "approved_at", "locked_at"]
    actions = ["mark_active", "lock_budgets", "close_budgets", "reopen_budgets", "recalculate_totals"]

    def mark_active(self, request, queryset):
        updated = 0
        for budget in queryset:
            budget.mark_active(user=request.user)
            updated += 1
        self.message_user(request, f"{updated} budget(s) marked ACTIVE.", level=messages.SUCCESS)

    mark_active.short_description = "Activate selected budgets"

    def lock_budgets(self, request, queryset):
        updated = queryset.update(status=Budget.STATUS_LOCKED, locked_at=timezone.now())
        self.message_user(request, f"{updated} budget(s) locked.", level=messages.INFO)

    lock_budgets.short_description = "Lock selected budgets"

    def close_budgets(self, request, queryset):
        updated = queryset.update(status=Budget.STATUS_CLOSED, updated_at=timezone.now())
        self.message_user(request, f"{updated} budget(s) marked as CLOSED.", level=messages.SUCCESS)

    close_budgets.short_description = "Mark selected budgets as CLOSED"

    close_budgets.short_description = "Mark selected budgets as CLOSED"

    def reopen_budgets(self, request, queryset):
        updated = queryset.update(status=Budget.STATUS_ACTIVE)
        self.message_user(request, f"{updated} budget(s) reopened (ACTIVE).", level=messages.SUCCESS)

    reopen_budgets.short_description = "Reopen selected budgets (ACTIVE)"

    def recalculate_totals(self, request, queryset):
        for budget in queryset:
            budget.recalculate_totals(commit=True)
        self.message_user(request, "Recalculated totals for selected budgets.", level=messages.SUCCESS)

    recalculate_totals.short_description = "Recalculate totals from budget lines"


@admin.register(BudgetLine)
class BudgetLineAdmin(admin.ModelAdmin):
    list_display = ["budget", "sequence", "item_name", "procurement_class", "value_limit", "consumed_value", "remaining_value", "is_active"]
    list_filter = ["procurement_class", "is_active", "budget__company"]
    search_fields = ["item_name", "item_code", "budget__name"]
    readonly_fields = ["consumed_quantity", "consumed_value", "created_at", "updated_at"]
    ordering = ["budget", "sequence"]


@admin.register(BudgetOverrideRequest)
class BudgetOverrideRequestAdmin(admin.ModelAdmin):
    list_display = ["reference_id", "cost_center", "requested_amount", "status", "requested_by", "approver", "created_at"]
    list_filter = ["status", "company"]
    search_fields = ["reference_id", "reason", "cost_center__name", "requested_by__username"]
    readonly_fields = ["created_at", "updated_at", "approved_at"]
    actions = ["mark_approved", "mark_rejected"]

    def mark_approved(self, request, queryset):
        updated = queryset.filter(status=BudgetOverrideRequest.STATUS_PENDING).update(
            status=BudgetOverrideRequest.STATUS_APPROVED,
            approver=request.user,
            approved_at=timezone.now(),
        )
        self.message_user(request, f"{updated} override request(s) marked approved.", level=messages.SUCCESS)

    mark_approved.short_description = "Approve selected override requests"

    def mark_rejected(self, request, queryset):
        updated = queryset.filter(status=BudgetOverrideRequest.STATUS_PENDING).update(
            status=BudgetOverrideRequest.STATUS_REJECTED,
            approver=request.user,
            approved_at=timezone.now(),
        )
        self.message_user(request, f"{updated} override request(s) rejected.", level=messages.WARNING)

    mark_rejected.short_description = "Reject selected override requests"


@admin.register(BudgetConsumptionSnapshot)
class BudgetConsumptionSnapshotAdmin(admin.ModelAdmin):
    list_display = ["budget", "snapshot_date", "total_limit", "total_consumed", "total_remaining"]
    list_filter = ["snapshot_date", "budget__company"]
    search_fields = ["budget__name", "budget__cost_center__name"]


@admin.register(BudgetItemCode)
class BudgetItemCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "category", "uom", "standard_price", "is_active", "company"]
    list_filter = ["company", "category", "is_active"]
    search_fields = ["code", "name", "category"]
    ordering = ["code"]
