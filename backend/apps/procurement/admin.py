from django.contrib import admin

from .models import Supplier, PurchaseRequisition, PurchaseOrder, PurchaseOrderLine


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "email", "phone", "is_active", "company")
    search_fields = ("code", "name", "email", "phone")
    list_filter = ("is_active", "company")


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 0


@admin.register(PurchaseRequisition)
class PurchaseRequisitionAdmin(admin.ModelAdmin):
    list_display = ("requisition_number", "status", "priority", "cost_center", "requested_by", "company", "created_at")
    list_filter = ("status", "priority", "company")
    search_fields = ("requisition_number", "justification")
    date_hierarchy = "created_at"


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "supplier", "order_date", "status", "total_amount", "company")
    list_filter = ("status", "order_date", "company")
    search_fields = ("order_number", "external_reference", "notes")
    date_hierarchy = "order_date"
    inlines = [PurchaseOrderLineInline]

