from django.urls import path

from .views import CurrentUserProfileView, UserLookupView

urlpatterns = [
    path("lookup/", UserLookupView.as_view(), name="user-lookup"),
    path("me/", CurrentUserProfileView.as_view(), name="user-profile"),
]
