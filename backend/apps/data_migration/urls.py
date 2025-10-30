from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.job_views import MigrationJobViewSet

router = DefaultRouter()
router.register(r"jobs", MigrationJobViewSet, basename="migration-job")

urlpatterns = [
    path("", include(router.urls)),
]
