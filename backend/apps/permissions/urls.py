from django.urls import path
from .views import RoleListView

urlpatterns = [
    path('roles/', RoleListView.as_view()),
]

