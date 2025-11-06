from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PolicyDocumentViewSet, PolicyAcknowledgementViewSet, PolicyCategoryViewSet

router = DefaultRouter()
router.register(r"policies", PolicyDocumentViewSet, basename="policy-document")
router.register(r"acknowledgements", PolicyAcknowledgementViewSet, basename="policy-ack")
router.register(r"categories", PolicyCategoryViewSet, basename="policy-category")

urlpatterns = [
    path("", include(router.urls)),
]
