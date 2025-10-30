from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.companies.models import Company, CompanyGroup
from apps.users.models import UserCompanyRole


User = get_user_model()


class CompanySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "code", "name", "currency_code", "is_active"]


class CompanyGroupSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyGroup
        fields = ["id", "name", "industry_pack_type", "supports_intercompany"]


class UserCompanyRoleSerializer(serializers.ModelSerializer):
    company = CompanySummarySerializer(read_only=True)
    company_group = CompanyGroupSummarySerializer(read_only=True)
    role_id = serializers.IntegerField(source="role.id", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    role_description = serializers.CharField(source="role.description", read_only=True)

    class Meta:
        model = UserCompanyRole
        fields = [
            "id",
            "role_id",
            "role_name",
            "role_description",
            "company",
            "company_group",
            "is_active",
            "assigned_at",
        ]


class UserSummarySerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "display_name"]

    def get_display_name(self, obj):
        if obj.first_name or obj.last_name:
            return f"{obj.first_name} {obj.last_name}".strip()
        return obj.username


class UserProfileSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    default_company = CompanySummarySerializer(read_only=True)
    default_company_group = CompanyGroupSummarySerializer(read_only=True)
    default_company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        source="default_company",
        required=False,
        allow_null=True,
        write_only=True,
    )
    default_company_group_id = serializers.PrimaryKeyRelatedField(
        queryset=CompanyGroup.objects.all(),
        source="default_company_group",
        required=False,
        allow_null=True,
        write_only=True,
    )
    memberships = UserCompanyRoleSerializer(source="usercompanyrole_set", many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "display_name",
            "first_name",
            "last_name",
            "phone",
            "is_staff",
            "is_system_admin",
            "avatar_url",
            "default_company",
            "default_company_group",
            "default_company_id",
            "default_company_group_id",
            "memberships",
        ]
        read_only_fields = [
            "id",
            "username",
            "email",
            "display_name",
            "is_staff",
            "is_system_admin",
            "avatar_url",
            "default_company",
            "default_company_group",
            "memberships",
        ]
        extra_kwargs = {
            "first_name": {"required": False, "allow_blank": True},
            "last_name": {"required": False, "allow_blank": True},
            "phone": {"required": False, "allow_blank": True},
        }

    def get_display_name(self, obj):
        if obj.first_name or obj.last_name:
            return f"{obj.first_name} {obj.last_name}".strip()
        return obj.username

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get("request")
        avatar_url = obj.avatar.url
        if request is not None:
            return request.build_absolute_uri(avatar_url)
        return avatar_url

    def update(self, instance, validated_data):
        default_company = validated_data.pop("default_company", serializers.empty)
        default_company_group = validated_data.pop("default_company_group", serializers.empty)

        updated_fields = set()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            updated_fields.add(attr)

        if default_company is not serializers.empty:
            if default_company is not None and not UserCompanyRole.objects.filter(
                user=instance, company=default_company, is_active=True
            ).exists():
                raise serializers.ValidationError(
                    {"default_company_id": "You are not assigned to this company."}
                )
            instance.default_company = default_company

        if default_company_group is not serializers.empty:
            if default_company_group is not None and not instance.company_groups.filter(
                pk=default_company_group.pk
            ).exists():
                raise serializers.ValidationError(
                    {"default_company_group_id": "You are not assigned to this company group."}
                )
            instance.default_company_group = default_company_group
            updated_fields.add("default_company_group")

        if default_company is not serializers.empty:
            updated_fields.add("default_company")

        if updated_fields:
            instance.save(update_fields=list(updated_fields))
        else:
            instance.save()
        return instance
