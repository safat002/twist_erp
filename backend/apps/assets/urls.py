from django.urls import path

from .views import (
    AssetDetailView,
    AssetListCreateView,
    AssetOverviewView,
    AssetRegisterView,
    MaintenancePlanDetailView,
    MaintenancePlanListCreateView,
    MaintenanceSummaryView,
)

urlpatterns = [
    path("", AssetListCreateView.as_view()),
    path("register/", AssetRegisterView.as_view()),
    path("overview/", AssetOverviewView.as_view()),
    path("maintenance/summary/", MaintenanceSummaryView.as_view()),
    path("maintenance/", MaintenancePlanListCreateView.as_view()),
    path("maintenance/<int:pk>/", MaintenancePlanDetailView.as_view()),
    path("<int:pk>/", AssetDetailView.as_view()),
]
