from django.db import transaction
from .models import WorkflowTemplate, WorkflowInstance


class WorkflowService:
    """Simplified workflow engine based on JSON templates."""

    @staticmethod
    @transaction.atomic
    def start_workflow(content_object, workflow_name: str) -> WorkflowInstance:
        """
        Start a new workflow instance for the given object using a template name.
        Chooses the first state in template.definition["states"] as initial.
        """
        company = getattr(content_object, "company", None)

        try:
            template = WorkflowTemplate.objects.get(name__iexact=workflow_name, company=company)
        except WorkflowTemplate.DoesNotExist:
            # Fallback to global template (no company)
            try:
                template = WorkflowTemplate.objects.get(name__iexact=workflow_name, company__isnull=True)
            except WorkflowTemplate.DoesNotExist:
                raise ValueError(f"Workflow template '{workflow_name}' not found.")

        definition = template.definition or {}
        states = definition.get("states") or []
        if not states:
            raise ValueError(f"Workflow template '{template.name}' has no states defined.")
        initial = definition.get("initial") or states[0]

        # Store minimal context reference to the object
        ctx = {}
        try:
            ctx = {"content_type": content_object.__class__.__name__, "object_pk": content_object.pk}
        except Exception:
            pass

        instance = WorkflowInstance.objects.create(
            template=template,
            state=initial,
            context=ctx,
            company=company,
        )
        return instance

    @staticmethod
    def get_available_transitions(instance: WorkflowInstance) -> list[str]:
        """Return the list of allowed 'to' states from the current state."""
        definition = instance.template.definition or {}
        transitions = definition.get("transitions", {})
        return list(transitions.get(instance.state, []))

    @staticmethod
    @transaction.atomic
    def trigger_transition(instance: WorkflowInstance, to_state: str) -> WorkflowInstance:
        """Move the instance to a new state if allowed by the template."""
        allowed = set(WorkflowService.get_available_transitions(instance))
        if allowed and to_state not in allowed:
            raise ValueError(f"Transition from {instance.state} to {to_state} not allowed")
        instance.state = to_state
        instance.save(update_fields=["state", "updated_at"])
        return instance
