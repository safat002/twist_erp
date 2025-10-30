import logging
from django.dispatch import Signal

logger = logging.getLogger(__name__)

class EventBus:
    """
    A simple, in-process event bus using Django's Signal dispatcher.
    This allows for decoupled communication between different apps.

    - register_event(event_name): Pre-defines an event.
    - publish(event_name, **kwargs): Sends an event.
    - subscribe(event_name, handler): Registers a function to handle an event.
    """
    def __init__(self):
        self._signals = {}

    def register_event(self, event_name: str):
        """
        Registers an event name so it's known to the bus, even if no handlers are yet subscribed.
        """
        if event_name not in self._signals:
            self._signals[event_name] = Signal()
        logger.debug(f"Event '{event_name}' registered.")

    def publish(self, event_name: str, **kwargs):
        """
        Publishes an event to all subscribed handlers.

        Args:
            event_name: The unique name of the event (e.g., 'order.created').
            **kwargs: Arbitrary keyword arguments to pass to the handlers.
                      Commonly includes 'instance' or an object ID.
        """
        if event_name not in self._signals:
            # Automatically register if not pre-registered, but log a warning
            self.register_event(event_name)
            logger.warning(f"Event '{event_name}' was published without being pre-registered.")
            
        signal = self._signals[event_name]
        logger.info(f"Publishing event '{event_name}' with args: {kwargs}")
        results = signal.send(sender=self.__class__, **kwargs)
        if not results:
            logger.debug(f"Event '{event_name}' was published, but no handlers received it.")

    def subscribe(self, event_name: str, handler):
        """
        Subscribes a handler function to a specific event.

        Args:
            event_name: The unique name of the event.
            handler: The function to be called when the event is published.
        """
        if event_name not in self._signals:
            self.register_event(event_name) # Ensure event is registered before subscribing
        
        signal = self._signals[event_name]
        signal.connect(handler)
        logger.info(f"Handler {handler.__name__} subscribed to event '{event_name}'.")

# Global instance of the event bus to be used throughout the application
event_bus = EventBus()

# Example of how to subscribe a handler:
#
# from shared.event_bus import event_bus
#
# def handle_order_creation(sender, **kwargs):
#     order = kwargs.get('instance')
#     print(f"New order created: {order.id}")
#
# event_bus.subscribe('order.created', handle_order_creation)


# Example of how to publish an event:
#
# from shared.event_bus import event_bus
#
# def create_order(data):
#     # ... logic to create order ...
#     new_order = ...
#     event_bus.publish('order.created', instance=new_order)
