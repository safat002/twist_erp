from __future__ import annotations

from rest_framework import serializers

from .models import TaskItem


class TaskItemSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.ReadOnlyField(source="assigned_to.get_full_name")
    assigned_by_name = serializers.ReadOnlyField(source="assigned_by.get_full_name")

    class Meta:
        model = TaskItem
        fields = [
            "id",
            "company",
            "company_group",
            "task_type",
            "title",
            "description",
            "assigned_to",
            "assigned_to_name",
            "assigned_by",
            "assigned_by_name",
            "due_date",
            "priority",
            "status",
            "linked_entity_type",
            "linked_entity_id",
            "visibility_scope",
            "calendar_event_id",
            "calendar_sync_status",
            "recurrence",
            "recurrence_until",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company_group", "created_at", "updated_at", "assigned_by"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        if not company and request and request.user.is_authenticated:
            company = request.user.companies.filter(is_active=True).first()
        if not company:
            raise serializers.ValidationError({"company": "Active company context is required."})
        validated_data["company"] = company
        validated_data["company_group"] = company.company_group
        validated_data["assigned_by"] = request.user
        return super().create(validated_data)


class TaskStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskItem
        fields = ["status"]
