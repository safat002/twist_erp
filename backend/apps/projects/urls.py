from django.urls import path
from .views import ProjectListCreateView, ProjectGanttView

urlpatterns = [
    path('', ProjectListCreateView.as_view()),
    path('<int:pk>/gantt/', ProjectGanttView.as_view()),
]
