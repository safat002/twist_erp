from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    AccountViewSet,
    BankStatementViewSet,
    FiscalPeriodViewSet,
    InvoiceViewSet,
    JournalViewSet,
    JournalVoucherViewSet,
    PaymentViewSet,
    FinanceReportsViewSet,
    CurrencyViewSet,
    InventoryPostingRuleViewSet,
)
from .views.financial_statement_views import FinancialStatementViewSet
from .extra_views.reconciliation_views import GLReconciliationViewSet

router = DefaultRouter()
router.register(r'accounts', AccountViewSet)
router.register(r'journals', JournalViewSet)
router.register(r'journal-vouchers', JournalVoucherViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'periods', FiscalPeriodViewSet)
router.register(r'bank-statements', BankStatementViewSet)
router.register(r'reports', FinanceReportsViewSet, basename='finance-reports')
router.register(r'financial-statements', FinancialStatementViewSet, basename='financial-statements')
router.register(r'gl-reconciliation', GLReconciliationViewSet, basename='gl-reconciliation')
router.register(r'currencies', CurrencyViewSet, basename='finance-currencies')
router.register(r'inventory-posting-rules', InventoryPostingRuleViewSet, basename='inventory-posting-rule')

urlpatterns = [
    path('', include(router.urls)),
]
