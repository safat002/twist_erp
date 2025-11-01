from __future__ import annotations

from rest_framework import serializers

from apps.report_builder.models import ReportDefinition


class ReportDefinitionSerializer(serializers.ModelSerializer):
    metadata_id = serializers.IntegerField(source="metadata.id", read_only=True)

    class Meta:
        model = ReportDefinition
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "layer",
            "scope_type",
            "status",
            "version",
            "is_active",
            "company_group",
            "company",
            "definition",
            "summary",
            "required_permissions",
            "metadata_id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "last_published_at",
        ]
        read_only_fields = [
            "slug",
            "version",
            "metadata_id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "last_published_at",
        ]


class ReportPreviewRequestSerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False, min_value=1, max_value=5000)
