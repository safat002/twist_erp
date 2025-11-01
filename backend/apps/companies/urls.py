from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    CompanyViewSet,
    CompanyGroupProvisionView,
)

router = DefaultRouter()
router.register(r'', CompanyViewSet, basename='company')

urlpatterns = [
    path('provision/', CompanyGroupProvisionView.as_view(), name='company-group-provision'),
]

urlpatterns += router.urls
