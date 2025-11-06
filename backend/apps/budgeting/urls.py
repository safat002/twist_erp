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
    BudgetItemCodeViewSet,
    BudgetUnitOfMeasureViewSet,
    BudgetApprovalQueueView,
    BudgetRemarkTemplateViewSet,
    BudgetItemCategoryViewSet,
    BudgetItemSubCategoryViewSet,
    BudgetVarianceAuditViewSet,
    # Entry endpoints
    PermittedCostCentersView,
    DeclaredBudgetsView,
    EntrySummaryView,
    LastPriceView,
    AddBudgetItemView,
    SubmitEntryView,
    EntryLinesView,
)

router = DefaultRouter()
router.register(r'cost-centers', CostCenterViewSet, basename='budget-cost-centers')
router.register(r'periods', BudgetViewSet, basename='budget-periods')
router.register(r'lines', BudgetLineViewSet, basename='budget-lines')
router.register(r'usage', BudgetUsageViewSet, basename='budget-usage')
router.register(r'overrides', BudgetOverrideRequestViewSet, basename='budget-overrides')
router.register(r'snapshots', BudgetSnapshotViewSet, basename='budget-snapshots')
router.register(r'item-codes', BudgetItemCodeViewSet, basename='budget-item-codes')
router.register(r'uoms', BudgetUnitOfMeasureViewSet, basename='budget-uoms')
router.register(r'remark-templates', BudgetRemarkTemplateViewSet, basename='budget-remark-templates')
router.register(r'variance-audit', BudgetVarianceAuditViewSet, basename='budget-variance-audit')
router.register(r'item-categories', BudgetItemCategoryViewSet, basename='budget-item-categories')
router.register(r'item-sub-categories', BudgetItemSubCategoryViewSet, basename='budget-item-sub-categories')

urlpatterns = [
    path('', include(router.urls)),
    path('check-availability/', BudgetAvailabilityCheckView.as_view(), name='budget-availability'),
    path('workspace/summary/', BudgetWorkspaceSummaryView.as_view(), name='budget-workspace-summary'),
    path('approvals/queue/', BudgetApprovalQueueView.as_view(), name='budget-approval-queue'),
    # Budget Entry specific
    path('entry/declared/', DeclaredBudgetsView.as_view(), name='budget-entry-declared'),
    path('entry/cost-centers/', PermittedCostCentersView.as_view(), name='budget-entry-cost-centers'),
    path('entry/summary/', EntrySummaryView.as_view(), name='budget-entry-summary'),
    path('entry/price/', LastPriceView.as_view(), name='budget-entry-price'),
    path('entry/lines/', EntryLinesView.as_view(), name='budget-entry-lines'),
    path('entry/add/', AddBudgetItemView.as_view(), name='budget-entry-add'),
    path('entry/submit/', SubmitEntryView.as_view(), name='budget-entry-submit'),
]
