# backend/apps/inventory/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ProductCategory, UnitOfMeasure, Product,
    Warehouse, StockLedger, StockMovement, StockMovementLine
)

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'parent_category', 'is_active', 'company']
    list_filter = ['is_active', 'company']
    search_fields = ['code', 'name']

@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active", "company"]
    list_filter = ["is_active", "company"]
    search_fields = ["code", "name"]
    readonly_fields = ["created_at", "updated_at"]
    exclude = ["created_by"]

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'category', 'product_type',
        'colored_cost', 'colored_price', 'stock_status', 
        'is_active', 'company'
    ]
    list_filter = ['product_type', 'category', 'is_active', 'company']
    search_fields = ['code', 'name', 'description']

    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'code', 'name', 'description', 
                      'category', 'product_type')
        }),
        ('Unit & Tracking', {
            'fields': ('uom', 'track_inventory', 'track_serial', 'track_batch')
        }),
        ('Pricing', {
            'fields': ('cost_price', 'selling_price')
        }),
        ('Inventory', {
            'fields': ('reorder_level', 'reorder_quantity')
        }),
        ('Accounting', {
            'fields': ('inventory_account', 'income_account', 'expense_account')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    def colored_cost(self, obj):
        return format_html('৳ {:,.2f}', obj.cost_price)
    colored_cost.short_description = 'Cost'

    def colored_price(self, obj):
        return format_html(
            '<strong style="color: green;">৳ {:,.2f}</strong>',
            obj.selling_price
        )
    colored_price.short_description = 'Price'

    def stock_status(self, obj):
        # Mock stock check
        stock_qty = 0  # Get from StockLedger
        if stock_qty <= obj.reorder_level:
            color = 'red'
            status = 'Low Stock'
        else:
            color = 'green'
            status = 'In Stock'

        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            status
        )
    stock_status.short_description = 'Stock'

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'warehouse_type', 'address', 'is_active', 'company']
    list_filter = ['warehouse_type', 'is_active', 'company']
    search_fields = ['code', 'name', 'address']

class StockMovementLineInline(admin.TabularInline):
    model = StockMovementLine
    extra = 1
    fields = ['product', 'quantity', 'rate', 'batch_no', 'serial_no']

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        'movement_number', 'movement_type', 'movement_date',
        'from_warehouse', 'to_warehouse', 'status_badge', 'company'
    ]
    list_filter = ['movement_type', 'status', 'movement_date', 'company']
    search_fields = ['movement_number', 'reference']
    date_hierarchy = 'movement_date'
    inlines = [StockMovementLineInline]

    def status_badge(self, obj):
        colors = {
            'DRAFT': 'gray',
            'SUBMITTED': 'blue',
            'COMPLETED': 'green',
            'CANCELLED': 'red'
        }
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.status
        )
    status_badge.short_description = 'Status'

@admin.register(StockLedger)
class StockLedgerAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_date', 'product', 'warehouse',
        'transaction_type', 'colored_qty_in', 'colored_qty_out',
        'colored_balance', 'company'
    ]
    list_filter = ['transaction_type', 'transaction_date', 'warehouse', 'company']
    search_fields = ['product__name', 'product__code']
    date_hierarchy = 'transaction_date'

    def colored_qty_in(self, obj):
        if obj.qty_in > 0:
            return format_html(
                '<span style="color: green;">+{:.2f}</span>',
                obj.qty_in
            )
        return '-'
    colored_qty_in.short_description = 'In'

    def colored_qty_out(self, obj):
        if obj.qty_out > 0:
            return format_html(
                '<span style="color: red;">-{:.2f}</span>',
                obj.qty_out
            )
        return '-'
    colored_qty_out.short_description = 'Out'

    def colored_balance(self, obj):
        return format_html('<strong>{:.2f}</strong>', obj.balance_qty)
    colored_balance.short_description = 'Balance'
