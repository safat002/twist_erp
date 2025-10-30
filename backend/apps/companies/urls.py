from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    CompanyViewSet,
    ActiveCompanyView,
    ActivateCompanyView,
    CompanyGroupProvisionView,
)

router = DefaultRouter()
router.register(r'', CompanyViewSet, basename='company')

urlpatterns = [
    path('active/', ActiveCompanyView.as_view(), name='company-active'),
    path('<int:pk>/activate/', ActivateCompanyView.as_view(), name='company-activate'),
    path('provision/', CompanyGroupProvisionView.as_view(), name='company-group-provision'),
]

urlpatterns += router.urls
