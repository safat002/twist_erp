# backend/apps/inventory/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ProductCategory, UnitOfMeasure, Product,
    Warehouse, WarehouseBin, StockLedger, StockMovement, StockMovementLine,
    GoodsReceipt, GoodsReceiptLine, DeliveryOrder, DeliveryOrderLine,
    InternalRequisition, ItemCategory,
    ItemValuationMethod, CostLayer, ValuationChangeLog,
    Item, ItemOperationalExtension, ItemWarehouseConfig,
    ItemSupplier, ItemUOMConversion, MovementEvent, InTransitShipmentLine,
    StandardCostVariance, PurchasePriceVariance,
    LandedCostComponent, LandedCostLineApportionment,
    LandedCostVoucher, LandedCostAllocation,
    ReturnToVendor, ReturnToVendorLine,
    # Phase 3: QC & Compliance
    StockHold, QCCheckpoint, QCResult, BatchLot, SerialNumber,
    # Warehouse Category Mapping
    WarehouseCategoryMapping, WarehouseOverrideLog
)

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'parent_category', 'is_active', 'company']
    list_filter = ['is_active', 'company']
    search_fields = ['code', 'name']
    readonly_fields = ['code']

# Moved to Budgeting admin via proxy registration. Keep admin class here for reuse.
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active", "company"]
    list_filter = ["is_active", "company"]
    search_fields = ["code", "name"]
    readonly_fields = ["code", "created_at", "updated_at"]
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
    readonly_fields = ['code']

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
    readonly_fields = ['code']

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['code', 'budget_item', 'item_type', 'category', 'is_active', 'company']
    list_filter = ['item_type', 'category', 'is_active', 'company']
    search_fields = ['code', 'name', 'budget_item__code', 'budget_item__name']
    autocomplete_fields = ['budget_item', 'category', 'uom']
    readonly_fields = ['code', 'created_at', 'updated_at']

@admin.register(ItemOperationalExtension)
class ItemOperationalExtensionAdmin(admin.ModelAdmin):
    list_display = ['budget_item', 'hazmat_class', 'storage_class', 'requires_batch_tracking', 'requires_serial_tracking', 'requires_expiry_tracking', 'company']
    list_filter = ['requires_batch_tracking', 'requires_serial_tracking', 'requires_expiry_tracking', 'hazmat_class', 'storage_class', 'company']
    search_fields = ['budget_item__code', 'budget_item__name', 'barcode', 'qr_code']
    autocomplete_fields = ['budget_item', 'budget_item', 'company', 'purchase_uom', 'stock_uom', 'sales_uom']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ItemWarehouseConfig)
class ItemWarehouseConfigAdmin(admin.ModelAdmin):
    list_display = ['budget_item', 'warehouse', 'pack_size_qty', 'min_stock_level', 'max_stock_level', 'reorder_point', 'is_active', 'company']
    list_filter = ['is_active', 'warehouse', 'company']
    search_fields = ['budget_item__code', 'budget_item__name', 'warehouse__code', 'warehouse__name']
    autocomplete_fields = ['budget_item', 'budget_item', 'warehouse', 'company', 'default_bin', 'pack_size_uom']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ItemSupplier)
class ItemSupplierAdmin(admin.ModelAdmin):
    list_display = ['budget_item', 'supplier', 'supplier_item_code', 'moq_qty', 'preferred_rank', 'is_active', 'company']
    list_filter = ['is_active', 'preferred_rank', 'company']
    search_fields = ['budget_item__code', 'budget_item__name', 'supplier__name', 'supplier_item_code']
    autocomplete_fields = ['budget_item', 'budget_item', 'supplier', 'company', 'supplier_pack_uom']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ItemUOMConversion)
class ItemUOMConversionAdmin(admin.ModelAdmin):
    list_display = ['budget_item', 'from_uom', 'to_uom', 'conversion_factor', 'effective_date', 'precedence', 'company']
    list_filter = ['is_purchase_conversion', 'is_sales_conversion', 'is_stock_conversion', 'company']
    search_fields = ['budget_item__code', 'budget_item__name', 'from_uom__code', 'to_uom__code']
    autocomplete_fields = ['budget_item', 'budget_item', 'company', 'from_uom', 'to_uom']
    readonly_fields = ['created_at', 'updated_at']

class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        base = super().get_readonly_fields(request, obj)
        if base:
            return base
        field_names = [field.name for field in self.model._meta.fields]
        field_names += [field.name for field in self.model._meta.many_to_many]
        return field_names

@admin.register(MovementEvent)
class MovementEventAdmin(ReadOnlyAdmin):
    list_display = ['event_timestamp', 'event_type', 'budget_item', 'warehouse', 'qty_change', 'reference_document_type', 'reference_document_id']
    list_filter = ['event_type', 'event_date', 'warehouse', 'company']
    search_fields = ['item__code', 'item__name', 'reference_number']
    autocomplete_fields = ['company', 'movement', 'movement_line', 'budget_item', 'warehouse', 'stock_uom', 'source_uom']

@admin.register(InTransitShipmentLine)
class InTransitShipmentLineAdmin(ReadOnlyAdmin):
    list_display = ['budget_item', 'from_warehouse', 'to_warehouse', 'quantity', 'created_at']
    list_filter = ['from_warehouse', 'to_warehouse', 'company']
    search_fields = ['item__code', 'item__name']
    autocomplete_fields = ['company', 'movement', 'movement_line', 'budget_item', 'from_warehouse', 'to_warehouse']

class StockMovementLineInline(admin.TabularInline):
    model = StockMovementLine
    extra = 1
    fields = ['budget_item', 'quantity', 'rate', 'batch_no', 'serial_no']

class GoodsReceiptLineInline(admin.TabularInline):
    model = GoodsReceiptLine
    extra = 0
    fields = ['purchase_order_line', 'budget_item', 'quantity_received', 'batch_no', 'expiry_date']
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
    fields = ['sales_order_line', 'budget_item', 'quantity_shipped']

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
        'transaction_date', 'budget_item', 'warehouse',
        'transaction_type', 'colored_qty_in', 'colored_qty_out',
        'colored_balance', 'company'
    ]
    list_filter = ['transaction_type', 'transaction_date', 'warehouse', 'company']
    search_fields = ['budget_item__name', 'budget_item__code']
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
        balance = float(obj.balance_qty) if obj.balance_qty is not None else 0.0
        balance_str = f"{balance:.2f}"
        return format_html('<strong>{}</strong>', balance_str)
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
    search_fields = ['budget_item__code', 'budget_item__name', 'warehouse__code', 'warehouse__name']
    date_hierarchy = 'effective_date'
    readonly_fields = ['created_by', 'created_at', 'updated_at']

    fieldsets = (
        ('Product & Warehouse', {
            'fields': ('company', 'budget_item', 'warehouse')
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
            obj.budget_item.code,
            obj.budget_item.name[:30]
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
    search_fields = ['budget_item__code', 'budget_item__name', 'batch_no', 'serial_no']
    date_hierarchy = 'receipt_date'
    readonly_fields = [
        'company', 'budget_item', 'warehouse', 'receipt_date',
        'qty_received', 'cost_per_unit', 'total_cost',
        'qty_remaining', 'cost_remaining', 'fifo_sequence',
        'batch_no', 'serial_no', 'is_standard_cost',
        'landed_cost_adjustment', 'adjustment_date', 'adjustment_reason',
        'source_document_type', 'source_document_id',
        'immutable_after_post', 'is_closed', 'created_at'
    ]

    fieldsets = (
        ('Layer Information', {
            'fields': ('company', 'budget_item', 'warehouse', 'fifo_sequence')
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
    def product_code(self, obj):
        if obj.budget_item:
            return obj.budget_item.code
        return 'N/A'
    product_code.short_description = 'Product'

    def warehouse_code(self, obj):
        return obj.warehouse.code
    warehouse_code.short_description = 'WH'

    def colored_qty(self, obj):
        qty_received = float(obj.qty_received) if obj.qty_received is not None else 0.0
        qty_remaining = float(obj.qty_remaining) if obj.qty_remaining is not None else 0.0
        # Format numbers first as strings to avoid SafeString issues
        qty_recv_str = f"{qty_received:,.2f}"
        qty_rem_str = f"{qty_remaining:,.2f}"
        return format_html(
            '<div style="text-align: right;">'
            '<strong>{}</strong><br/>'
            '<small style="color: gray;">{} rem.</small>'
            '</div>',
            qty_recv_str,
            qty_rem_str
        )
    colored_qty.short_description = 'Quantity'

    def colored_cost(self, obj):
        cost_per_unit = float(obj.cost_per_unit) if obj.cost_per_unit is not None else 0.0
        landed_cost_adj = float(obj.landed_cost_adjustment) if obj.landed_cost_adjustment is not None else 0.0
        cost_remaining = float(obj.cost_remaining) if obj.cost_remaining is not None else 0.0
        effective_cost = cost_per_unit + landed_cost_adj
        # Format numbers first as strings to avoid SafeString issues
        eff_cost_str = f"{effective_cost:,.2f}"
        cost_rem_str = f"{cost_remaining:,.2f}"
        return format_html(
            '<div style="text-align: right;">'
            '<strong>৳ {}</strong><br/>'
            '<small style="color: gray;">৳ {} total</small>'
            '</div>',
            eff_cost_str,
            cost_rem_str
        )
    colored_cost.short_description = 'Cost'

    def percentage_bar(self, obj):
        qty_received = float(obj.qty_received) if obj.qty_received is not None else 0.0
        qty_remaining = float(obj.qty_remaining) if obj.qty_remaining is not None else 0.0

        if qty_received > 0:
            consumed_pct = ((qty_received - qty_remaining) / qty_received) * 100
            remaining_pct = 100 - consumed_pct
            # Format numbers first as strings to avoid SafeString issues
            consumed_pct_str = f"{consumed_pct:.0f}"

            return format_html(
                '<div style="width: 100px; background: #e9ecef; border-radius: 3px; overflow: hidden;">'
                '<div style="width: {}%; background: #28a745; height: 20px; float: left;"></div>'
                '<div style="width: {}%; background: #ffc107; height: 20px; float: left;"></div>'
                '</div>'
                '<small>{}% consumed</small>',
                consumed_pct, remaining_pct, consumed_pct_str
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
    search_fields = ['budget_item__code', 'budget_item__name', 'reason']
    date_hierarchy = 'requested_date'
    readonly_fields = [
        'company', 'requested_by', 'requested_date',
        'approved_by', 'approval_date', 'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Change Request', {
            'fields': ('company', 'budget_item', 'warehouse', 'effective_date')
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
        return obj.budget_item.code
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


# ========================================
# PHASE 2: VARIANCE TRACKING ADMIN
# ========================================

@admin.register(StandardCostVariance)
class StandardCostVarianceAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'product_code_link', 'warehouse', 'transaction_date',
        'transaction_type', 'quantity', 'variance_badge',
        'total_variance_amount', 'posted_status', 'company'
    ]
    list_filter = [
        'transaction_type', 'variance_type', 'posted_to_gl',
        'transaction_date', 'company'
    ]
    search_fields = ['budget_item__code', 'budget_item__name', 'notes']
    readonly_fields = [
        'company', 'variance_per_unit', 'total_variance_amount',
        'variance_type', 'variance_je_id', 'posted_to_gl',
        'gl_posted_date', 'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Transaction Details', {
            'fields': ('company', 'budget_item', 'warehouse', 'transaction_date',
                      'transaction_type', 'reference_id')
        }),
        ('Cost Information', {
            'fields': ('standard_cost', 'actual_cost', 'quantity')
        }),
        ('Variance Calculation', {
            'fields': ('variance_per_unit', 'total_variance_amount', 'variance_type')
        }),
        ('GL Integration', {
            'fields': ('variance_je_id', 'posted_to_gl', 'gl_posted_date')
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )

    def product_code_link(self, obj):
        return format_html(
            '<a href="/admin/budgeting/budgetitemcode/{}/change/">{}</a>',
            obj.budget_item.id, obj.budget_item.code
        )
    product_code_link.short_description = 'Product'

    def variance_badge(self, obj):
        color = 'green' if obj.variance_type == 'FAVORABLE' else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.variance_type
        )
    variance_badge.short_description = 'Variance Type'

    def posted_status(self, obj):
        if obj.posted_to_gl:
            return format_html(
                '<span style="color: green;">✓ Posted (JE#{})</span>',
                obj.variance_je_id
            )
        return format_html('<span style="color: orange;">○ Pending</span>')
    posted_status.short_description = 'GL Status'


@admin.register(PurchasePriceVariance)
class PurchasePriceVarianceAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'grn_link', 'product_code', 'warehouse',
        'po_price', 'invoice_price', 'variance_badge',
        'total_variance_amount', 'posted_status', 'company'
    ]
    list_filter = [
        'variance_type', 'posted_to_gl', 'goods_receipt__receipt_date', 'company'
    ]
    search_fields = [
        'budget_item__code', 'budget_item__name',
        'goods_receipt__grn_number', 'notes'
    ]
    readonly_fields = [
        'company', 'variance_per_unit', 'total_variance_amount',
        'variance_type', 'variance_je_id', 'posted_to_gl',
        'gl_posted_date', 'created_at', 'updated_at'
    ]

    fieldsets = (
        ('GRN Details', {
            'fields': ('company', 'goods_receipt', 'budget_item', 'warehouse')
        }),
        ('Price Information', {
            'fields': ('po_price', 'invoice_price', 'quantity')
        }),
        ('Variance Calculation', {
            'fields': ('variance_per_unit', 'total_variance_amount', 'variance_type')
        }),
        ('GL Integration', {
            'fields': ('variance_je_id', 'posted_to_gl', 'gl_posted_date')
        }),
        ('Additional Info', {
            'fields': ('supplier_id', 'notes', 'created_at', 'updated_at')
        }),
    )

    def grn_link(self, obj):
        return format_html(
            '<a href="/admin/inventory/goodsreceipt/{}/change/">GRN#{}</a>',
            obj.goods_receipt.id, obj.goods_receipt.grn_number
        )
    grn_link.short_description = 'GRN'

    def product_code(self, obj):
        return obj.budget_item.code
    product_code.short_description = 'Product'

    def variance_badge(self, obj):
        color = 'green' if obj.variance_type == 'FAVORABLE' else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.variance_type
        )
    variance_badge.short_description = 'Variance Type'

    def posted_status(self, obj):
        if obj.posted_to_gl:
            return format_html(
                '<span style="color: green;">✓ Posted (JE#{})</span>',
                obj.variance_je_id
            )
        return format_html('<span style="color: orange;">○ Pending</span>')
    posted_status.short_description = 'GL Status'


# ========================================
# PHASE 2: LANDED COST ADMIN
# ========================================

class LandedCostLineApportionmentInline(admin.TabularInline):
    model = LandedCostLineApportionment
    extra = 0
    readonly_fields = [
        'budget_item', 'basis_value', 'allocation_percentage',
        'apportioned_amount', 'cost_per_unit_adjustment'
    ]
    fields = [
        'goods_receipt_line', 'budget_item', 'basis_value',
        'allocation_percentage', 'apportioned_amount',
        'cost_per_unit_adjustment'
    ]
    can_delete = False


@admin.register(LandedCostComponent)
class LandedCostComponentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'grn_link', 'component_type', 'total_amount',
        'apportionment_method', 'posted_status', 'applied_date', 'company'
    ]
    list_filter = [
        'component_type', 'apportionment_method', 'posted_to_gl',
        'created_at', 'company'
    ]
    search_fields = [
        'goods_receipt__grn_number', 'description',
        'invoice_number', 'notes'
    ]
    readonly_fields = [
        'company', 'apportioned_to_inventory', 'apportioned_to_cogs',
        'je_id', 'posted_to_gl', 'gl_posted_date', 'applied_by',
        'applied_date', 'created_at', 'updated_at'
    ]
    inlines = [LandedCostLineApportionmentInline]

    fieldsets = (
        ('GRN & Component', {
            'fields': ('company', 'goods_receipt', 'component_type', 'description')
        }),
        ('Cost Information', {
            'fields': ('total_amount', 'currency', 'apportionment_method')
        }),
        ('Apportionment Results', {
            'fields': ('apportioned_to_inventory', 'apportioned_to_cogs')
        }),
        ('Invoice Details', {
            'fields': ('invoice_number', 'invoice_date', 'supplier_id')
        }),
        ('GL Integration', {
            'fields': ('je_id', 'posted_to_gl', 'gl_posted_date')
        }),
        ('Application Info', {
            'fields': ('applied_by', 'applied_date', 'notes', 'created_at', 'updated_at')
        }),
    )

    def grn_link(self, obj):
        return format_html(
            '<a href="/admin/inventory/goodsreceipt/{}/change/">GRN#{}</a>',
            obj.goods_receipt.id, obj.goods_receipt.grn_number
        )
    grn_link.short_description = 'GRN'

    def posted_status(self, obj):
        if obj.posted_to_gl:
            return format_html(
                '<span style="color: green;">✓ Posted (JE#{})</span>',
                obj.je_id
            )
        return format_html('<span style="color: orange;">○ Pending</span>')
    posted_status.short_description = 'GL Status'


@admin.register(LandedCostLineApportionment)
class LandedCostLineApportionmentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'component_type', 'product_code', 'basis_value',
        'allocation_percentage', 'apportioned_amount',
        'cost_per_unit_adjustment', 'company'
    ]
    list_filter = ['landed_cost_component__component_type', 'company']
    search_fields = ['budget_item__code', 'budget_item__name']
    readonly_fields = [
        'company', 'landed_cost_component', 'goods_receipt_line',
        'budget_item', 'basis_value', 'allocation_percentage',
        'apportioned_amount', 'cost_per_unit_adjustment', 'created_at'
    ]

    def component_type(self, obj):
        return obj.landed_cost_component.get_component_type_display()
    component_type.short_description = 'Component Type'

    def product_code(self, obj):
        return obj.budget_item.code
    product_code.short_description = 'Product'


# ============================================================================
# LANDED COST VOUCHER ADMIN
# ============================================================================

class LandedCostAllocationInline(admin.TabularInline):
    model = LandedCostAllocation
    extra = 0
    fields = [
        'goods_receipt', 'budget_item', 'allocated_amount',
        'allocation_percentage', 'to_inventory', 'to_cogs',
        'cost_per_unit_adjustment'
    ]
    readonly_fields = fields
    can_delete = False


@admin.register(LandedCostVoucher)
class LandedCostVoucherAdmin(admin.ModelAdmin):
    list_display = [
        'voucher_number', 'voucher_date', 'description_short',
        'total_cost', 'allocated_cost', 'unallocated_cost',
        'status_badge', 'gl_status', 'company'
    ]
    list_filter = ['status', 'posted_to_gl', 'voucher_date', 'company']
    search_fields = ['voucher_number', 'description', 'invoice_number', 'supplier_id']
    readonly_fields = [
        'voucher_number', 'allocated_cost', 'unallocated_cost',
        'je_id', 'gl_posted_date', 'created_at', 'updated_at'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'voucher_number', 'voucher_date', 'description', 'currency')
        }),
        ('Cost Details', {
            'fields': ('total_cost', 'allocated_cost', 'unallocated_cost')
        }),
        ('Invoice Information', {
            'fields': ('invoice_number', 'invoice_date', 'supplier_id')
        }),
        ('Workflow', {
            'fields': ('status', 'submitted_by', 'submitted_at', 'approved_by', 'approved_at')
        }),
        ('GL Integration', {
            'fields': ('je_id', 'posted_to_gl', 'gl_posted_date')
        }),
        ('Additional', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )
    inlines = [LandedCostAllocationInline]
    date_hierarchy = 'voucher_date'

    def description_short(self, obj):
        if len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description
    description_short.short_description = 'Description'

    def status_badge(self, obj):
        colors = {
            'DRAFT': 'gray',
            'SUBMITTED': 'blue',
            'APPROVED': 'green',
            'ALLOCATED': 'purple',
            'POSTED': 'darkgreen',
            'CANCELLED': 'red',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def gl_status(self, obj):
        if obj.posted_to_gl:
            return format_html(
                '<span style="color: green;">✓ Posted (JE#{})</span>',
                obj.je_id
            )
        return format_html('<span style="color: orange;">○ Pending</span>')
    gl_status.short_description = 'GL Status'


@admin.register(LandedCostAllocation)
class LandedCostAllocationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'voucher_number', 'grn_number', 'product_code',
        'allocated_amount', 'allocation_percentage',
        'to_inventory', 'to_cogs', 'cost_adjustment', 'company'
    ]
    list_filter = ['voucher__status', 'company', 'created_at']
    search_fields = [
        'voucher__voucher_number', 'goods_receipt__grn_number',
        'budget_item__code', 'budget_item__name'
    ]
    readonly_fields = [
        'company', 'voucher', 'goods_receipt', 'goods_receipt_line',
        'budget_item', 'cost_layer', 'allocated_amount', 'allocation_percentage',
        'to_inventory', 'to_cogs', 'original_cost_per_unit',
        'cost_per_unit_adjustment', 'new_cost_per_unit', 'created_at', 'updated_at'
    ]
    fieldsets = (
        ('Allocation Details', {
            'fields': ('company', 'voucher', 'goods_receipt', 'goods_receipt_line', 'budget_item', 'cost_layer')
        }),
        ('Cost Allocation', {
            'fields': (
                'allocated_amount', 'allocation_percentage',
                'to_inventory', 'to_cogs'
            )
        }),
        ('Cost Impact', {
            'fields': (
                'original_cost_per_unit', 'cost_per_unit_adjustment', 'new_cost_per_unit'
            )
        }),
        ('Additional', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )

    def voucher_number(self, obj):
        return obj.voucher.voucher_number
    voucher_number.short_description = 'Voucher'

    def grn_number(self, obj):
        return obj.goods_receipt.grn_number
    grn_number.short_description = 'GRN'

    def product_code(self, obj):
        return obj.budget_item.code
    product_code.short_description = 'Product'

    def cost_adjustment(self, obj):
        return format_html(
            '<span style="color: blue;">+{}</span>',
            obj.cost_per_unit_adjustment
        )
    cost_adjustment.short_description = 'Cost Adj/Unit'


# ============================================================================
# RETURN TO VENDOR (RTV) ADMIN
# ============================================================================

class ReturnToVendorLineInline(admin.TabularInline):
    model = ReturnToVendorLine
    extra = 0
    fields = [
        'budget_item', 'quantity_to_return', 'uom', 'unit_cost',
        'line_total', 'reason', 'budget_reversed'
    ]
    readonly_fields = ['line_total', 'budget_reversed']


@admin.register(ReturnToVendor)
class ReturnToVendorAdmin(admin.ModelAdmin):
    list_display = [
        'rtv_number', 'rtv_date', 'grn_number', 'supplier_id',
        'reason_display', 'total_return_value', 'status_badge',
        'refund_status_display', 'gl_status', 'company'
    ]
    list_filter = ['status', 'return_reason', 'refund_expected', 'posted_to_gl', 'rtv_date', 'company']
    search_fields = [
        'rtv_number', 'goods_receipt__grn_number',
        'supplier_id', 'debit_note_number', 'tracking_number'
    ]
    readonly_fields = [
        'rtv_number', 'total_return_value', 'je_id',
        'gl_posted_date', 'created_at', 'updated_at'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'company', 'rtv_number', 'rtv_date',
                'goods_receipt', 'supplier_id', 'reason'
            )
        }),
        ('Financial Details', {
            'fields': (
                'total_return_value', 'refund_expected',
                'refund_amount', 'refund_status'
            )
        }),
        ('Workflow', {
            'fields': (
                'status', 'created_by', 'submitted_at',
                'approved_by', 'approved_at', 'completed_at'
            )
        }),
        ('Shipping Information', {
            'fields': (
                'carrier', 'tracking_number', 'pickup_date',
                'actual_pickup_date', 'expected_delivery_date',
                'delivered_to_vendor_date'
            )
        }),
        ('GL Integration', {
            'fields': (
                'je_id', 'posted_to_gl', 'gl_posted_date',
                'debit_note_number', 'debit_note_date'
            )
        }),
        ('Additional', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )
    inlines = [ReturnToVendorLineInline]
    date_hierarchy = 'rtv_date'

    def grn_number(self, obj):
        return obj.goods_receipt.grn_number
    grn_number.short_description = 'GRN'

    def reason_display(self, obj):
        return obj.get_reason_display()
    reason_display.short_description = 'Reason'

    def status_badge(self, obj):
        colors = {
            'DRAFT': 'gray',
            'SUBMITTED': 'blue',
            'APPROVED': 'green',
            'IN_TRANSIT': 'orange',
            'COMPLETED': 'darkgreen',
            'CANCELLED': 'red',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def gl_status(self, obj):
        if obj.posted_to_gl:
            return format_html(
                '<span style="color: green;">✓ Posted (JE#{})</span>',
                obj.je_id
            )
        return format_html('<span style="color: orange;">○ Pending</span>')
    gl_status.short_description = 'GL Status'

    def refund_status_display(self, obj):
        status = obj.refund_status
        colors = {
            'PENDING': 'orange',
            'RECEIVED': 'green',
            'NOT_APPLICABLE': 'gray',
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(status, 'gray'),
            status.replace('_', ' ').title()
        )
    refund_status_display.short_description = 'Refund Status'


@admin.register(ReturnToVendorLine)
class ReturnToVendorLineAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'rtv_number', 'product_code_rtv', 'quantity_to_return',
        'uom_name', 'unit_cost', 'line_total',
        'budget_reversal_status', 'company'
    ]
    list_filter = ['budget_reversed', 'company', 'created_at']
    search_fields = [
        'rtv__rtv_number', 'budget_item__code', 'budget_item__name',
        'batch_lot_id'
    ]
    readonly_fields = [
        'company', 'rtv', 'goods_receipt_line', 'budget_item',
        'line_total', 'movement_event', 'budget_reversed',
        'budget_reversal_date', 'created_at', 'updated_at'
    ]
    fieldsets = (
        ('Line Details', {
            'fields': (
                'company', 'rtv', 'goods_receipt_line', 'budget_item',
                'description'
            )
        }),
        ('Quantity and Cost', {
            'fields': (
                'quantity_to_return', 'uom', 'unit_cost', 'line_total'
            )
        }),
        ('Return Information', {
            'fields': (
                'reason', 'batch_lot_id', 'serial_numbers', 'quality_notes'
            )
        }),
        ('Budget Impact', {
            'fields': (
                'budget_reversed', 'budget_reversal_date'
            )
        }),
        ('Movement', {
            'fields': ('movement_event',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def rtv_number(self, obj):
        return obj.rtv.rtv_number
    rtv_number.short_description = 'RTV'

    def product_code_rtv(self, obj):
        return obj.budget_item.code if obj.budget_item else 'N/A'
    product_code_rtv.short_description = 'Product'

    def uom_name(self, obj):
        return obj.uom.name if obj.uom else 'N/A'
    uom_name.short_description = 'UOM'

    def budget_reversal_status(self, obj):
        if obj.budget_reversed:
            return format_html(
                '<span style="color: green;">✓ Reversed</span>'
            )
        elif obj.budget_item:
            return format_html(
                '<span style="color: orange;">○ Pending</span>'
            )
        return format_html(
            '<span style="color: gray;">N/A</span>'
        )
    budget_reversal_status.short_description = 'Budget Reversal'


# Simple admin registrations for autocomplete_fields compatibility
@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    search_fields = ["name", "code"]
    list_filter = ["is_active", "company"]

@admin.register(StockMovementLine)
class StockMovementLineAdmin(admin.ModelAdmin):
    list_display = ["id", "movement", "budget_item", "quantity"]
    search_fields = ["budget_item__code"]
    list_filter = ["movement__company"]

@admin.register(WarehouseBin)
class WarehouseBinAdmin(admin.ModelAdmin):
    list_display = ["code", "warehouse", "is_active"]
    search_fields = ["code", "name"]
    list_filter = ["is_active"]
    readonly_fields = ["code"]

@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ["code", "name"]
    search_fields = ["code", "name"]
    readonly_fields = ["code"]


# ============================================================================
# WAREHOUSE CATEGORY MAPPING ADMIN
# ============================================================================

@admin.register(WarehouseCategoryMapping)
class WarehouseCategoryMappingAdmin(admin.ModelAdmin):
    """Admin interface for Warehouse-Category Mapping configuration"""
    list_display = [
        'id', 'warehouse_info', 'category_info', 'subcategory_info',
        'default_badge', 'priority_display', 'warning_badge',
        'multi_warehouse_badge', 'company'
    ]
    list_filter = ['is_default', 'warning_level', 'allow_multi_warehouse', 'warehouse', 'company']
    search_fields = ['warehouse__code', 'warehouse__name', 'category__code', 'category__name']
    autocomplete_fields = ['warehouse', 'category', 'subcategory']
    readonly_fields = ['created_at', 'updated_at', 'created_by']

    fieldsets = (
        ('Configuration', {
            'fields': ('company', 'warehouse', 'category', 'subcategory')
        }),
        ('Settings', {
            'fields': ('is_default', 'priority', 'allow_multi_warehouse', 'warning_level')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def warehouse_info(self, obj):
        return format_html(
            '<strong>{}</strong><br/><small>{}</small>',
            obj.warehouse.code,
            obj.warehouse.name[:30]
        )
    warehouse_info.short_description = 'Warehouse'
    warehouse_info.admin_order_field = 'warehouse__code'

    def category_info(self, obj):
        return format_html(
            '<strong>{}</strong><br/><small>{}</small>',
            obj.category.code,
            obj.category.name[:30]
        )
    category_info.short_description = 'Category'
    category_info.admin_order_field = 'category__code'

    def subcategory_info(self, obj):
        if obj.subcategory:
            return format_html(
                '<strong>{}</strong><br/><small>{}</small>',
                obj.subcategory.code,
                obj.subcategory.name[:30]
            )
        return format_html('<span style="color: gray;">—</span>')
    subcategory_info.short_description = 'Subcategory'

    def default_badge(self, obj):
        if obj.is_default:
            return format_html(
                '<span style="background-color: #1890ff; color: white; '
                'padding: 3px 8px; border-radius: 3px; font-weight: bold;">★ DEFAULT</span>'
            )
        return format_html('<span style="color: gray;">—</span>')
    default_badge.short_description = 'Default'
    default_badge.admin_order_field = 'is_default'

    def priority_display(self, obj):
        colors = {
            1: '#52c41a',  # green - highest
            2: '#1890ff',  # blue
            3: '#faad14',  # orange
        }
        color = colors.get(obj.priority, '#d9d9d9')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.priority
        )
    priority_display.short_description = 'Priority'
    priority_display.admin_order_field = 'priority'

    def warning_badge(self, obj):
        colors = {
            'INFO': '#1890ff',
            'WARNING': '#faad14',
            'CRITICAL': '#ff4d4f',
        }
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.warning_level, '#d9d9d9'),
            obj.get_warning_level_display()
        )
    warning_badge.short_description = 'Warning Level'
    warning_badge.admin_order_field = 'warning_level'

    def multi_warehouse_badge(self, obj):
        if obj.allow_multi_warehouse:
            return format_html(
                '<span style="color: green;">✓ Yes</span>'
            )
        return format_html('<span style="color: gray;">—</span>')
    multi_warehouse_badge.short_description = 'Multi-WH'
    multi_warehouse_badge.admin_order_field = 'allow_multi_warehouse'

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(WarehouseOverrideLog)
class WarehouseOverrideLogAdmin(admin.ModelAdmin):
    """Admin interface for Warehouse Override Audit Log - Read-only"""
    list_display = [
        'id', 'transaction_info', 'budget_item_display',
        'warehouse_change', 'warning_badge', 'approval_status',
        'overridden_by', 'overridden_at', 'company'
    ]
    list_filter = [
        'transaction_type', 'warning_level', 'was_approved',
        'was_valid_override', 'overridden_at', 'company'
    ]
    search_fields = [
        'transaction_number', 'budget_item__code', 'budget_item__name',
        'override_reason', 'overridden_by__username'
    ]
    readonly_fields = [
        'company', 'transaction_type', 'transaction_id', 'transaction_number',
        'budget_item', 'item_category', 'suggested_warehouse', 'actual_warehouse',
        'warning_level', 'override_reason', 'overridden_by', 'overridden_at',
        'was_approved', 'approved_by',
        'was_valid_override', 'reviewed_by', 'reviewed_at', 'review_notes'
    ]
    date_hierarchy = 'overridden_at'

    fieldsets = (
        ('Transaction Details', {
            'fields': (
                'company', 'transaction_type', 'transaction_id',
                'transaction_number', 'budget_item'
            )
        }),
        ('Warehouse Override', {
            'fields': (
                'suggested_warehouse', 'actual_warehouse',
                'warning_level', 'override_reason'
            )
        }),
        ('Override Action', {
            'fields': (
                'overridden_by', 'overridden_at'
            )
        }),
        ('Approval Workflow', {
            'fields': (
                'was_approved', 'approved_by'
            ),
            'classes': ('collapse',)
        }),
        ('Review & Validation', {
            'fields': (
                'was_valid_override', 'reviewed_by', 'reviewed_at', 'review_notes'
            ),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        # Override logs are created automatically, no manual creation
        return False

    def has_delete_permission(self, request, obj=None):
        # Override logs are audit records, should not be deleted
        return False

    def transaction_info(self, obj):
        return format_html(
            '<strong>{}</strong><br/>'
            '<small>{} #{}</small>',
            obj.transaction_type.replace('_', ' ').title(),
            obj.transaction_number or 'N/A',
            obj.transaction_id
        )
    transaction_info.short_description = 'Transaction'

    def budget_item_display(self, obj):
        if obj.budget_item:
            return format_html(
                '<strong>{}</strong><br/><small>{}</small>',
                obj.budget_item.code,
                obj.budget_item.name[:30]
            )
        return format_html('<span style="color: gray;">N/A</span>')
    budget_item_display.short_description = 'Item'
    budget_item_display.admin_order_field = 'budget_item__code'

    def warehouse_change(self, obj):
        return format_html(
            '<div style="text-align: center;">'
            '<div style="background: #f0f0f0; padding: 4px; border-radius: 3px; margin-bottom: 4px;">'
            '<strong>{}</strong><br/><small>{}</small>'
            '</div>'
            '<div style="color: gray;">↓</div>'
            '<div style="background: #e6f7ff; padding: 4px; border-radius: 3px; margin-top: 4px;">'
            '<strong>{}</strong><br/><small>{}</small>'
            '</div>'
            '</div>',
            obj.suggested_warehouse.code,
            obj.suggested_warehouse.name[:20],
            obj.actual_warehouse.code,
            obj.actual_warehouse.name[:20]
        )
    warehouse_change.short_description = 'Warehouse Change'

    def warning_badge(self, obj):
        colors = {
            'INFO': '#1890ff',
            'WARNING': '#faad14',
            'CRITICAL': '#ff4d4f',
        }
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.warning_level, '#d9d9d9'),
            obj.get_warning_level_display()
        )
    warning_badge.short_description = 'Warning'
    warning_badge.admin_order_field = 'warning_level'

    def approval_status(self, obj):
        if obj.warning_level == 'CRITICAL':
            if obj.was_approved:
                return format_html(
                    '<span style="color: green;">✓ Approved</span><br/>'
                    '<small>{}</small>',
                    obj.approved_by.username if obj.approved_by else 'N/A'
                )
            else:
                return format_html(
                    '<span style="color: red;">✗ Not Approved</span>'
                )
        return format_html('<span style="color: gray;">N/A</span>')
    approval_status.short_description = 'Approval'


# ============================================================================
# PHASE 3: QUALITY CONTROL & COMPLIANCE ADMIN
# ============================================================================

@admin.register(StockHold)
class StockHoldAdmin(admin.ModelAdmin):
    list_display = ['id', 'budget_item_code', 'warehouse_code', 'hold_type', 'qty_held',
                   'hold_status_badge', 'hold_date', 'expected_release_date', 'is_overdue']
    list_filter = ['status', 'hold_type', 'qc_pass_result', 'escalation_flag', 'company']
    search_fields = ['budget_item__code', 'budget_item__name', 'hold_reason']
    readonly_fields = ['created_at', 'updated_at', 'days_held']
    date_hierarchy = 'hold_date'

    fieldsets = (
        ('Hold Information', {
            'fields': ('company', 'budget_item', 'warehouse', 'bin', 'batch_lot',
                      'hold_type', 'qty_held', 'hold_reason')
        }),
        ('Timeline', {
            'fields': ('hold_date', 'hold_by', 'expected_release_date',
                      'actual_release_date', 'released_by', 'days_held')
        }),
        ('QC Results', {
            'fields': ('qc_pass_result', 'qc_notes', 'escalation_flag')
        }),
        ('Status & Disposition', {
            'fields': ('status', 'disposition')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def budget_item_code(self, obj):
        return obj.budget_item.code if obj.budget_item else 'N/A'
    budget_item_code.short_description = 'Item'
    budget_item_code.admin_order_field = 'budget_item__code'

    def warehouse_code(self, obj):
        return obj.warehouse.code
    warehouse_code.short_description = 'Warehouse'
    warehouse_code.admin_order_field = 'warehouse__code'

    def hold_status_badge(self, obj):
        colors = {
            'ACTIVE': 'orange',
            'RELEASED': 'green',
            'SCRAPPED': 'red',
            'RETURNED': 'blue',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            color, obj.get_status_display()
        )
    hold_status_badge.short_description = 'Status'
    hold_status_badge.admin_order_field = 'status'

    def is_overdue(self, obj):
        if obj.status != 'ACTIVE' or not obj.expected_release_date:
            return False
        from datetime import date
        overdue = obj.expected_release_date < date.today()
        if overdue:
            return format_html('<span style="color: red; font-weight: bold;">⚠ OVERDUE</span>')
        return '—'
    is_overdue.short_description = 'Overdue?'

    def days_held(self, obj):
        from datetime import date
        if obj.status == 'ACTIVE':
            days = (date.today() - obj.hold_date).days
        elif obj.actual_release_date:
            days = (obj.actual_release_date - obj.hold_date).days
        else:
            return 0
        return f"{days} days"
    days_held.short_description = 'Days Held'


@admin.register(QCCheckpoint)
class QCCheckpointAdmin(admin.ModelAdmin):
    list_display = ['checkpoint_name', 'warehouse', 'checkpoint_order', 'acceptance_threshold',
                   'escalation_threshold', 'automatic_after', 'assigned_to', 'active_badge']
    list_filter = ['is_active', 'automatic_after', 'company', 'warehouse']
    search_fields = ['checkpoint_name', 'inspection_criteria']
    ordering = ['warehouse', 'checkpoint_order']

    fieldsets = (
        ('Checkpoint Configuration', {
            'fields': ('company', 'warehouse', 'checkpoint_name', 'checkpoint_order')
        }),
        ('Inspection Details', {
            'fields': ('automatic_after', 'inspection_criteria', 'inspection_template')
        }),
        ('Thresholds', {
            'fields': ('acceptance_threshold', 'escalation_threshold')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: gray;">○ Inactive</span>')
    active_badge.short_description = 'Status'
    active_badge.admin_order_field = 'is_active'


@admin.register(QCResult)
class QCResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'grn_number', 'checkpoint_name', 'inspected_date',
                   'qty_inspected', 'qty_accepted', 'qty_rejected', 'rejection_pct',
                   'qc_status_badge', 'hold_created']
    list_filter = ['qc_status', 'rejection_reason', 'hold_created', 'company']
    search_fields = ['grn__grn_number', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'rejection_percentage']
    date_hierarchy = 'inspected_date'

    fieldsets = (
        ('Inspection Details', {
            'fields': ('company', 'grn', 'checkpoint', 'inspected_by', 'inspected_date')
        }),
        ('Quantities', {
            'fields': ('qty_inspected', 'qty_accepted', 'qty_rejected', 'rejection_percentage')
        }),
        ('Results', {
            'fields': ('qc_status', 'rejection_reason', 'notes', 'rework_instruction')
        }),
        ('Documentation', {
            'fields': ('attachment', 'hold_created')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def grn_number(self, obj):
        return obj.grn.grn_number
    grn_number.short_description = 'GRN'
    grn_number.admin_order_field = 'grn__grn_number'

    def checkpoint_name(self, obj):
        return obj.checkpoint.checkpoint_name
    checkpoint_name.short_description = 'Checkpoint'

    def rejection_pct(self, obj):
        if obj.qty_inspected > 0:
            pct = float(obj.qty_rejected / obj.qty_inspected * 100)
            color = 'red' if pct > 5 else 'orange' if pct > 0 else 'green'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color, pct
            )
        return '0%'
    rejection_pct.short_description = 'Reject %'

    def rejection_percentage(self, obj):
        if obj.qty_inspected > 0:
            return f"{float(obj.qty_rejected / obj.qty_inspected * 100):.2f}%"
        return "0%"
    rejection_percentage.short_description = 'Rejection Percentage'

    def qc_status_badge(self, obj):
        colors = {
            'PASS': 'green',
            'FAIL': 'red',
            'CONDITIONAL_PASS': 'orange',
        }
        color = colors.get(obj.qc_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            color, obj.get_qc_status_display()
        )
    qc_status_badge.short_description = 'QC Status'
    qc_status_badge.admin_order_field = 'qc_status'


@admin.register(BatchLot)
class BatchLotAdmin(admin.ModelAdmin):
    list_display = ['internal_batch_code', 'budget_item_code', 'grn_number',
                   'received_date', 'exp_date', 'expiry_indicator', 'current_qty',
                   'hold_status_badge', 'cost_per_unit']
    list_filter = ['hold_status', 'company']
    search_fields = ['internal_batch_code', 'supplier_lot_number', 'budget_item__code']
    readonly_fields = ['created_at', 'updated_at', 'is_expired', 'days_until_expiry_display',
                      'utilization_percentage']
    date_hierarchy = 'received_date'

    fieldsets = (
        ('Batch Information', {
            'fields': ('company', 'budget_item', 'internal_batch_code', 'supplier_lot_number')
        }),
        ('Receipt Details', {
            'fields': ('grn', 'received_date', 'received_qty', 'current_qty', 'utilization_percentage')
        }),
        ('Dates & Expiry', {
            'fields': ('mfg_date', 'exp_date', 'is_expired', 'days_until_expiry_display')
        }),
        ('Cost & Valuation', {
            'fields': ('cost_per_unit',)
        }),
        ('Storage & Safety', {
            'fields': ('storage_location', 'hazmat_classification')
        }),
        ('Quality Control', {
            'fields': ('hold_status', 'fefo_sequence')
        }),
        ('Documentation', {
            'fields': ('certificate_of_analysis', 'coa_upload_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def budget_item_code(self, obj):
        return obj.budget_item.code if obj.budget_item else 'N/A'
    budget_item_code.short_description = 'Item'
    budget_item_code.admin_order_field = 'budget_item__code'

    def grn_number(self, obj):
        return obj.grn.grn_number if obj.grn else 'N/A'
    grn_number.short_description = 'GRN'

    def expiry_indicator(self, obj):
        if not obj.exp_date:
            return '—'

        days = obj.days_until_expiry()
        if days is None:
            return '—'

        if days < 0:
            return format_html('<span style="color: red; font-weight: bold;">⚠ EXPIRED</span>')
        elif days <= 7:
            return format_html('<span style="color: red;">⚠ {} days</span>', days)
        elif days <= 30:
            return format_html('<span style="color: orange;">⚠ {} days</span>', days)
        else:
            return format_html('<span style="color: green;">{} days</span>', days)
    expiry_indicator.short_description = 'Expiry Status'

    def days_until_expiry_display(self, obj):
        days = obj.days_until_expiry()
        if days is None:
            return 'No expiry date'
        if days < 0:
            return f"Expired {abs(days)} days ago"
        return f"{days} days until expiry"
    days_until_expiry_display.short_description = 'Days Until Expiry'

    def utilization_percentage(self, obj):
        if obj.received_qty > 0:
            consumed = obj.received_qty - obj.current_qty
            pct = float(consumed / obj.received_qty * 100)
            return f"{pct:.1f}%"
        return "0%"
    utilization_percentage.short_description = 'Utilization'

    def hold_status_badge(self, obj):
        colors = {
            'QUARANTINE': 'orange',
            'ON_HOLD': 'red',
            'RELEASED': 'green',
            'SCRAP': 'gray',
        }
        color = colors.get(obj.hold_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            color, obj.get_hold_status_display()
        )
    hold_status_badge.short_description = 'Hold Status'
    hold_status_badge.admin_order_field = 'hold_status'


@admin.register(SerialNumber)
class SerialNumberAdmin(admin.ModelAdmin):
    list_display = ['serial_number', 'budget_item_code', 'batch_lot_code',
                   'status_badge', 'warranty_status', 'issued_to', 'issued_date']
    list_filter = ['status', 'company']
    search_fields = ['serial_number', 'budget_item__code', 'asset_tag', 'issued_to']
    readonly_fields = ['created_at', 'updated_at', 'is_under_warranty_display', 'days_in_service_display']

    fieldsets = (
        ('Serial Number Information', {
            'fields': ('company', 'budget_item', 'serial_number', 'batch_lot', 'asset_tag')
        }),
        ('Warranty', {
            'fields': ('warranty_start', 'warranty_end', 'is_under_warranty_display')
        }),
        ('Assignment & Issuance', {
            'fields': ('assigned_to_customer_order', 'issued_date', 'issued_to', 'days_in_service_display')
        }),
        ('Return & Inspection', {
            'fields': ('received_back_date', 'inspection_date')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def budget_item_code(self, obj):
        return obj.budget_item.code if obj.budget_item else 'N/A'
    budget_item_code.short_description = 'Item'
    budget_item_code.admin_order_field = 'budget_item__code'

    def batch_lot_code(self, obj):
        return obj.batch_lot.internal_batch_code if obj.batch_lot else 'N/A'
    batch_lot_code.short_description = 'Batch'

    def status_badge(self, obj):
        colors = {
            'IN_STOCK': 'green',
            'ASSIGNED': 'blue',
            'ISSUED': 'orange',
            'RETURNED': 'purple',
            'SCRAPPED': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def warranty_status(self, obj):
        if not obj.warranty_end:
            return '—'
        from datetime import date
        if obj.warranty_end >= date.today():
            return format_html('<span style="color: green;">✓ Under Warranty</span>')
        return format_html('<span style="color: gray;">Expired</span>')
    warranty_status.short_description = 'Warranty'

    def is_under_warranty_display(self, obj):
        if not obj.warranty_end:
            return 'No warranty info'
        from datetime import date
        if obj.warranty_end >= date.today():
            days = (obj.warranty_end - date.today()).days
            return f"Yes ({days} days remaining)"
        days = (date.today() - obj.warranty_end).days
        return f"Expired {days} days ago"
    is_under_warranty_display.short_description = 'Warranty Status'

    def days_in_service_display(self, obj):
        if obj.issued_date:
            from datetime import date
            end_date = obj.received_back_date or date.today()
            days = (end_date - obj.issued_date).days
            return f"{days} days"
        return "Not issued"
    days_in_service_display.short_description = 'Days in Service'

