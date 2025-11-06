"""
Serializers for GL Reconciliation API endpoints
"""

from rest_framework import serializers


class ReconciliationAccountSerializer(serializers.Serializer):
    """Serializer for individual account reconciliation result"""
    account_code = serializers.CharField()
    account_name = serializers.CharField()
    gl_balance = serializers.DecimalField(max_digits=20, decimal_places=2)
    inventory_value = serializers.DecimalField(max_digits=20, decimal_places=2)
    variance = serializers.DecimalField(max_digits=20, decimal_places=2)
    variance_percent = serializers.DecimalField(max_digits=10, decimal_places=2)
    is_reconciled = serializers.BooleanField()


class ReconciliationSummarySerializer(serializers.Serializer):
    """Serializer for reconciliation summary"""
    total_gl_balance = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_inventory_value = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_variance = serializers.DecimalField(max_digits=20, decimal_places=2)
    variance_percent = serializers.DecimalField(max_digits=10, decimal_places=2)
    accounts_checked = serializers.IntegerField()
    accounts_reconciled = serializers.IntegerField()
    accounts_unreconciled = serializers.IntegerField()


class ReconciliationReportSerializer(serializers.Serializer):
    """Serializer for full reconciliation report"""
    company = serializers.CharField()
    company_name = serializers.CharField()
    warehouse = serializers.CharField()
    as_of_date = serializers.DateField()
    summary = ReconciliationSummarySerializer()
    accounts = ReconciliationAccountSerializer(many=True)
    unreconciled_accounts = serializers.ListField(
        child=serializers.DictField()
    )


class CostLayerDetailSerializer(serializers.Serializer):
    """Serializer for cost layer detail"""
    layer_id = serializers.IntegerField()
    receipt_date = serializers.DateField()
    quantity = serializers.DecimalField(max_digits=15, decimal_places=3)
    cost_per_unit = serializers.DecimalField(max_digits=20, decimal_places=4)
    value = serializers.DecimalField(max_digits=20, decimal_places=2)


class ProductDetailSerializer(serializers.Serializer):
    """Serializer for product inventory detail"""
    product_code = serializers.CharField()
    product_name = serializers.CharField()
    warehouse = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=15, decimal_places=3)
    unit_cost = serializers.DecimalField(max_digits=20, decimal_places=4)
    total_value = serializers.DecimalField(max_digits=20, decimal_places=2)
    cost_layers = CostLayerDetailSerializer(many=True)


class GLTransactionSerializer(serializers.Serializer):
    """Serializer for GL transaction"""
    date = serializers.DateField()
    voucher_number = serializers.CharField()
    description = serializers.CharField()
    debit = serializers.DecimalField(max_digits=20, decimal_places=2)
    credit = serializers.DecimalField(max_digits=20, decimal_places=2)
    source_document = serializers.CharField()


class ReconciliationDetailSerializer(serializers.Serializer):
    """Serializer for detailed reconciliation breakdown"""
    account_code = serializers.CharField()
    account_name = serializers.CharField()
    gl_balance = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_inventory_value = serializers.DecimalField(max_digits=20, decimal_places=2)
    product_details = ProductDetailSerializer(many=True)
    recent_gl_transactions = GLTransactionSerializer(many=True)
