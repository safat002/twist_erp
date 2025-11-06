from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CompanyGroupViewSet,
    CompanyViewSet,
    BranchViewSet,
    DepartmentViewSet,
    DepartmentMembershipViewSet,
    CompanyGroupProvisionView,
    OrganizationalContextView,
    CurrencyChoicesView,
)

# Router for ViewSets
router = DefaultRouter()
router.register(r'groups', CompanyGroupViewSet, basename='company-group')
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'branches', BranchViewSet, basename='branch')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'department-memberships', DepartmentMembershipViewSet, basename='department-membership')

# Custom URL patterns
urlpatterns = [
    # Legacy provisioning endpoint
    path('provision/', CompanyGroupProvisionView.as_view(), name='company-group-provision'),
    # Currency choices
    path('currency-choices/', CurrencyChoicesView.as_view(), name='currency-choices'),

    # Organizational context management
    path('context/', OrganizationalContextView.as_view(), name='organizational-context'),

    # Include router URLs
    path('', include(router.urls)),
]
