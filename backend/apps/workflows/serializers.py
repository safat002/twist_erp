from django.utils.text import slugify
from rest_framework import serializers

from apps.audit.utils import log_audit_event
from apps.metadata.services import MetadataScope, create_metadata_version
from .models import WorkflowTemplate, WorkflowInstance


class WorkflowTemplateSerializer(serializers.ModelSerializer):
    publish = serializers.BooleanField(write_only=True, required=False, default=True)
    metadata = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = WorkflowTemplate
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "definition",
            "layer",
            "scope_type",
            "status",
            "version",
            "metadata",
            "publish",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "metadata", "status", "version", "slug"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        user = getattr(request, "user", None)

        publish = validated_data.pop("publish", True)
        scope_type = validated_data.get("scope_type") or "COMPANY"
        layer = validated_data.get("layer") or "COMPANY_OVERRIDE"

        if scope_type == "COMPANY":
            if not company:
                raise serializers.ValidationError({"detail": "Active company context required for workflow builder."})
            scope = MetadataScope.for_company(company)
        elif scope_type == "GROUP":
            company_group = getattr(company, "company_group", None) or getattr(request, "company_group", None)
            if not company_group:
                raise serializers.ValidationError({"detail": "Company group context required for group workflows."})
            scope = MetadataScope.for_group(company_group)
        else:
            scope = MetadataScope.global_scope()

        slug = validated_data.get("slug") or slugify(validated_data.get("name") or "")
        if not slug:
            raise serializers.ValidationError({"detail": "Workflow name required."})

        definition = validated_data.get("definition") or {}
        summary = {
            "state_count": len(definition.get("states", [])),
            "transition_count": sum(len(v) for v in definition.get("transitions", {}).values())
            if isinstance(definition.get("transitions"), dict)
            else 0,
        }
        metadata = create_metadata_version(
            key=f"workflow:{slug}",
            kind="WORKFLOW",
            layer=layer,
            scope=scope,
            definition={
                "name": validated_data.get("name"),
                "slug": slug,
                "description": validated_data.get("description", ""),
                "definition": definition,
                "scope_type": scope_type,
                "layer": layer,
            },
            summary=summary,
            status="active" if publish else "draft",
            user=user,
        )
        if publish:
            metadata.activate(user=user)

        template = WorkflowTemplate.objects.create(
            name=validated_data.get("name"),
            slug=slug,
            description=validated_data.get("description", ""),
            definition=definition,
            layer=layer,
            scope_type=scope_type,
            status=metadata.status,
            version=metadata.version,
            metadata=metadata,
            company=company if scope_type == "COMPANY" else None,
            company_group=scope.company_group if scope_type != "GLOBAL" else None,
        )

        if publish:
            scope_filter = {"slug": slug, "scope_type": scope_type}
            if scope_type == "COMPANY":
                scope_filter["company"] = company
            elif scope_type == "GROUP":
                scope_filter["company_group"] = scope.company_group
            WorkflowTemplate.objects.filter(**scope_filter).exclude(pk=template.pk).update(status="archived")

        log_audit_event(
            user=user,
            company=company if scope_type == "COMPANY" else None,
            company_group=scope.company_group,
            action="WORKFLOW_CHANGED",
            entity_type="WorkflowTemplate",
            entity_id=template.slug,
            description=f"Workflow '{template.name}' saved (v{template.version}, status={template.status}).",
            after={
                "states": definition.get("states", []),
                "transitions": definition.get("transitions", {}),
                "metadata_id": str(metadata.id),
            },
        )
        return template

    def get_metadata(self, obj: WorkflowTemplate):
        if not obj.metadata:
            return None
        return {
            "id": str(obj.metadata.id),
            "key": obj.metadata.key,
            "version": obj.metadata.version,
            "status": obj.metadata.status,
        }


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowInstance
        fields = ["id", "template", "state", "context", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        return WorkflowInstance.objects.create(company=company, **validated_data)
