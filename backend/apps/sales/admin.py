from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import SalesOrder, SalesOrderLine
from .models.customer import Customer

class SalesOrderLineInline(admin.TabularInline):
    model = SalesOrderLine
    extra = 1
    fields = [
        'product', 'description', 'quantity',
        'unit_price', 'discount_percent', 'line_total_display'
    ]
    readonly_fields = ['line_total_display']

    def line_total_display(self, obj):
        if obj.pk:
            return format_html('৳ {:,.2f}', obj.line_total)
        return '-'
    line_total_display.short_description = 'Total'

@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'customer_link', 'order_date',
        'delivery_date', 'colored_total', 'status_badge',
        'fulfillment_progress'
    ]
    list_filter = ['status', 'order_date', 'company']
    search_fields = ['order_number', 'customer__name']
    date_hierarchy = 'order_date'
    inlines = [SalesOrderLineInline]

    def customer_link(self, obj):
        url = reverse('admin:sales_customer_change', args=[obj.customer.pk])
        return format_html('<a href="{}">{}</a>', url, obj.customer.name)
    customer_link.short_description = 'Customer'

    def colored_total(self, obj):
        return format_html(
            '<strong> {:,.2f}</strong>',
            obj.total_amount
        )
    colored_total.short_description = 'Total'

    def status_badge(self, obj):
        colors = {
            'DRAFT': '#d9d9d9',
            'CONFIRMED': '#1890ff',
            'PROCESSING': '#fa8c16',
            'DELIVERED': '#52c41a',
            'CANCELLED': '#f5222d'
        }
        return format_html(
            '<span>{}</span>',
            colors.get(obj.status, '#999'),
            obj.status
        )
    status_badge.short_description = 'Status'

    def fulfillment_progress(self, obj):
        lines = obj.lines.all()
        if not lines:
            return '-'

        total_qty = sum(line.quantity for line in lines)
        delivered_qty = sum(line.delivered_qty for line in lines)

        if total_qty > 0:
            percent = (delivered_qty / total_qty) * 100
            return format_html(
                '<div>'
                '<div style="width: {}%; background: #52c41a; height: 5px; border-radius: 3px;"></div>'
                '<span>{:.0f}%</span>'
                '</div>',
                percent, percent
            )
        return '-'
    fulfillment_progress.short_description = 'Fulfillment'


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'customer_status', 'email', 'phone', 'company', 'credit_limit'
    ]
    list_filter = ['customer_status', 'company']
    search_fields = ['code', 'name', 'email', 'phone']
