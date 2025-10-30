
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

