from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from django.apps import apps as django_apps
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model, QuerySet, Q

from apps.companies.models import Company
from apps.form_builder.models import DynamicEntity
from apps.form_builder.services.dynamic_entities import load_runtime_entity
from apps.permissions.permissions import has_permission


STATIC_DATASETS: List[Dict[str, Any]] = []


@dataclass
class DatasetRuntime:
    type: str
    key: str
    label: str
    model: type[Model]
    queryset: QuerySet
    field_map: Dict[str, str]
    metadata: Dict[str, Any]
    default_limit: Optional[int] = None


def get_available_datasets(user, company: Company) -> List[Dict[str, Any]]:
    """
    Return datasets the user can use as a data source when designing reports.
    """
    if not user or not company:
        return []

    if not has_permission(user, "can_build_reports", company):
        return []

    datasets: List[Dict[str, Any]] = []
    datasets.extend(_dynamic_entity_datasets(user, company))
    datasets.extend(_static_datasets(user, company))
    return datasets


def resolve_dataset(data_source: Dict[str, Any], *, company: Company, user) -> DatasetRuntime:
    if not data_source:
        raise ImproperlyConfigured("Report data source is not defined.")

    ds_type = data_source.get("type")
    if ds_type == "dynamic_entity":
        slug = data_source.get("slug") or data_source.get("key")
        if not slug:
            raise ImproperlyConfigured("Dynamic entity data source requires a slug.")
        required = data_source.get("required_permissions")
        return _resolve_dynamic_entity(slug, company, user, required_permissions=required)

    if ds_type == "model":
        model_path = data_source.get("model")
        if not model_path:
            raise ImproperlyConfigured("Model data source requires the 'model' attribute (app_label.ModelName).")
        return _resolve_model_dataset(model_path, data_source, company, user)

    raise ImproperlyConfigured(f"Unsupported data source type '{ds_type}'.")


def _dynamic_entity_datasets(user, company: Company) -> List[Dict[str, Any]]:
    qs = (
        DynamicEntity.objects.filter(is_active=True)
        .filter(
            Q(scope_type="GLOBAL")
            | Q(scope_type="GROUP", company_group=company.company_group)
            | Q(scope_type="COMPANY", company=company)
        )
        .order_by("name")
    )

    datasets: List[Dict[str, Any]] = []
    for entity in qs:
        dataset = {
            "type": "dynamic_entity",
            "key": f"dynamic::{entity.slug}",
            "slug": entity.slug,
            "label": entity.name,
            "description": entity.description,
            "fields": _format_dynamic_fields(entity.fields),
            "required_permissions": ["can_build_reports"],
            "default_limit": 500,
            "scope_type": entity.scope_type,
        }
        datasets.append(dataset)
    return datasets


def _static_datasets(user, company: Company) -> Iterable[Dict[str, Any]]:
    for dataset in STATIC_DATASETS:
        required = dataset.get("required_permissions") or ["can_build_reports"]
        if all(has_permission(user, code, company) for code in required):
            yield dataset


def _resolve_dynamic_entity(
    slug: str,
    company: Company,
    user,
    required_permissions: Optional[Iterable[str]] = None,
) -> DatasetRuntime:
    runtime = load_runtime_entity(slug, company)
    permission_codes = list(required_permissions or []) or ["can_build_reports"]
    metadata_dict = {
        "type": "dynamic_entity",
        "slug": slug,
        "label": runtime.entity.name,
        "description": runtime.entity.description,
        "fields": runtime.entity.fields,
    }

    if not all(has_permission(user, code, company) for code in permission_codes):
        raise PermissionError(f"You do not have permission to access dataset '{runtime.entity.name}'.")

    queryset = runtime.model.objects.filter(company=company)
    field_map = {
        field["name"]: field["name"] for field in runtime.entity.fields if isinstance(field, dict) and field.get("name")
    }
    field_map.update({"id": "id", "created_at": "created_at", "updated_at": "updated_at"})

    return DatasetRuntime(
        type="dynamic_entity",
        key=f"dynamic::{slug}",
        label=runtime.entity.name,
        model=runtime.model,
        queryset=queryset,
        field_map=field_map,
        metadata=metadata_dict,
        default_limit=500,
    )


def _resolve_model_dataset(model_path: str, data_source: Dict[str, Any], company: Company, user) -> DatasetRuntime:
    try:
        app_label, model_name = model_path.split(".")
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"Invalid model path '{model_path}'. Expected format 'app_label.ModelName'."
        ) from exc

    try:
        model = django_apps.get_model(app_label, model_name)
    except LookupError as exc:
        raise ImproperlyConfigured(f"Model '{model_path}' could not be found.") from exc

    required = data_source.get("required_permissions") or ["can_build_reports"]
    if not all(has_permission(user, code, company) for code in required):
        raise PermissionError(f"You do not have permission to access dataset '{data_source.get('label', model_name)}'.")

    queryset = model.objects.all()
    if hasattr(model, "company_id"):
        queryset = queryset.filter(company_id=company.id)
    elif hasattr(model, "company"):
        queryset = queryset.filter(company=company)

    if hasattr(model, "company_group_id"):
        queryset = queryset.filter(company_group_id=company.company_group_id)

    field_map = data_source.get("field_map") or {}
    if not field_map:
        # Build a naive field map from model _meta
        field_map = {field.name: field.name for field in model._meta.fields}

    metadata = {
        "type": "model",
        "model": model_path,
        "label": data_source.get("label") or model._meta.verbose_name.title(),
        "fields": [{"name": name, "label": name.replace("_", " ").title()} for name in field_map],
    }

    return DatasetRuntime(
        type="model",
        key=data_source.get("key") or model_path,
        label=metadata["label"],
        model=model,
        queryset=queryset,
        field_map=field_map,
        metadata=metadata,
        default_limit=data_source.get("default_limit"),
    )


def _format_dynamic_fields(fields: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    formatted: List[Dict[str, Any]] = []
    for field in fields or []:
        if not isinstance(field, dict):
            continue
        formatted.append(
            {
                "name": field.get("name"),
                "label": field.get("label") or (field.get("name") or "").replace("_", " ").title(),
                "type": field.get("type"),
                "required": field.get("required", False),
            }
        )
    formatted.extend(
        [
            {"name": "created_at", "label": "Created At", "type": "datetime"},
            {"name": "updated_at", "label": "Updated At", "type": "datetime"},
        ]
    )
    return formatted
