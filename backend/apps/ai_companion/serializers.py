from __future__ import annotations

import json

from django.db import models
from rest_framework import serializers

from apps.companies.models import Company

from .models import UserAIPreference


class AIPreferenceSerializer(serializers.ModelSerializer):
    scope = serializers.SerializerMethodField()
    company_id = serializers.IntegerField(source="company.id", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    company = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = UserAIPreference
        fields = [
            "id",
            "key",
            "value",
            "scope",
            "source",
            "company",
            "company_id",
            "company_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "scope", "source", "company_id", "company_name", "created_at", "updated_at")

    def get_scope(self, obj: UserAIPreference) -> str:
        return obj.scope

    def validate_value(self, value):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return value
            return parsed
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if isinstance(data.get("value"), (dict, list)):
            return data
        # Ensure scalar values appear as-is without forcing to string "None"
        if data.get("value") is None:
            data["value"] = None
        return data
