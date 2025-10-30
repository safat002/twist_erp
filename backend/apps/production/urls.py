from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BillOfMaterialViewSet,
    MaterialIssueViewSet,
    ProductionReceiptViewSet,
    WorkOrderViewSet,
)

router = DefaultRouter()
router.register(r"boms", BillOfMaterialViewSet, basename="production-boms")
router.register(r"work-orders", WorkOrderViewSet, basename="production-work-orders")
router.register(r"issues", MaterialIssueViewSet, basename="production-issues")
router.register(r"receipts", ProductionReceiptViewSet, basename="production-receipts")

urlpatterns = [
    path("", include(router.urls)),
]
