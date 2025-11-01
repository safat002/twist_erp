from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from apps.security.models import SecPermission, SecRole, SecUserRole, SecUserRoleScope, SecScope, SecSoDRule
from datetime import date

class PermissionService:
    CACHE_TIMEOUT = 60 * 5  # 5 minutes

    @staticmethod
    def _get_user_roles_and_scopes(user):
        """Helper to get all roles and their associated scopes for a user."""
        user_roles_data = []
        user_roles = SecUserRole.objects.filter(user=user, valid_from__lte=date.today()).filter(Q(valid_to__isnull=True) | Q(valid_to__gte=date.today()))

        for user_role in user_roles:
            role_scopes = SecUserRoleScope.objects.filter(user_role=user_role).select_related('scope')
            scopes = [{'id': urs.scope.id, 'type': urs.scope.scope_type, 'object_id': urs.scope.object_id} for urs in role_scopes]
            user_roles_data.append({
                'role': user_role.role,
                'scopes': scopes
            })
        return user_roles_data

    @classmethod
    def get_user_effective_permissions(cls, user):
        """Resolves and caches a user's effective permissions and their scopes.
        Returns a dict: { 'permission_code': set(scope_object_ids_or_wildcard) }"""
        if not user.is_authenticated:
            return {}

        if user.is_superuser:
            # Superusers have all permissions globally
            all_perms = SecPermission.objects.values_list('code', flat=True)
            return {perm_code: {'*': True} for perm_code in all_perms} # Use a dict to indicate global scope

        cache_key = f'user_perms:{user.id}'
        effective_permissions = cache.get(cache_key)

        if effective_permissions is None:
            effective_permissions = {}
            user_roles_data = cls._get_user_roles_and_scopes(user)

            for role_data in user_roles_data:
                role = role_data['role']
                assigned_scopes = role_data['scopes']

                role_permissions = SecRolePermission.objects.filter(role=role).select_related('permission')

                for rp in role_permissions:
                    perm_code = rp.permission.code
                    if perm_code not in effective_permissions:
                        effective_permissions[perm_code] = set()

                    if not rp.permission.scope_required:
                        # If permission doesn't require scope, it's global for this user
                        effective_permissions[perm_code] = {'*'} # Use a set to indicate global scope
                    elif '*' not in effective_permissions[perm_code]: # Not already global
                        # Add specific scopes
                        for scope in assigned_scopes:
                            effective_permissions[perm_code].add(f"{scope['type']}:{scope['object_id']}")
            
            cache.set(cache_key, effective_permissions, cls.CACHE_TIMEOUT)

        return effective_permissions

    @classmethod
    def user_has_permission(cls, user, perm_code, record_scope_str=None):
        """Checks if a user has a specific permission for a given record scope.
        record_scope_str format: "scope_type:object_id" (e.g., "company:1", "cost_center:HR")
        """
        if not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        effective_permissions = cls.get_user_effective_permissions(user)

        if perm_code not in effective_permissions:
            return False

        allowed_scopes = effective_permissions[perm_code]

        if '*' in allowed_scopes: # Global permission
            return True

        if record_scope_str is None:
            # Permission requires scope, but no record_scope provided
            return False

        return record_scope_str in allowed_scopes

    @staticmethod
    def resolve_record_scope(record):
        """Resolves the scope string for a given Django model instance.
        Returns a list of scope strings (e.g., ["company:1", "cost_center:HR"]).
        """
        scopes = []

        # Common scope types
        if hasattr(record, 'company_id') and record.company_id:
            scopes.append(f"company:{record.company_id}")
        elif hasattr(record, 'company') and hasattr(record.company, 'id'):
            scopes.append(f"company:{record.company.id}")

        if hasattr(record, 'cost_center_id') and record.cost_center_id:
            scopes.append(f"cost_center:{record.cost_center_id}")
        elif hasattr(record, 'cost_center') and hasattr(record.cost_center, 'id'):
            scopes.append(f"cost_center:{record.cost_center.id}")

        if hasattr(record, 'department_id') and record.department_id:
            scopes.append(f"department:{record.department_id}")
        elif hasattr(record, 'department') and hasattr(record.department, 'id'):
            scopes.append(f"department:{record.department.id}")

        if hasattr(record, 'project_id') and record.project_id:
            scopes.append(f"project:{record.project_id}")
        elif hasattr(record, 'project') and hasattr(record.project, 'id'):
            scopes.append(f"project:{record.project.id}")

        if hasattr(record, 'warehouse_id') and record.warehouse_id:
            scopes.append(f"warehouse:{record.warehouse_id}")
        elif hasattr(record, 'warehouse') and hasattr(record.warehouse, 'id'):
            scopes.append(f"warehouse:{record.warehouse.id}")

        # Add more scope types as needed (e.g., branch, grant, plant)
        return scopes

    @classmethod
    def check_sod(cls, user, perm_code, record, action_type):
        """Checks Segregation of Duties rules.
        This is a placeholder and needs full implementation based on SoD rules and audit logs.
        """
        # This is a complex check. For now, return True (no SoD violation)
        # Full implementation would involve:
        # 1. Finding SoD rules where second_action_code == perm_code
        # 2. Checking audit logs to see if the user already performed first_action_code on this record
        # 3. Applying enforcement (BLOCK/WARN)
        return True
