# backend/apps/finance/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Account, Journal, JournalVoucher, JournalEntry,
    Invoice, InvoiceLine, Payment, PaymentAllocation
)

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'account_type', 'colored_balance',
        'currency', 'is_active', 'company'
    ]
    list_filter = ['account_type', 'is_active', 'company']
    search_fields = ['code', 'name']
    ordering = ['code']

    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'code', 'name', 'account_type')
        }),
        ('Configuration', {
            'fields': ('parent_account', 'currency', 'is_bank_account', 
                      'is_control_account', 'allow_direct_posting')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    def colored_balance(self, obj):
        color = 'green' if obj.current_balance >= 0 else 'red'
        return format_html(
            '<span style="color: {};">৳ {:,.2f}</span>',
            color,
            obj.current_balance
        )
    colored_balance.short_description = 'Balance'
    colored_balance.admin_order_field = 'current_balance'

class JournalEntryInline(admin.TabularInline):
    model = JournalEntry
    extra = 2
    fields = ['line_number', 'account', 'debit_amount', 'credit_amount', 'description']

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Add custom validation
        return formset

@admin.register(JournalVoucher)
class JournalVoucherAdmin(admin.ModelAdmin):
    list_display = [
        'voucher_number', 'journal', 'entry_date', 'status',
        'total_debit', 'total_credit', 'posted_at', 'company'
    ]
    list_filter = ['status', 'journal', 'entry_date', 'company']
    search_fields = ['voucher_number', 'description', 'reference']
    date_hierarchy = 'entry_date'
    inlines = [JournalEntryInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'voucher_number', 'journal', 'entry_date', 'period')
        }),
        ('Details', {
            'fields': ('reference', 'description')
        }),
        ('Status', {
            'fields': ('status', 'posted_by', 'posted_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['voucher_number', 'posted_by', 'posted_at']

    actions = ['post_vouchers', 'unpost_vouchers']

    def post_vouchers(self, request, queryset):
        count = 0
        for voucher in queryset.filter(status='DRAFT'):
            voucher.status = 'POSTED'
            voucher.posted_by = request.user
            voucher.posted_at = timezone.now()
            voucher.save()
            count += 1
        self.message_user(request, f'{count} vouchers posted successfully.')
    post_vouchers.short_description = 'Post selected vouchers'

    def total_debit(self, obj):
        total = sum(e.debit_amount for e in obj.entries.all())
        return format_html('<strong>৳ {:,.2f}</strong>', total)
    total_debit.short_description = 'Total Debit'

    def total_credit(self, obj):
        total = sum(e.credit_amount for e in obj.entries.all())
        return format_html('<strong>৳ {:,.2f}</strong>', total)
    total_credit.short_description = 'Total Credit'

class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 1
    fields = ['line_number', 'description', 'quantity', 'unit_price', 'line_total']
    readonly_fields = ['line_total']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'invoice_type', 'partner_name',
        'invoice_date', 'due_date', 'colored_total',
        'colored_balance', 'status_badge', 'company'
    ]
    list_filter = ['invoice_type', 'status', 'invoice_date', 'company']
    search_fields = ['invoice_number', 'notes']
    date_hierarchy = 'invoice_date'
    inlines = [InvoiceLineInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'invoice_number', 'invoice_type', 
                      'partner_type', 'partner_id')
        }),
        ('Dates', {
            'fields': ('invoice_date', 'due_date')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 
                      'total_amount', 'paid_amount', 'currency', 'exchange_rate')
        }),
        ('Status', {
            'fields': ('status', 'notes')
        }),
    )

    readonly_fields = ['invoice_number', 'paid_amount']

    def partner_name(self, obj):
        # Get partner name dynamically
        return f"{obj.partner_type}: {obj.partner_id}"
    partner_name.short_description = 'Partner'

    def colored_total(self, obj):
        return format_html(
            '<strong>৳ {:,.2f}</strong>',
            obj.total_amount
        )
    colored_total.short_description = 'Total'

    def colored_balance(self, obj):
        balance = obj.total_amount - obj.paid_amount
        color = 'red' if balance > 0 else 'green'
        return format_html(
            '<span style="color: {};">৳ {:,.2f}</span>',
            color,
            balance
        )
    colored_balance.short_description = 'Balance Due'

    def status_badge(self, obj):
        colors = {
            'DRAFT': 'gray',
            'POSTED': 'blue',
            'PAID': 'green',
            'PARTIALLY_PAID': 'orange',
            'OVERDUE': 'red',
            'CANCELLED': 'darkgray',
        }
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.status
        )
    status_badge.short_description = 'Status'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_number', 'payment_type', 'payment_date',
        'colored_amount', 'payment_method', 'status_badge', 'company'
    ]
    list_filter = ['payment_type', 'payment_method', 'status', 'company']
    search_fields = ['payment_number', 'reference']
    date_hierarchy = 'payment_date'

    def colored_amount(self, obj):
        return format_html(
            '<strong style="color: green;">৳ {:,.2f}</strong>',
            obj.amount
        )
    colored_amount.short_description = 'Amount'

    def status_badge(self, obj):
        colors = {'DRAFT': 'gray', 'POSTED': 'green', 'CANCELLED': 'red'}
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.status
        )
    status_badge.short_description = 'Status'
