from django.urls import path

from .views import CashflowView, SalesPerformanceView, WarehouseStatusView


urlpatterns = [
    path('sales-performance/', SalesPerformanceView.as_view(), name='analytics-sales-performance'),
    path('cashflow/', CashflowView.as_view(), name='analytics-cashflow'),
    path('runs/', WarehouseStatusView.as_view(), name='analytics-run-status'),
]
