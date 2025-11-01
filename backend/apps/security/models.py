from django.db import models
from django.conf import settings
from apps.companies.models import Company, CompanyGroup
from shared.models import CompanyAwareModel

class SecPermission(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=100, unique=True, help_text="Unique code for the permission (e.g., procurement_create_pr)")
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, help_text="Category of the permission (e.g., finance, procurement)")
    scope_required = models.BooleanField(default=False, help_text="Does this permission require a specific scope (e.g., company, cost center)?")
    is_sensitive = models.BooleanField(default=False, help_text="Does this permission involve sensitive data or actions?")
    is_assignable = models.BooleanField(default=True, help_text="Can this permission be assigned to roles by admins?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'code']
        verbose_name = "Security Permission"
        verbose_name_plural = "Security Permissions"

    def __str__(self):
        return self.code

class SecRole(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, help_text="Name of the role (e.g., Procurement Officer)")
    code = models.CharField(max_length=100, unique=True, help_text="Unique code for the role (e.g., r_procurement_officer)")
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False, help_text="Is this a system-defined role that cannot be modified by admins?")
    company_group = models.ForeignKey(CompanyGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='security_roles')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('code', 'company_group') # Roles can be unique per company group or global
        ordering = ['name']
        verbose_name = "Security Role"
        verbose_name_plural = "Security Roles"

    def __str__(self):
        return self.name

class SecRolePermission(models.Model):
    id = models.BigAutoField(primary_key=True)
    role = models.ForeignKey(SecRole, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(SecPermission, on_delete=models.CASCADE, related_name='role_permissions')
    amount_limit = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, help_text="Optional: Amount limit for this permission within the role")
    percent_limit = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Optional: Percentage limit for this permission within the role")
    conditions = models.JSONField(default=dict, blank=True, help_text="Optional: JSON conditions for complex permission rules")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('role', 'permission')
        verbose_name = "Role Permission Assignment"
        verbose_name_plural = "Role Permission Assignments"

    def __str__(self):
        return f"{self.role.name} - {self.permission.code}"

class SecScope(models.Model):
    id = models.BigAutoField(primary_key=True)
    scope_type = models.CharField(max_length=50, help_text="Type of scope (e.g., company, cost_center, branch)")
    object_id = models.CharField(max_length=255, help_text="ID of the actual object (e.g., Company.id, CostCenter.id)")
    name = models.CharField(max_length=255, help_text="Display name of the scope (e.g., 'Company A', 'HR Department')")
    company_group = models.ForeignKey(CompanyGroup, on_delete=models.CASCADE, related_name='security_scopes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('scope_type', 'object_id', 'company_group')
        ordering = ['scope_type', 'name']
        verbose_name = "Security Scope"
        verbose_name_plural = "Security Scopes"

    def __str__(self):
        return f"{self.name} ({self.scope_type}:{self.object_id})"

class SecUserRole(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(SecRole, on_delete=models.CASCADE, related_name='user_roles')
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    is_delegated = models.BooleanField(default=False)
    delegated_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='delegated_roles')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'role') # A user can have a role only once, scopes define where
        ordering = ['user__username', 'role__name']
        verbose_name = "User Role Assignment"
        verbose_name_plural = "User Role Assignments"

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"

class SecUserRoleScope(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_role = models.ForeignKey(SecUserRole, on_delete=models.CASCADE, related_name='scopes')
    scope = models.ForeignKey(SecScope, on_delete=models.CASCADE, related_name='user_role_scopes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_role', 'scope')
        verbose_name = "User Role Scope Assignment"
        verbose_name_plural = "User Role Scope Assignments"

    def __str__(self):
        return f"{self.user_role.user.username} - {self.user_role.role.name} in {self.scope.name}"

class SecSoDRule(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    first_action_code = models.CharField(max_length=100, help_text="Permission code for the first action")
    second_action_code = models.CharField(max_length=100, help_text="Permission code for the second action that cannot be performed by the same user")
    enforcement = models.CharField(max_length=10, choices=[('BLOCK', 'Block'), ('WARN', 'Warn')], default='BLOCK')
    scope_type = models.CharField(max_length=50, null=True, blank=True, help_text="Optional: Scope type for which this rule applies")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Segregation of Duties Rule"
        verbose_name_plural = "Segregation of Duties Rules"

    def __str__(self):
        return self.name

class SecUserDirectPermission(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='direct_permissions')
    permission = models.ForeignKey(SecPermission, on_delete=models.CASCADE, related_name='direct_user_permissions')
    scope = models.ForeignKey(SecScope, on_delete=models.CASCADE, null=True, blank=True, related_name='direct_user_permissions')
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'permission', 'scope')
        verbose_name = "User Direct Permission"
        verbose_name_plural = "User Direct Permissions"

    def __str__(self):
        return f"{self.user.username} - {self.permission.code}"
