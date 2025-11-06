from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BorrowerViewSet, LoanProductViewSet, LoanViewSet, LoanRepaymentViewSet

router = DefaultRouter()
router.register(r"borrowers", BorrowerViewSet, basename="mf-borrower")
router.register(r"products", LoanProductViewSet, basename="mf-product")
router.register(r"loans", LoanViewSet, basename="mf-loan")
router.register(r"repayments", LoanRepaymentViewSet, basename="mf-repayment")

urlpatterns = [
    path("", include(router.urls)),
]

