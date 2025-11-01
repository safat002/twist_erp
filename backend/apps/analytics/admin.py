from django.contrib import admin

from .models import WarehouseRunLog, SalesPerformanceSnapshot, CashflowSnapshot


@admin.register(WarehouseRunLog)
class WarehouseRunLogAdmin(admin.ModelAdmin):
    list_display = ("run_at", "run_type", "status", "company_code", "processed_records")
    list_filter = ("status", "run_type")
    search_fields = ("company_code", "company_name", "message")
    date_hierarchy = "run_at"


@admin.register(SalesPerformanceSnapshot)
class SalesPerformanceSnapshotAdmin(admin.ModelAdmin):
    list_display = ("snapshot_date", "period", "company_code", "total_orders", "total_revenue")
    list_filter = ("period",)
    search_fields = ("company_code", "company_name")
    date_hierarchy = "snapshot_date"


@admin.register(CashflowSnapshot)
class CashflowSnapshotAdmin(admin.ModelAdmin):
    list_display = ("snapshot_date", "period", "company_code", "net_cash")
    list_filter = ("period",)
    search_fields = ("company_code", "company_name")
    date_hierarchy = "snapshot_date"

