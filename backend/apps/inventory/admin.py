# backend/apps/inventory/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ProductCategory, UnitOfMeasure, Product,
    Warehouse, StockLedger, StockMovement, StockMovementLine,
    GoodsReceipt, GoodsReceiptLine, DeliveryOrder, DeliveryOrderLine,
    ItemValuationMethod, CostLayer, ValuationChangeLog
)

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'parent_category', 'is_active', 'company']
    list_filter = ['is_active', 'company']
    search_fields = ['code', 'name']

# Moved to Budgeting admin via proxy registration. Keep admin class here for reuse.
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
            'fields': (
                'uom', 'track_inventory', 'track_serial', 'track_batch',
                'prevent_expired_issuance', 'expiry_warning_days'
            )
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

class GoodsReceiptLineInline(admin.TabularInline):
    model = GoodsReceiptLine
    extra = 0
    fields = ['purchase_order_line', 'product', 'quantity_received', 'batch_no', 'expiry_date']
    readonly_fields = []

@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'supplier', 'receipt_date', 'status', 'quality_status', 'company']
    list_filter = ['status', 'quality_status', 'receipt_date', 'company']
    search_fields = ['receipt_number', 'supplier__name', 'purchase_order__order_number']
    date_hierarchy = 'receipt_date'
    inlines = [GoodsReceiptLineInline]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Header', {
            'fields': ('company', 'receipt_number', 'receipt_date', 'status', 'notes')
        }),
        ('Supplier & PO', {
            'fields': ('supplier', 'purchase_order')
        }),
        ('Quality Control', {
            'fields': ('quality_status', 'hold_reason', 'quality_checked_by', 'quality_checked_at')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class DeliveryOrderLineInline(admin.TabularInline):
    model = DeliveryOrderLine
    extra = 0
    fields = ['sales_order_line', 'product', 'quantity_shipped']

@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display = ['delivery_number', 'delivery_date', 'status', 'customer', 'company']
    list_filter = ['status', 'delivery_date', 'company']
    search_fields = ['delivery_number', 'sales_order__order_number', 'customer__name']
    date_hierarchy = 'delivery_date'
    inlines = [DeliveryOrderLineInline]

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
        'transaction_date', 'item', 'warehouse',
        'transaction_type', 'colored_qty_in', 'colored_qty_out',
        'colored_balance', 'company'
    ]
    list_filter = ['transaction_type', 'transaction_date', 'warehouse', 'company']
    search_fields = ['product__name', 'product__code']
    date_hierarchy = 'transaction_date'

    def colored_qty_in(self, obj):
        # StockLedger stores signed quantity; positive is IN, negative is OUT
        if getattr(obj, 'quantity', 0) > 0:
            return format_html(
                '<span style="color: green;">+{:.2f}</span>',
                obj.quantity
            )
        return '-'
    colored_qty_in.short_description = 'In'

    def colored_qty_out(self, obj):
        # Show absolute value for OUT movements (negative quantity)
        if getattr(obj, 'quantity', 0) < 0:
            return format_html(
                '<span style="color: red;">-{:.2f}</span>',
                abs(obj.quantity)
            )
        return '-'
    colored_qty_out.short_description = 'Out'

    def colored_balance(self, obj):
        return format_html('<strong>{:.2f}</strong>', obj.balance_qty)
    colored_balance.short_description = 'Balance'

from .models import InternalRequisition

@admin.register(InternalRequisition)
class InternalRequisitionAdmin(admin.ModelAdmin):
    list_display = ("requisition_number", "company", "request_date", "needed_by", "status")
    list_filter = ("company", "status")
    search_fields = ("requisition_number", "purpose")
    readonly_fields = ("requisition_number", "created_at", "updated_at", "created_by")
    date_hierarchy = 'request_date'

    actions = ["mark_submitted", "mark_approved", "mark_cancelled"]

    def _bulk_update_status(self, request, queryset, status_value: str):
        updated = queryset.update(status=status_value)
        self.message_user(request, f"Updated {updated} requisitions to {status_value}")

    def mark_submitted(self, request, queryset):
        self._bulk_update_status(request, queryset, "SUBMITTED")
    mark_submitted.short_description = "Mark selected as SUBMITTED"

    def mark_approved(self, request, queryset):
        self._bulk_update_status(request, queryset, "APPROVED")
    mark_approved.short_description = "Mark selected as APPROVED"

    def mark_cancelled(self, request, queryset):
        self._bulk_update_status(request, queryset, "CANCELLED")
    mark_cancelled.short_description = "Mark selected as CANCELLED"

    def export_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename=internal_requisitions.csv'
        writer = csv.writer(resp)
        writer.writerow(['Number', 'Company', 'Request Date', 'Needed By', 'Status', 'Items', 'Purpose'])
        for obj in queryset:
            writer.writerow([
                obj.requisition_number,
                getattr(obj.company, 'code', obj.company_id),
                obj.request_date,
                obj.needed_by,
                obj.status,
                len(obj.lines or []),
                (obj.purpose or '').replace('\n', ' '),
            ])
        return resp
    export_csv.short_description = "Export selected to CSV"

    actions.append('export_csv')


# ========================================
# VALUATION ADMIN CLASSES
# ========================================

@admin.register(ItemValuationMethod)
class ItemValuationMethodAdmin(admin.ModelAdmin):
    """Admin interface for Item Valuation Methods"""
    list_display = [
        'product_info', 'warehouse_info', 'method_badge',
        'avg_period', 'effective_date', 'status_badge', 'company'
    ]
    list_filter = ['valuation_method', 'is_active', 'effective_date', 'company', 'warehouse']
    search_fields = ['product__code', 'product__name', 'warehouse__code', 'warehouse__name']
    date_hierarchy = 'effective_date'
    readonly_fields = ['created_by', 'created_at', 'updated_at']

    fieldsets = (
        ('Product & Warehouse', {
            'fields': ('company', 'product', 'warehouse')
        }),
        ('Valuation Configuration', {
            'fields': ('valuation_method', 'avg_period', 'effective_date')
        }),
        ('Control Settings', {
            'fields': ('allow_negative_inventory', 'prevent_cost_below_zero', 'is_active')
        }),
        ('Audit Info', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def product_info(self, obj):
        return format_html(
            '<strong>{}</strong><br/><small>{}</small>',
            obj.product.code,
            obj.product.name[:30]
        )
    product_info.short_description = 'Product'

    def warehouse_info(self, obj):
        return format_html(
            '<strong>{}</strong><br/><small>{}</small>',
            obj.warehouse.code,
            obj.warehouse.name[:30]
        )
    warehouse_info.short_description = 'Warehouse'

    def method_badge(self, obj):
        colors = {
            'FIFO': '#17a2b8',  # info
            'LIFO': '#6c757d',  # secondary
            'WEIGHTED_AVG': '#28a745',  # success
            'STANDARD': '#ffc107'  # warning
        }
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 4px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.valuation_method, '#6c757d'),
            obj.get_valuation_method_display()
        )
    method_badge.short_description = 'Method'

    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">● Active</span>'
            )
        return format_html(
            '<span style="color: gray;">○ Inactive</span>'
        )
    status_badge.short_description = 'Status'

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CostLayer)
class CostLayerAdmin(admin.ModelAdmin):
    """Admin interface for Cost Layers - Read-only view"""
    list_display = [
        'layer_info', 'product_code', 'warehouse_code',
        'receipt_date', 'colored_qty', 'colored_cost',
        'percentage_bar', 'layer_status', 'company'
    ]
    list_filter = ['is_closed', 'receipt_date', 'warehouse', 'company']
    search_fields = ['product__code', 'product__name', 'batch_no', 'serial_no']
    date_hierarchy = 'receipt_date'
    readonly_fields = [
        'company', 'product', 'warehouse', 'receipt_date',
        'qty_received', 'cost_per_unit', 'total_cost',
        'qty_remaining', 'cost_remaining', 'fifo_sequence',
        'batch_no', 'serial_no', 'is_standard_cost',
        'landed_cost_adjustment', 'adjustment_date', 'adjustment_reason',
        'source_document_type', 'source_document_id',
        'immutable_after_post', 'is_closed', 'created_at'
    ]

    fieldsets = (
        ('Layer Information', {
            'fields': ('company', 'product', 'warehouse', 'fifo_sequence')
        }),
        ('Receipt Details', {
            'fields': ('receipt_date', 'qty_received', 'cost_per_unit', 'total_cost')
        }),
        ('Current Status', {
            'fields': ('qty_remaining', 'cost_remaining', 'is_closed')
        }),
        ('Batch/Serial', {
            'fields': ('batch_no', 'serial_no'),
            'classes': ('collapse',)
        }),
        ('Landed Cost Adjustments', {
            'fields': ('landed_cost_adjustment', 'adjustment_date', 'adjustment_reason'),
            'classes': ('collapse',)
        }),
        ('Source Document', {
            'fields': ('source_document_type', 'source_document_id'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('is_standard_cost', 'immutable_after_post', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        # Cost layers are created automatically, no manual creation
        return False

    def has_delete_permission(self, request, obj=None):
        # Cost layers are immutable
        return False

    def layer_info(self, obj):
        return format_html(
            '<strong>Layer #{}</strong><br/><small>{}</small>',
            obj.fifo_sequence,
            obj.source_document_type
        )
    layer_info.short_description = 'Layer'

    def product_code(self, obj):
        return obj.product.code
    product_code.short_description = 'Product'

    def warehouse_code(self, obj):
        return obj.warehouse.code
    warehouse_code.short_description = 'WH'

    def colored_qty(self, obj):
        return format_html(
            '<div style="text-align: right;">'
            '<strong>{:,.2f}</strong><br/>'
            '<small style="color: gray;">{:,.2f} rem.</small>'
            '</div>',
            obj.qty_received,
            obj.qty_remaining
        )
    colored_qty.short_description = 'Quantity'

    def colored_cost(self, obj):
        effective_cost = obj.cost_per_unit + obj.landed_cost_adjustment
        return format_html(
            '<div style="text-align: right;">'
            '<strong>৳ {:,.2f}</strong><br/>'
            '<small style="color: gray;">৳ {:,.2f} total</small>'
            '</div>',
            effective_cost,
            obj.cost_remaining
        )
    colored_cost.short_description = 'Cost'

    def percentage_bar(self, obj):
        if obj.qty_received > 0:
            consumed_pct = ((obj.qty_received - obj.qty_remaining) / obj.qty_received) * 100
            remaining_pct = 100 - consumed_pct

            return format_html(
                '<div style="width: 100px; background: #e9ecef; border-radius: 3px; overflow: hidden;">'
                '<div style="width: {}%; background: #28a745; height: 20px; float: left;"></div>'
                '<div style="width: {}%; background: #ffc107; height: 20px; float: left;"></div>'
                '</div>'
                '<small>{:.0f}% consumed</small>',
                consumed_pct, remaining_pct, consumed_pct
            )
        return '-'
    percentage_bar.short_description = 'Usage'

    def layer_status(self, obj):
        if obj.is_closed:
            return format_html(
                '<span style="color: gray;">✓ Closed</span>'
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">● Open</span>'
        )
    layer_status.short_description = 'Status'


@admin.register(ValuationChangeLog)
class ValuationChangeLogAdmin(admin.ModelAdmin):
    """Admin interface for Valuation Change Logs"""
    list_display = [
        'change_info', 'product_code', 'warehouse_code',
        'method_change', 'effective_date', 'impact_display',
        'status_badge', 'company'
    ]
    list_filter = ['status', 'effective_date', 'old_method', 'new_method', 'company']
    search_fields = ['product__code', 'product__name', 'reason']
    date_hierarchy = 'requested_date'
    readonly_fields = [
        'company', 'requested_by', 'requested_date',
        'approved_by', 'approval_date', 'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Change Request', {
            'fields': ('company', 'product', 'warehouse', 'effective_date')
        }),
        ('Method Change', {
            'fields': ('old_method', 'new_method', 'reason')
        }),
        ('Financial Impact', {
            'fields': ('old_inventory_value', 'new_inventory_value', 'revaluation_amount', 'revaluation_je_id')
        }),
        ('Approval Workflow', {
            'fields': ('status', 'rejection_reason')
        }),
        ('Audit Trail', {
            'fields': ('requested_by', 'requested_date', 'approved_by', 'approval_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_changes', 'reject_changes']

    def change_info(self, obj):
        return format_html(
            '<strong>Change #{}</strong><br/>'
            '<small>{}</small>',
            obj.id,
            obj.requested_date.strftime('%Y-%m-%d')
        )
    change_info.short_description = 'Request'

    def product_code(self, obj):
        return obj.product.code
    product_code.short_description = 'Product'

    def warehouse_code(self, obj):
        return obj.warehouse.code
    warehouse_code.short_description = 'WH'

    def method_change(self, obj):
        return format_html(
            '<span style="background: #ffc107; padding: 2px 8px; border-radius: 3px; color: black;">{}</span> '
            '→ '
            '<span style="background: #28a745; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.get_old_method_display(),
            obj.get_new_method_display()
        )
    method_change.short_description = 'Change'

    def impact_display(self, obj):
        if obj.revaluation_amount:
            color = 'green' if obj.revaluation_amount > 0 else 'red'
            sign = '+' if obj.revaluation_amount > 0 else ''
            return format_html(
                '<div style="text-align: right; color: {}; font-weight: bold;">{} ৳ {:,.2f}</div>',
                color, sign, obj.revaluation_amount
            )
        return '-'
    impact_display.short_description = 'Impact'

    def status_badge(self, obj):
        colors = {
            'PENDING': '#ffc107',
            'APPROVED': '#28a745',
            'REJECTED': '#dc3545',
            'EFFECTIVE': '#17a2b8'
        }
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 4px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def approve_changes(self, request, queryset):
        """Bulk approve change requests"""
        from django.utils import timezone
        pending = queryset.filter(status='PENDING')
        count = 0
        for change in pending:
            change.status = 'APPROVED'
            change.approved_by = request.user
            change.approval_date = timezone.now()
            change.save()

            # Create new valuation method
            ItemValuationMethod.objects.create(
                company=change.company,
                product=change.product,
                warehouse=change.warehouse,
                valuation_method=change.new_method,
                effective_date=change.effective_date,
                created_by=request.user,
                is_active=True
            )

            change.status = 'EFFECTIVE'
            change.save()
            count += 1

        self.message_user(request, f"Approved {count} valuation changes")
    approve_changes.short_description = "Approve selected change requests"

    def reject_changes(self, request, queryset):
        """Bulk reject change requests"""
        from django.utils import timezone
        pending = queryset.filter(status='PENDING')
        updated = pending.update(
            status='REJECTED',
            approved_by=request.user,
            approval_date=timezone.now(),
            rejection_reason='Bulk rejected by admin'
        )
        self.message_user(request, f"Rejected {updated} valuation changes")
    reject_changes.short_description = "Reject selected change requests"
