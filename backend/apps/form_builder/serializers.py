from __future__ import annotations

from django.utils.text import slugify
from rest_framework import serializers

from apps.audit.utils import log_audit_event
from apps.metadata.services import MetadataScope, create_metadata_version
from apps.metadata.models import MetadataDefinition
from .models import DynamicEntity, FormSubmission, FormTemplate
from .services.dynamic_entities import generate_dynamic_entity


class DynamicEntitySerializer(serializers.ModelSerializer):
    metadata = serializers.SerializerMethodField()
    scope_type = serializers.CharField(read_only=True)

    class Meta:
        model = DynamicEntity
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "api_path",
            "model_name",
            "table_name",
            "scope_type",
            "fields",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_metadata(self, obj: DynamicEntity):
        if not obj.metadata:
            return None
        return {
            "id": str(obj.metadata.id),
            "key": obj.metadata.key,
            "version": obj.metadata.version,
            "status": obj.metadata.status,
        }


class FormTemplateSerializer(serializers.ModelSerializer):
    generate_scaffold = serializers.BooleanField(write_only=True, required=False, default=False)
    publish = serializers.BooleanField(write_only=True, required=False, default=True)
    metadata = serializers.SerializerMethodField()
    scope_options = serializers.SerializerMethodField()
    entity = DynamicEntitySerializer(read_only=True)

    class Meta:
        model = FormTemplate
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "schema",
            "layer",
            "scope_type",
            "status",
            "version",
            "metadata",
            "is_active",
            "created_at",
            "updated_at",
            "generate_scaffold",
            "publish",
            "entity",
            "scope_options",
        ]
        read_only_fields = ["created_at", "updated_at", "entity", "metadata", "version", "status", "slug", "scope_options"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        user = getattr(request, "user", None)
        generate = validated_data.pop("generate_scaffold", False)
        publish = validated_data.pop("publish", True)
        scope_type = validated_data.get("scope_type") or "COMPANY"
        layer = validated_data.get("layer") or "COMPANY_OVERRIDE"

        if scope_type == "COMPANY":
            if not company:
                raise serializers.ValidationError({"detail": "Active company context required for company scoped forms."})
            scope = MetadataScope.for_company(company)
        elif scope_type == "GROUP":
            if company:
                scope = MetadataScope.for_group(company.company_group)
            else:
                company_group = getattr(request, "company_group", None)
                if not company_group:
                    raise serializers.ValidationError({"detail": "Company group context required for group scoped forms."})
                scope = MetadataScope.for_group(company_group)
        else:
            scope = MetadataScope.global_scope()

        slug = validated_data.get("slug") or slugify(validated_data.get("name") or "")
        if not slug:
            raise serializers.ValidationError({"detail": "Name is required to derive form identifier."})

        definition = {
            "name": validated_data.get("name"),
            "slug": slug,
            "description": validated_data.get("description", ""),
            "schema": validated_data.get("schema", []),
            "layer": layer,
            "scope_type": scope_type,
        }
        summary = {
            "field_count": len(definition["schema"]),
            "status": "active" if publish else "draft",
            "layer": layer,
            "scope_type": scope_type,
        }

        metadata = create_metadata_version(
            key=f"form:{slug}",
            kind="FORM",
            layer=layer,
            scope=scope,
            definition=definition,
            summary=summary,
            status="active" if publish else "draft",
            user=user,
        )
        if publish:
            metadata.activate(user=user)

        template = FormTemplate.objects.create(
            name=validated_data.get("name"),
            slug=slug,
            description=validated_data.get("description", ""),
            schema=validated_data.get("schema", []),
            layer=layer,
            scope_type=scope_type,
            version=metadata.version,
            status=metadata.status,
            metadata=metadata,
            company=company if scope_type == "COMPANY" else None,
            company_group=scope.company_group if scope_type != "GLOBAL" else None,
            created_by=user,
            is_active=metadata.status == "active",
        )

        if publish:
            scope_filter = {
                "slug": slug,
                "scope_type": scope_type,
            }
            if scope_type == "COMPANY":
                scope_filter["company"] = company
            elif scope_type == "GROUP":
                scope_filter["company_group"] = scope.company_group
            FormTemplate.objects.filter(**scope_filter).exclude(pk=template.pk).update(
                is_active=False,
                status="archived",
            )

        log_audit_event(
            user=user,
            company=company if scope_type == "COMPANY" else None,
            company_group=scope.company_group,
            action="FORM_LAYOUT_CHANGED",
            entity_type="FormTemplate",
            entity_id=template.slug,
            description=f"Form '{template.name}' saved (v{template.version}, status={template.status}).",
            after={
                "field_count": len(template.schema),
                "fields": template.schema,
                "metadata_id": str(metadata.id),
            },
        )
        if template.schema:
            log_audit_event(
                user=user,
                company=company if scope_type == "COMPANY" else None,
                company_group=scope.company_group,
                action="FORM_FIELD_ADDED",
                entity_type="FormTemplate",
                entity_id=template.slug,
                description=f"Added {len(template.schema)} fields to form '{template.name}'.",
                after={"fields": template.schema},
            )

        if generate:
            try:
                runtime = generate_dynamic_entity(template, user=user, scope=scope)
                log_audit_event(
                    user=user,
                    company=company if scope_type == "COMPANY" else None,
                    company_group=scope.company_group,
                    action="CUSTOM_MODULE_CREATED",
                    entity_type="DynamicEntity",
                    entity_id=runtime.entity.slug,
                    description=f"Dynamic module '{runtime.entity.name}' scaffolded for form '{template.name}'.",
                    after={
                        "fields": runtime.entity.fields,
                        "table": runtime.entity.table_name,
                        "model": runtime.entity.model_name,
                        "api_path": runtime.entity.api_path,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                raise serializers.ValidationError({"detail": f"Failed to generate dynamic entity: {exc}"}) from exc
        return template

    def get_metadata(self, obj: FormTemplate):
        if not obj.metadata:
            return None
        return {
            "id": str(obj.metadata.id),
            "version": obj.metadata.version,
            "status": obj.metadata.status,
            "key": obj.metadata.key,
            "label": obj.metadata.label,
            "layer": obj.metadata.layer,
            "scope_type": obj.metadata.scope_type,
        }

    def get_scope_options(self, obj: FormTemplate):
        return [scope for scope, _ in FormTemplate.SCOPE_CHOICES]


class FormSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormSubmission
        fields = ["id", "template", "data", "created_at"]
        read_only_fields = ["created_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        company = getattr(request, "company", None)
        user = getattr(request, "user", None)
        return FormSubmission.objects.create(company=company, submitted_by=user, **validated_data)
