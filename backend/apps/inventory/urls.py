from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet,
    StockMovementViewSet,
    WarehouseViewSet,
    UnitOfMeasureViewSet,
    StockMovementLineViewSet,
    ProductCategoryViewSet,
    StockLedgerViewSet,
    DeliveryOrderViewSet,
    GoodsReceiptViewSet,
    StockLevelViewSet,
    GoodsReceiptLineViewSet,
    DeliveryOrderLineViewSet,
    InternalRequisitionViewSet,
    InventoryOverviewView,
    StockLedgerSummaryView,
    StockLedgerEventsView,
    # Valuation endpoints
    ItemValuationMethodViewSet,
    CostLayerViewSet,
    ValuationChangeLogViewSet,
    ValuationReportView,
    CurrentCostView,
    LandedCostAdjustmentView,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'stock-movements', StockMovementViewSet, basename='stock-movement')
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
router.register(r'requisitions/internal', InternalRequisitionViewSet, basename='internal-requisition')

# Valuation endpoints
router.register(r'valuation-methods', ItemValuationMethodViewSet, basename='valuation-method')
router.register(r'cost-layers', CostLayerViewSet, basename='cost-layer')
router.register(r'valuation-changes', ValuationChangeLogViewSet, basename='valuation-change')

urlpatterns = [
    path('', include(router.urls)),
    # Aliases for frontend expectations
    path('movements/', StockMovementViewSet.as_view({'get': 'list'}), name='inventory-movements'),
    path('overview/', InventoryOverviewView.as_view(), name='inventory-overview'),
    path('stock-ledger/summary/', StockLedgerSummaryView.as_view(), name='inventory-stock-ledger-summary'),
    path('stock-ledger/events/', StockLedgerEventsView.as_view(), name='inventory-stock-ledger-events'),

    # Valuation custom views
    path('valuation/report/', ValuationReportView.as_view(), name='valuation-report'),
    path('valuation/current-cost/', CurrentCostView.as_view(), name='current-cost'),
    path('valuation/landed-cost-adjustment/', LandedCostAdjustmentView.as_view(), name='landed-cost-adjustment'),
]
