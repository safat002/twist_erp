from rest_framework import serializers
from apps.finance.models import (
    Account, Journal, JournalVoucher, JournalEntry,
    Invoice, InvoiceLine, Payment, PaymentAllocation
)

class AccountSerializer(serializers.ModelSerializer):
    """Serialize Account model"""
    parent_account_name = serializers.CharField(
        source='parent_account.name',
        read_only=True
    )
    current_balance = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Account
        fields = [
            'id', 'code', 'name', 'account_type',
            'parent_account', 'parent_account_name',
            'is_active', 'is_bank_account', 'allow_direct_posting',
            'current_balance', 'currency', 'created_at'
        ]
        read_only_fields = ['id', 'current_balance', 'created_at']

class JournalEntrySerializer(serializers.ModelSerializer):
    """Serialize Journal Entry"""
    account_name = serializers.CharField(
        source='account.name',
        read_only=True
    )

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'line_number', 'account', 'account_name',
            'debit_amount', 'credit_amount', 'description',
            'cost_center', 'project'
        ]

class JournalVoucherSerializer(serializers.ModelSerializer):
    """Serialize Journal Voucher with entries"""
    entries = JournalEntrySerializer(many=True)

    class Meta:
        model = JournalVoucher
        fields = [
            'id', 'voucher_number', 'journal', 'entry_date',
            'period', 'reference', 'description', 'status',
            'entries', 'posted_at', 'posted_by', 'created_at'
        ]
        read_only_fields = ['id', 'voucher_number', 'created_at']

    def validate_entries(self, entries):
        """Validate double-entry bookkeeping"""
        total_debit = sum(e['debit_amount'] for e in entries)
        total_credit = sum(e['credit_amount'] for e in entries)

        if abs(total_debit - total_credit) > 0.01:
            raise serializers.ValidationError(
                "Debits must equal credits"
            )

        return entries

    def create(self, validated_data):
        entries_data = validated_data.pop('entries')
        voucher = JournalVoucher.objects.create(**validated_data)

        for entry_data in entries_data:
            JournalEntry.objects.create(voucher=voucher, **entry_data)

        return voucher

class InvoiceLineSerializer(serializers.ModelSerializer):
    """Serialize Invoice Line"""

    class Meta:
        model = InvoiceLine
        fields = [
            'id', 'line_number', 'description', 'quantity',
            'unit_price', 'tax_rate', 'discount_percent',
            'line_total', 'product_id', 'account'
        ]

class InvoiceSerializer(serializers.ModelSerializer):
    """Serialize Invoice (AP/AR)"""
    lines = InvoiceLineSerializer(many=True)
    balance_due = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        read_only=True
    )
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'invoice_type',
            'partner_type', 'partner_id', 'invoice_date', 'due_date',
            'subtotal', 'tax_amount', 'discount_amount', 'total_amount',
            'paid_amount', 'balance_due', 'currency', 'exchange_rate',
            'status', 'is_overdue', 'lines', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'invoice_number', 'balance_due', 'is_overdue']

    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        invoice = Invoice.objects.create(**validated_data)

        for line_data in lines_data:
            InvoiceLine.objects.create(invoice=invoice, **line_data)

        return invoice

class PaymentAllocationSerializer(serializers.ModelSerializer):
    """Serialize Payment Allocation"""
    invoice_number = serializers.CharField(
        source='invoice.invoice_number',
        read_only=True
    )

    class Meta:
        model = PaymentAllocation
        fields = [
            'id', 'invoice', 'invoice_number', 'allocated_amount'
        ]

class PaymentSerializer(serializers.ModelSerializer):
    """Serialize Payment"""
    allocations = PaymentAllocationSerializer(many=True, required=False)

    class Meta:
        model = Payment
        fields = [
            'id', 'payment_number', 'payment_date', 'payment_type',
            'payment_method', 'bank_account', 'amount', 'currency',
            'partner_type', 'partner_id', 'reference', 'notes',
            'status', 'allocations', 'created_at'
        ]
        read_only_fields = ['id', 'payment_number', 'created_at']
