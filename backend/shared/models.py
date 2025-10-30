
from django.db import models
from django.contrib.auth import get_user_model

class CompanyAwareModel(models.Model):
    """
    Abstract base model that adds company isolation
    to all transactional data
    """
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        db_index=True,
        help_text="Company this record belongs to"
    )
    company_group = models.ForeignKey(
        'companies.CompanyGroup',
        on_delete=models.PROTECT,
        db_index=True,
        help_text="Company group this record belongs to"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Validate company access
        if not self.company_id:
            raise ValueError("Company must be specified")
        if not self.company_group_id:
            # Auto-populate company_group from company if not provided
            self.company_group = self.company.company_group
        super().save(*args, **kwargs)