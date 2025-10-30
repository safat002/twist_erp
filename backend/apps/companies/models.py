


from django.db import models

from django.core.validators import RegexValidator



class CompanyGroup(models.Model):

    """

    A group of companies that can transact with each other.

    This is the tenancy boundary.

    """

    name = models.CharField(max_length=255, unique=True)

    db_name = models.CharField(max_length=255, unique=True, help_text="Physical Postgres database identifier")

    industry_pack_type = models.CharField(max_length=50, blank=True)

    supports_intercompany = models.BooleanField(default=False)

    status = models.CharField(max_length=20, default='active')

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)



    class Meta:

        verbose_name_plural = "Company Groups"

        ordering = ['name']



    def __str__(self):

        return self.name



class Company(models.Model):

    """

    Company/Legal Entity Master

    """

    company_group = models.ForeignKey(CompanyGroup, on_delete=models.PROTECT, related_name='companies')

    code = models.CharField(

        max_length=10,

        unique=True,

        validators=[RegexValidator(r'^[A-Z0-9]+$')],

        help_text="Unique company code"

    )

    name = models.CharField(max_length=255)

    legal_name = models.CharField(max_length=255)

    # Financial Settings

    currency_code = models.CharField(max_length=3, default='BDT')

    fiscal_year_start = models.DateField()

    # Tax & Legal

    tax_id = models.CharField(max_length=50, unique=True)

    registration_number = models.CharField(max_length=100)

    # Configuration

    settings = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)



    class Meta:

        verbose_name_plural = "Companies"

        ordering = ['code']



    def __str__(self):

        return f"{self.code} - {self.name}"





class InterCompanyLink(models.Model):

    """

    Links mirrored AR/AP or inventory movements between companies within the same CompanyGroup.

    """

    company_group = models.ForeignKey(CompanyGroup, on_delete=models.CASCADE, related_name='inter_company_links')

    initiating_company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='initiated_links')

    counterparty_company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='counterparty_links')

    source_entity = models.CharField(max_length=50, help_text="e.g., invoice, stock_transfer")

    source_record_id = models.CharField(max_length=100, help_text="ID of the record in the initiating company")

    status = models.CharField(max_length=20, default='pending') # pending, confirmed, canceled

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)



    class Meta:

        unique_together = [['initiating_company', 'source_entity', 'source_record_id']]

        verbose_name = "Inter-Company Link"

        verbose_name_plural = "Inter-Company Links"



    def __str__(self):

        return f"Link from {self.initiating_company.code} to {self.counterparty_company.code} for {self.source_entity}:{self.source_record_id}"





class GroupAccountMap(models.Model):

    """

    Maps local accounts to a consolidated chart and flags inter-company accounts for eliminations.

    This table is per CompanyGroup.

    """

    company_group = models.ForeignKey(CompanyGroup, on_delete=models.CASCADE, related_name='group_account_maps')

    local_account_code = models.CharField(max_length=50, help_text="Local Chart of Account code")

    consolidated_account_code = models.CharField(max_length=50, help_text="Consolidated Chart of Account code")

    is_intercompany_account = models.BooleanField(default=False, help_text="True if this account is used for inter-company transactions")

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)



    class Meta:

        unique_together = [['company_group', 'local_account_code']]

        verbose_name = "Group Account Map"

        verbose_name_plural = "Group Account Maps"



    def __str__(self):

        return f"{self.company_group.name}: {self.local_account_code} -> {self.consolidated_account_code}"
