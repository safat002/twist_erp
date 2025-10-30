from django.db import models

class Permission(models.Model):
    """
    Granular permissions for modules and actions
    """
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    module = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'permissions'

class Role(models.Model):
    """
    Role definitions with permission sets
    Can be company-specific or global
    """
    name = models.CharField(max_length=100)
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Null for global roles"
    )
    permissions = models.ManyToManyField(Permission)
    description = models.TextField(blank=True)
    is_system_role = models.BooleanField(default=False)

    class Meta:
        unique_together = [['name', 'company']]
        db_table = 'roles'

    def __str__(self):
        if self.company:
            return f"{self.name} ({self.company.code})"
        return self.name
