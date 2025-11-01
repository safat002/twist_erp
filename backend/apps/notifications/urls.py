from django.urls import path

from .views import (
    NotificationListView,
    NotificationCenterView,
    NotificationMarkView,
    NotificationClearAllView,
    EmailAwarenessView,
)


urlpatterns = [
    path("", NotificationListView.as_view()),  # latest
    path("center/", NotificationCenterView.as_view()),
    path("<int:pk>/mark/", NotificationMarkView.as_view()),
    path("clear-all/", NotificationClearAllView.as_view()),
    path("email-awareness/", EmailAwarenessView.as_view()),
]
