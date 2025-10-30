from __future__ import annotations

import copy

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.models import Company, CompanyGroup
from .models import MetadataDefinition
from .serializers import (
    MetadataDefinitionSerializer,
    MetadataFieldSerializer,
    MetadataResolveSerializer,
)
from .services import MetadataScope, create_metadata_version, resolve_metadata


class MetadataDefinitionViewSet(viewsets.ModelViewSet):
    queryset = MetadataDefinition.objects.all()
    serializer_class = MetadataDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        kind = self.request.query_params.get('kind')
        status_filter = self.request.query_params.get('status')
        if kind:
            qs = qs.filter(kind=kind)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by('-updated_at')

    @action(detail=True, methods=['post'], url_path='fields')
    def add_field(self, request, pk=None):
        metadata = self.get_object()
        serializer = MetadataFieldSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        field_payload = serializer.validated_data
        publish_now = bool(request.data.get('publish', False))

        definition = copy.deepcopy(metadata.definition) or {}
        definition.setdefault('fields', [])
        fields = definition['fields']

        # Replace field if it already exists by name
        fields = [f for f in fields if f.get('name') != field_payload['name']]
        fields.append(field_payload)
        definition['fields'] = fields

        scope = _scope_from_definition(metadata)
        new_version = create_metadata_version(
            key=metadata.key,
            kind=metadata.kind,
            layer=metadata.layer,
            scope=scope,
            definition=definition,
            summary={"field_count": len(fields)},
            status='active' if publish_now else 'draft',
            user=request.user,
        )
        if publish_now:
            new_version.activate(user=request.user)
        response_serializer = MetadataDefinitionSerializer(new_version)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class MetadataResolveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = MetadataResolveSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        company = None
        company_group = None
        if payload.get('company_id') is not None:
            company = get_object_or_404(Company, id=payload['company_id'])
        if payload.get('company_group_id') is not None:
            company_group = get_object_or_404(CompanyGroup, id=payload['company_group_id'])

        merged = resolve_metadata(
            key=payload['key'],
            kind=payload['kind'],
            company=company,
            company_group=company_group,
        )
        return Response(merged)


def _scope_from_definition(metadata: MetadataDefinition) -> MetadataScope:
    if metadata.scope_type == 'COMPANY':
        return MetadataScope.for_company(metadata.company)
    if metadata.scope_type == 'GROUP':
        return MetadataScope.for_group(metadata.company_group)
    return MetadataScope.global_scope()
