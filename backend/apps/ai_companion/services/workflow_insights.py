from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from django.utils import timezone

from apps.workflows.models import WorkflowInstance


def explain_instance(instance: WorkflowInstance) -> Dict[str, object]:
    template = instance.template
    definition = template.definition or {}
    transitions = definition.get("transitions") or {}
    approvals_map = definition.get("approvals") or {}
    sla_map = definition.get("sla_hours") or {}
    state_meta = definition.get("state_metadata") or {}

    now = timezone.now()
    updated_at = instance.updated_at or instance.created_at or now
    time_in_state_hours = round((now - updated_at).total_seconds() / 3600.0, 2)
    next_states: List[str] = list(transitions.get(instance.state, []))
    approvals = approvals_map.get(instance.state) or []
    sla_hours = sla_map.get(instance.state)
    state_notes = state_meta.get(instance.state, {})

    summary = f"Workflow '{template.name}' is currently in state '{instance.state}'."
    recommendations: List[str] = []

    if approvals:
        recommendations.append(
            f"Waiting for approval from: {', '.join(approvals)}."
        )
    if next_states:
        recommendations.append(
            f"Next possible transitions: {', '.join(next_states)}."
        )
    if sla_hours:
        recommendations.append(
            f"SLA target for this state is {sla_hours} hour(s)."
        )
    if time_in_state_hours > (sla_hours or 24):
        recommendations.append(
            "This instance has exceeded the expected SLA window; consider escalating."
        )

    return {
        "instance_id": instance.id,
        "workflow": template.name,
        "state": instance.state,
        "time_in_state_hours": time_in_state_hours,
        "next_states": next_states,
        "approvals": approvals,
        "context": instance.context or {},
        "summary": summary,
        "recommendations": recommendations,
        "state_metadata": state_notes,
        "last_updated": updated_at.isoformat() if isinstance(updated_at, datetime) else updated_at,
    }
