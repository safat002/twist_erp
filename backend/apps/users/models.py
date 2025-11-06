
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Extended user model with multi-company support
    """
    company_groups = models.ManyToManyField(
        'companies.CompanyGroup',
        related_name='users',
        blank=True
    )
    default_company_group = models.ForeignKey(
        'companies.CompanyGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='default_users'
    )
    companies = models.ManyToManyField(
        'companies.Company',
        through='UserCompanyRole',
        related_name='users'
    )
    default_company = models.ForeignKey(
        'companies.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='default_users'
    )
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    is_system_admin = models.BooleanField(default=False)
    admin_theme = models.CharField(max_length=20, default='default')

    class Meta:
        db_table = 'users'

    def has_company_access(self, company):
        """Check if user has access to company"""
        return self.companies.filter(id=company.id).exists()

class UserCompanyRole(models.Model):
    """
    Many-to-many relationship between users and companies
    with role assignment
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company_group = models.ForeignKey('companies.CompanyGroup', on_delete=models.CASCADE)
    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE)
    role = models.ForeignKey('permissions.Role', on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['user', 'company', 'role']]
        db_table = 'user_company_roles'


class UserOrganizationalAccess(models.Model):
    """
    Multi-scoped access for users.
    A user can have different roles at different levels.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='org_access'
    )

    # Top-level access
    access_groups = models.ManyToManyField(
        'companies.CompanyGroup',
        blank=True,
        related_name='members_via_group'
    )

    access_companies = models.ManyToManyField(
        'companies.Company',
        blank=True,
        related_name='members_via_company'
    )

    access_branches = models.ManyToManyField(
        'companies.Branch',
        blank=True,
        related_name='members_via_branch'
    )

    access_departments = models.ManyToManyField(
        'companies.Department',
        blank=True,
        related_name='members_via_department'
    )

    # Default/primary context for UX
    primary_group = models.ForeignKey(
        'companies.CompanyGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text='Default group on login'
    )

    primary_company = models.ForeignKey(
        'companies.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text='Default company on login'
    )

    primary_branch = models.ForeignKey(
        'companies.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text='Default branch on login (if applicable)'
    )

    primary_department = models.ForeignKey(
        'companies.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text='Default department on login (if applicable)'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_organizational_access'
        verbose_name = 'User Organizational Access'
        verbose_name_plural = 'User Organizational Access'

    def __str__(self):
        return f"{self.user.username} - Organizational Access"
