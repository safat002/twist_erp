# backend/apps/assets/permissions.py

from apps.security.permission_registry import register_permissions

ASSET_PERMISSIONS = [
    {"code": "asset_view_dashboard", "description": "Can view Asset Management dashboard", "category": "Asset Management", "scope_required": True},
    {"code": "asset_view_register", "description": "Can view asset register", "category": "Asset Management", "scope_required": True},
    {"code": "asset_manage_register", "description": "Can create, edit, delete assets in register", "category": "Asset Management", "scope_required": True, "is_sensitive": True},
    {"code": "asset_view_maintenance", "description": "Can view asset maintenance schedules and records", "category": "Asset Management", "scope_required": True},
    {"code": "asset_manage_maintenance", "description": "Can create, edit, delete asset maintenance tasks", "category": "Asset Management", "scope_required": True},
    {"code": "asset_manage_depreciation", "description": "Can run and manage asset depreciation", "category": "Asset Management", "scope_required": True, "is_sensitive": True},
    {"code": "asset_view_reports", "description": "Can view asset reports", "category": "Asset Management", "scope_required": True},
]

register_permissions(ASSET_PERMISSIONS)
