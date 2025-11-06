from django.urls import path, include
from . import views

urlpatterns = [
    path('auth/', include('apps.authentication.urls')),
    path('users/', include('apps.users.urls')),
    path('companies/', include('apps.companies.urls')),
    path('hr/', include('apps.hr.urls')),
    path('health/', views.health),
]
