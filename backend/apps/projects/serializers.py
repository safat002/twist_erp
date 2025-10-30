from rest_framework import serializers
from .models import Project, Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "name", "start_date", "end_date", "depends_on"]


class ProjectSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ["id", "name", "start_date", "end_date", "tasks", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at", "tasks"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        return Project.objects.create(company=company, **validated_data)
