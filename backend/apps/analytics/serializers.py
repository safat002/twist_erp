from decimal import Decimal
from rest_framework import serializers
from .models import SalesPerformanceSnapshot, CashflowSnapshot


def _decimal_to_float(value: Decimal | None) -> float:
    if value is None:
        return 0.0
    return float(value)


class SalesPerformanceSnapshotSerializer(serializers.ModelSerializer):
    total_revenue = serializers.SerializerMethodField()
    avg_order_value = serializers.SerializerMethodField()

    class Meta:
        model = SalesPerformanceSnapshot
        fields = [
            'snapshot_date',
            'period',
            'company_id',
            'company_code',
            'company_name',
            'timeframe_start',
            'timeframe_end',
            'total_orders',
            'total_revenue',
            'avg_order_value',
            'sales_trend',
            'top_customers',
            'top_products',
            'metadata',
        ]

    def get_total_revenue(self, obj):
        return _decimal_to_float(obj.total_revenue)

    def get_avg_order_value(self, obj):
        return _decimal_to_float(obj.avg_order_value)


class CashflowSnapshotSerializer(serializers.ModelSerializer):
    cash_in = serializers.SerializerMethodField()
    cash_out = serializers.SerializerMethodField()
    net_cash = serializers.SerializerMethodField()
    receivables_balance = serializers.SerializerMethodField()
    payables_balance = serializers.SerializerMethodField()

    class Meta:
        model = CashflowSnapshot
        fields = [
            'snapshot_date',
            'period',
            'company_id',
            'company_code',
            'company_name',
            'timeframe_start',
            'timeframe_end',
            'cash_in',
            'cash_out',
            'net_cash',
            'cash_trend',
            'receivables_balance',
            'payables_balance',
            'bank_balances',
            'metadata',
        ]

    def get_cash_in(self, obj):
        return _decimal_to_float(obj.cash_in)

    def get_cash_out(self, obj):
        return _decimal_to_float(obj.cash_out)

    def get_net_cash(self, obj):
        return _decimal_to_float(obj.net_cash)

    def get_receivables_balance(self, obj):
        return _decimal_to_float(obj.receivables_balance)

    def get_payables_balance(self, obj):
        return _decimal_to_float(obj.payables_balance)
