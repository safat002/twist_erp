"""
MIS App Services Package
Centralized business logic and service layer
"""

# Import main services for easy access
from .notification_service import notification_service

__all__ = [
    'notification_service',
]