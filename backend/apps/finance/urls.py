from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AccountViewSet, InvoiceViewSet, JournalViewSet, JournalVoucherViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r'accounts', AccountViewSet)
router.register(r'journals', JournalViewSet)
router.register(r'journal-vouchers', JournalVoucherViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
