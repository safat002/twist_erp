from rest_framework import serializers
from .models import Product, StockMovement, Warehouse, UnitOfMeasure, StockMovementLine, ProductCategory, StockLedger, DeliveryOrder, GoodsReceipt, StockLevel, GoodsReceiptLine, DeliveryOrderLine

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
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

class StockMovementLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovementLine
        fields = '__all__'

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
    class Meta:
        model = GoodsReceiptLine
        fields = '__all__'

class DeliveryOrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryOrderLine
        fields = '__all__'