from django.urls import path

from .views import DashboardDataView, DashboardLayoutView, DashboardDefinitionListCreateView


urlpatterns = [
    path('', DashboardDataView.as_view(), name='dashboard-data'),
    path('layout/', DashboardLayoutView.as_view(), name='dashboard-layout'),
    path('definitions/', DashboardDefinitionListCreateView.as_view(), name='dashboard-definitions'),
]
