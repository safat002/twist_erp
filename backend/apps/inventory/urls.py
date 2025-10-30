from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, StockMovementViewSet, WarehouseViewSet, UnitOfMeasureViewSet, StockMovementLineViewSet, ProductCategoryViewSet, StockLedgerViewSet, DeliveryOrderViewSet, GoodsReceiptViewSet, StockLevelViewSet, GoodsReceiptLineViewSet, DeliveryOrderLineViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'stock-movements', StockMovementViewSet)
router.register(r'warehouses', WarehouseViewSet)
router.register(r'units-of-measure', UnitOfMeasureViewSet)
router.register(r'stock-movement-lines', StockMovementLineViewSet)
router.register(r'product-categories', ProductCategoryViewSet)
router.register(r'stock-ledgers', StockLedgerViewSet)
router.register(r'delivery-orders', DeliveryOrderViewSet)
router.register(r'goods-receipts', GoodsReceiptViewSet)
router.register(r'stock-levels', StockLevelViewSet)
router.register(r'goods-receipt-lines', GoodsReceiptLineViewSet)
router.register(r'delivery-order-lines', DeliveryOrderLineViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
