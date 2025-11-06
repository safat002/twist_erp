


from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.conf import settings as django_settings
from django.utils import timezone
from django.utils.text import slugify


class CompanyCategory(models.TextChoices):
    """Industry categories for default master data assignment"""
    MANUFACTURING = 'MANUFACTURING', 'Manufacturing'
    TRADING = 'TRADING', 'Trading/Wholesale'
    RETAIL = 'RETAIL', 'Retail'
    SERVICE = 'SERVICE', 'Service Provider'
    CONSULTING = 'CONSULTING', 'Consulting'
    NGO = 'NGO', 'Non-Profit/NGO'
    HEALTHCARE = 'HEALTHCARE', 'Healthcare'
    EDUCATION = 'EDUCATION', 'Education'
    HOSPITALITY = 'HOSPITALITY', 'Hospitality/Hotel/Restaurant'
    CONSTRUCTION = 'CONSTRUCTION', 'Construction/Real Estate'
    AGRICULTURE = 'AGRICULTURE', 'Agriculture/Farming'
    TECHNOLOGY = 'TECHNOLOGY', 'Technology/Software'
    TRANSPORTATION = 'TRANSPORTATION', 'Transportation/Logistics'
    FINANCE = 'FINANCE', 'Financial Services'
    GOVERNMENT = 'GOVERNMENT', 'Government/Public Sector'



class CompanyGroup(models.Model):
    """
    Top-level holding/conglomerate entity.
    Represents a group of companies, often for:
    - Holding companies with subsidiaries
    - Multi-entity consortiums
    - NGO umbrellas with program offices
    """
    # Identifiers
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255, unique=True)

    # Descriptors
    group_type = models.CharField(
        max_length=50,
        choices=[
            ('holding', 'Holding Company'),
            ('consortium', 'Consortium/Association'),
            ('ngo_umbrella', 'NGO Umbrella Organization'),
            ('franchise', 'Franchise Network'),
            ('group_of_companies', 'Group of Companies'),
            ('other', 'Other'),
        ],
        default='holding'
    )
    description = models.TextField(blank=True, null=True)

    # Legacy fields (keep for backward compatibility)
    db_name = models.CharField(max_length=255, unique=True, null=True, blank=True,
                               help_text="Physical Postgres database identifier (legacy)")
    industry_pack_type = models.CharField(max_length=50, blank=True)
    supports_intercompany = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default='active')

    # Configuration
    # Common ISO 4217 currency codes supported by system
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('BDT', 'Bangladeshi Taka'),
        ('INR', 'Indian Rupee'),
        ('PKR', 'Pakistani Rupee'),
        ('LKR', 'Sri Lankan Rupee'),
        ('CNY', 'Chinese Yuan'),
        ('JPY', 'Japanese Yen'),
        ('AUD', 'Australian Dollar'),
        ('CAD', 'Canadian Dollar'),
        ('SGD', 'Singapore Dollar'),
        ('MYR', 'Malaysian Ringgit'),
        ('THB', 'Thai Baht'),
        ('IDR', 'Indonesian Rupiah'),
        ('PHP', 'Philippine Peso'),
        ('AED', 'UAE Dirham'),
        ('SAR', 'Saudi Riyal'),
        ('KWD', 'Kuwaiti Dinar'),
        ('OMR', 'Omani Rial'),
        ('QAR', 'Qatari Riyal'),
        ('ZAR', 'South African Rand'),
        ('NGN', 'Nigerian Naira'),
        ('GHS', 'Ghanaian Cedi'),
        ('KES', 'Kenyan Shilling'),
    ]
    base_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')

    # Month choices for user-friendly selection
    MONTH_CHOICES = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'),
        (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]
    fiscal_year_end_month = models.IntegerField(default=12, choices=MONTH_CHOICES)  # 1-12

    # Hierarchy & Consolidation
    parent_group = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_groups'
    )
    hierarchy_path = models.CharField(
        max_length=500,
        editable=False,
        blank=True,
        help_text='Path for hierarchy: 1/2/3'
    )

    # Governance
    owner_user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_groups'
    )
    owner_name = models.CharField(max_length=255, blank=True)
    owner_email = models.EmailField(blank=True)
    owner_phone = models.CharField(max_length=20, blank=True)

    # Compliance & Metadata
    registration_number = models.CharField(max_length=100, blank=True)
    registration_authority = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    legal_address = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    is_consolidated = models.BooleanField(
        default=True,
        help_text='Include in group consolidation reports'
    )

    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_groups',
        editable=False
    )

    class Meta:
        db_table = 'company_group'
        verbose_name_plural = "Company Groups"
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['parent_group', 'is_active']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}" if self.code else self.name

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        # Save first to get primary key for deterministic code/db_name
        super().save(*args, **kwargs)

        updated_fields = []

        # Auto-generate code using a consistent pattern if not provided
        if is_new and not self.code:
            year = timezone.now().strftime('%Y')
            self.code = f"CG-{year}-{self.id:05d}"
            updated_fields.append('code')

        # Auto-generate db_name if not provided
        if is_new and not self.db_name:
            base = slugify(self.name) or 'tenant'
            candidate = f"cg_{base}"
            # Ensure uniqueness; if exists, append id suffix
            if CompanyGroup.objects.exclude(pk=self.pk).filter(db_name=candidate).exists():
                candidate = f"cg_{base}_{self.id}"
            self.db_name = candidate
            updated_fields.append('db_name')

        # Auto-compute hierarchy path
        new_path = self._compute_hierarchy_path()
        if self.hierarchy_path != new_path:
            self.hierarchy_path = new_path
            updated_fields.append('hierarchy_path')

        if updated_fields:
            super().save(update_fields=updated_fields)

    def _compute_hierarchy_path(self):
        """Build path by traversing parent chain."""
        if not self.parent_group:
            return str(self.id)
        return f"{self.parent_group.hierarchy_path}/{self.id}"



class Company(models.Model):
    """
    Legal business entity. Each company has:
    - Independent chart of accounts
    - Separate legal compliance requirements
    - Optional branch layer
    - Users with company-scoped access
    """
    # Identifiers
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^[A-Z0-9]+$')],
        help_text="Unique company code"
    )
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)

    # Hierarchy
    company_group = models.ForeignKey(
        CompanyGroup,
        on_delete=models.PROTECT,
        related_name='companies',
        help_text='Parent group (optional for standalone companies)'
    )
    parent_company = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subsidiary_companies'
    )

    # Financial & Compliance
    # Currency selections (ISO 4217) for consistency with CompanyGroup
    COMPANY_CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('BDT', 'Bangladeshi Taka'),
        ('INR', 'Indian Rupee'),
        ('PKR', 'Pakistani Rupee'),
        ('LKR', 'Sri Lankan Rupee'),
        ('CNY', 'Chinese Yuan'),
        ('JPY', 'Japanese Yen'),
        ('AUD', 'Australian Dollar'),
        ('CAD', 'Canadian Dollar'),
        ('SGD', 'Singapore Dollar'),
        ('MYR', 'Malaysian Ringgit'),
        ('THB', 'Thai Baht'),
        ('IDR', 'Indonesian Rupiah'),
        ('PHP', 'Philippine Peso'),
        ('AED', 'UAE Dirham'),
        ('SAR', 'Saudi Riyal'),
        ('KWD', 'Kuwaiti Dinar'),
        ('OMR', 'Omani Rial'),
        ('QAR', 'Qatari Riyal'),
        ('ZAR', 'South African Rand'),
        ('NGN', 'Nigerian Naira'),
        ('GHS', 'Ghanaian Cedi'),
        ('KES', 'Kenyan Shilling'),
    ]
    base_currency = models.CharField(max_length=3, default='USD', choices=COMPANY_CURRENCY_CHOICES)
    currency_code = models.CharField(max_length=3, default='BDT', choices=COMPANY_CURRENCY_CHOICES)
    fiscal_year_start = models.DateField(null=True, blank=True)
    fiscal_year_end_date = models.DateField(null=True, blank=True)

    company_type = models.CharField(
        max_length=50,
        choices=[
            ('subsidiary', 'Subsidiary'),
            ('division', 'Division'),
            ('branch_entity', 'Branch Entity'),
            ('joint_venture', 'Joint Venture'),
            ('independent', 'Independent'),
        ],
        default='independent'
    )

    # Industry classification for default master data
    industry_category = models.CharField(
        max_length=50,
        choices=CompanyCategory.choices,
        default=CompanyCategory.SERVICE,
        help_text='Industry category determines default Chart of Accounts and master data'
    )
    industry_sub_category = models.CharField(
        max_length=100,
        blank=True,
        help_text='More specific industry classification (e.g., "Textile Manufacturing")'
    )
    default_data_loaded = models.BooleanField(
        default=False,
        help_text='True if industry-specific default master data has been loaded'
    )
    default_data_loaded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When default master data was loaded'
    )

    # Legal & Tax
    registration_number = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    legal_address = models.TextField(blank=True)
    registration_country = models.CharField(max_length=100, blank=True)

    # Contact
    owner_user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_companies'
    )
    company_admin_user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_for_companies',
        help_text='Primary admin for this company'
    )

    # Configuration
    requires_branch_structure = models.BooleanField(
        default=False,
        help_text='If True, departments must be under branches; if False, departments attach directly'
    )
    enable_inter_company_transactions = models.BooleanField(default=True)
    business_type = models.CharField(max_length=50, blank=True, help_text='Business type derived from industry packs')

    # Status & Features
    is_active = models.BooleanField(default=True)
    is_consolidation_enabled = models.BooleanField(default=True)
    feature_flags = models.JSONField(default=dict, blank=True)
    settings = models.JSONField(default=dict, blank=True)  # Legacy field

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_companies',
        editable=False
    )

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'company'
        verbose_name_plural = "Companies"
        unique_together = [['company_group', 'code']]
        ordering = ['code']
        indexes = [
            models.Index(fields=['company_group', 'is_active']),
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_all_departments(self):
        """
        Returns all departments under this company.
        If branches exist, gets departments from all branches.
        If no branches, gets direct departments.
        """
        if self.requires_branch_structure:
            # Get all branches and their departments
            branches = self.branches.all()
            departments = Department.objects.filter(branch__in=branches)
        else:
            # Get direct departments with parent=company
            departments = Department.objects.filter(company=self, branch__isnull=True)
        return departments

    def get_all_cost_centers(self):
        """Get cost centers scoped to this company."""
        try:
            from apps.budgeting.models import CostCenter
            return CostCenter.objects.filter(company=self)
        except ImportError:
            return []


class Branch(models.Model):
    """
    Optional intermediate level between Company and Department.
    Use when company has multiple locations, factories, retail outlets, etc.
    """
    # Identifiers
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)

    # Hierarchy
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='branches',
        help_text='Parent company'
    )
    parent_branch = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_branches',
        help_text='For hierarchical branches if needed'
    )

    # Location & Configuration
    branch_type = models.CharField(
        max_length=50,
        choices=[
            ('headquarters', 'Headquarters'),
            ('factory', 'Factory/Manufacturing'),
            ('warehouse', 'Warehouse'),
            ('retail', 'Retail Store'),
            ('office', 'Office'),
            ('regional', 'Regional Office'),
            ('distribution', 'Distribution Center'),
            ('other', 'Other'),
        ],
        default='office'
    )

    # Geographic
    location = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Contact
    branch_head_user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_branches'
    )
    manager_name = models.CharField(max_length=255, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)

    # Configuration
    has_warehouse = models.BooleanField(default=False)
    warehouse_code = models.CharField(max_length=20, blank=True, null=True)

    # Operations
    is_active = models.BooleanField(default=True)
    operational_start_date = models.DateField(null=True, blank=True)
    operational_end_date = models.DateField(null=True, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_branches',
        editable=False
    )

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'branch'
        unique_together = [['company', 'code']]
        verbose_name_plural = "Branches"
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['branch_type']),
        ]

    def __str__(self):
        return f"{self.company.code}/{self.code} - {self.name}"

    def get_all_departments(self):
        """Get all departments under this branch."""
        return self.departments.all()


class Department(models.Model):
    """
    Functional or operational grouping.
    Can belong to:
    1. A specific branch (if branch structure is used)
    2. Directly to company (if no branch layer)
    """
    # Identifiers
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)

    # Hierarchy - Flexible Parent Assignment
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='direct_departments',
        help_text='Always scoped to a company'
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='departments',
        help_text='Null if department is directly under company (no branch layer)'
    )

    parent_department = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_departments',
        help_text='For hierarchical departments (e.g., Finance > Accounting > Payroll)'
    )

    # Descriptors
    department_type = models.CharField(
        max_length=50,
        choices=[
            ('finance', 'Finance'),
            ('operations', 'Operations'),
            ('sales', 'Sales'),
            ('marketing', 'Marketing'),
            ('hr', 'Human Resources'),
            ('production', 'Production'),
            ('warehouse', 'Warehouse'),
            ('it', 'IT/Systems'),
            ('admin', 'Administration'),
            ('quality', 'Quality Assurance'),
            ('legal', 'Legal'),
            ('strategy', 'Strategy'),
            ('procurement', 'Procurement'),
            ('logistics', 'Logistics'),
            ('other', 'Other'),
        ],
        blank=True
    )

    # Leadership
    department_head = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_departments'
    )
    deputy_head = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deputy_headed_departments'
    )

    # Staff Assignment
    employees = models.ManyToManyField(
        django_settings.AUTH_USER_MODEL,
        through='DepartmentMembership',
        related_name='departments',
        blank=True
    )

    # Budget & Cost Allocation
    cost_center_code = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Associated cost center if exists'
    )

    # Configuration
    budget_threshold_percent = models.IntegerField(default=90)
    requires_approval_threshold = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Transactions above this value require approval'
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_departments',
        editable=False
    )

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'department'
        unique_together = [['company', 'code']]
        verbose_name_plural = "Departments"
        indexes = [
            models.Index(fields=['company', 'branch', 'is_active']),
            models.Index(fields=['department_head']),
        ]

    def __str__(self):
        if self.branch:
            return f"{self.company.code}/{self.branch.code}/{self.code} - {self.name}"
        else:
            return f"{self.company.code}/{self.code} - {self.name}"

    def clean(self):
        """Validation: If company requires branch structure, branch must be set."""
        if self.company.requires_branch_structure and not self.branch:
            raise ValidationError(
                f"Company {self.company.name} requires branch structure. "
                "Branch field is mandatory."
            )
        if self.branch and self.branch.company != self.company:
            raise ValidationError("Branch must belong to the same company.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def get_hierarchy_path(self):
        """Return path like Company/Branch/Department or Company/Department."""
        if self.branch:
            return f"{self.company.code}/{self.branch.code}/{self.code}"
        else:
            return f"{self.company.code}/{self.code}"


class DepartmentMembership(models.Model):
    """
    Link users (employees) to departments with roles and status.
    """
    user = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    # Role within department
    role = models.CharField(
        max_length=100,
        choices=[
            ('head', 'Department Head'),
            ('deputy', 'Deputy Head'),
            ('manager', 'Manager'),
            ('senior_staff', 'Senior Staff'),
            ('staff', 'Staff'),
            ('intern', 'Intern'),
        ],
        default='staff'
    )

    # Assignment dates
    assigned_date = models.DateField(auto_now_add=True)
    departure_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Permissions override (optional)
    custom_permissions = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'department_membership'
        unique_together = [['user', 'department']]
        indexes = [
            models.Index(fields=['department', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.department.name} ({self.role})"


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
