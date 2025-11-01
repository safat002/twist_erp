# backend/apps/finance/permissions.py

from apps.security.permission_registry import register_permissions

FINANCE_PERMISSIONS = [
    {"code": "finance_view_dashboard", "description": "Can view Finance dashboard", "category": "Finance", "scope_required": True},
    {"code": "finance_view_coa", "description": "Can view Chart of Accounts", "category": "Finance", "scope_required": True},
    {"code": "finance_manage_coa", "description": "Can create, edit, delete Chart of Accounts", "category": "Finance", "scope_required": True, "is_sensitive": True},
    {"code": "finance_view_journal", "description": "Can view Journal Vouchers", "category": "Finance", "scope_required": True},
    {"code": "finance_manage_journal", "description": "Can create, edit, delete Journal Vouchers", "category": "Finance", "scope_required": True, "is_sensitive": True},
    {"code": "finance_post_journal", "description": "Can post Journal Vouchers to GL", "category": "Finance", "scope_required": True, "is_sensitive": True},
    {"code": "finance_view_invoice", "description": "Can view Invoices (AR/AP)", "category": "Finance", "scope_required": True},
    {"code": "finance_manage_invoice", "description": "Can create, edit, delete Invoices (AR/AP)", "category": "Finance", "scope_required": True, "is_sensitive": True},
    {"code": "finance_view_payment", "description": "Can view Payments/Receipts", "category": "Finance", "scope_required": True},
    {"code": "finance_manage_payment", "description": "Can create, edit, delete Payments/Receipts", "category": "Finance", "scope_required": True, "is_sensitive": True},
    {"code": "finance_reconcile_bank", "description": "Can perform bank reconciliation", "category": "Finance", "scope_required": True, "is_sensitive": True},
    {"code": "finance_view_reports", "description": "Can view financial reports (P&L, BS, Cash Flow)", "category": "Finance", "scope_required": True, "is_sensitive": True},
    {"code": "finance_close_period", "description": "Can close financial periods", "category": "Finance", "scope_required": True, "is_sensitive": True},
]

register_permissions(FINANCE_PERMISSIONS)
