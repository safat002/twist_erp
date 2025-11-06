from rest_framework import serializers
from .models import Company, CompanyGroup, Branch, Department, DepartmentMembership


# ============================================================================
# CompanyGroup Serializers
# ============================================================================

class CompanyGroupSerializer(serializers.ModelSerializer):
    """Full serializer for CompanyGroup with all fields."""
    child_groups_count = serializers.SerializerMethodField()
    companies_count = serializers.SerializerMethodField()
    owner_name_display = serializers.CharField(source='owner_user.get_full_name', read_only=True)

    class Meta:
        model = CompanyGroup
        fields = '__all__'
        read_only_fields = ['hierarchy_path', 'created_at', 'updated_at', 'created_by']

    def get_child_groups_count(self, obj):
        return obj.child_groups.count() if obj.pk else 0

    def get_companies_count(self, obj):
        return obj.companies.count() if obj.pk else 0

    def validate_base_currency(self, value: str) -> str:
        codes = {code for code, _ in getattr(CompanyGroup, 'CURRENCY_CHOICES', [])}
        if codes and value not in codes:
            raise serializers.ValidationError("Unsupported currency code.")
        return value

    def validate_industry_pack_type(self, value: str) -> str:
        if not value:
            return value
        # Build available pack list from metadata summaries
        try:
            from apps.metadata.models import MetadataDefinition
            packs = set()
            qs = MetadataDefinition.objects.filter(layer='INDUSTRY_PACK').values_list('summary', flat=True)
            for summary in qs:
                if isinstance(summary, dict):
                    p = summary.get('industry_pack') or summary.get('industry') or summary.get('pack')
                    if p:
                        packs.add(str(p))
            if packs and value not in packs:
                raise serializers.ValidationError("Unknown industry pack.")
        except Exception:
            # If metadata not available, accept provided value
            pass
        return value


class CompanyGroupListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    companies_count = serializers.IntegerField(source='companies.count', read_only=True)

    class Meta:
        model = CompanyGroup
        fields = ['id', 'code', 'name', 'group_type', 'is_active', 'companies_count', 'created_at']


class CompanyGroupMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for dropdowns/references."""
    class Meta:
        model = CompanyGroup
        fields = ['id', 'code', 'name']


# ============================================================================
# Company Serializers
# ============================================================================

class CompanySerializer(serializers.ModelSerializer):
    """Full serializer for Company with all fields."""
    company_group_name = serializers.CharField(source='company_group.name', read_only=True)
    parent_company_name = serializers.CharField(source='parent_company.name', read_only=True)
    branches_count = serializers.SerializerMethodField()
    owner_user_name = serializers.SerializerMethodField()
    company_admin_user_name = serializers.SerializerMethodField()
    departments_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by']

    def get_branches_count(self, obj):
        return obj.branches.count() if obj.pk else 0

    def get_departments_count(self, obj):
        return obj.direct_departments.count() if obj.pk else 0

    def get_owner_user_name(self, obj):
        try:
            return obj.owner_user.get_full_name() or obj.owner_user.username if obj.owner_user else None
        except Exception:
            return None

    def get_company_admin_user_name(self, obj):
        try:
            return obj.company_admin_user.get_full_name() or obj.company_admin_user.username if obj.company_admin_user else None
        except Exception:
            return None

    def validate(self, data):
        """Validate company data."""
        # Ensure fiscal year dates are consistent
        if data.get('fiscal_year_start') and data.get('fiscal_year_end_date'):
            if data['fiscal_year_start'] >= data['fiscal_year_end_date']:
                raise serializers.ValidationError({
                    'fiscal_year_end_date': 'Fiscal year end date must be after start date.'
                })
        return data


class CompanyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    company_group_name = serializers.CharField(source='company_group.name', read_only=True)
    branches_count = serializers.IntegerField(source='branches.count', read_only=True)

    class Meta:
        model = Company
        fields = [
            'id', 'code', 'name', 'legal_name', 'company_group', 'company_group_name',
            'base_currency', 'is_active', 'requires_branch_structure', 'branches_count', 'created_at'
        ]


class CompanyMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for dropdowns/references."""
    class Meta:
        model = Company
        fields = ['id', 'code', 'name']


# ============================================================================
# Branch Serializers
# ============================================================================

class BranchSerializer(serializers.ModelSerializer):
    """Full serializer for Branch with all fields."""
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_code = serializers.CharField(source='company.code', read_only=True)
    parent_branch_name = serializers.CharField(source='parent_branch.name', read_only=True)
    branch_head_name = serializers.CharField(source='branch_head_user.get_full_name', read_only=True)
    departments_count = serializers.SerializerMethodField()
    hierarchy_path = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by']

    def get_departments_count(self, obj):
        return obj.departments.count() if obj.pk else 0

    def get_hierarchy_path(self, obj):
        return f"{obj.company.code}/{obj.code}"

    def validate(self, data):
        """Validate branch data."""
        # Ensure branch code is unique within company
        company = data.get('company') or self.instance.company if self.instance else None
        code = data.get('code')

        if company and code:
            qs = Branch.objects.filter(company=company, code=code)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    'code': f'Branch with code "{code}" already exists in this company.'
                })
        return data


class BranchListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    company_name = serializers.CharField(source='company.name', read_only=True)
    departments_count = serializers.IntegerField(source='departments.count', read_only=True)

    class Meta:
        model = Branch
        fields = [
            'id', 'code', 'name', 'company', 'company_name', 'branch_type',
            'location', 'city', 'is_active', 'departments_count', 'created_at'
        ]


class BranchMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for dropdowns/references."""
    class Meta:
        model = Branch
        fields = ['id', 'code', 'name', 'branch_type']


# ============================================================================
# Department Serializers
# ============================================================================

class DepartmentSerializer(serializers.ModelSerializer):
    """Full serializer for Department with all fields."""
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_code = serializers.CharField(source='company.code', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    department_head_name = serializers.CharField(source='department_head.get_full_name', read_only=True)
    deputy_head_name = serializers.CharField(source='deputy_head.get_full_name', read_only=True)
    parent_department_name = serializers.CharField(source='parent_department.name', read_only=True)
    employees_count = serializers.SerializerMethodField()
    hierarchy_path = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by']

    def get_employees_count(self, obj):
        return obj.employees.filter(departmentmembership__is_active=True).count() if obj.pk else 0

    def get_hierarchy_path(self, obj):
        return obj.get_hierarchy_path()

    def validate(self, data):
        """Validate department data."""
        company = data.get('company') or (self.instance.company if self.instance else None)
        branch = data.get('branch')
        code = data.get('code')

        # Check if company requires branch structure
        if company and company.requires_branch_structure and not branch:
            raise serializers.ValidationError({
                'branch': f'Company "{company.name}" requires branch structure. Branch field is mandatory.'
            })

        # Ensure branch belongs to the same company
        if branch and company and branch.company_id != company.id:
            raise serializers.ValidationError({
                'branch': 'Branch must belong to the same company.'
            })

        # Ensure department code is unique within company
        if company and code:
            qs = Department.objects.filter(company=company, code=code)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    'code': f'Department with code "{code}" already exists in this company.'
                })

        return data


class DepartmentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    company_name = serializers.CharField(source='company.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    department_head_name = serializers.CharField(source='department_head.get_full_name', read_only=True)
    employees_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = [
            'id', 'code', 'name', 'company', 'company_name', 'branch', 'branch_name',
            'department_type', 'department_head_name', 'is_active', 'employees_count', 'created_at'
        ]


class DepartmentMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for dropdowns/references."""
    class Meta:
        model = Department
        fields = ['id', 'code', 'name', 'department_type']


# ============================================================================
# DepartmentMembership Serializers
# ============================================================================

class DepartmentMembershipSerializer(serializers.ModelSerializer):
    """Full serializer for DepartmentMembership."""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = DepartmentMembership
        fields = '__all__'
        read_only_fields = ['assigned_date']

    def validate(self, data):
        """Validate membership data."""
        user = data.get('user')
        department = data.get('department') or (self.instance.department if self.instance else None)

        # Check if user already has active membership in this department
        if user and department:
            qs = DepartmentMembership.objects.filter(
                user=user,
                department=department,
                is_active=True
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    'user': f'User "{user.get_full_name()}" already has active membership in this department.'
                })

        return data


# ============================================================================
# Legacy/Backward Compatibility Serializers
# ============================================================================

class CompanyProvisionSerializer(serializers.Serializer):
    """Legacy provisioning serializer."""
    group_name = serializers.CharField(max_length=255)
    industry_pack_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    supports_intercompany = serializers.BooleanField(default=False)
    company = serializers.DictField(required=False)

    def validate_group_name(self, value):
        if CompanyGroup.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("A company group with this name already exists.")
        return value
