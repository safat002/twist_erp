from rest_framework import serializers
from django.utils import timezone
from .models import (
    Product, Item, StockMovement, Warehouse, UnitOfMeasure, StockMovementLine,
    ProductCategory, StockLedger, DeliveryOrder, GoodsReceipt, StockLevel,
    GoodsReceiptLine, DeliveryOrderLine, InternalRequisition,
    ItemValuationMethod, CostLayer, ValuationChangeLog,
    ItemOperationalExtension, ItemWarehouseConfig, ItemUOMConversion,
    MovementEvent, WarehouseBin, ItemSupplier, ItemFEFOConfig,
    StandardCostVariance, PurchasePriceVariance, LandedCostComponent,
    LandedCostLineApportionment, InTransitShipmentLine,
    LandedCostVoucher, LandedCostAllocation, ReturnToVendor, ReturnToVendorLine,
    # Phase 3: QC & Compliance models
    StockHold, QCCheckpoint, QCResult, BatchLot, SerialNumber,
    # Material Issue Management
    MaterialIssue, MaterialIssueLine,
    # Warehouse Category Mapping
    WarehouseCategoryMapping, WarehouseOverrideLog
)
from apps.budgeting.models import BudgetItemCode
from .services.uom_service import UoMConversionService


class BudgetLinkedSerializerMixin:
    """Ensures serializers always carry a budgeting master link."""

    budget_field = 'budget_item'
    item_field = 'budget_item'

    def _ensure_budget_link(self, attrs):
        budget_item = attrs.get(self.budget_field) or getattr(self.instance, self.budget_field, None)
        item = attrs.get(self.item_field) or getattr(self.instance, self.item_field, None)
        if not budget_item and item:
            budget_item = getattr(item, 'budget_item', None)
            if budget_item:
                attrs[self.budget_field] = budget_item
        if not budget_item:
            raise serializers.ValidationError({self.budget_field: 'Budget item is required.'})
        if not attrs.get(self.item_field) and item is None:
            linked = Item.objects.filter(budget_item=budget_item).first()
            if linked:
                attrs[self.item_field] = linked
        return attrs

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return self._ensure_budget_link(attrs)


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class WarehouseBinSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseBin
        fields = '__all__'

class ItemOperationalExtensionSerializer(BudgetLinkedSerializerMixin, serializers.ModelSerializer):
    purchase_uom_code = serializers.CharField(source='purchase_uom.code', read_only=True)
    stock_uom_code = serializers.CharField(source='stock_uom.code', read_only=True)
    sales_uom_code = serializers.CharField(source='sales_uom.code', read_only=True)
    budget_item_code = serializers.CharField(source='budget_item.code', read_only=True)
    budget_item_name = serializers.CharField(source='budget_item.name', read_only=True)

    class Meta:
        model = ItemOperationalExtension
        fields = '__all__'
        read_only_fields = ['company', 'budget_item', 'created_at', 'updated_at']

class ItemWarehouseConfigSerializer(BudgetLinkedSerializerMixin, serializers.ModelSerializer):
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    budget_item_code = serializers.CharField(source='budget_item.code', read_only=True)
    budget_item_name = serializers.CharField(source='budget_item.name', read_only=True)

    class Meta:
        model = ItemWarehouseConfig
        fields = '__all__'
        read_only_fields = ['company', 'created_at', 'updated_at']

class ItemUOMConversionSerializer(BudgetLinkedSerializerMixin, serializers.ModelSerializer):
    from_uom_code = serializers.CharField(source='from_uom.code', read_only=True)
    from_uom_name = serializers.CharField(source='from_uom.name', read_only=True)
    to_uom_code = serializers.CharField(source='to_uom.code', read_only=True)
    to_uom_name = serializers.CharField(source='to_uom.name', read_only=True)
    budget_item_code = serializers.CharField(source='budget_item.code', read_only=True)

    class Meta:
        model = ItemUOMConversion
        fields = '__all__'
        read_only_fields = ['company', 'created_at', 'updated_at']

class ItemSerializer(serializers.ModelSerializer):
    operational_profile = ItemOperationalExtensionSerializer(read_only=True)
    warehouse_configs = ItemWarehouseConfigSerializer(many=True, read_only=True)
    uom_conversions = ItemUOMConversionSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    uom_code = serializers.CharField(source='uom.code', read_only=True)
    budget_item_code = serializers.CharField(source='budget_item.code', read_only=True)
    budget_item_name = serializers.CharField(source='budget_item.name', read_only=True)
    budget_item_uom_code = serializers.CharField(source='budget_item.uom.code', read_only=True)
    budget_item_standard_price = serializers.DecimalField(
        source='budget_item.standard_price',
        read_only=True,
        max_digits=20,
        decimal_places=2,
    )

    class Meta:
        model = Item
        fields = '__all__'

    def validate(self, attrs):
        if not self.instance and not attrs.get('budget_item'):
            raise serializers.ValidationError({'budget_item': 'Link to a budgeting item is required.'})
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        company = getattr(request, 'company', None)
        if company:
            validated_data.setdefault('company', company)
        elif 'company' not in validated_data:
            raise serializers.ValidationError({'company': 'Active company context is required.'})
        return super().create(validated_data)

class MovementEventSerializer(serializers.ModelSerializer):
    item_code = serializers.CharField(source='item.code', read_only=True)
    item_name = serializers.CharField(source='item.name', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    stock_uom_code = serializers.CharField(source='stock_uom.code', read_only=True)
    source_uom_code = serializers.CharField(source='source_uom.code', read_only=True)

    class Meta:
        model = MovementEvent
        fields = [
            'id', 'company', 'budget_item', 'item_code', 'item_name', 'warehouse', 'warehouse_code',
            'warehouse_name', 'bin', 'event_type', 'qty_change', 'stock_uom', 'stock_uom_code',
            'source_uom', 'source_uom_code', 'source_quantity', 'event_date', 'event_timestamp',
            'reference_document_type', 'reference_document_id', 'reference_number',
            'cost_per_unit_at_event', 'valuation_method_used', 'event_metadata'
        ]
        read_only_fields = [f for f in fields if f not in {'event_metadata'}]

class ItemSupplierSerializer(BudgetLinkedSerializerMixin, serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    supplier_code = serializers.CharField(source='supplier.code', read_only=True)
    item_code = serializers.SerializerMethodField()
    item_name = serializers.SerializerMethodField()
    supplier_pack_uom_code = serializers.CharField(source='supplier_pack_uom.code', read_only=True)
    budget_item_code = serializers.CharField(source='budget_item.code', read_only=True)
    budget_item_name = serializers.CharField(source='budget_item.name', read_only=True)

    class Meta:
        model = ItemSupplier
        fields = '__all__'
        read_only_fields = ['company', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        company = getattr(request, 'company', None)
        if not company:
            raise serializers.ValidationError({'detail': 'Active company context is required'})
        validated_data['company'] = company
        if not validated_data.get('supplier_pack_uom'):
            base_uom = None
            if validated_data.get('budget_item'):
                base_uom = validated_data['budget_item'].uom
            if not base_uom and validated_data.get('budget_item') and validated_data['budget_item'].uom_id:
                base_uom = validated_data['budget_item'].uom
            if base_uom:
                validated_data['supplier_pack_uom'] = base_uom
        return super().create(validated_data)

    def get_item_code(self, obj):
        if obj.budget_item_id and obj.budget_item:
            return obj.budget_item.code
        return getattr(obj.item, 'code', None)

    def get_item_name(self, obj):
        if obj.budget_item_id and obj.budget_item:
            return obj.budget_item.name
        return getattr(obj.item, 'name', None)

class ItemFEFOConfigSerializer(BudgetLinkedSerializerMixin, serializers.ModelSerializer):
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    budget_item_code = serializers.CharField(source='budget_item.code', read_only=True)
    budget_item_name = serializers.CharField(source='budget_item.name', read_only=True)

    class Meta:
        model = ItemFEFOConfig
        fields = '__all__'
        read_only_fields = ['company', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        company = getattr(request, 'company', None)
        if not company:
            raise serializers.ValidationError({'detail': 'Active company context is required'})
        validated_data['company'] = company
        return super().create(validated_data)

class InTransitShipmentLineSerializer(serializers.ModelSerializer):
    item_code = serializers.CharField(source='item.code', read_only=True)
    item_name = serializers.CharField(source='item.name', read_only=True)
    from_warehouse_code = serializers.CharField(source='from_warehouse.code', read_only=True)
    to_warehouse_code = serializers.CharField(source='to_warehouse.code', read_only=True)
    movement_number = serializers.CharField(source='movement.movement_number', read_only=True)

    class Meta:
        model = InTransitShipmentLine
        fields = '__all__'
        read_only_fields = ['company', 'created_at']

class StockMovementSerializer(serializers.ModelSerializer):
    from_warehouse_name = serializers.SerializerMethodField()
    to_warehouse_name = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = '__all__'

    def get_from_warehouse_name(self, obj):
        return getattr(obj.from_warehouse, 'name', None) if obj.from_warehouse else None

    def get_to_warehouse_name(self, obj):
        return getattr(obj.to_warehouse, 'name', None) if obj.to_warehouse else None

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
        if product is not None and not attrs.get('budget_item'):
            attrs['budget_item'] = product
        attrs = super().validate(attrs)
        return self._normalize_quantities(attrs)

    def _normalize_quantities(self, attrs):
        item = attrs.get('budget_item') or getattr(self.instance, 'budget_item', None)
        if not item:
            return attrs
        movement = attrs.get('movement') or getattr(self.instance, 'movement', None)
        entered_uom = attrs.get('entered_uom') or getattr(self.instance, 'entered_uom', None)
        entered_qty = attrs.get('entered_quantity', None)
        if entered_qty is None and attrs.get('quantity') is not None and not entered_uom:
            # Ensure entered fields mirror stock qty to keep history consistent
            attrs['entered_quantity'] = attrs['quantity']
            attrs['entered_uom'] = entered_uom or item.uom
            return attrs
        if entered_qty is None:
            return attrs
        if not entered_uom:
            entered_uom = item.uom
            attrs['entered_uom'] = entered_uom
        context = self._movement_context(movement)
        converted = UoMConversionService.convert_quantity(
            item=item,
            quantity=entered_qty,
            from_uom=entered_uom,
            to_uom=item.uom,
            context=context,
        )
        attrs['quantity'] = converted
        return attrs

    @staticmethod
    def _movement_context(movement):
        if not movement:
            return None
        movement_type = (movement.movement_type or '').upper()
        if movement_type == 'RECEIPT':
            return 'purchase'
        if movement_type == 'ISSUE':
            return 'sales'
        return 'stock'

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
        if product is not None and not attrs.get('budget_item'):
            attrs['budget_item'] = product

        # Validate serial numbers for serialized items
        item = attrs.get('budget_item')
        serial_numbers = attrs.get('serial_numbers', [])
        quantity_received = attrs.get('quantity_received')

        if item and serial_numbers:
            # Get operational profile to check if item requires serial tracking
            profile = item.get_operational_profile()
            if profile and getattr(profile, 'is_serialized', False):
                # For serialized items, number of serials should match quantity
                if len(serial_numbers) != int(quantity_received):
                    raise serializers.ValidationError({
                        'serial_numbers': f'Number of serial numbers ({len(serial_numbers)}) must match quantity received ({int(quantity_received)}) for serialized items.'
                    })

        return super().validate(attrs)

class DeliveryOrderLineSerializer(serializers.ModelSerializer):
    # Back-compat: accept 'item' as alias for 'product' (model field name kept as product)
    item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all(), write_only=True, required=False, allow_null=True)

    class Meta:
        model = DeliveryOrderLine
        fields = '__all__'

    def validate(self, attrs):
        item = attrs.pop('budget_item', None)
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
    product_code = serializers.CharField(source='budget_item.code', read_only=True)
    product_name = serializers.CharField(source='budget_item.name', read_only=True)
    item_code = serializers.CharField(source='budget_item.code', read_only=True)
    item_name = serializers.CharField(source='budget_item.name', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    effective_cost_per_unit = serializers.SerializerMethodField()
    percentage_consumed = serializers.SerializerMethodField()

    class Meta:
        model = CostLayer
        fields = [
            'id',
            'company',
            'budget_item',
            'product_code',  # deprecated - use budget_item
            'product_name',  # deprecated - use budget_item
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


class StandardCostVarianceSerializer(serializers.ModelSerializer):
    """Serializer for standard cost variance tracking"""
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    variance_type_display = serializers.CharField(source='get_variance_type_display', read_only=True)
    variance_percentage = serializers.SerializerMethodField()

    class Meta:
        model = StandardCostVariance
        fields = [
            'id', 'company', 'product', 'product_code', 'product_name',
            'warehouse', 'warehouse_code', 'warehouse_name',
            'transaction_date', 'transaction_type', 'transaction_type_display',
            'reference_id', 'standard_cost', 'actual_cost', 'quantity',
            'variance_per_unit', 'total_variance_amount',
            'variance_type', 'variance_type_display', 'variance_percentage',
            'variance_je_id', 'posted_to_gl', 'gl_posted_date',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['variance_per_unit', 'total_variance_amount', 'variance_type']

    def get_variance_percentage(self, obj):
        """Calculate variance as percentage of standard cost"""
        if obj.standard_cost and obj.standard_cost > 0:
            return float((obj.variance_per_unit / obj.standard_cost) * 100)
        return 0.0


class PurchasePriceVarianceSerializer(serializers.ModelSerializer):
    """Serializer for purchase price variance tracking"""
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    grn_number = serializers.CharField(source='goods_receipt.grn_number', read_only=True)
    variance_type_display = serializers.CharField(source='get_variance_type_display', read_only=True)
    variance_percentage = serializers.SerializerMethodField()

    class Meta:
        model = PurchasePriceVariance
        fields = [
            'id', 'company', 'goods_receipt', 'grn_number',
            'product', 'product_code', 'product_name',
            'warehouse', 'warehouse_code', 'warehouse_name',
            'po_price', 'invoice_price', 'quantity',
            'variance_per_unit', 'total_variance_amount',
            'variance_type', 'variance_type_display', 'variance_percentage',
            'variance_je_id', 'posted_to_gl', 'gl_posted_date',
            'supplier_id', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['variance_per_unit', 'total_variance_amount', 'variance_type']

    def get_variance_percentage(self, obj):
        """Calculate variance as percentage of PO price"""
        if obj.po_price and obj.po_price > 0:
            return float((obj.variance_per_unit / obj.po_price) * 100)
        return 0.0


class LandedCostLineApportionmentSerializer(serializers.ModelSerializer):
    """Serializer for landed cost line-level apportionment detail"""
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    component_type = serializers.CharField(source='landed_cost_component.component_type', read_only=True)
    component_type_display = serializers.CharField(source='landed_cost_component.get_component_type_display', read_only=True)

    class Meta:
        model = LandedCostLineApportionment
        fields = [
            'id', 'company', 'landed_cost_component',
            'component_type', 'component_type_display',
            'goods_receipt_line', 'product', 'product_code', 'product_name',
            'basis_value', 'allocation_percentage', 'apportioned_amount',
            'cost_per_unit_adjustment', 'created_at'
        ]
        read_only_fields = ['allocation_percentage', 'apportioned_amount', 'cost_per_unit_adjustment']


class LandedCostComponentSerializer(serializers.ModelSerializer):
    """Serializer for landed cost components with line-level detail"""
    grn_number = serializers.CharField(source='goods_receipt.grn_number', read_only=True)
    component_type_display = serializers.CharField(source='get_component_type_display', read_only=True)
    apportionment_method_display = serializers.CharField(source='get_apportionment_method_display', read_only=True)
    line_apportionments = LandedCostLineApportionmentSerializer(many=True, read_only=True)
    applied_by_name = serializers.CharField(source='applied_by.get_full_name', read_only=True)

    class Meta:
        model = LandedCostComponent
        fields = [
            'id', 'company', 'goods_receipt', 'grn_number',
            'component_type', 'component_type_display',
            'description', 'total_amount', 'currency',
            'apportionment_method', 'apportionment_method_display',
            'apportioned_to_inventory', 'apportioned_to_cogs',
            'invoice_number', 'invoice_date', 'supplier_id',
            'je_id', 'posted_to_gl', 'gl_posted_date',
            'applied_by', 'applied_by_name', 'applied_date',
            'notes', 'line_apportionments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['apportioned_to_inventory', 'apportioned_to_cogs', 'posted_to_gl', 'gl_posted_date']

    def create(self, validated_data):
        request = self.context.get('request')
        company = getattr(request, 'company', None)
        user = getattr(request, 'user', None)
        validated_data['company'] = company
        if user:
            validated_data['applied_by'] = user
        return super().create(validated_data)


class LandedCostPreviewSerializer(serializers.Serializer):
    """Serializer for previewing landed cost apportionment before applying"""
    goods_receipt = serializers.IntegerField()
    components = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        )
    )
    apportionment_method = serializers.ChoiceField(choices=LandedCostComponent.APPORTIONMENT_METHOD_CHOICES)

    def validate(self, attrs):
        # Validate goods receipt exists
        try:
            grn = GoodsReceipt.objects.get(id=attrs['goods_receipt'])
            attrs['grn_instance'] = grn
        except GoodsReceipt.DoesNotExist:
            raise serializers.ValidationError({'goods_receipt': 'Goods Receipt not found'})

        # Validate components structure
        for component in attrs['components']:
            if 'component_type' not in component:
                raise serializers.ValidationError({'components': 'Each component must have component_type'})
            if 'total_amount' not in component:
                raise serializers.ValidationError({'components': 'Each component must have total_amount'})

        return attrs


# ============================================================================
# LANDED COST VOUCHER SERIALIZERS
# ============================================================================

class LandedCostAllocationSerializer(serializers.ModelSerializer):
    """Serializer for landed cost allocation to cost layers."""

    goods_receipt_number = serializers.CharField(source='goods_receipt.grn_number', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)
    cost_layer_info = serializers.SerializerMethodField()

    class Meta:
        model = LandedCostAllocation
        fields = [
            'id', 'company', 'voucher', 'goods_receipt', 'goods_receipt_number',
            'goods_receipt_line', 'product', 'product_name', 'product_code',
            'cost_layer', 'cost_layer_info', 'allocated_amount', 'allocation_percentage',
            'to_inventory', 'to_cogs', 'original_cost_per_unit',
            'cost_per_unit_adjustment', 'new_cost_per_unit', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_cost_layer_info(self, obj):
        if obj.cost_layer:
            return {
                'id': obj.cost_layer.id,
                'quantity': str(obj.cost_layer.quantity),
                'cost_per_unit': str(obj.cost_layer.cost_per_unit),
                'remaining_quantity': str(obj.cost_layer.remaining_quantity)
            }
        return None


class LandedCostVoucherSerializer(serializers.ModelSerializer):
    """Serializer for landed cost voucher."""

    allocations = LandedCostAllocationSerializer(many=True, read_only=True)
    submitted_by_name = serializers.CharField(source='submitted_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_submit = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()
    can_allocate = serializers.SerializerMethodField()

    class Meta:
        model = LandedCostVoucher
        fields = [
            'id', 'company', 'voucher_number', 'voucher_date', 'description',
            'total_cost', 'allocated_cost', 'unallocated_cost', 'currency',
            'status', 'status_display', 'submitted_by', 'submitted_by_name',
            'submitted_at', 'approved_by', 'approved_by_name', 'approved_at',
            'je_id', 'posted_to_gl', 'gl_posted_date', 'allocations',
            'invoice_number', 'invoice_date', 'supplier_id', 'notes',
            'can_edit', 'can_submit', 'can_approve', 'can_allocate',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'voucher_number', 'allocated_cost', 'unallocated_cost',
            'je_id', 'posted_to_gl', 'gl_posted_date', 'created_at', 'updated_at'
        ]

    def get_can_edit(self, obj):
        return obj.can_edit()

    def get_can_submit(self, obj):
        return obj.can_submit()

    def get_can_approve(self, obj):
        return obj.can_approve()

    def get_can_allocate(self, obj):
        return obj.can_allocate()

    def validate_total_cost(self, value):
        if value <= 0:
            raise serializers.ValidationError("Total cost must be greater than zero")
        return value


# ============================================================================
# RETURN TO VENDOR (RTV) SERIALIZERS
# ============================================================================

class ReturnToVendorLineSerializer(serializers.ModelSerializer):
    """Serializer for return to vendor line items."""

    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)
    uom_name = serializers.CharField(source='uom.name', read_only=True)
    budget_item_name = serializers.CharField(source='budget_item.name', read_only=True)
    movement_event_info = serializers.SerializerMethodField()

    class Meta:
        model = ReturnToVendorLine
        fields = [
            'id', 'company', 'rtv', 'goods_receipt_line', 'product',
            'product_name', 'product_code', 'description',
            'quantity_to_return', 'uom', 'uom_name', 'unit_cost', 'line_total',
            'reason', 'batch_lot_id', 'serial_numbers', 'quality_notes',
            'budget_item', 'budget_item_name', 'budget_reversed',
            'budget_reversal_date', 'movement_event', 'movement_event_info',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'line_total', 'budget_reversed', 'budget_reversal_date',
            'movement_event', 'created_at', 'updated_at'
        ]

    def get_movement_event_info(self, obj):
        if obj.movement_event:
            return {
                'id': obj.movement_event.id,
                'event_type': obj.movement_event.event_type,
                'quantity': str(obj.movement_event.quantity),
                'created_at': obj.movement_event.created_at.isoformat()
            }
        return None

    def validate_quantity_to_return(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero")
        return value


class ReturnToVendorSerializer(serializers.ModelSerializer):
    """Serializer for return to vendor (RTV)."""

    lines = ReturnToVendorLineSerializer(many=True, read_only=True)
    goods_receipt_number = serializers.CharField(source='goods_receipt.grn_number', read_only=True)
    supplier_name = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_submit = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()
    can_complete = serializers.SerializerMethodField()

    class Meta:
        model = ReturnToVendor
        fields = [
            'id', 'company', 'rtv_number', 'rtv_date', 'goods_receipt',
            'goods_receipt_number', 'supplier_id', 'supplier_name',
            'reason', 'reason_display', 'status', 'status_display',
            'total_return_value', 'refund_expected', 'refund_amount',
            'refund_status', 'carrier', 'tracking_number', 'pickup_date',
            'actual_pickup_date', 'expected_delivery_date', 'delivered_to_vendor_date',
            'je_id', 'posted_to_gl', 'gl_posted_date', 'debit_note_number',
            'debit_note_date', 'created_by', 'created_by_name', 'submitted_at',
            'approved_by', 'approved_by_name', 'approved_at', 'completed_at',
            'notes', 'lines', 'can_edit', 'can_submit', 'can_approve', 'can_complete',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'rtv_number', 'total_return_value', 'je_id', 'posted_to_gl',
            'gl_posted_date', 'created_at', 'updated_at'
        ]

    def get_supplier_name(self, obj):
        # This would need to fetch from procurement.Supplier model
        # For now, return supplier_id as string
        return f"Supplier {obj.supplier_id}" if obj.supplier_id else None

    def get_can_edit(self, obj):
        return obj.can_edit()

    def get_can_submit(self, obj):
        return obj.can_submit()

    def get_can_approve(self, obj):
        return obj.can_approve()

    def get_can_complete(self, obj):
        return obj.can_complete()

    def validate_refund_amount(self, value):
        if value and value < 0:
            raise serializers.ValidationError("Refund amount cannot be negative")
        return value


# ============================================================================
# PHASE 3: QUALITY CONTROL & COMPLIANCE SERIALIZERS
# ============================================================================

class StockHoldSerializer(serializers.ModelSerializer):
    """Serializer for stock holds"""
    hold_type_display = serializers.CharField(source='get_hold_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    disposition_display = serializers.CharField(source='get_disposition_display', read_only=True)
    qc_pass_result_display = serializers.CharField(source='get_qc_pass_result_display', read_only=True)

    budget_item_code = serializers.CharField(source='budget_item.code', read_only=True)
    budget_item_name = serializers.CharField(source='budget_item.name', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    bin_code = serializers.CharField(source='bin.code', read_only=True, allow_null=True)
    batch_lot_code = serializers.CharField(source='batch_lot.internal_batch_code', read_only=True, allow_null=True)

    hold_by_name = serializers.CharField(source='hold_by.get_full_name', read_only=True)
    released_by_name = serializers.CharField(source='released_by.get_full_name', read_only=True, allow_null=True)

    is_overdue = serializers.SerializerMethodField()
    days_held = serializers.SerializerMethodField()

    class Meta:
        model = StockHold
        fields = [
            'id', 'company', 'budget_item', 'budget_item_code', 'budget_item_name',
            'warehouse', 'warehouse_code', 'warehouse_name', 'bin', 'bin_code',
            'batch_lot', 'batch_lot_code', 'hold_type', 'hold_type_display',
            'qty_held', 'hold_reason', 'hold_date', 'hold_by', 'hold_by_name',
            'expected_release_date', 'actual_release_date', 'released_by', 'released_by_name',
            'qc_pass_result', 'qc_pass_result_display', 'qc_notes', 'escalation_flag',
            'status', 'status_display', 'disposition', 'disposition_display',
            'is_overdue', 'days_held', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_is_overdue(self, obj):
        if obj.status != 'ACTIVE' or not obj.expected_release_date:
            return False
        from datetime import date
        return obj.expected_release_date < date.today()

    def get_days_held(self, obj):
        from datetime import date
        if obj.status == 'ACTIVE':
            return (date.today() - obj.hold_date).days
        elif obj.actual_release_date:
            return (obj.actual_release_date - obj.hold_date).days
        return 0


class QCCheckpointSerializer(serializers.ModelSerializer):
    """Serializer for QC checkpoints"""
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True, allow_null=True)

    class Meta:
        model = QCCheckpoint
        fields = [
            'id', 'company', 'warehouse', 'warehouse_code', 'warehouse_name',
            'checkpoint_name', 'checkpoint_order', 'automatic_after',
            'inspection_criteria', 'inspection_template', 'acceptance_threshold',
            'escalation_threshold', 'assigned_to', 'assigned_to_name',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class QCResultSerializer(serializers.ModelSerializer):
    """Serializer for QC inspection results"""
    qc_status_display = serializers.CharField(source='get_qc_status_display', read_only=True)
    rejection_reason_display = serializers.CharField(source='get_rejection_reason_display', read_only=True, allow_null=True)

    grn_number = serializers.CharField(source='grn.grn_number', read_only=True)
    checkpoint_name = serializers.CharField(source='checkpoint.checkpoint_name', read_only=True)
    inspected_by_name = serializers.CharField(source='inspected_by.get_full_name', read_only=True)

    rejection_percentage = serializers.SerializerMethodField()
    passed = serializers.SerializerMethodField()

    class Meta:
        model = QCResult
        fields = [
            'id', 'company', 'grn', 'grn_number', 'checkpoint', 'checkpoint_name',
            'inspected_by', 'inspected_by_name', 'inspected_date',
            'qty_inspected', 'qty_accepted', 'qty_rejected', 'rejection_percentage',
            'rejection_reason', 'rejection_reason_display', 'qc_status', 'qc_status_display',
            'passed', 'notes', 'rework_instruction', 'attachment', 'hold_created',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_rejection_percentage(self, obj):
        if obj.qty_inspected > 0:
            return float(obj.qty_rejected / obj.qty_inspected * 100)
        return 0.0

    def get_passed(self, obj):
        return obj.qc_status == 'PASS'


class BatchLotSerializer(serializers.ModelSerializer):
    """Serializer for batch/lot tracking"""
    hold_status_display = serializers.CharField(source='get_hold_status_display', read_only=True)

    budget_item_code = serializers.CharField(source='budget_item.code', read_only=True)
    budget_item_name = serializers.CharField(source='budget_item.name', read_only=True)
    grn_number = serializers.CharField(source='grn.grn_number', read_only=True, allow_null=True)

    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True, allow_null=True)
    total_value = serializers.SerializerMethodField()
    utilization_pct = serializers.SerializerMethodField()

    class Meta:
        model = BatchLot
        fields = [
            'id', 'company', 'budget_item', 'budget_item_code', 'budget_item_name',
            'supplier_lot_number', 'internal_batch_code', 'grn', 'grn_number',
            'mfg_date', 'exp_date', 'received_date', 'received_qty', 'current_qty',
            'cost_per_unit', 'total_value', 'utilization_pct',
            'certificate_of_analysis', 'coa_upload_date', 'storage_location',
            'hazmat_classification', 'hold_status', 'hold_status_display',
            'fefo_sequence', 'is_expired', 'days_until_expiry',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_expired', 'days_until_expiry']

    def get_total_value(self, obj):
        return float(obj.current_qty * obj.cost_per_unit)

    def get_utilization_pct(self, obj):
        if obj.received_qty > 0:
            consumed = obj.received_qty - obj.current_qty
            return float(consumed / obj.received_qty * 100)
        return 0.0


class SerialNumberSerializer(serializers.ModelSerializer):
    """Serializer for serial number tracking"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    budget_item_code = serializers.CharField(source='budget_item.code', read_only=True)
    budget_item_name = serializers.CharField(source='budget_item.name', read_only=True)
    batch_lot_code = serializers.CharField(source='batch_lot.internal_batch_code', read_only=True, allow_null=True)

    is_under_warranty = serializers.SerializerMethodField()
    days_in_service = serializers.SerializerMethodField()

    class Meta:
        model = SerialNumber
        fields = [
            'id', 'company', 'budget_item', 'budget_item_code', 'budget_item_name',
            'serial_number', 'batch_lot', 'batch_lot_code',
            'warranty_start', 'warranty_end', 'is_under_warranty', 'asset_tag',
            'assigned_to_customer_order', 'issued_date', 'issued_to',
            'received_back_date', 'inspection_date', 'days_in_service',
            'status', 'status_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_is_under_warranty(self, obj):
        if not obj.warranty_end:
            return False
        from datetime import date
        return obj.warranty_end >= date.today()

    def get_days_in_service(self, obj):
        if obj.issued_date:
            from datetime import date
            end_date = obj.received_back_date or date.today()
            return (end_date - obj.issued_date).days
        return 0


# ============================================================================
# MATERIAL ISSUE SERIALIZERS
# ============================================================================

class MaterialIssueLineSerializer(serializers.ModelSerializer):
    """Serializer for Material Issue Line items"""
    budget_item_code = serializers.CharField(source='budget_item.code', read_only=True)
    budget_item_name = serializers.CharField(source='budget_item.name', read_only=True)
    uom_code = serializers.CharField(source='uom.code', read_only=True)
    batch_code = serializers.CharField(source='batch_lot.internal_batch_code', read_only=True, allow_null=True)
    cost_center_name = serializers.CharField(source='cost_center.name', read_only=True, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)

    class Meta:
        model = MaterialIssueLine
        fields = [
            'id', 'material_issue', 'company', 'budget_item', 'budget_item_code', 'budget_item_name',
            'budget_item', 'quantity_requested', 'quantity_issued', 'uom', 'uom_code',
            'batch_lot', 'batch_code', 'serial_numbers', 'unit_cost', 'total_cost',
            'cost_center', 'cost_center_name', 'project', 'project_name',
            'notes', 'movement_event', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'total_cost', 'movement_event', 'created_at', 'updated_at']


class MaterialIssueSerializer(serializers.ModelSerializer):
    """Serializer for Material Issue"""
    lines = MaterialIssueLineSerializer(many=True, required=False)

    issue_type_display = serializers.CharField(source='get_issue_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    cost_center_name = serializers.CharField(source='cost_center.name', read_only=True, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)

    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    issued_by_name = serializers.CharField(source='issued_by.get_full_name', read_only=True, allow_null=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True, allow_null=True)

    requisition_number = serializers.CharField(source='requisition.requisition_number', read_only=True, allow_null=True)

    total_cost = serializers.SerializerMethodField()
    total_lines = serializers.SerializerMethodField()

    class Meta:
        model = MaterialIssue
        fields = [
            'id', 'company', 'issue_number', 'issue_type', 'issue_type_display',
            'status', 'status_display', 'warehouse', 'warehouse_name',
            'cost_center', 'cost_center_name', 'project', 'project_name', 'department',
            'requisition', 'requisition_number', 'issue_date',
            'requested_by', 'requested_by_name', 'issued_by', 'issued_by_name',
            'approved_by', 'approved_by_name', 'purpose', 'notes',
            'stock_movement', 'total_cost', 'total_lines',
            'lines', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'issue_number', 'stock_movement', 'created_at', 'updated_at']

    def get_total_cost(self, obj):
        return float(sum(line.total_cost for line in obj.lines.all()))

    def get_total_lines(self, obj):
        return obj.lines.count()

    def create(self, validated_data):
        lines_data = validated_data.pop('lines', [])
        material_issue = MaterialIssue.objects.create(**validated_data)

        for line_data in lines_data:
            MaterialIssueLine.objects.create(
                material_issue=material_issue,
                company=material_issue.company,
                **line_data
            )

        return material_issue

    def update(self, instance, validated_data):
        lines_data = validated_data.pop('lines', None)

        # Update main fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update lines if provided and status is DRAFT
        if lines_data is not None and instance.status == 'DRAFT':
            # Delete existing lines
            instance.lines.all().delete()

            # Create new lines
            for line_data in lines_data:
                MaterialIssueLine.objects.create(
                    material_issue=instance,
                    company=instance.company,
                    **line_data
                )

        return instance


# ============================================================================
# WAREHOUSE CATEGORY MAPPING SERIALIZERS
# ============================================================================

class WarehouseCategoryMappingSerializer(serializers.ModelSerializer):
    """Serializer for warehouse-category mapping configuration"""
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_code = serializers.CharField(source='category.code', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True, allow_null=True)
    subcategory_code = serializers.CharField(source='subcategory.code', read_only=True, allow_null=True)
    warning_level_display = serializers.CharField(source='get_warning_level_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = WarehouseCategoryMapping
        fields = [
            'id', 'company', 'warehouse', 'warehouse_name', 'warehouse_code',
            'category', 'category_name', 'category_code',
            'subcategory', 'subcategory_name', 'subcategory_code',
            'is_default', 'priority', 'allow_multi_warehouse',
            'warning_level', 'warning_level_display', 'notes',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class WarehouseOverrideLogSerializer(serializers.ModelSerializer):
    """Serializer for warehouse override audit log - read-only"""
    budget_item_code = serializers.CharField(source='budget_item.code', read_only=True)
    budget_item_name = serializers.CharField(source='budget_item.name', read_only=True)
    suggested_warehouse_name = serializers.CharField(source='suggested_warehouse.name', read_only=True)
    suggested_warehouse_code = serializers.CharField(source='suggested_warehouse.code', read_only=True)
    actual_warehouse_name = serializers.CharField(source='actual_warehouse.name', read_only=True)
    actual_warehouse_code = serializers.CharField(source='actual_warehouse.code', read_only=True)
    warning_level_display = serializers.CharField(source='get_warning_level_display', read_only=True)
    overridden_by_name = serializers.CharField(source='overridden_by.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True, allow_null=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True, allow_null=True)

    class Meta:
        model = WarehouseOverrideLog
        fields = [
            'id', 'company', 'transaction_type', 'transaction_id', 'transaction_number',
            'budget_item', 'budget_item_code', 'budget_item_name',
            'suggested_warehouse', 'suggested_warehouse_name', 'suggested_warehouse_code',
            'actual_warehouse', 'actual_warehouse_name', 'actual_warehouse_code',
            'warning_level', 'warning_level_display', 'override_reason',
            'overridden_by', 'overridden_by_name', 'overridden_at',
            'was_approved', 'approved_by', 'approved_by_name',
            'was_valid_override', 'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'review_notes'
        ]
        read_only_fields = '__all__'  # All fields are read-only


class WarehouseValidationRequestSerializer(serializers.Serializer):
    """Serializer for warehouse validation request"""
    budget_item_id = serializers.IntegerField(required=True)
    selected_warehouse_id = serializers.IntegerField(required=True)

    def validate_budget_item_id(self, value):
        """Validate that budget item exists"""
        if not BudgetItemCode.objects.filter(id=value).exists():
            raise serializers.ValidationError("Budget item does not exist")
        return value

    def validate_selected_warehouse_id(self, value):
        """Validate that warehouse exists"""
        from .models import Warehouse
        if not Warehouse.objects.filter(id=value).exists():
            raise serializers.ValidationError("Warehouse does not exist")
        return value


class WarehouseOverrideCreateSerializer(serializers.Serializer):
    """Serializer for creating a warehouse override log entry"""
    transaction_type = serializers.CharField(max_length=50, required=True)
    transaction_id = serializers.IntegerField(required=True)
    transaction_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    budget_item_id = serializers.IntegerField(required=True)
    suggested_warehouse_id = serializers.IntegerField(required=True)
    actual_warehouse_id = serializers.IntegerField(required=True)
    warning_level = serializers.ChoiceField(
        choices=['INFO', 'WARNING', 'CRITICAL'],
        required=True
    )
    override_reason = serializers.CharField(required=True, allow_blank=False)
    was_approved = serializers.BooleanField(default=False)
    approved_by_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, data):
        """Validate that critical warnings require approval"""
        if data.get('warning_level') == 'CRITICAL' and not data.get('was_approved'):
            raise serializers.ValidationError({
                'was_approved': 'Critical warnings require supervisor approval'
            })
        return data

    def create(self, validated_data):
        """Create the override log entry"""
        from .models import WarehouseOverrideLog
        from apps.budgeting.models import BudgetItemCode
        from .models import Warehouse
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Get the actual objects
        budget_item = BudgetItemCode.objects.get(id=validated_data['budget_item_id'])
        suggested_warehouse = Warehouse.objects.get(id=validated_data['suggested_warehouse_id'])
        actual_warehouse = Warehouse.objects.get(id=validated_data['actual_warehouse_id'])
        overridden_by = self.context['request'].user

        # Get company from budget item
        company = budget_item.company

        # Get approved_by if provided
        approved_by = None
        if validated_data.get('approved_by_id'):
            approved_by = User.objects.get(id=validated_data['approved_by_id'])

        # Create the log entry
        log_entry = WarehouseOverrideLog.objects.create(
            company=company,
            transaction_type=validated_data['transaction_type'],
            transaction_id=validated_data['transaction_id'],
            transaction_number=validated_data.get('transaction_number', ''),
            budget_item=budget_item,
            item_category=budget_item.category if hasattr(budget_item, 'category') else None,
            suggested_warehouse=suggested_warehouse,
            actual_warehouse=actual_warehouse,
            warning_level=validated_data['warning_level'],
            override_reason=validated_data['override_reason'],
            overridden_by=overridden_by,
            was_approved=validated_data.get('was_approved', False),
            approved_by=approved_by
        )

        return log_entry
