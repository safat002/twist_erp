import redis
import json
from django.conf import settings
from django.utils import timezone

class EventBus:
    """
    Simple pub/sub event bus using Redis
    For inter-module communication
    """
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB
        )
        self.pubsub = self.redis_client.pubsub()

    def publish(self, channel, event_type, data):
        """Publish event to channel"""
        message = {
            'event_type': event_type,
            'data': data,
            'timestamp': timezone.now().isoformat()
        }
        self.redis_client.publish(channel, json.dumps(message))

    def subscribe(self, channel, callback):
        """Subscribe to channel with callback"""
        self.pubsub.subscribe(channel)
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                callback(data)

# Usage example
# event_bus = EventBus()

# Publish event
# event_bus.publish(
#     'company.events',
#     'company.created',
#     {'company_id': 1, 'name': 'ACME Corp'}
# )
