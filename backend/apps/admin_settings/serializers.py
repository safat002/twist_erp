from rest_framework import serializers
from .models import ModuleFeatureToggle, FeatureAuditLog


class ModuleFeatureToggleSerializer(serializers.ModelSerializer):
    """Serializer for feature toggles."""

    full_key = serializers.ReadOnlyField()
    is_module_toggle = serializers.ReadOnlyField()

    class Meta:
        model = ModuleFeatureToggle
        fields = [
            'id',
            'module_name',
            'feature_key',
            'full_key',
            'feature_name',
            'description',
            'help_text',
            'icon',
            'status',
            'is_enabled',
            'is_visible',
            'is_module_toggle',
            'scope_type',
            'config',
            'depends_on',
            'priority',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class FeatureMapSerializer(serializers.Serializer):
    """Serializer for feature map (frontend consumption)."""

    features = serializers.DictField(
        child=serializers.DictField(),
        help_text="Map of feature keys to feature data"
    )
    modules = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of enabled module names"
    )
    scope = serializers.CharField(help_text="Scope type applied")
    cached = serializers.BooleanField(help_text="Whether data came from cache")


class FeatureAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit logs."""

    feature_name = serializers.CharField(source='feature_toggle.feature_name', read_only=True)
    feature_key = serializers.CharField(source='feature_toggle.full_key', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = FeatureAuditLog
        fields = [
            'id',
            'feature_name',
            'feature_key',
            'action',
            'old_value',
            'new_value',
            'username',
            'ip_address',
            'timestamp',
        ]


class FeatureToggleUpdateSerializer(serializers.Serializer):
    """Serializer for updating feature toggles from dashboard."""

    is_enabled = serializers.BooleanField(required=True)

    class Meta:
        fields = ['is_enabled']
