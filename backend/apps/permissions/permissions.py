"""
Core permission checking logic for the ERP.
"""
from apps.users.models import User
from apps.companies.models import Company

def has_permission(user: User, permission_code: str, company: Company) -> bool:
    """
    Checks if a user has a specific permission within the context of a given company.

    This is the central function for all permission checks across the system.

    Args:
        user: The user instance to check.
        permission_code: The code of the permission (e.g., 'sales.view_order').
        company: The company context for the permission check.

    Returns:
        True if the user has the permission, False otherwise.
    """
    # Basic auth guard
    if not user or not user.is_authenticated:
        return False

    # System administrators and superusers have all permissions implicitly,
    # even if no explicit company context was provided.
    if getattr(user, 'is_system_admin', False) or (getattr(user, 'is_staff', False) and getattr(user, 'is_superuser', False)):
        return True

    # For non-superusers, company context is required from here on.
    if not company:
        return False

    # Get all active roles for the user in the specified company
    user_company_roles = user.usercompanyrole_set.filter(company=company, is_active=True)

    if not user_company_roles.exists():
        return False

    # Check if any of the user's roles contain the required permission.
    # This is optimized to perform a single database query.
    return user_company_roles.filter(
        role__permissions__code=permission_code
    ).exists()
