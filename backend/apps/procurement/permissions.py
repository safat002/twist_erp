# backend/apps/procurement/permissions.py

from apps.security.permission_registry import register_permissions

PROCUREMENT_PERMISSIONS = [
    {"code": "procurement_view_dashboard", "description": "Can view Procurement dashboard", "category": "Procurement", "scope_required": True},
    {"code": "procurement_view_supplier", "description": "Can view supplier records", "category": "Procurement", "scope_required": True},
    {"code": "procurement_manage_supplier", "description": "Can create, edit, delete supplier records", "category": "Procurement", "scope_required": True},
    {"code": "procurement_create_pr", "description": "Can create Purchase Requisitions", "category": "Procurement", "scope_required": True},
    {"code": "procurement_approve_pr", "description": "Can approve Purchase Requisitions", "category": "Procurement", "scope_required": True, "is_sensitive": True},
    {"code": "procurement_create_po", "description": "Can create Purchase Orders", "category": "Procurement", "scope_required": True},
    {"code": "procurement_approve_po", "description": "Can approve Purchase Orders", "category": "Procurement", "scope_required": True, "is_sensitive": True},
    {"code": "procurement_manage_grn", "description": "Can create, edit, delete Goods Receipt Notes", "category": "Procurement", "scope_required": True, "is_sensitive": True},
    {"code": "procurement_view_reports", "description": "Can view procurement reports", "category": "Procurement", "scope_required": True},
    {"code": "procurement_manage_price_tolerance", "description": "Can approve purchases exceeding price tolerance", "category": "Procurement", "scope_required": True, "is_sensitive": True},
    {"code": "procurement_manage_out_of_budget", "description": "Can approve out-of-budget purchase requests", "category": "Procurement", "scope_required": True, "is_sensitive": True},
]

register_permissions(PROCUREMENT_PERMISSIONS)
