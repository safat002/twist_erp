# backend/apps/ai_companion/permissions.py

from apps.security.permission_registry import register_permissions

AI_PERMISSIONS = [
    {"code": "ai_view_dashboard", "description": "Can view AI Ops dashboard", "category": "AI Ops", "scope_required": False},
    {"code": "ai_manage_training_data", "description": "Can manage AI training data and feedback", "category": "AI Ops", "scope_required": False, "is_sensitive": True},
    {"code": "ai_manage_model_config", "description": "Can configure AI models and parameters", "category": "AI Ops", "scope_required": False, "is_sensitive": True},
    {"code": "ai_view_audit", "description": "Can view AI interaction audit logs", "category": "AI Ops", "scope_required": False, "is_sensitive": True},
]

register_permissions(AI_PERMISSIONS)
