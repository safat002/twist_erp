# backend/apps/inventory/permissions.py

from apps.security.permission_registry import register_permissions

INVENTORY_PERMISSIONS = [
    {"code": "inventory_view_dashboard", "description": "Can view Inventory dashboard", "category": "Inventory", "scope_required": True},
    {"code": "inventory_view_product", "description": "Can view products and product categories", "category": "Inventory", "scope_required": True},
    {"code": "inventory_manage_product", "description": "Can create, edit, delete products and product categories", "category": "Inventory", "scope_required": True},
    {"code": "inventory_view_warehouse", "description": "Can view warehouses and locations", "category": "Inventory", "scope_required": True},
    {"code": "inventory_manage_warehouse", "description": "Can create, edit, delete warehouses and locations", "category": "Inventory", "scope_required": True},
    {"code": "inventory_view_stock", "description": "Can view current stock levels", "category": "Inventory", "scope_required": True},
    {"code": "inventory_manage_stock_movement", "description": "Can create, edit, delete stock movements (GRN, Issue, Transfer)", "category": "Inventory", "scope_required": True, "is_sensitive": True},
    {"code": "inventory_perform_cycle_count", "description": "Can perform inventory cycle counts and adjustments", "category": "Inventory", "scope_required": True, "is_sensitive": True},
    {"code": "inventory_view_reports", "description": "Can view inventory reports (aging, valuation)", "category": "Inventory", "scope_required": True},
]

register_permissions(INVENTORY_PERMISSIONS)
