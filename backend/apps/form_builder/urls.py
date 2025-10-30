from django.urls import path

from .views import (
    DynamicEntityListView,
    DynamicEntityRecordDetailView,
    DynamicEntityRecordsView,
    DynamicEntitySchemaView,
    FormSubmissionCreateView,
    FormTemplateListCreateView,
)

urlpatterns = [
    path('', FormTemplateListCreateView.as_view()),
    path('templates/', FormTemplateListCreateView.as_view()),
    path('templates/<int:pk>/submit/', FormSubmissionCreateView.as_view()),
    path('entities/', DynamicEntityListView.as_view()),
    path('entities/<slug:slug>/', DynamicEntitySchemaView.as_view()),
    path('entities/<slug:slug>/records/', DynamicEntityRecordsView.as_view()),
    path('entities/<slug:slug>/records/<int:pk>/', DynamicEntityRecordDetailView.as_view()),
]
