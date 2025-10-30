from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, SalesOrderViewSet, SalesOrderLineViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'sales-orders', SalesOrderViewSet)
router.register(r'sales-order-lines', SalesOrderLineViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
