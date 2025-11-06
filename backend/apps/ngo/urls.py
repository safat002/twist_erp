from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DonorViewSet, ProgramViewSet, ComplianceRequirementViewSet, ComplianceSubmissionViewSet

router = DefaultRouter()
router.register(r"donors", DonorViewSet, basename="ngo-donor")
router.register(r"programs", ProgramViewSet, basename="ngo-program")
router.register(r"requirements", ComplianceRequirementViewSet, basename="ngo-requirement")
router.register(r"submissions", ComplianceSubmissionViewSet, basename="ngo-submission")

urlpatterns = [
    path("", include(router.urls)),
]

