from django.urls import path
from .views import UserListView, UserCreateView, ChangePasswordView, UserProfileView, UserLookupView, CurrentUserProfileView, UserRolesAssignmentView

urlpatterns = [
    # path('me/', UserProfileView.as_view(), name='user-profile'), # This line is commented out or removed based on the original context
    path('register/', UserCreateView.as_view(), name='user-register'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('list/', UserListView.as_view(), name='user-list'),
]
urlpatterns += [
    path("lookup/", UserLookupView.as_view(), name="user-lookup"),
    path("me/", CurrentUserProfileView.as_view(), name="user-profile"),
    path("<int:user_id>/roles/", UserRolesAssignmentView.as_view(), name="user-roles-assign"),
]
