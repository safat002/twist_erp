from rest_framework.permissions import BasePermission
from apps.security.services.permission_service import PermissionService

class HasERPPermission(BasePermission):
    """Custom DRF permission to check against the new security system."""

    def __init__(self, perm_code, scope_type=None):
        self.perm_code = perm_code
        self.scope_type = scope_type # Optional: if the permission needs a specific scope type from the object

    def has_permission(self, request, view):
        # For list/create operations, check if user has the permission globally or for any relevant scope
        # The PermissionService.user_has_permission handles superuser and global permissions
        return PermissionService.user_has_permission(request.user, self.perm_code)

    def has_object_permission(self, request, view, obj):
        # For retrieve/update/destroy operations, check if user has the permission for the specific object's scope
        record_scope_str = None
        if self.scope_type:
            # Attempt to resolve scope from the object based on the provided scope_type
            if hasattr(obj, f'{self.scope_type}_id'):
                record_scope_str = f'{self.scope_type}:{getattr(obj, f"{self.scope_type}_id")}'
            elif hasattr(obj, self.scope_type) and hasattr(getattr(obj, self.scope_type), 'id'):
                record_scope_str = f'{self.scope_type}:{getattr(obj, self.scope_type).id}'
            # Fallback to company if scope_type is not directly on obj but obj has company
            elif self.scope_type == 'company' and hasattr(obj, 'company_id'):
                record_scope_str = f'company:{obj.company_id}'

        # If no specific record_scope_str could be resolved, fall back to general permission check
        if record_scope_str is None:
            return PermissionService.user_has_permission(request.user, self.perm_code)
        
        return PermissionService.user_has_permission(request.user, self.perm_code, record_scope_str)