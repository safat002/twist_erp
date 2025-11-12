from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet,
    ItemViewSet,
    StockMovementViewSet,
    WarehouseViewSet,
    WarehouseBinViewSet,
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
    ItemOperationalExtensionViewSet,
    ItemWarehouseConfigViewSet,
    ItemUOMConversionViewSet,
    MovementEventViewSet,
    ItemSupplierViewSet,
    ItemFEFOConfigViewSet,
    InTransitShipmentLineViewSet,
    ReplenishmentSuggestionView,
    AutoReplenishmentView,
    # Phase 2: Variance tracking
    StandardCostVarianceViewSet,
    PurchasePriceVarianceViewSet,
    VarianceSummaryView,
    # Phase 2: Enhanced landed costs
    LandedCostComponentViewSet,
    LandedCostPreviewView,
    LandedCostApplyView,
    LandedCostSummaryView,
    # Landed Cost Vouchers
    LandedCostVoucherViewSet,
    LandedCostAllocationViewSet,
    # Return To Vendor
    ReturnToVendorViewSet,
    ReturnToVendorLineViewSet,
    # Phase 3: QC & Compliance
    StockHoldViewSet,
    QCCheckpointViewSet,
    QCResultViewSet,
    BatchLotViewSet,
    SerialNumberViewSet,
    # Material Issue Management
    MaterialIssueViewSet,
    MaterialIssueLineViewSet,
    # Warehouse Category Mapping
    WarehouseCategoryMappingViewSet,
    WarehouseOverrideLogViewSet,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'items', ItemViewSet, basename='inventory-item')
router.register(r'stock-movements', StockMovementViewSet, basename='stock-movement')
router.register(r'warehouses', WarehouseViewSet)
router.register(r'warehouse-bins', WarehouseBinViewSet, basename='warehouse-bin')
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
router.register(r'item-operational-profiles', ItemOperationalExtensionViewSet, basename='item-operational-profile')
router.register(r'item-warehouse-configs', ItemWarehouseConfigViewSet, basename='item-warehouse-config')
router.register(r'item-uom-conversions', ItemUOMConversionViewSet, basename='item-uom-conversion')
router.register(r'movement-events', MovementEventViewSet, basename='movement-event')
router.register(r'item-suppliers', ItemSupplierViewSet, basename='item-supplier')
router.register(r'item-fefo-configs', ItemFEFOConfigViewSet, basename='item-fefo-config')
router.register(r'in-transit-lines', InTransitShipmentLineViewSet, basename='in-transit-line')

# Phase 2: Variance tracking
router.register(r'variances/standard-cost', StandardCostVarianceViewSet, basename='standard-cost-variance')
router.register(r'variances/purchase-price', PurchasePriceVarianceViewSet, basename='purchase-price-variance')

# Phase 2: Enhanced landed costs
router.register(r'landed-costs', LandedCostComponentViewSet, basename='landed-cost-component')

# Landed Cost Vouchers
router.register(r'landed-cost-vouchers', LandedCostVoucherViewSet, basename='landed-cost-voucher')
router.register(r'landed-cost-allocations', LandedCostAllocationViewSet, basename='landed-cost-allocation')

# Return To Vendor
router.register(r'return-to-vendor', ReturnToVendorViewSet, basename='return-to-vendor')
router.register(r'return-to-vendor-lines', ReturnToVendorLineViewSet, basename='return-to-vendor-line')

# Phase 3: QC & Compliance
router.register(r'stock-holds', StockHoldViewSet, basename='stock-hold')
router.register(r'qc-checkpoints', QCCheckpointViewSet, basename='qc-checkpoint')
router.register(r'qc-results', QCResultViewSet, basename='qc-result')
router.register(r'batch-lots', BatchLotViewSet, basename='batch-lot')
router.register(r'serial-numbers', SerialNumberViewSet, basename='serial-number')

# Material Issue Management
router.register(r'material-issues', MaterialIssueViewSet, basename='material-issue')
router.register(r'material-issue-lines', MaterialIssueLineViewSet, basename='material-issue-line')

# Warehouse Category Mapping
router.register(r'warehouse-mappings', WarehouseCategoryMappingViewSet, basename='warehouse-mapping')
router.register(r'warehouse-overrides', WarehouseOverrideLogViewSet, basename='warehouse-override')

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
    path('replenishment/suggestions/', ReplenishmentSuggestionView.as_view(), name='replenishment-suggestions'),
    path('replenishment/auto-pr/', AutoReplenishmentView.as_view(), name='replenishment-auto-pr'),

    # Phase 2: Variance tracking
    path('variances/summary/', VarianceSummaryView.as_view(), name='variance-summary'),

    # Phase 2: Enhanced landed costs
    path('landed-costs/preview/', LandedCostPreviewView.as_view(), name='landed-cost-preview'),
    path('landed-costs/apply/', LandedCostApplyView.as_view(), name='landed-cost-apply'),
    path('landed-costs/grn/<int:grn_id>/summary/', LandedCostSummaryView.as_view(), name='landed-cost-summary'),
]
