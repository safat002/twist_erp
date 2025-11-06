from django.urls import path
from .views import (
    FeatureFlagsView,
    FeatureCheckView,
    FeatureToggleUpdateView,
    FeatureListView,
    FeatureAuditLogView,
    CacheInvalidationView,
)

app_name = 'admin_settings'

urlpatterns = [
    # Public endpoints (authenticated users)
    path('features/', FeatureFlagsView.as_view(), name='feature_flags'),
    path('features/check/', FeatureCheckView.as_view(), name='feature_check'),

    # Dashboard toggle endpoint
    path('features/<str:module_name>/<str:feature_key>/toggle/',
         FeatureToggleUpdateView.as_view(), name='feature_toggle'),

    # Admin-only endpoints
    path('features/list/', FeatureListView.as_view(), name='feature_list'),
    path('features/audit/', FeatureAuditLogView.as_view(), name='feature_audit'),
    path('features/invalidate-cache/', CacheInvalidationView.as_view(), name='invalidate_cache'),
]
