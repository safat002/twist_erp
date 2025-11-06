from decimal import Decimal
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Account, Journal, JournalVoucher, JournalEntry,
    Invoice, InvoiceLine, Payment, PaymentAllocation,
    FiscalPeriod, TaxJurisdiction, TaxCode,
    BankStatement, BankStatementLine,
    InventoryPostingRule,
)


def _fmt_amt(value) -> str:
    try:
        amt = Decimal(value or 0)
    except Exception:
        try:
            amt = Decimal(str(value))
        except Exception:
            amt = Decimal('0')
    return f"{amt:,.2f}"


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
        label = f"{(obj.currency or '').upper()} {_fmt_amt(obj.current_balance)}".strip()
        return format_html('<span style="color: {};"><strong>{}</strong></span>', color, label)

    colored_balance.short_description = 'Balance'
    colored_balance.admin_order_field = 'current_balance'


class JournalEntryInline(admin.TabularInline):
    model = JournalEntry
    extra = 2
    fields = ['line_number', 'account', 'debit_amount', 'credit_amount', 'description']

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
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
        total = sum((e.debit_amount or 0) for e in obj.entries.all())
        curr = getattr(getattr(obj, 'company', None), 'default_currency', '') or ''
        return format_html('<strong>{} {}</strong>', curr, _fmt_amt(total))

    total_debit.short_description = 'Total Debit'

    def total_credit(self, obj):
        total = sum((e.credit_amount or 0) for e in obj.entries.all())
        curr = getattr(getattr(obj, 'company', None), 'default_currency', '') or ''
        return format_html('<strong>{} {}</strong>', curr, _fmt_amt(total))

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
            'fields': ('company', 'invoice_number', 'invoice_type', 'partner_type', 'partner_id')
        }),
        ('Dates', {
            'fields': ('invoice_date', 'due_date')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'paid_amount', 'currency', 'exchange_rate')
        }),
        ('Status', {
            'fields': ('status', 'notes')
        }),
    )

    readonly_fields = ['invoice_number', 'paid_amount']

    def partner_name(self, obj):
        return f"{obj.partner_type}: {obj.partner_id}"

    partner_name.short_description = 'Partner'

    def colored_total(self, obj):
        return format_html('<strong>{} {}</strong>', (obj.currency or ''), _fmt_amt(obj.total_amount))

    colored_total.short_description = 'Total'

    def colored_balance(self, obj):
        total = Decimal(obj.total_amount or 0)
        paid = Decimal(obj.paid_amount or 0)
        balance = total - paid
        color = 'red' if balance > 0 else 'green'
        return format_html('<span style="color: {};"><strong>{} {}</strong></span>', color, (obj.currency or ''), _fmt_amt(balance))

    colored_balance.short_description = 'Balance Due'

    def status_badge(self, obj):
        colors = {
            'DRAFT': 'gray',
            'APPROVED': 'blue',
            'POSTED': 'blue',
            'PAID': 'green',
            'PARTIAL': 'orange',
            'OVERDUE': 'red',
            'CANCELLED': 'darkgray',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.status,
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
        return format_html('<strong style="color: green;">{} {}</strong>', (obj.currency or ''), _fmt_amt(obj.amount))

    colored_amount.short_description = 'Amount'

    def status_badge(self, obj):
        colors = {
            'DRAFT': 'gray',
            'APPROVED': 'blue',
            'POSTED': 'green',
            'RECONCILED': 'purple',
            'CANCELLED': 'red',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.status,
        )

    status_badge.short_description = 'Status'


@admin.register(InventoryPostingRule)
class InventoryPostingRuleAdmin(admin.ModelAdmin):
    list_display = ['company', 'category', 'warehouse_type', 'transaction_type', 'inventory_account', 'cogs_account', 'is_active']
    list_filter = ['company', 'warehouse_type', 'transaction_type', 'is_active']
    search_fields = ['company__code', 'category__code']


@admin.register(FiscalPeriod)
class FiscalPeriodAdmin(admin.ModelAdmin):
    list_display = ['company', 'period', 'status', 'locked_by', 'locked_at']
    list_filter = ['company', 'status']
    search_fields = ['period']


@admin.register(TaxJurisdiction)
class TaxJurisdictionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'company', 'is_active']
    list_filter = ['company', 'is_active']
    search_fields = ['code', 'name']


@admin.register(TaxCode)
class TaxCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'rate', 'is_inclusive', 'company', 'is_active']
    list_filter = ['company', 'is_active', 'is_inclusive']
    search_fields = ['code', 'name']


class BankStatementLineInline(admin.TabularInline):
    model = BankStatementLine
    extra = 0
    fields = ['line_date', 'description', 'reference', 'amount', 'balance', 'match_status', 'matched_payment', 'matched_voucher']
    readonly_fields = []


@admin.register(BankStatement)
class BankStatementAdmin(admin.ModelAdmin):
    list_display = ['company', 'bank_account', 'statement_date', 'opening_balance', 'closing_balance', 'status']
    list_filter = ['company', 'bank_account', 'status']
    search_fields = ['imported_filename']
    inlines = [BankStatementLineInline]
    date_hierarchy = 'statement_date'
