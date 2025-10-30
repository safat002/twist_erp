from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PurchaseOrderLineViewSet,
    PurchaseOrderViewSet,
    PurchaseRequisitionViewSet,
    SupplierViewSet,
)

router = DefaultRouter()
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'purchase-requisitions', PurchaseRequisitionViewSet, basename='purchase-requisition')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
router.register(r'purchase-order-lines', PurchaseOrderLineViewSet, basename='purchase-order-line')

urlpatterns = [
    path('', include(router.urls)),
]
