from django.contrib import admin

from .models import WorkOrder, WorkOrderComponent, BillOfMaterial, BillOfMaterialComponent


class WorkOrderComponentInline(admin.TabularInline):
    model = WorkOrderComponent
    extra = 0


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ("number", "product", "quantity_planned", "status", "priority", "company", "created_at")
    list_filter = ("status", "priority", "company")
    search_fields = ("number", "notes")
    date_hierarchy = "created_at"
    inlines = [WorkOrderComponentInline]


class BillOfMaterialComponentInline(admin.TabularInline):
    model = BillOfMaterialComponent
    extra = 0


@admin.register(BillOfMaterial)
class BillOfMaterialAdmin(admin.ModelAdmin):
    list_display = ("code", "product", "version", "status", "company")
    list_filter = ("status", "company")
    search_fields = ("code", "name", "product__name", "product__code")
    inlines = [BillOfMaterialComponentInline]

