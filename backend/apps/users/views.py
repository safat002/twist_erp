from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from .serializers import UserSerializer, UserProfileSerializer, UserCreateSerializer

User = get_user_model()

class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAdminUser]

class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not user.check_password(old_password):
            return Response({'old_password': ['Wrong password.']}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({'status': 'password set'})


class UserLookupView(generics.ListAPIView):
    serializer_class = UserProfileSerializer
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

