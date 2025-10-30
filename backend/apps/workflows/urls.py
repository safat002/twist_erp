from django.urls import path
from .views import (
    WorkflowTemplateListCreateView,
    WorkflowInstanceCreateView,
    WorkflowTransitionView,
)

urlpatterns = [
    path('templates/', WorkflowTemplateListCreateView.as_view()),
    path('instances/', WorkflowInstanceCreateView.as_view()),
    path('instances/<int:pk>/transition/', WorkflowTransitionView.as_view()),
]
