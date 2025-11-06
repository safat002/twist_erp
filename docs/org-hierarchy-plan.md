# Twist ERP: Organizational Hierarchy Implementation Plan
## Group → Company → Branch → Department Architecture

---

## Executive Summary

This document provides a complete technical and functional specification for implementing the organizational hierarchy in Twist ERP with four-level nesting: **Group → Company → Branch (optional) → Department**. This structure enables complex enterprise organizations, multi-entity holdings, and decentralized operations while maintaining data integrity and audit trails.

---

## 1. Organizational Hierarchy Architecture

### 1.1 Hierarchy Overview

```
CompanyGroup (Holding/Conglomerate)
    ├── Company 1 (Legal Entity A)
    │   ├── Branch 1 (Location/Division) [Optional]
    │   │   ├── Department 1
    │   │   ├── Department 2
    │   │   └── Department 3
    │   ├── Branch 2 (Location/Division)
    │   │   └── Department 1
    │   └── [If no branches] → Department 1 (Direct)
    ├── Company 2 (Legal Entity B)
    │   ├── Department 1 (Direct, no branches)
    │   └── Department 2
    └── Company 3
        ├── Branch 1
        │   └── Department 1
```

### 1.2 Design Principles

| Principle | Implementation |
|-----------|-----------------|
| **Flexibility** | Branches are optional; departments can attach directly to company if no branches exist |
| **Hierarchy** | Each level has clear parent-child relationships with cascade rules |
| **Multi-tenancy** | Each company is independently scoped; users see only their company's data by default |
| **Segregation** | Data isolation at company and branch level; department is logical grouping only |
| **Auditability** | Every organizational change is tracked with who/what/when/why |
| **Performance** | Materialized paths and denormalized lookups for fast permission checks |

---

## 2. Database Schema Design

### 2.1 CompanyGroup Model

```python
class CompanyGroup(models.Model):
    """
    Top-level holding/conglomerate entity.
    Represents a group of companies, often for:
    - Holding companies with subsidiaries
    - Multi-entity consortiums
    - NGO umbrellas with program offices
    """
    # Identifiers
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    
    # Descriptors
    group_type = models.CharField(
        max_length=50,
        choices=[
            ('holding', 'Holding Company'),
            ('consortium', 'Consortium/Association'),
            ('ngo_umbrella', 'NGO Umbrella Organization'),
            ('franchise', 'Franchise Network'),
            ('other', 'Other'),
        ],
        default='holding'
    )
    description = models.TextField(blank=True, null=True)
    
    # Configuration
    base_currency = models.CharField(max_length=3, default='USD')
    fiscal_year_end_month = models.IntegerField(default=12)  # 1-12
    
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
        editable=False,  # Auto-computed
        help_text='Path for hierarchy: 1/2/3'
    )
    
    # Governance
    owner_user = models.ForeignKey(
        'auth.User',
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
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_groups',
        editable=False
    )
    
    class Meta:
        db_table = 'company_group'
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['parent_group', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def save(self, *args, **kwargs):
        # Auto-compute hierarchy path
        self.hierarchy_path = self._compute_hierarchy_path()
        super().save(*args, **kwargs)
    
    def _compute_hierarchy_path(self):
        """Build path by traversing parent chain."""
        if not self.parent_group:
            return str(self.id)
        return f"{self.parent_group.hierarchy_path}/{self.id}"
```

### 2.2 Company Model (Enhanced)

```python
class Company(models.Model):
    """
    Legal business entity. Each company has:
    - Independent chart of accounts
    - Separate legal compliance requirements
    - Optional branch layer
    - Users with company-scoped access
    """
    # Identifiers
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    
    # Hierarchy
    company_group = models.ForeignKey(
        CompanyGroup,
        on_delete=models.CASCADE,
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
    base_currency = models.CharField(max_length=3, default='USD')
    fiscal_year_start_date = models.DateField()
    fiscal_year_end_date = models.DateField()
    
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
    
    # Legal & Tax
    registration_number = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    legal_address = models.TextField()
    registration_country = models.CharField(max_length=100, blank=True)
    
    # Contact
    owner_user = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_companies'
    )
    company_admin_user = models.ForeignKey(
        'auth.User',
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
    
    # Status & Features
    is_active = models.BooleanField(default=True)
    is_consolidation_enabled = models.BooleanField(default=True)
    feature_flags = models.JSONField(default=dict, blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_companies',
        editable=False
    )
    
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'company'
        unique_together = [['company_group', 'code']]
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
        return CostCenter.objects.filter(company=self)
```

### 2.3 Branch Model (Optional Layer)

```python
class Branch(models.Model):
    """
    Optional intermediate level between Company and Department.
    Use when company has multiple locations, factories, retail outlets, etc.
    """
    # Identifiers
    id = models.AutoField(primary_key=True)
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
        'auth.User',
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
    warehouse_code = models.CharField(max_length=20, blank=True, unique=True)
    
    # Operations
    is_active = models.BooleanField(default=True)
    operational_start_date = models.DateField(null=True, blank=True)
    operational_end_date = models.DateField(null=True, blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_branches',
        editable=False
    )
    
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'branch'
        unique_together = [['company', 'code']]
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['branch_type']),
        ]
    
    def __str__(self):
        return f"{self.company.code}/{self.code} - {self.name}"
    
    def get_all_departments(self):
        """Get all departments under this branch."""
        return Department.objects.filter(branch=self)
```

### 2.4 Department Model (Enhanced)

```python
class Department(models.Model):
    """
    Functional or operational grouping.
    Can belong to:
    1. A specific branch (if branch structure is used)
    2. Directly to company (if no branch layer)
    """
    # Identifiers
    id = models.AutoField(primary_key=True)
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
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_departments'
    )
    deputy_head = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deputy_headed_departments'
    )
    
    # Staff Assignment
    employees = models.ManyToManyField(
        'auth.User',
        through='DepartmentMembership',
        related_name='departments',
        blank=True
    )
    
    # Budget & Cost Allocation
    cost_center_code = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text='Associated cost center if exists'
    )
    default_cost_center = models.ForeignKey(
        'CostCenter',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='departments'
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
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_departments',
        editable=False
    )
    
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'department'
        unique_together = [['company', 'code']]
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
```

### 2.5 DepartmentMembership Model

```python
class DepartmentMembership(models.Model):
    """
    Link users (employees) to departments with roles and status.
    """
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
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
```

### 2.6 CostCenter Model (Enhanced)

```python
class CostCenter(models.Model):
    """
    Cost tracking entity. Can be tied to department, branch, or company level.
    """
    # Identifiers
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    
    # Hierarchy
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='cost_centers')
    
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cost_centers'
    )
    
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cost_centers',
        help_text='Optional link to department'
    )
    
    parent_cost_center = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_cost_centers'
    )
    
    # Type
    cost_center_type = models.CharField(
        max_length=50,
        choices=[
            ('department', 'Department'),
            ('branch', 'Branch'),
            ('project', 'Project'),
            ('program', 'Program'),
            ('production_line', 'Production Line'),
        ],
        default='department'
    )
    
    # Owner
    owner = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_cost_centers'
    )
    
    deputy_owner = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deputy_owned_cost_centers'
    )
    
    # Users allowed to enter budget lines
    budget_entry_users = models.ManyToManyField(
        'auth.User',
        related_name='budget_entry_cost_centers',
        blank=True
    )
    
    # Configuration
    budget_threshold_percent = models.IntegerField(default=90)
    
    is_active = models.BooleanField(default=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cost_center'
        unique_together = [['company', 'code']]
        indexes = [
            models.Index(fields=['company', 'branch', 'department']),
        ]
```

---

## 3. Permission & Access Control Model

### 3.1 Organizational Scope-Based Permissions

```python
class OrganizationalScope:
    """
    Defines access boundary for a user.
    """
    LEVEL_CHOICES = [
        ('group', 'Company Group'),
        ('company', 'Single Company'),
        ('branch', 'Branch/Location'),
        ('department', 'Department'),
        ('cost_center', 'Cost Center'),
    ]

class UserOrganizationalAccess(models.Model):
    """
    Multi-scoped access for users.
    A user can have different roles at different levels.
    """
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='org_access')
    
    # Top-level access
    access_groups = models.ManyToManyField(
        CompanyGroup,
        blank=True,
        related_name='members_via_group'
    )
    
    access_companies = models.ManyToManyField(
        Company,
        blank=True,
        related_name='members_via_company'
    )
    
    access_branches = models.ManyToManyField(
        Branch,
        blank=True,
        related_name='members_via_branch'
    )
    
    access_departments = models.ManyToManyField(
        Department,
        blank=True,
        related_name='members_via_department'
    )
    
    # Default/primary context for UX
    primary_group = models.ForeignKey(
        CompanyGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text='Default group on login'
    )
    
    primary_company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text='Default company on login'
    )
    
    primary_branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text='Default branch on login (if applicable)'
    )
    
    primary_department = models.ForeignKey(
        Department,
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
```

### 3.2 Permission Middleware

```python
class OrganizationalScopeMiddleware:
    """
    Middleware to inject organizational context into every request.
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Extract org context from headers/session
            company_id = request.headers.get('X-Company-ID') or request.session.get('current_company_id')
            branch_id = request.headers.get('X-Branch-ID') or request.session.get('current_branch_id')
            department_id = request.headers.get('X-Department-ID') or request.session.get('current_department_id')
            
            # Fall back to user's primary context
            if not company_id:
                org_access = getattr(request.user, 'org_access', None)
                if org_access:
                    company_id = org_access.primary_company_id
                    branch_id = org_access.primary_branch_id
                    department_id = org_access.primary_department_id
            
            # Validate user has access to selected context
            if company_id:
                user_companies = request.user.userorganizationalacc
ess.access_companies.values_list('id', flat=True)
                if company_id not in user_companies:
                    raise PermissionDenied("User does not have access to this company.")
            
            # Inject into request
            request.current_company_id = company_id
            request.current_branch_id = branch_id
            request.current_department_id = department_id
            
            # Load objects for convenience
            if company_id:
                request.current_company = Company.objects.get(id=company_id)
            if branch_id:
                request.current_branch = Branch.objects.get(id=branch_id)
            if department_id:
                request.current_department = Department.objects.get(id=department_id)
        
        response = self.get_response(request)
        return response
```

### 3.3 Queryset Filtering by Organizational Scope

```python
class OrganizationallyScopedQuerySet(models.QuerySet):
    """
    Auto-filters querysets by current user's organizational access.
    """
    def for_user(self, user):
        """Filter by user's accessible companies."""
        if not user.is_authenticated:
            return self.none()
        
        org_access = user.org_access if hasattr(user, 'org_access') else None
        if not org_access:
            return self.none()
        
        # Get accessible company IDs
        accessible_company_ids = org_access.access_companies.values_list('id', flat=True)
        return self.filter(company__in=accessible_company_ids)

class OrganizationallyScopedModel(models.Model):
    """Base class for models that need organizational scoping."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    
    objects = OrganizationallyScopedQuerySet.as_manager()
    
    class Meta:
        abstract = True
```

---

## 4. Functional Specifications

### 4.1 Company & Branch Management Module

#### Creation Workflow

```
Admin → Create Company Group
         ↓
    Create Company (under Group)
         ↓
    [Optional] Create Branches (under Company)
         ↓
    Create Departments (under Branch or Company)
         ↓
    Assign Users & Permissions
```

#### Key Operations

| Operation | Roles | Constraints |
|-----------|-------|------------|
| Create Company Group | Super Admin | - |
| Create Company | Group Admin | Must belong to a group |
| Create Branch | Company Admin | Only if `requires_branch_structure=True` |
| Create Department | Company/Branch Admin | Validates parent structure |
| Assign Users | Department Head, Admin | User must have company access |
| Deactivate Department | Company Admin | Cannot deactivate if active children exist |

#### Business Rules

1. **Uniqueness:** Company code is unique within its group; Branch code is unique within company; Department code is unique within company.
2. **Cascade Rules:** Deleting a company cascades to branches, departments, and cost centers.
3. **Activation:** Deactivating parent (company/branch) automatically cascades to children.
4. **Budget Isolation:** Budgets are scoped to department or cost center, not branch/company directly.

### 4.2 Department-specific Features

#### Assignment Scenarios

| Scenario | Structure | Implementation |
|----------|-----------|-----------------|
| Single-location small company | Company → Department (no branch) | `requires_branch_structure=False`, department.branch=Null |
| Multi-location factory | Company → Factory Branch → Departments | `requires_branch_structure=True`, each department.branch set |
| Hybrid structure | Company → Some branches + Direct depts | Custom validation: some depts.branch set, some null |
| Hierarchical depts | Any level → Sub-departments | department.parent_department set |

#### Validation Logic

```python
def validate_department_structure(company, branch=None, department=None):
    """
    Validate that department structure matches company requirements.
    """
    if company.requires_branch_structure:
        # All departments MUST have a branch
        if not branch:
            raise ValidationError("Branch structure required; branch field is mandatory.")
        if branch.company != company:
            raise ValidationError("Branch must belong to same company.")
    else:
        # Departments can be direct (branch=null) or under optional branches
        if branch:
            if branch.company != company:
                raise ValidationError("Branch must belong to same company.")
    
    return True
```

### 4.3 Multi-Company User Access

#### Scenario: User with Access to Multiple Companies

```
User: Alice (Finance Manager)
├── Company A (Primary)
│   ├── Role: Finance Manager
│   ├── Access: All departments
│   └── Default on login
├── Company B (Secondary)
│   ├── Role: Auditor
│   └── Access: Read-only to accounting dept
└── Company C (Read-only)
    └── Role: Viewer
    └── Access: Limited dashboard

On login:
- Alice defaults to Company A
- Can switch to B, C via UI selector
- Dashboard/data automatically filters by selected company
```

#### UI Component: Company/Branch/Department Selector

```javascript
// Frontend: CompanyContextSelector.jsx
const [selectedGroup, setSelectedGroup] = useState(userOrg.primaryGroup);
const [selectedCompany, setSelectedCompany] = useState(userOrg.primaryCompany);
const [selectedBranch, setSelectedBranch] = useState(userOrg.primaryBranch);
const [selectedDept, setSelectedDept] = useState(userOrg.primaryDepartment);

const handleCompanyChange = (companyId) => {
    setSelectedCompany(companyId);
    // Fetch available branches if company uses branch structure
    if (getCompany(companyId).requires_branch_structure) {
        fetchBranches(companyId);
    } else {
        setSelectedBranch(null); // Not applicable
    }
    // Save to session/header for API calls
    sessionStorage.setItem('current_company_id', companyId);
};
```

---

## 5. API Design

### 5.1 RESTful Endpoints

```
# Company Group Management
GET    /api/v1/company-groups
POST   /api/v1/company-groups
GET    /api/v1/company-groups/{id}
PUT    /api/v1/company-groups/{id}
DELETE /api/v1/company-groups/{id}

# Companies (scoped to group)
GET    /api/v1/company-groups/{group_id}/companies
POST   /api/v1/company-groups/{group_id}/companies
GET    /api/v1/companies/{id}
PUT    /api/v1/companies/{id}
DELETE /api/v1/companies/{id}

# Branches (scoped to company)
GET    /api/v1/companies/{company_id}/branches
POST   /api/v1/companies/{company_id}/branches
GET    /api/v1/branches/{id}
PUT    /api/v1/branches/{id}
DELETE /api/v1/branches/{id}

# Departments (scoped to company and optionally branch)
GET    /api/v1/companies/{company_id}/departments
GET    /api/v1/companies/{company_id}/branches/{branch_id}/departments
POST   /api/v1/companies/{company_id}/departments
GET    /api/v1/departments/{id}
PUT    /api/v1/departments/{id}
DELETE /api/v1/departments/{id}

# Department Members
GET    /api/v1/departments/{dept_id}/members
POST   /api/v1/departments/{dept_id}/members
DELETE /api/v1/departments/{dept_id}/members/{user_id}

# User Organizational Access
GET    /api/v1/users/{user_id}/organizational-access
PUT    /api/v1/users/{user_id}/organizational-access

# Current Context (for UI)
GET    /api/v1/me/organizational-context
PUT    /api/v1/me/organizational-context (set current company/branch/dept)
```

### 5.2 Example: Creating a Department

```bash
POST /api/v1/companies/{company_id}/departments

Request Body:
{
    "code": "FIN",
    "name": "Finance",
    "department_type": "finance",
    "branch_id": 5,  // null if company doesn't use branches
    "department_head_id": 12,
    "deputy_head_id": 13,
    "budget_threshold_percent": 85,
    "metadata": {
        "cost_center_type": "department",
        "internal_name": "Finance & Accounts"
    }
}

Response (201 Created):
{
    "id": 42,
    "code": "FIN",
    "name": "Finance",
    "company_id": 1,
    "branch_id": 5,
    "branch_name": "Mumbai Factory",
    "department_type": "finance",
    "department_head": {
        "id": 12,
        "name": "Rajesh Kumar"
    },
    "deputy_head": {
        "id": 13,
        "name": "Priya Singh"
    },
    "hierarchy_path": "ACME-IND/MUM/FIN",
    "is_active": true,
    "created_at": "2025-11-04T12:30:00Z"
}
```

---

## 6. Integrations with Other Modules

### 6.1 Budget Module Integration

```
Budget Structure:
├── Declared Budget (Company-level, no CC specified)
└── Cost Center Budgets
    └── Each CC is tied to a Department or Branch
    └── Entry users: department members with "budget_entry" role

Budget Entry Flow:
1. User selects company (middleware → auto-filters to user's companies)
2. User selects declared budget (shows those with active entry periods)
3. System loads cost centers → maps to departments → filters by user access
4. User enters budget lines for their department's CC
5. Approval chain: Department Head → CC Owner → Budget Module Owner
```

### 6.2 Finance Module Integration

```
Chart of Accounts (COA):
├── Company A COA (independent)
└── Cost Center linkage
    └── Each CC belongs to a Department/Branch
    └── GL posting tags department for internal control reporting

Inter-Company Transactions:
└── Company A sells to Company B
    └── Sale invoice posted in A (AR account)
    └── Purchase entry auto-created in B (AP account)
    └── Consolidation reports eliminate inter-company balances
```

### 6.3 HR Module Integration

```
Employee & Department:
├── Employee linked to Department via DepartmentMembership
├── Employee.company = Department.company (cascaded)
├── Payroll scoped to company
└── Reports filtered by employee's department

Leave Approval:
└── Department Head auto-approved as first approver
```

### 6.4 Inventory Module Integration

```
Warehouse-Branch Linkage:
├── Warehouse → Branch mapping (branch.warehouse_code)
├── Stock movements tagged by warehouse → branch → company
└── Consolidation: Inventory visibility by branch/company

Stock Transfer:
└── Inter-branch transfer: 
    └── Warehouse A (Branch 1) → Warehouse B (Branch 2)
    └── Automatic GL posting if company enables inter-branch costing
```

---

## 7. Data Migration & Hierarchy Setup

### 7.1 Initial Data Load

```python
# Step 1: Create Company Group
group = CompanyGroup.objects.create(
    code="ACME-GROUP",
    name="ACME Holdings Ltd",
    group_type="holding",
    base_currency="USD"
)

# Step 2: Create Companies
company_a = Company.objects.create(
    company_group=group,
    code="ACME-US",
    name="ACME USA Inc.",
    fiscal_year_start_date="2024-01-01",
    fiscal_year_end_date="2024-12-31",
    requires_branch_structure=False
)

company_b = Company.objects.create(
    company_group=group,
    code="ACME-IND",
    name="ACME India Pvt Ltd",
    fiscal_year_start_date="2024-04-01",
    fiscal_year_end_date="2025-03-31",
    requires_branch_structure=True  # Requires branch layer
)

# Step 3: Create Branches (for Company B which requires them)
branch_mumbai = Branch.objects.create(
    company=company_b,
    code="MUM",
    name="Mumbai Factory",
    branch_type="factory",
    location="Pune Road, Mumbai"
)

branch_delhi = Branch.objects.create(
    company=company_b,
    code="DEL",
    name="Delhi Distribution Center",
    branch_type="distribution",
    location="Gurgaon, Delhi"
)

# Step 4: Create Departments
# For Company A (no branches)
dept_finance_a = Department.objects.create(
    company=company_a,
    branch=None,  # Direct to company
    code="FIN",
    name="Finance",
    department_type="finance"
)

# For Company B (under branches)
dept_ops_mumbai = Department.objects.create(
    company=company_b,
    branch=branch_mumbai,
    code="OPS",
    name="Operations",
    department_type="operations"
)

dept_warehouse_delhi = Department.objects.create(
    company=company_b,
    branch=branch_delhi,
    code="WH",
    name="Warehouse",
    department_type="warehouse"
)

# Step 5: Assign Users
alice = User.objects.get(username='alice')
org_access, created = UserOrganizationalAccess.objects.get_or_create(user=alice)
org_access.access_companies.set([company_a, company_b])
org_access.primary_company = company_a
org_access.save()

# Step 6: Add user to department
DepartmentMembership.objects.create(
    user=alice,
    department=dept_finance_a,
    role='head'
)
```

### 7.2 Migration from Legacy System

```python
# From Old Flat Structure to New Hierarchy:
# Old: company_id, department_name
# New: company_id, branch_id, department_id

def migrate_legacy_data(legacy_records):
    """
    Transform legacy flat data into hierarchical structure.
    """
    for record in legacy_records:
        # Map old company ID to new Company object
        company = Company.objects.get(legacy_id=record['company_id'])
        
        # Create branch if needed (grouped by location)
        branch = None
        if company.requires_branch_structure:
            branch_name = record.get('location')
            branch, _ = Branch.objects.get_or_create(
                company=company,
                name=branch_name,
                defaults={'code': generate_branch_code()}
            )
        
        # Create or retrieve department
        department, created = Department.objects.get_or_create(
            company=company,
            branch=branch,
            code=record['dept_code'],
            defaults={'name': record['dept_name']}
        )
        
        # Update transactional records to point to new department
        update_related_records(record['old_id'], department)
```

---

## 8. Implementation Phases

### Phase 1: Data Models & Database (Week 1-2)
- [ ] Define CompanyGroup, Company, Branch, Department models
- [ ] Create DepartmentMembership & CostCenter linking
- [ ] Run migrations
- [ ] Set up indexes and foreign keys

### Phase 2: APIs & Backend (Week 3-4)
- [ ] Implement REST endpoints for hierarchy
- [ ] Middleware for organizational scoping
- [ ] Permission checks & validation
- [ ] API tests

### Phase 3: Frontend Navigation (Week 5)
- [ ] Company/Branch/Department selector UI
- [ ] Context switching logic
- [ ] Session/header management
- [ ] Navigation menu reflecting hierarchy

### Phase 4: Integration with Existing Modules (Week 6-7)
- [ ] Update Budget module to use department hierarchy
- [ ] Update Finance module for multi-company GL
- [ ] Update HR module for department linking
- [ ] Update Inventory for branch/warehouse linking

### Phase 5: Testing & Documentation (Week 8)
- [ ] End-to-end testing (create hierarchy → assign users → perform operations)
- [ ] Data migration scripts for legacy systems
- [ ] Admin documentation

---

## 9. Configuration Reference

### 9.1 Company Settings

```python
COMPANY_CONFIGURATIONS = {
    'ACME-IND': {
        'requires_branch_structure': True,  # Enforce branch layer
        'enable_inter_company_transactions': True,
        'allow_direct_departments': False,  # No depts outside branches
        'budget_entry_requires_approval': True,
        'consolidated_reporting_enabled': True,
    },
    'ACME-US': {
        'requires_branch_structure': False,  # Optional branches
        'allow_direct_departments': True,  # Depts can be direct to company
        'budget_entry_requires_approval': False,
        'consolidated_reporting_enabled': False,
    },
}
```

### 9.2 Permission Templates by Role

```python
ROLE_PERMISSIONS = {
    'group_admin': [
        'view_all_companies',
        'manage_companies',
        'manage_inter_company_transactions',
        'view_consolidated_reports',
    ],
    'company_admin': [
        'view_company',
        'manage_branches',
        'manage_departments',
        'manage_users_in_company',
        'manage_cost_centers',
        'manage_budgets_in_company',
    ],
    'branch_head': [
        'view_branch',
        'manage_departments_in_branch',
        'manage_users_in_branch',
    ],
    'department_head': [
        'view_department',
        'manage_users_in_department',
        'approve_department_budgets',
        'access_department_reports',
    ],
}
```

---

## 10. Key Benefits of This Architecture

| Benefit | Implementation |
|---------|-----------------|
| **Scalability** | Supports from single company to complex multi-entity groups |
| **Flexibility** | Branches are optional; departments can attach at multiple levels |
| **Data Isolation** | Company-scoped data at API & middleware level |
| **Audit Trail** | Every hierarchy change tracked with user/timestamp |
| **Multi-tenancy** | Users can access multiple companies with role-based permissions |
| **Ease of Migration** | Clear mapping from legacy flat structures to new hierarchy |
| **Performance** | Indexed queries, materialized paths for fast lookups |
| **Compliance** | Independent configurations per company for tax/regulatory rules |

---

## 11. Conclusion

This **four-level organizational hierarchy (Group → Company → Branch → Department)** provides the flexibility required for SMEs with complex structures while maintaining security, auditability, and ease of use. The design supports both simple single-company deployments and sophisticated multi-entity holding company scenarios.

The middleware-based organizational scoping ensures data isolation at every layer, and the optional branch layer allows companies to adopt the structure that fits their operations without unnecessary complexity.
