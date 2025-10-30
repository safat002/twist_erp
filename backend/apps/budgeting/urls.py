from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BudgetAvailabilityCheckView,
    BudgetLineViewSet,
    BudgetOverrideRequestViewSet,
    BudgetSnapshotViewSet,
    BudgetUsageViewSet,
    BudgetViewSet,
    BudgetWorkspaceSummaryView,
    CostCenterViewSet,
)

router = DefaultRouter()
router.register(r'cost-centers', CostCenterViewSet, basename='budget-cost-centers')
router.register(r'periods', BudgetViewSet, basename='budget-periods')
router.register(r'lines', BudgetLineViewSet, basename='budget-lines')
router.register(r'usage', BudgetUsageViewSet, basename='budget-usage')
router.register(r'overrides', BudgetOverrideRequestViewSet, basename='budget-overrides')
router.register(r'snapshots', BudgetSnapshotViewSet, basename='budget-snapshots')

urlpatterns = [
    path('', include(router.urls)),
    path('check-availability/', BudgetAvailabilityCheckView.as_view(), name='budget-availability'),
    path('workspace/summary/', BudgetWorkspaceSummaryView.as_view(), name='budget-workspace-summary'),
]
