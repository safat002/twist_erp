from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from shared.views import HealthCheckView
from core.admin_views import admin_appearance, set_admin_theme
from apps.companies.admin_views import AdminCompanyGroupProvisionView
from .views import favicon, home

admin.site.site_header = "Twist Erp administration Control Centre"
admin.site.site_title = "Twist Erp administration Control Centre"

urlpatterns = [
    path('', home, name='home'),
    re_path(r'^favicon\.ico$', favicon, name='favicon'),
    # Admin custom pages must come before the admin site include
    path('admin/appearance/', admin_appearance, name='admin-appearance'),
    path('admin/theme/<slug:theme>/', set_admin_theme, name='set-admin-theme'),
    path('admin/companies/provision/', AdminCompanyGroupProvisionView.as_view(), name='admin-company-group-provision'),
    path('admin/', admin.site.urls),
    path('api/', include('apps.api_gateway.urls')),
    path('api/finance/', include('apps.finance.urls')),
    path('api/procurement/', include('apps.procurement.urls')),
    path('api/sales/', include('apps.sales.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    # API schema & docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
]
