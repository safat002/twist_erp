from rest_framework import serializers
from .models import (
    Product, Item, StockMovement, Warehouse, UnitOfMeasure, StockMovementLine,
    ProductCategory, StockLedger, DeliveryOrder, GoodsReceipt, StockLevel,
    GoodsReceiptLine, DeliveryOrderLine, InternalRequisition,
    ItemValuationMethod, CostLayer, ValuationChangeLog
)

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'

class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = '__all__'

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'

class UnitOfMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitOfMeasure
        fields = '__all__'

    def create(self, validated_data):
        request = self.context.get('request')
        company = getattr(request, 'company', None)
        user = getattr(request, 'user', None)
        code = validated_data.get('code')
        if not company:
            raise serializers.ValidationError({'detail': 'Active company is required.'})
        # Enforce group-level uniqueness for UOM code (unless forced)
        force = False
        try:
            force = (str(request.query_params.get('force') or request.data.get('force') or '')).lower() in {'1','true','yes','on'}
        except Exception:
            force = False
        if not force:
            exists = UnitOfMeasure.objects.filter(company__company_group_id=company.company_group_id, code__iexact=code).exists()
            if exists:
                raise serializers.ValidationError({'code': 'A UOM with this code already exists for your company group.'})
        validated_data['company'] = company
        if user and 'created_by' not in validated_data:
            validated_data['created_by'] = user
        return super().create(validated_data)

class StockMovementLineSerializer(serializers.ModelSerializer):
    # Back-compat: allow posting 'product' as alias for 'item'
    product = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all(), write_only=True, required=False, allow_null=True)

    class Meta:
        model = StockMovementLine
        fields = '__all__'

    def validate(self, attrs):
        product = attrs.pop('product', None)
        if product is not None and not attrs.get('item'):
            attrs['item'] = product
        return super().validate(attrs)

class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = '__all__'

class StockLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockLedger
        fields = '__all__'

class DeliveryOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryOrder
        fields = '__all__'

class GoodsReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsReceipt
        fields = '__all__'

class StockLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockLevel
        fields = '__all__'

class GoodsReceiptLineSerializer(serializers.ModelSerializer):
    # Back-compat: accept 'product' as alias for 'item'
    product = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all(), write_only=True, required=False, allow_null=True)

    class Meta:
        model = GoodsReceiptLine
        fields = '__all__'

    def validate(self, attrs):
        product = attrs.pop('product', None)
        if product is not None and not attrs.get('item'):
            attrs['item'] = product
        return super().validate(attrs)

class DeliveryOrderLineSerializer(serializers.ModelSerializer):
    # Back-compat: accept 'item' as alias for 'product' (model field name kept as product)
    item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all(), write_only=True, required=False, allow_null=True)

    class Meta:
        model = DeliveryOrderLine
        fields = '__all__'

    def validate(self, attrs):
        item = attrs.pop('item', None)
        if item is not None and not attrs.get('product'):
            attrs['product'] = item
        return super().validate(attrs)


class InternalRequisitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalRequisition
        fields = [
            'id',
            'company',
            'requisition_number',
            'request_date',
            'needed_by',
            'warehouse',
            'purpose',
            'status',
            'lines',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['company', 'requisition_number', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        company = getattr(request, 'company', None)
        user = getattr(request, 'user', None)
        validated_data['company'] = company
        if user and 'created_by' not in validated_data:
            validated_data['created_by'] = user
        return super().create(validated_data)


# ========================================
# VALUATION SERIALIZERS
# ========================================

class ItemValuationMethodSerializer(serializers.ModelSerializer):
    """Serializer for ItemValuationMethod model"""
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    item_code = serializers.CharField(source='product.code', read_only=True)
    item_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    valuation_method_display = serializers.CharField(source='get_valuation_method_display', read_only=True)
    avg_period_display = serializers.CharField(source='get_avg_period_display', read_only=True)

    class Meta:
        model = ItemValuationMethod
        fields = [
            'id',
            'company',
            'product',
            'product_code',  # deprecated alias for item_code
            'product_name',  # deprecated alias for item_name
            'item_code',
            'item_name',
            'warehouse',
            'warehouse_code',
            'warehouse_name',
            'valuation_method',
            'valuation_method_display',
            'avg_period',
            'avg_period_display',
            'allow_negative_inventory',
            'prevent_cost_below_zero',
            'effective_date',
            'is_active',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['company', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        company = getattr(request, 'company', None)
        user = getattr(request, 'user', None)
        validated_data['company'] = company
        if user and 'created_by' not in validated_data:
            validated_data['created_by'] = user
        return super().create(validated_data)


class CostLayerSerializer(serializers.ModelSerializer):
    """Serializer for CostLayer model"""
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    item_code = serializers.CharField(source='product.code', read_only=True)
    item_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    effective_cost_per_unit = serializers.SerializerMethodField()
    percentage_consumed = serializers.SerializerMethodField()

    class Meta:
        model = CostLayer
        fields = [
            'id',
            'company',
            'product',
            'product_code',  # deprecated
            'product_name',  # deprecated
            'item_code',
            'item_name',
            'warehouse',
            'warehouse_code',
            'warehouse_name',
            'receipt_date',
            'qty_received',
            'cost_per_unit',
            'total_cost',
            'qty_remaining',
            'cost_remaining',
            'effective_cost_per_unit',
            'percentage_consumed',
            'fifo_sequence',
            'batch_no',
            'serial_no',
            'is_standard_cost',
            'landed_cost_adjustment',
            'adjustment_date',
            'adjustment_reason',
            'source_document_type',
            'source_document_id',
            'immutable_after_post',
            'is_closed',
            'created_at',
        ]
        read_only_fields = ['company', 'created_at']

    def get_effective_cost_per_unit(self, obj):
        """Calculate effective cost including landed cost adjustments"""
        return float(obj.cost_per_unit + obj.landed_cost_adjustment)

    def get_percentage_consumed(self, obj):
        """Calculate percentage of layer consumed"""
        if obj.qty_received > 0:
            consumed = obj.qty_received - obj.qty_remaining
            return float((consumed / obj.qty_received) * 100)
        return 0.0


class CostLayerDetailSerializer(CostLayerSerializer):
    """Detailed serializer with nested product and warehouse info"""
    product = ItemSerializer(read_only=True)
    warehouse = WarehouseSerializer(read_only=True)


class ValuationChangeLogSerializer(serializers.ModelSerializer):
    """Serializer for ValuationChangeLog model"""
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    item_code = serializers.CharField(source='product.code', read_only=True)
    item_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    old_method_display = serializers.SerializerMethodField()
    new_method_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    impact_percentage = serializers.SerializerMethodField()

    class Meta:
        model = ValuationChangeLog
        fields = [
            'id',
            'company',
            'product',
            'product_code',  # deprecated
            'product_name',  # deprecated
            'item_code',
            'item_name',
            'warehouse',
            'warehouse_code',
            'warehouse_name',
            'old_method',
            'old_method_display',
            'new_method',
            'new_method_display',
            'effective_date',
            'old_inventory_value',
            'new_inventory_value',
            'revaluation_amount',
            'impact_percentage',
            'requested_by',
            'requested_by_name',
            'requested_date',
            'approved_by',
            'approved_by_name',
            'approval_date',
            'status',
            'status_display',
            'reason',
            'rejection_reason',
            'revaluation_je_id',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'company',
            'requested_by',
            'requested_date',
            'approved_by',
            'approval_date',
            'created_at',
            'updated_at'
        ]

    def get_old_method_display(self, obj):
        """Get display name for old method"""
        for code, display in ItemValuationMethod.VALUATION_METHOD_CHOICES:
            if code == obj.old_method:
                return display
        return obj.old_method

    def get_new_method_display(self, obj):
        """Get display name for new method"""
        for code, display in ItemValuationMethod.VALUATION_METHOD_CHOICES:
            if code == obj.new_method:
                return display
        return obj.new_method

    def get_impact_percentage(self, obj):
        """Calculate percentage impact of revaluation"""
        if obj.old_inventory_value and obj.old_inventory_value > 0:
            return float((obj.revaluation_amount / obj.old_inventory_value) * 100)
        return 0.0

    def create(self, validated_data):
        request = self.context.get('request')
        company = getattr(request, 'company', None)
        user = getattr(request, 'user', None)
        validated_data['company'] = company
        if user:
            validated_data['requested_by'] = user
        validated_data['status'] = 'PENDING'
        return super().create(validated_data)
