from rest_framework.routers import DefaultRouter
from django.urls import include, path

from .views import MetadataDefinitionViewSet, MetadataResolveView

router = DefaultRouter()
router.register(r'definitions', MetadataDefinitionViewSet, basename='metadata-definition')

urlpatterns = [
    path('resolve/', MetadataResolveView.as_view(), name='metadata-resolve'),
]

urlpatterns += router.urls
