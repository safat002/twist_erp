from django.urls import path

from .views import (
    TaskListCreateView,
    MyTasksView,
    TeamTasksView,
    TaskStatusUpdateView,
    TaskSnoozeView,
    TaskEscalateView,
    TaskCalendarSyncView,
    CalendarFeedICSView,
    CalendarMeView,
    CalendarEventsView,
    OutlookAuthURLView,
    OutlookAuthCallbackView,
)


urlpatterns = [
    path("", TaskListCreateView.as_view()),
    path("my/", MyTasksView.as_view()),
    path("team/", TeamTasksView.as_view()),
    path("<int:pk>/status/", TaskStatusUpdateView.as_view()),
    path("<int:pk>/snooze/", TaskSnoozeView.as_view()),
    path("<int:pk>/escalate/", TaskEscalateView.as_view()),
    path("<int:pk>/sync-calendar/", TaskCalendarSyncView.as_view()),
    path("calendar/events/", CalendarEventsView.as_view()),
    path("calendar/me/", CalendarMeView.as_view()),
    path("calendar.ics", CalendarFeedICSView.as_view()),
    path("calendar/outlook/auth-url", OutlookAuthURLView.as_view()),
    path("calendar/outlook/callback", OutlookAuthCallbackView.as_view()),
]
