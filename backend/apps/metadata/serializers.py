from __future__ import annotations

from rest_framework import serializers

from .models import MetadataDefinition


class MetadataDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetadataDefinition
        fields = '__all__'


class MetadataFieldSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    label = serializers.CharField(max_length=255)
    type = serializers.CharField(max_length=50)
    required = serializers.BooleanField(default=False)
    options = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    metadata = serializers.DictField(required=False, default=dict)


class MetadataResolveSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=255)
    kind = serializers.CharField(max_length=20)
    company_id = serializers.IntegerField(required=False)
    company_group_id = serializers.IntegerField(required=False)
