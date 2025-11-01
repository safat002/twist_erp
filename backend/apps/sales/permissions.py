# backend/apps/sales/permissions.py

from apps.security.permission_registry import register_permissions

SALES_PERMISSIONS = [
    {"code": "sales_view_dashboard", "description": "Can view Sales & CRM dashboard", "category": "Sales & CRM", "scope_required": True},
    {"code": "sales_view_customer", "description": "Can view customer records", "category": "Sales & CRM", "scope_required": True},
    {"code": "sales_manage_customer", "description": "Can create, edit, delete customer records", "category": "Sales & CRM", "scope_required": True},
    {"code": "sales_view_quotation", "description": "Can view sales quotations", "category": "Sales & CRM", "scope_required": True},
    {"code": "sales_manage_quotation", "description": "Can create, edit, delete sales quotations", "category": "Sales & CRM", "scope_required": True},
    {"code": "sales_view_order", "description": "Can view sales orders", "category": "Sales & CRM", "scope_required": True},
    {"code": "sales_manage_order", "description": "Can create, edit, delete sales orders", "category": "Sales & CRM", "scope_required": True, "is_sensitive": True},
    {"code": "sales_manage_pipeline", "description": "Can manage sales pipeline (leads, opportunities)", "category": "Sales & CRM", "scope_required": True},
    {"code": "sales_view_reports", "description": "Can view sales reports", "category": "Sales & CRM", "scope_required": True},
]

register_permissions(SALES_PERMISSIONS)
