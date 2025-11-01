from django.urls import path, include
from .views import api_root

urlpatterns = [
    path('', api_root, name='api-root'),
    path('v1/auth/', include('apps.authentication.urls')),
    path('v1/companies/', include('apps.companies.urls')),
    path('v1/', include('core.api_urls')),
    path('v1/users/', include('apps.users.urls')),
    path('v1/analytics/', include('apps.analytics.urls')),
    path('v1/dashboard/', include('apps.dashboard.urls')),
    path('v1/metadata/', include('apps.metadata.urls')),
    path('v1/tasks/', include('apps.tasks.urls')),
    path('v1/notifications/', include('apps.notifications.urls')),
    # Phase 4-6 modules
    path('v1/forms/', include('apps.form_builder.urls')),
    path('v1/workflows/', include('apps.workflows.urls')),
    path('v1/ai/', include('apps.ai_companion.urls')),
    path('v1/assets/', include('apps.assets.urls')),
    path('v1/budgets/', include('apps.budgeting.urls')),
    path('v1/data-migration/', include('apps.data_migration.urls')),
    path('v1/hr/', include('apps.hr.urls')),
    path('v1/projects/', include('apps.projects.urls')),
    path('v1/report-builder/', include('apps.report_builder.urls')),
    path('v1/procurement/', include('apps.procurement.urls')),
    path('v1/inventory/', include('apps.inventory.urls')),
    path('v1/production/', include('apps.production.urls')),
    path('v1/sales/', include('apps.sales.urls')),
    path('v1/finance/', include('apps.finance.urls')),
]
