from shared.event_bus import event_bus
from .services import WorkflowService
import logging

logger = logging.getLogger(__name__)

def handle_model_creation(sender, **kwargs):
    """
    A generic event handler that starts a workflow when a model instance is created.
    """
    instance = kwargs.get('instance')
    if not instance:
        return

    model_name = instance.__class__.__name__
    # The workflow name is conventionally named after the model.
    workflow_name = f"{model_name} Lifecycle"

    try:
        # Check if a workflow should be started for this object.
        # This assumes a naming convention for events, e.g., 'salesorder.created'
        WorkflowService.start_workflow(content_object=instance, workflow_name=workflow_name)
        logger.info(f"Successfully started workflow '{workflow_name}' for {model_name} ID {instance.pk}.")
    except ValueError as e:
        # This can happen if no matching workflow is defined, or one is already active.
        # We log this as a warning, as not every object needs a workflow.
        logger.debug(f"Did not start workflow for {model_name} ID {instance.pk}. Reason: {e}")
    except Exception as e:
        # Catch any other unexpected errors during workflow startup.
        logger.error(f"Error starting workflow for {model_name} ID {instance.pk}: {e}", exc_info=True)


def register_workflow_listeners():
    """
    Subscribes the workflow handler to various model creation events.
    This function should be called once at application startup.
    """
    # A list of events that should trigger a workflow.
    # This list can be expanded or configured in the future.
    workflow_trigger_events = [
        'salesorder.created',
        'purchaserequest.created',
        'invoice.created',
    ]

    for event_name in workflow_trigger_events:
        event_bus.subscribe(event_name, handle_model_creation)
