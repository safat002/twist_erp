from rest_framework import serializers

from .models import Company, CompanyGroup


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"


class CompanyGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyGroup
        fields = "__all__"


class CompanyProvisionSerializer(serializers.Serializer):
    group_name = serializers.CharField(max_length=255)
    industry_pack_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    supports_intercompany = serializers.BooleanField(default=False)
    company = serializers.DictField(required=False)

    def validate_group_name(self, value):
        if CompanyGroup.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("A company group with this name already exists.")
        return value
