# backend/apps/projects/permissions.py

from apps.security.permission_registry import register_permissions

PROJECTS_PERMISSIONS = [
    {"code": "projects_view_dashboard", "description": "Can view Projects dashboard", "category": "Projects", "scope_required": True},
    {"code": "projects_view_project", "description": "Can view project records", "category": "Projects", "scope_required": True},
    {"code": "projects_manage_project", "description": "Can create, edit, delete project records", "category": "Projects", "scope_required": True},
    {"code": "projects_view_task", "description": "Can view project tasks", "category": "Projects", "scope_required": True},
    {"code": "projects_manage_task", "description": "Can create, edit, delete project tasks", "category": "Projects", "scope_required": True},
    {"code": "projects_view_timesheet", "description": "Can view timesheets", "category": "Projects", "scope_required": True},
    {"code": "projects_manage_timesheet", "description": "Can create, edit, delete timesheets", "category": "Projects", "scope_required": True},
    {"code": "projects_view_reports", "description": "Can view project reports", "category": "Projects", "scope_required": True},
]

register_permissions(PROJECTS_PERMISSIONS)
