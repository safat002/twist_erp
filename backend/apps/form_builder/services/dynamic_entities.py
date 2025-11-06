from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple, Type, Optional

from django.apps import apps as django_apps
from django.core.exceptions import ImproperlyConfigured
from django.db import connections, models, router, transaction
from django.db.models import Q
from django.db.utils import OperationalError, ProgrammingError
from django.utils.text import slugify
from rest_framework import serializers

from shared.models import CompanyAwareModel
from ..models import DynamicEntity, FormTemplate

logger = logging.getLogger(__name__)


FIELD_TYPE_MAP = {
    'text': 'char',
    'textarea': 'text',
    'email': 'char',
    'phone': 'char',
    'select': 'char',
    'number': 'decimal',
    'date': 'date',
    'checkbox': 'boolean',
}


@dataclass
class RuntimeEntity:
    entity: DynamicEntity
    model: Type[models.Model]
    serializer_class: Type[serializers.ModelSerializer]
    field_names: List[str]


def generate_dynamic_entity(template: FormTemplate, user=None, scope: Optional[MetadataScope] = None) -> RuntimeEntity:
    from apps.metadata.services import MetadataScope, create_metadata_version
    if not template.schema:
        raise ValueError("Template schema is empty. Add fields before generating an entity.")

    raw_fields = template.schema if isinstance(template.schema, list) else template.schema.get('fields', [])
    if not isinstance(raw_fields, list) or not raw_fields:
        raise ValueError("Template schema must be a list of field definitions.")

    if scope is None:
        if template.scope_type == "COMPANY" and template.company:
            scope = MetadataScope.for_company(template.company)
        elif template.scope_type == "GROUP":
            company_group = template.company_group or getattr(template.company, "company_group", None)
            if not company_group:
                raise ValueError("Company group context required for group scoped dynamic entities.")
            scope = MetadataScope.for_group(company_group)
        else:
            scope = MetadataScope.global_scope()

    slug_base = template.slug or slugify(template.name) or f"entity-{template.id}"
    slug_value = _ensure_unique_slug(slug_base, scope)
    model_name = _build_model_name(slug_value)
    table_name = _build_table_name(scope, slug_value)
    field_definitions = _normalise_fields(raw_fields)
    api_path = f"/api/v1/forms/entities/{slug_value}/records/"

    entity_definition = {
        'name': template.name,
        'slug': slug_value,
        'description': template.description,
        'fields': field_definitions,
        'model_name': model_name,
        'table_name': table_name,
        'api_path': api_path,
        'scope_type': template.scope_type,
        'layer': template.layer,
    }

    with transaction.atomic():
        entity, created = DynamicEntity.objects.get_or_create(
            template=template,
            defaults={
                'company': template.company if template.scope_type == "COMPANY" else None,
                'company_group': scope.company_group if template.scope_type != "GLOBAL" else None,
                'scope_type': template.scope_type,
                'name': template.name,
                'description': template.description,
                'slug': slug_value,
                'fields': field_definitions,
                'model_name': model_name,
                'table_name': table_name,
                'api_path': api_path,
                'created_by': user,
                'metadata': None,
            },
        )
        if not created:
            entity.name = template.name
            entity.description = template.description
            entity.fields = field_definitions
            entity.is_active = True
            entity.api_path = api_path
            entity.scope_type = template.scope_type
            if template.scope_type == "COMPANY":
                entity.company = template.company
                entity.company_group = getattr(template.company, "company_group", None)
            else:
                entity.company = None
                entity.company_group = scope.company_group
            entity.save(
                update_fields=[
                    'name',
                    'description',
                    'fields',
                    'is_active',
                    'api_path',
                    'scope_type',
                    'company',
                    'company_group',
                    'updated_at',
                ]
            )

        entity_metadata = create_metadata_version(
            key=f"entity:{slug_value}",
            kind="ENTITY",
            layer=template.layer,
            scope=scope,
            definition=entity_definition,
            summary={'field_count': len(field_definitions), 'table': table_name},
            status="active",
            user=user,
        )
        entity_metadata.activate(user=user)
        if entity.metadata_id != entity_metadata.id:
            entity.metadata = entity_metadata
            entity.save(update_fields=['metadata', 'updated_at'])

    return ensure_runtime_entity(entity)


def ensure_runtime_entity(entity: DynamicEntity) -> RuntimeEntity:
    if not entity.is_active:
        raise ImproperlyConfigured(f"Dynamic entity {entity.slug} is inactive.")

    model = _get_or_create_model(entity)
    _ensure_table_exists(model)
    serializer_cls = _build_serializer(model, entity)
    field_names = [f['name'] for f in entity.fields]
    return RuntimeEntity(entity=entity, model=model, serializer_class=serializer_cls, field_names=field_names)


def load_runtime_entity(slug: str, company) -> RuntimeEntity:
    if not company:
        raise ValueError("Company context required to load runtime entity.")
    entity = (
        DynamicEntity.objects.filter(slug=slug, is_active=True)
        .filter(
            Q(scope_type="GLOBAL")
            | Q(scope_type="GROUP", company_group=company.company_group)
            | Q(scope_type="COMPANY", company=company)
        )
        .select_related('template')
        .first()
    )
    if not entity:
        raise DynamicEntity.DoesNotExist(f"No dynamic entity found for slug '{slug}'.")
    return ensure_runtime_entity(entity)


def register_all_entities():
    try:
        for entity in DynamicEntity.objects.filter(is_active=True):
            try:
                ensure_runtime_entity(entity)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to register dynamic entity %s: %s", entity.slug, exc)
    except (OperationalError, ProgrammingError):
        logger.debug("Database not ready yet. Skipping dynamic entity bootstrap.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_unique_slug(base_slug: str, scope: MetadataScope) -> str:
    slug_candidate = base_slug
    suffix = 1
    filters = {'slug': slug_candidate, 'scope_type': scope.scope_type}
    if scope.scope_type == "COMPANY":
        filters['company'] = scope.company
    elif scope.scope_type == "GROUP":
        filters['company_group'] = scope.company_group
    while DynamicEntity.objects.filter(**filters).exists():
        suffix += 1
        slug_candidate = f"{base_slug}-{suffix}"
        filters['slug'] = slug_candidate
    return slug_candidate


def _ensure_unique_field_name(base_name: str, existing: Sequence[str]) -> str:
    candidate = base_name
    suffix = 1
    while candidate in existing:
        suffix += 1
        candidate = f"{base_name}_{suffix}"
    return candidate


def _normalise_fields(raw_fields: List[Dict]) -> List[Dict]:
    normalised = []
    existing_names: List[str] = []

    for field in raw_fields:
        field_type = field.get('type') or 'text'
        mapped_type = FIELD_TYPE_MAP.get(field_type, 'char')
        label = field.get('label') or field.get('name') or 'Field'
        base_name = slugify(field.get('name') or label or field.get('id') or f"field_{len(normalised)+1}")
        base_name = base_name.replace('-', '_') or f"field_{len(normalised)+1}"
        field_name = _ensure_unique_field_name(base_name, existing_names)
        existing_names.append(field_name)
        normalised.append({
            'id': field.get('id'),
            'name': field_name,
            'label': label,
            'type': mapped_type,
            'raw_type': field_type,
            'required': bool(field.get('required')),
            'options': copy.deepcopy(field.get('options') or []),
            'placeholder': field.get('placeholder', ''),
            'helperText': field.get('helperText', ''),
        })
    return normalised


def _build_model_name(slug_value: str) -> str:
    parts = [part.capitalize() for part in slug_value.split('-') if part]
    name = ''.join(parts) or 'DynamicEntity'
    if name[0].isdigit():
        name = f"Entity{name}"
    return f"{name}Record"


def _build_table_name(scope: MetadataScope, slug_value: str) -> str:
    if scope.scope_type == "COMPANY" and scope.company:
        anchor = f"c{scope.company.id}"
    elif scope.scope_type == "GROUP" and scope.company_group:
        anchor = f"g{scope.company_group.id}"
    else:
        anchor = "global"
    base = f"fb_{anchor}_{slug_value}".replace('-', '_')
    return base[:58]  # leave space for db constraints


def _get_or_create_model(entity: DynamicEntity) -> Type[models.Model]:
    try:
        return django_apps.get_model('form_builder', entity.model_name)
    except LookupError:
        pass

    attrs: Dict[str, models.Field] = {}
    for field in entity.fields:
        attrs[field['name']] = _build_model_field(field)

    attrs['Meta'] = type('Meta', (), {
        'app_label': 'form_builder',
        'db_table': entity.table_name,
        'ordering': ['-created_at'],
    })
    attrs['__module__'] = 'apps.form_builder.dynamic_models'

    model_class = type(entity.model_name, (CompanyAwareModel,), attrs)
    try:
        django_apps.register_model('form_builder', model_class)
    except RuntimeError:
        # Model might already be registered in a race condition; fetch existing
        model_class = django_apps.get_model('form_builder', entity.model_name)
    return model_class


def _ensure_table_exists(model: Type[models.Model]):
    db_alias = router.db_for_write(model)
    connection = connections[db_alias]
    existing_tables = connection.introspection.table_names()
    if model._meta.db_table in existing_tables:
        return
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(model)


def _build_model_field(field: Dict) -> models.Field:
    field_type = field['type']
    required = field.get('required', False)
    label = field.get('label') or field['name'].replace('_', ' ').title()

    if field_type == 'char':
        max_length = max(255, max(len(str(opt)) for opt in field.get('options', []) or []))
        kwargs = {
            'max_length': max_length,
            'verbose_name': label,
            'blank': not required,
        }
        if not required:
            kwargs['null'] = True
        options = field.get('options') or []
        if options:
            kwargs['choices'] = [(opt, opt) for opt in options]
        return models.CharField(**kwargs)

    if field_type == 'text':
        kwargs = {
            'verbose_name': label,
            'blank': not required,
        }
        if not required:
            kwargs['null'] = True
        return models.TextField(**kwargs)

    if field_type == 'decimal':
        kwargs = {
            'verbose_name': label,
            'max_digits': 20,
            'decimal_places': 2,
        }
        if not required:
            kwargs['null'] = True
            kwargs['blank'] = True
        return models.DecimalField(**kwargs)

    if field_type == 'date':
        kwargs = {
            'verbose_name': label,
        }
        if not required:
            kwargs['null'] = True
            kwargs['blank'] = True
        return models.DateField(**kwargs)

    if field_type == 'boolean':
        return models.BooleanField(default=False, verbose_name=label)

    # Fallback to char
    return models.CharField(max_length=255, verbose_name=label, blank=not required, null=not required)


def _build_serializer(model: Type[models.Model], entity: DynamicEntity) -> Type[serializers.ModelSerializer]:
    field_names = [f['name'] for f in entity.fields]
    serializer_fields = ['id', *field_names, 'created_at', 'updated_at']

    class Meta:
        model = model
        fields = serializer_fields
        read_only_fields = ['id', 'created_at', 'updated_at', 'company', 'created_by']

    attrs = {'Meta': Meta}
    serializer_name = f"{model.__name__}Serializer"
    return type(serializer_name, (serializers.ModelSerializer,), attrs)
