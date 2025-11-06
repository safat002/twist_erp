from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from .serializers import UserSerializer, UserProfileSerializer, UserCreateSerializer
from django.apps import apps
from django.db import transaction

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
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserRolesAssignmentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id: int):
        Role = apps.get_model('permissions', 'Role')
        UserCompanyRole = apps.get_model('users', 'UserCompanyRole')
        company_id = request.query_params.get('company')
        if not company_id:
            return Response({"detail": "company is required"}, status=400)
        roles_qs = Role.objects.filter(company_id=company_id) | Role.objects.filter(company__isnull=True)
        roles_qs = roles_qs.order_by('company_id', 'name').distinct()
        assigned_ids = list(
            UserCompanyRole.objects.filter(user_id=user_id, company_id=company_id, is_active=True).values_list('role_id', flat=True)
        )
        data = {
            'available': [
                {'id': r.id, 'name': r.name, 'company': r.company_id, 'is_system_role': r.is_system_role}
                for r in roles_qs
            ],
            'assigned': assigned_ids,
        }
        return Response(data)

    @transaction.atomic
    def post(self, request, user_id: int):
        Role = apps.get_model('permissions', 'Role')
        UserCompanyRole = apps.get_model('users', 'UserCompanyRole')
        Company = apps.get_model('companies', 'Company')
        company_id = request.data.get('company')
        role_ids = request.data.get('roles') or []
        if not company_id:
            return Response({"detail": "company is required"}, status=400)
        company = Company.objects.filter(id=company_id).first()
        if not company:
            return Response({"detail": "Invalid company"}, status=400)
        # Deactivate all
        existing_qs = UserCompanyRole.objects.filter(user_id=user_id, company_id=company_id)
        existing_qs.update(is_active=False)
        # Activate/create selected
        valid_roles = Role.objects.filter(id__in=role_ids).all()
        for r in valid_roles:
            ucr, _ = UserCompanyRole.objects.get_or_create(
                user_id=user_id,
                company_group=company.company_group,
                company=company,
                role=r,
                defaults={'is_active': True},
            )
            if not ucr.is_active:
                ucr.is_active = True
                ucr.save(update_fields=['is_active'])
        return Response({'status': 'ok', 'assigned': [r.id for r in valid_roles]})

