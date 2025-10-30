from rest_framework import viewsets
from .models import Product, StockMovement, Warehouse, UnitOfMeasure, StockMovementLine, ProductCategory, StockLedger, DeliveryOrder, GoodsReceipt, StockLevel, GoodsReceiptLine, DeliveryOrderLine
from .serializers import ProductSerializer, StockMovementSerializer, WarehouseSerializer, UnitOfMeasureSerializer, StockMovementLineSerializer, ProductCategorySerializer, StockLedgerSerializer, DeliveryOrderSerializer, GoodsReceiptSerializer, StockLevelSerializer, GoodsReceiptLineSerializer, DeliveryOrderLineSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class StockMovementViewSet(viewsets.ModelViewSet):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer

class UnitOfMeasureViewSet(viewsets.ModelViewSet):
    queryset = UnitOfMeasure.objects.all()
    serializer_class = UnitOfMeasureSerializer

class StockMovementLineViewSet(viewsets.ModelViewSet):
    queryset = StockMovementLine.objects.all()
    serializer_class = StockMovementLineSerializer

class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer

class StockLedgerViewSet(viewsets.ModelViewSet):
    queryset = StockLedger.objects.all()
    serializer_class = StockLedgerSerializer

class DeliveryOrderViewSet(viewsets.ModelViewSet):
    queryset = DeliveryOrder.objects.all()
    serializer_class = DeliveryOrderSerializer

class GoodsReceiptViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceipt.objects.all()
    serializer_class = GoodsReceiptSerializer

class StockLevelViewSet(viewsets.ModelViewSet):
    queryset = StockLevel.objects.all()
    serializer_class = StockLevelSerializer

class GoodsReceiptLineViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceiptLine.objects.all()
    serializer_class = GoodsReceiptLineSerializer

class DeliveryOrderLineViewSet(viewsets.ModelViewSet):
    queryset = DeliveryOrderLine.objects.all()
    serializer_class = DeliveryOrderLineSerializer