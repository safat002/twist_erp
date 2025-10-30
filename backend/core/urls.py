from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from shared.views import HealthCheckView
from .views import favicon, home

urlpatterns = [
    path('', home, name='home'),
    re_path(r'^favicon\.ico$', favicon, name='favicon'),
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
