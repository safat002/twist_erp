from __future__ import annotations

from rest_framework import serializers

from .models import Notification, EmailAwarenessState


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "user",
            "title",
            "body",
            "severity",
            "status",
            "group_key",
            "entity_type",
            "entity_id",
            "created_at",
        ]
        read_only_fields = ["created_at", "user"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        if not company and request and request.user.is_authenticated:
            company = request.user.companies.filter(is_active=True).first()
        if not company:
            raise serializers.ValidationError({"company": "Active company context is required."})
        validated_data["company"] = company
        validated_data["company_group"] = company.company_group
        if not validated_data.get("user"):
            validated_data["user"] = request.user
        return super().create(validated_data)


class NotificationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["status"]


class EmailAwarenessSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailAwarenessState
        fields = ["id", "user", "unread_count", "created_at", "updated_at", "company", "company_group"]
        read_only_fields = ["company", "company_group", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        if not company and request and request.user.is_authenticated:
            company = request.user.companies.filter(is_active=True).first()
        if not company:
            raise serializers.ValidationError({"company": "Active company context is required."})
        validated_data["company"] = company
        validated_data["company_group"] = company.company_group
        if not validated_data.get("user"):
            validated_data["user"] = request.user
        # Upsert behavior
        instance, _ = EmailAwarenessState.objects.update_or_create(
            company=validated_data["company"],
            user=validated_data["user"],
            defaults={"company_group": validated_data["company_group"], "unread_count": validated_data["unread_count"]},
        )
        return instance
