# backend/apps/budgeting/permissions.py

from apps.security.permission_registry import register_permissions

BUDGETING_PERMISSIONS = [
    {"code": "budgeting_view_dashboard", "description": "Can view Budgeting dashboard", "category": "Budgeting", "scope_required": True},
    {"code": "budgeting_view_cost_center", "description": "Can view cost centers", "category": "Budgeting", "scope_required": True},
    {"code": "budgeting_manage_cost_center", "description": "Can create, edit, delete cost centers", "category": "Budgeting", "scope_required": True},
    {"code": "budgeting_view_budget_plan", "description": "Can view budget plans", "category": "Budgeting", "scope_required": True},
    {"code": "budgeting_manage_budget_plan", "description": "Can create, edit, delete budget plans", "category": "Budgeting", "scope_required": True, "is_sensitive": True},
    {"code": "budgeting_approve_budget", "description": "Can approve budget plans", "category": "Budgeting", "scope_required": True, "is_sensitive": True},
    {"code": "budgeting_view_monitor", "description": "Can view budget monitor and usage", "category": "Budgeting", "scope_required": True},
    {"code": "budgeting_manage_out_of_budget_exception", "description": "Can approve out-of-budget exceptions", "category": "Budgeting", "scope_required": True, "is_sensitive": True},
]

register_permissions(BUDGETING_PERMISSIONS)
