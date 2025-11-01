# backend/apps/hr/permissions.py

from apps.security.permission_registry import register_permissions

HR_PERMISSIONS = [
    {"code": "hr_view_dashboard", "description": "Can view HR & Payroll dashboard", "category": "HR & Payroll", "scope_required": True},
    {"code": "hr_view_employee", "description": "Can view employee records", "category": "HR & Payroll", "scope_required": True},
    {"code": "hr_manage_employee", "description": "Can create, edit, delete employee records", "category": "HR & Payroll", "scope_required": True, "is_sensitive": True},
    {"code": "hr_view_attendance", "description": "Can view attendance records", "category": "HR & Payroll", "scope_required": True},
    {"code": "hr_manage_attendance", "description": "Can create, edit, delete attendance records", "category": "HR & Payroll", "scope_required": True},
    {"code": "hr_view_leave", "description": "Can view leave requests and balances", "category": "HR & Payroll", "scope_required": True},
    {"code": "hr_manage_leave", "description": "Can create, edit, delete leave requests and manage leave types", "category": "HR & Payroll", "scope_required": True},
    {"code": "hr_approve_leave", "description": "Can approve/reject leave requests", "category": "HR & Payroll", "scope_required": True, "is_sensitive": True},
    {"code": "hr_view_payroll", "description": "Can view payroll runs and details", "category": "HR & Payroll", "scope_required": True, "is_sensitive": True},
    {"code": "hr_manage_payroll", "description": "Can create, edit, delete payroll runs and lines", "category": "HR & Payroll", "scope_required": True, "is_sensitive": True},
    {"code": "hr_post_payroll", "description": "Can post payroll to finance", "category": "HR & Payroll", "scope_required": True, "is_sensitive": True},
    {"code": "hr_view_recruitment", "description": "Can view job requisitions and candidates", "category": "HR & Payroll", "scope_required": True},
    {"code": "hr_manage_recruitment", "description": "Can create, edit, delete job requisitions, candidates, and interviews", "category": "HR & Payroll", "scope_required": True},
    {"code": "hr_view_onboarding", "description": "Can view onboarding records and tasks", "category": "HR & Payroll", "scope_required": True},
    {"code": "hr_manage_onboarding", "description": "Can create, edit, delete onboarding records and tasks", "category": "HR & Payroll", "scope_required": True},
    {"code": "hr_view_performance", "description": "Can view performance reviews and goals", "category": "HR & Payroll", "scope_required": True},
    {"code": "hr_manage_performance", "description": "Can create, edit, delete performance reviews and goals", "category": "HR & Payroll", "scope_required": True},
    {"code": "hr_view_exit", "description": "Can view employee exit records", "category": "HR & Payroll", "scope_required": True, "is_sensitive": True},
    {"code": "hr_manage_exit", "description": "Can create, edit, delete employee exit records and final settlements", "category": "HR & Payroll", "scope_required": True, "is_sensitive": True},
    {"code": "hr_view_policy", "description": "Can view HR policy documents", "category": "HR & Payroll", "scope_required": True},
    {"code": "hr_manage_policy", "description": "Can create, edit, delete HR policy documents", "category": "HR & Payroll", "scope_required": True},
    {"code": "hr_manage_advance_loan", "description": "Can manage employee salary advances and loans", "category": "HR & Payroll", "scope_required": True, "is_sensitive": True},
]

register_permissions(HR_PERMISSIONS)
