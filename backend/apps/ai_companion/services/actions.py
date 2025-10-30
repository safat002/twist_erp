from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from django.db import transaction
from django.utils import timezone

from apps.audit.utils import log_audit_event
from apps.dashboard.models import DashboardLayout
from apps.finance.models import Invoice
from apps.metadata.models import MetadataDefinition
from apps.metadata.services import MetadataScope, create_metadata_version
from apps.workflows.models import WorkflowInstance

from ..models import AIActionExecution, AIProactiveSuggestion
from .telemetry import TelemetryService
from .workflow_insights import explain_instance

logger = logging.getLogger(__name__)
telemetry = TelemetryService()


class ActionExecutionError(Exception):
    """Raised when an AI action cannot be executed."""


@dataclass
class ActionContext:
    user: Any
    company: Any = None


ActionHandler = Callable[[ActionContext, Dict[str, Any]], Dict[str, Any]]


class ActionRegistry:
    def __init__(self):
        self._registry: Dict[str, ActionHandler] = {}

    def register(self, name: str) -> Callable[[ActionHandler], ActionHandler]:
        def decorator(func: ActionHandler) -> ActionHandler:
            self._registry[name] = func
            return func

        return decorator

    def get(self, name: str) -> Optional[ActionHandler]:
        return self._registry.get(name)


registry = ActionRegistry()


def execute_action(action_name: str, *, context: ActionContext, payload: Dict[str, Any]) -> Dict[str, Any]:
    handler = registry.get(action_name)
    if handler is None:
        raise ActionExecutionError(f"No handler registered for action '{action_name}'.")

    with transaction.atomic():
        execution = AIActionExecution.objects.create(
            action_name=action_name,
            status="success",
            user=context.user,
            company=context.company,
            payload=payload,
        )
        try:
            result = handler(context, payload)
            if context.company and execution.company_id != getattr(context.company, "id", None):
                execution.company = context.company
            execution.result = result or {}
            execution.save(update_fields=["company", "result", "updated_at"])

            log_audit_event(
                user=context.user,
                company=context.company,
                company_group=getattr(context.company, "company_group", None) if context.company else None,
                action="AI_ACTION",
                entity_type="AI_ACTION",
                entity_id=action_name,
                description="AI conversational action executed",
                after={"payload": payload, "result": result},
            )
            return result or {}
        except Exception as exc:
            execution.status = "error"
            execution.error_message = str(exc)
            if context.company and execution.company_id != getattr(context.company, "id", None):
                execution.company = context.company
            execution.save(update_fields=["company", "status", "error_message", "updated_at"])
            logger.exception("AI action '%s' failed: %s", action_name, exc)
            raise ActionExecutionError(str(exc)) from exc


@registry.register("finance.mark_receivable_followup")
def mark_receivable_followup(context: ActionContext, payload: Dict[str, Any]) -> Dict[str, Any]:
    invoice_id = payload.get("invoice_id")
    if not invoice_id:
        raise ActionExecutionError("invoice_id is required.")
    try:
        invoice = Invoice.objects.select_related("company").get(id=invoice_id)
    except Invoice.DoesNotExist as exc:
        raise ActionExecutionError("Invoice not found.") from exc

    if context.company and invoice.company_id != getattr(context.company, "id", None):
        raise ActionExecutionError("Invoice does not belong to the active company.")
    if not context.user.has_company_access(invoice.company):
        raise ActionExecutionError("You do not have access to this company.")

    context.company = invoice.company

    note = payload.get("note") or "Follow-up scheduled via AI assistant."
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
    new_note = f"[AI ACTION {timestamp}] {note}"
    invoice.notes = (invoice.notes or "") + ("\n" if invoice.notes else "") + new_note
    invoice.save(update_fields=["notes", "updated_at"])

    return {
        "message": f"Invoice {invoice.invoice_number} flagged for follow-up.",
        "invoice_number": invoice.invoice_number,
    }


@registry.register("inventory.raise_reorder_alert")
def raise_reorder_alert(context: ActionContext, payload: Dict[str, Any]) -> Dict[str, Any]:
    product_code = payload.get("product_code")
    if not product_code:
        raise ActionExecutionError("product_code is required.")

    # Deduplicate by metadata
    metadata = {
        "rule_code": "inventory.manual_reorder",
        "product_code": product_code,
    }
    exists = AIProactiveSuggestion.objects.filter(
        user=context.user,
        company=context.company,
        metadata__rule_code="inventory.manual_reorder",
        metadata__product_code=product_code,
        status="pending",
    ).exists()
    if not exists:
        AIProactiveSuggestion.objects.create(
            user=context.user,
            company=context.company,
            title=f"Reorder requested for {product_code}",
            body=payload.get("message") or "A manual reorder has been requested.",
            metadata=metadata,
            alert_type="inventory",
            severity=AIProactiveSuggestion.AlertSeverity.WARNING,
            source_skill="action_engine",
        )

    return {
        "message": f"Reorder alert recorded for {product_code}.",
        "product_code": product_code,
    }


@registry.register("workflows.explain_instance")
def explain_workflow_instance(context: ActionContext, payload: Dict[str, Any]) -> Dict[str, Any]:
    instance_id = payload.get("workflow_instance_id") or payload.get("instance_id")
    if not instance_id:
        raise ActionExecutionError("workflow_instance_id is required.")
    try:
        instance = WorkflowInstance.objects.select_related("template", "company").get(id=instance_id)
    except WorkflowInstance.DoesNotExist as exc:
        raise ActionExecutionError("Workflow instance not found.") from exc

    if instance.company and not context.user.has_company_access(instance.company):
        raise ActionExecutionError("You do not have access to this workflow instance.")

    context.company = instance.company
    insight = explain_instance(instance)
    summary = insight.get("summary")
    details = {
        "workflow": insight.get("workflow"),
        "state": insight.get("state"),
        "time_in_state_hours": insight.get("time_in_state_hours"),
        "next_states": insight.get("next_states"),
        "approvals": insight.get("approvals"),
        "recommendations": insight.get("recommendations"),
        "last_updated": insight.get("last_updated"),
    }
    return {
        "message": summary,
        "summary": summary,
        "details": details,
    }


def _scope_from_definition(definition: MetadataDefinition) -> MetadataScope:
    if definition.scope_type == "COMPANY":
        return MetadataScope.for_company(definition.company)
    if definition.scope_type == "GROUP":
        return MetadataScope.for_group(definition.company_group)
    return MetadataScope.global_scope()


@registry.register("metadata.promote_field")
def promote_metadata_field(context: ActionContext, payload: Dict[str, Any]) -> Dict[str, Any]:
    definition_key = payload.get("definition_key")
    field_config = payload.get("field")
    if not definition_key or not isinstance(field_config, dict):
        raise ActionExecutionError("definition_key and field payload are required.")

    definition = (
        MetadataDefinition.objects.filter(key=definition_key, status="active")
        .order_by("-version")
        .select_related("company", "company_group")
        .first()
    )
    if not definition:
        raise ActionExecutionError("Metadata definition not found.")
    if definition.company and not context.user.has_company_access(definition.company):
        raise ActionExecutionError("You do not have access to this metadata scope.")

    fields = list((definition.definition or {}).get("fields") or [])
    field_names = {f.get("name") for f in fields}
    field_name = field_config.get("name")
    if not field_name:
        raise ActionExecutionError("Field name is required.")
    if field_name in field_names:
        raise ActionExecutionError(f"Field '{field_name}' already exists in this definition.")

    fields.append(field_config)
    new_definition_payload = {
        **(definition.definition or {}),
        "fields": fields,
    }
    scope = _scope_from_definition(definition)
    new_version = create_metadata_version(
        key=definition.key,
        kind=definition.kind,
        layer=definition.layer,
        scope=scope,
        definition=new_definition_payload,
        summary={"field_count": len(fields)},
        status="active",
        user=context.user,
    )
    new_version.activate(user=context.user)
    telemetry.record_event(
        event_type="metadata.field_promoted",
        user=context.user,
        company=context.company,
        payload={
            "definition_key": definition.key,
            "field_name": field_name,
            "version": new_version.version,
        },
    )

    return {
        "message": f"Field '{field_name}' promoted on {definition.key}.",
        "definition_key": definition.key,
        "version": new_version.version,
    }


@registry.register("metadata.create_dashboard_widget")
def create_dashboard_widget(context: ActionContext, payload: Dict[str, Any]) -> Dict[str, Any]:
    if context.company is None:
        raise ActionExecutionError("An active company is required to create dashboard widgets.")

    widget = payload.get("widget")
    if not isinstance(widget, dict) or not widget.get("id"):
        raise ActionExecutionError("Widget payload with 'id' is required.")

    layout, _ = DashboardLayout.objects.get_or_create(
        user=context.user,
        company=context.company,
        defaults={
            "layout": {},
            "widgets": [],
        },
    )
    widgets = list(layout.widgets or [])
    if widget["id"] not in widgets:
        widgets.append(widget["id"])
    layout.widgets = widgets
    layout.save(update_fields=["widgets", "updated_at"])
    telemetry.record_event(
        event_type="metadata.dashboard_widget_added",
        user=context.user,
        company=context.company,
        payload={
            "widget_id": widget["id"],
            "title": widget.get("title"),
        },
    )
    return {
        "message": f"Dashboard widget '{widget['id']}' added.",
        "widget": widget,
    }
