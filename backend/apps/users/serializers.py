from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.companies.serializers import CompanySerializer

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)
    effective_permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_staff',
            'is_active',
            'date_joined',
            'last_login',
            'company',
            'effective_permissions',
        )
        read_only_fields = ('username', 'date_joined', 'last_login', 'is_staff', 'is_active', 'company')

    def get_effective_permissions(self, obj):
        # effective_permissions is attached by PermissionContextMiddleware
        return getattr(obj, 'effective_permissions', {})

class UserProfileSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'phone',
            'avatar',
            'company',
        )
        read_only_fields = ('username', 'company')


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'first_name', 'last_name')

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user