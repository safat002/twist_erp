from __future__ import annotations

import json

from django.utils import timezone
from rest_framework import serializers

from core.id_factory import IDFactory
from .models import PolicyDocument, PolicyAcknowledgement, PolicyCategory, PolicyAttachment, PolicyChangeLog


class PolicyAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyAttachment
        fields = ["id", "name", "mime_type", "size", "file", "uploaded_by", "uploaded_at"]
        read_only_fields = ["uploaded_by", "uploaded_at"]


class PolicyChangeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyChangeLog
        fields = ["id", "version", "change_type", "notes", "changed_by", "changed_at"]
        read_only_fields = ["changed_by", "changed_at"]


class PolicyDocumentSerializer(serializers.ModelSerializer):
    acknowledged = serializers.SerializerMethodField()
    attachments = PolicyAttachmentSerializer(many=True, read_only=True)
    change_logs = PolicyChangeLogSerializer(many=True, read_only=True)

    class Meta:
        model = PolicyDocument
        fields = [
            "id",
            "company",
            "code",
            "title",
            "category",
            "category_ref",
            "status",
            "version",
            "effective_date",
            "expiry_date",
            "description",
            "content",
            "file",
            "tags",
            "requires_acknowledgement",
            "published_at",
            "previous_version",
            "compliance_links",
            "owner",
            "owner_department",
            "audience_roles",
            "audience_departments",
            "reading_time_minutes",
            "review_cycle_months",
            "last_reviewed_at",
            "created_by",
            "created_at",
            "updated_at",
            "acknowledged",
            "attachments",
            "change_logs",
        ]
        read_only_fields = ["company", "created_by", "created_at", "updated_at", "version", "published_at"]

    def get_acknowledged(self, obj: PolicyDocument):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return PolicyAcknowledgement.objects.filter(policy=obj, user=user, version=obj.version).exists()

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        user = getattr(request, "user", None)
        validated_data["company"] = company
        if user and "created_by" not in validated_data:
            validated_data["created_by"] = user
        # If a category_ref is provided, mirror its code to simple category field
        category_ref = validated_data.get("category_ref")
        if category_ref and not validated_data.get("category"):
            validated_data["category"] = category_ref.code
        if not validated_data.get("code"):
            validated_data["code"] = IDFactory.make_master_code("POL", company, PolicyDocument, width=5)
        # New policies start at version 1 unless cloning/publishing sets otherwise
        if not validated_data.get("version"):
            validated_data["version"] = 1
        return super().create(validated_data)

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        raw_links = data.get("compliance_links")
        if isinstance(raw_links, str):
            try:
                ret["compliance_links"] = json.loads(raw_links)
            except Exception:  # noqa: BLE001
                pass
        return ret


class PolicyAcknowledgementSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyAcknowledgement
        fields = ["id", "company", "policy", "user", "version", "acknowledged_at", "note"]
        read_only_fields = ["company", "user", "version", "acknowledged_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        user = getattr(request, "user", None)
        policy: PolicyDocument = validated_data["policy"]
        validated_data["company"] = company
        validated_data["user"] = user
        validated_data["version"] = policy.version
        return super().create(validated_data)


class PolicyCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyCategory
        fields = ["id", "code", "name", "is_active"]
