from django.contrib.auth import get_user_model
from rest_framework import filters, generics
from rest_framework.permissions import IsAuthenticated

from .serializers import UserProfileSerializer, UserSummarySerializer


User = get_user_model()


class UserLookupView(generics.ListAPIView):
    serializer_class = UserSummarySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["username", "first_name", "last_name", "email"]
    pagination_class = None

    def get_queryset(self):
        queryset = User.objects.filter(is_active=True).order_by("first_name", "last_name", "username")
        company = getattr(self.request, "company", None)
        if company:
            queryset = queryset.filter(companies=company).distinct()

        limit_param = self.request.query_params.get("limit")
        try:
            limit = int(limit_param) if limit_param else 25
        except (TypeError, ValueError):
            limit = 25

        return queryset[: max(limit, 1)]


class CurrentUserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

