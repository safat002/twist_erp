# backend/apps/production/permissions.py

from apps.security.permission_registry import register_permissions

PRODUCTION_PERMISSIONS = [
    {"code": "production_view_dashboard", "description": "Can view Production dashboard", "category": "Production", "scope_required": True},
    {"code": "production_view_bom", "description": "Can view Bills of Materials", "category": "Production", "scope_required": True},
    {"code": "production_manage_bom", "description": "Can create, edit, delete Bills of Materials", "category": "Production", "scope_required": True, "is_sensitive": True},
    {"code": "production_view_work_order", "description": "Can view Work Orders", "category": "Production", "scope_required": True},
    {"code": "production_manage_work_order", "description": "Can create, edit, delete Work Orders", "category": "Production", "scope_required": True, "is_sensitive": True},
    {"code": "production_manage_mps", "description": "Can manage Master Production Schedule", "category": "Production", "scope_required": True, "is_sensitive": True},
    {"code": "production_manage_mrp", "description": "Can run and manage Material Requirements Planning", "category": "Production", "scope_required": True, "is_sensitive": True},
    {"code": "production_view_reports", "description": "Can view production reports", "category": "Production", "scope_required": True},
]

register_permissions(PRODUCTION_PERMISSIONS)
