# backend/apps/security/permission_registry.py

# This list will be populated by each app's permissions.py
# Each entry should be a dictionary with 'code', 'description', 'category', 'scope_required', 'is_sensitive', 'is_assignable'

ALL_PERMISSIONS = []

def register_permissions(permissions_list):
    """Registers a list of permissions from an app."""
    for perm in permissions_list:
        if not isinstance(perm, dict) or 'code' not in perm:
            raise ValueError("Each permission must be a dictionary with a 'code' key.")
        ALL_PERMISSIONS.append(perm)


# Example of how an app would declare and register its permissions:
# # myapp/permissions.py
# MYAPP_PERMISSIONS = [
#     {"code": "myapp_view_data", "description": "Can view My App data", "category": "myapp", "scope_required": True},
#     {"code": "myapp_edit_data", "description": "Can edit My App data", "category": "myapp", "scope_required": True, "is_sensitive": True},
# ]
# from apps.security.permission_registry import register_permissions
# register_permissions(MYAPP_PERMISSIONS)
