from rest_framework import serializers
from django.utils.text import slugify

from apps.ai_companion.services.telemetry import TelemetryService
from apps.audit.utils import log_audit_event
from apps.metadata.services import MetadataScope, create_metadata_version
from .models import DashboardDefinition, DashboardLayout, DashboardWidgetDefinition


class DashboardLayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardLayout
        fields = ['layout', 'widgets', 'updated_at']


class DashboardPayloadSerializer(serializers.Serializer):
    period = serializers.CharField()
    layout = serializers.DictField()
    widgets = serializers.ListField()
    available_widgets = serializers.ListField()


class DashboardWidgetDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardWidgetDefinition
        fields = ['id', 'key', 'widget_type', 'title', 'config', 'position']
        read_only_fields = ['id']


class DashboardDefinitionSerializer(serializers.ModelSerializer):
    widgets = DashboardWidgetDefinitionSerializer(many=True)
    publish = serializers.BooleanField(write_only=True, required=False, default=True)
    metadata = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DashboardDefinition
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'layout',
            'filters',
            'scope_type',
            'layer',
            'status',
            'version',
            'widgets',
            'metadata',
            'publish',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['slug', 'status', 'version', 'metadata', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        company = getattr(request, 'company', None)
        publish = validated_data.pop('publish', True)
        widgets_payload = validated_data.pop('widgets', [])
        scope_type = validated_data.get('scope_type') or 'COMPANY'
        layer = validated_data.get('layer') or 'COMPANY_OVERRIDE'

        if scope_type == 'COMPANY':
            if not company:
                raise serializers.ValidationError({'detail': 'Active company context required for dashboard builder.'})
            scope = MetadataScope.for_company(company)
        elif scope_type == 'GROUP':
            company_group = getattr(company, 'company_group', None) or getattr(request, 'company_group', None)
            if not company_group:
                raise serializers.ValidationError({'detail': 'Company group context required for group dashboards.'})
            scope = MetadataScope.for_group(company_group)
        else:
            scope = MetadataScope.global_scope()

        slug = validated_data.get('slug') or slugify(validated_data.get('name') or '')
        if not slug:
            raise serializers.ValidationError({'detail': 'Dashboard name required.'})

        dashboard_definition = {
            'name': validated_data.get('name'),
            'slug': slug,
            'description': validated_data.get('description', ''),
            'layout': validated_data.get('layout', {}),
            'filters': validated_data.get('filters', {}),
            'widgets': widgets_payload,
            'scope_type': scope_type,
            'layer': layer,
        }
        summary = {
            'widget_count': len(widgets_payload),
            'layout_breakpoints': list((validated_data.get('layout') or {}).keys()),
        }

        metadata = create_metadata_version(
            key=f"dashboard:{slug}",
            kind="DASHBOARD",
            layer=layer,
            scope=scope,
            definition=dashboard_definition,
            summary=summary,
            status="active" if publish else "draft",
            user=user,
        )
        if publish:
            metadata.activate(user=user)

        dashboard = DashboardDefinition.objects.create(
            name=validated_data.get('name'),
            slug=slug,
            description=validated_data.get('description', ''),
            layout=validated_data.get('layout', {}),
            filters=validated_data.get('filters', {}),
            scope_type=scope_type,
            layer=layer,
            status=metadata.status,
            version=metadata.version,
            metadata=metadata,
            company=company if scope_type == 'COMPANY' else None,
            company_group=scope.company_group if scope_type != 'GLOBAL' else None,
            created_by=user,
            updated_by=user,
        )

        if publish:
            scope_filter = {'slug': slug, 'scope_type': scope_type}
            if scope_type == 'COMPANY':
                scope_filter['company'] = company
            elif scope_type == 'GROUP':
                scope_filter['company_group'] = scope.company_group
            DashboardDefinition.objects.filter(**scope_filter).exclude(pk=dashboard.pk).update(status='archived')

        widget_entries = []
        for position, widget_payload in enumerate(widgets_payload):
            widget = DashboardWidgetDefinition.objects.create(
                dashboard=dashboard,
                key=widget_payload.get('key') or widget_payload.get('id') or f"widget-{position+1}",
                widget_type=widget_payload.get('widget_type') or widget_payload.get('type', 'kpi'),
                title=widget_payload.get('title', ''),
                config=widget_payload.get('config', widget_payload),
                position=position,
            )
            widget_entries.append(widget)
            widget_metadata = create_metadata_version(
                key=f"dashboard:{slug}:widget:{widget.key}",
                kind="WIDGET",
                layer=layer,
                scope=scope,
                definition={
                    'dashboard': slug,
                    'key': widget.key,
                    'widget_type': widget.widget_type,
                    'title': widget.title,
                    'config': widget.config,
                    'position': widget.position,
                },
                summary={'widget_type': widget.widget_type},
                status="active" if publish else "draft",
                user=user,
            )
            if publish:
                widget_metadata.activate(user=user)

        log_audit_event(
            user=user,
            company=company if scope_type == 'COMPANY' else None,
            company_group=scope.company_group,
            action="DASHBOARD_CHANGED",
            entity_type="DashboardDefinition",
            entity_id=dashboard.slug,
            description=f"Dashboard '{dashboard.name}' saved (v{dashboard.version}, status={dashboard.status}).",
            after={
                'widget_keys': [w.key for w in widget_entries],
                'metadata_id': str(metadata.id),
            },
        )
        TelemetryService().record_event(
            event_type="dashboard.definition.saved",
            user=user,
            company=company if scope_type == 'COMPANY' else None,
            payload={
                'slug': slug,
                'status': dashboard.status,
                'version': dashboard.version,
                'widget_count': len(widget_entries),
            },
        )
        return dashboard

    def get_metadata(self, obj: DashboardDefinition):
        if not obj.metadata:
            return None
        return {
            'id': str(obj.metadata.id),
            'key': obj.metadata.key,
            'version': obj.metadata.version,
            'status': obj.metadata.status,
        }
