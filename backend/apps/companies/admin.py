from django.contrib import admin
from django.contrib import messages
from django import forms
from .models import Company, CompanyGroup, Branch, Department, DepartmentMembership
from apps.metadata.models import MetadataDefinition


class CompanyGroupAdminForm(forms.ModelForm):
    class Meta:
        model = CompanyGroup
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Build industry pack choices dynamically from metadata definitions
        packs = set()
        try:
            qs = MetadataDefinition.objects.filter(layer='INDUSTRY_PACK').values_list('summary', flat=True)
            for summary in qs:
                if isinstance(summary, dict):
                    pack = summary.get('industry_pack') or summary.get('industry') or summary.get('pack')
                    if pack:
                        packs.add(str(pack))
        except Exception:
            # Fallback gracefully if metadata app not ready
            pass
        choices = [('', '---------')] + [(p, p.title()) for p in sorted(packs)]
        self.fields['industry_pack_type'].widget = forms.Select(choices=choices)


@admin.register(CompanyGroup)
class CompanyGroupAdmin(admin.ModelAdmin):
    form = CompanyGroupAdminForm
    list_display = ('code', 'name', 'group_type', 'is_active', 'companies_count', 'created_at')
    list_filter = ('group_type', 'is_active', 'status')
    search_fields = ('code', 'name', 'registration_number', 'tax_id')
    readonly_fields = ('hierarchy_path', 'created_at', 'updated_at', 'created_by')
    raw_id_fields = ('parent_group', 'owner_user', 'created_by')

    # Hide 'code' (auto-generated) and 'db_name' (auto-generated) from edit forms
    # Keep them visible via read-only display if needed in future.
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'group_type', 'description')
        }),
        ('Hierarchy', {
            'fields': ('parent_group', 'hierarchy_path')
        }),
        ('Configuration', {
            'fields': ('base_currency', 'fiscal_year_end_month', 'is_active', 'is_consolidated')
        }),
        ('Governance', {
            'fields': ('owner_user', 'owner_name', 'owner_email', 'owner_phone')
        }),
        ('Legal & Compliance', {
            'fields': ('registration_number', 'registration_authority', 'tax_id', 'legal_address')
        }),
        ('Legacy Fields', {
            'fields': ('industry_pack_type', 'supports_intercompany', 'status'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('tags', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def companies_count(self, obj):
        return obj.companies.count()
    companies_count.short_description = 'Companies'

    def has_delete_permission(self, request, obj=None):
        base = super().has_delete_permission(request, obj)
        if not base:
            return False
        if obj is None:
            return True
        # Block deletion if group still has companies
        if obj.companies.exists():
            return False
        return True

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj is not None and obj.companies.exists():
            sample = ", ".join([f"{c.code}-{c.name}" for c in obj.companies.all()[:10]])
            remainder = obj.companies.count() - 10
            if remainder > 0:
                sample = f"{sample} (+{remainder} more)"
            messages.warning(
                request,
                f"This group has {obj.companies.count()} companies. Delete the companies first before deleting the group. Affected: {sample}",
            )
        return super().change_view(request, object_id, form_url, extra_context)

    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj is not None:
            qs = obj.companies.all()
            if qs.exists():
                # Warn the admin user listing affected companies
                sample = ", ".join([f"{c.code}-{c.name}" for c in qs[:10]])
                remainder = qs.count() - 10
                if remainder > 0:
                    sample = f"{sample} (+{remainder} more)"
                messages.warning(
                    request,
                    f"This group has {qs.count()} companies which may stop working if you delete the group: {sample}",
                )
                extra_context['dependent_companies'] = qs
        return super().delete_view(request, object_id, extra_context=extra_context)


class CompanyAdminForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show only industries with pre-built templates
        # These templates are located in: backend/apps/companies/fixtures/industry_defaults/
        INDUSTRIES_WITH_TEMPLATES = [
            ('MANUFACTURING', 'Manufacturing'),
            ('SERVICE', 'Service Provider'),
            ('TRADING', 'Trading/Wholesale'),
        ]

        choices = [('', '---------')] + INDUSTRIES_WITH_TEMPLATES
        self.fields['business_type'].widget = forms.Select(choices=choices)
        self.fields['business_type'].help_text = (
            'Select an industry type to automatically load pre-configured templates '
            '(Chart of Accounts, Item Categories, Product Categories, etc.)'
        )

    def clean(self):
        cleaned_data = super().clean()
        business_type = cleaned_data.get('business_type')

        # Map business_type to industry_category
        if business_type:
            # Map the selection to the industry_category field
            # This ensures the DefaultDataService uses the correct template
            cleaned_data['industry_category'] = business_type

        return cleaned_data


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    form = CompanyAdminForm
    list_display = ('code', 'name', 'company_group', 'company_type', 'industry_category', 'base_currency', 'is_active', 'default_data_loaded', 'created_at')
    list_filter = ('company_group', 'company_type', 'industry_category', 'base_currency', 'is_active', 'requires_branch_structure', 'default_data_loaded')
    search_fields = ('code', 'name', 'legal_name', 'tax_id', 'registration_number')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'industry_category', 'default_data_loaded', 'default_data_loaded_at')
    # Use dropdowns for company_group and parent_company, and autocomplete for user fields
    autocomplete_fields = ('owner_user', 'company_admin_user')

    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'legal_name', 'company_type')
        }),
        ('Hierarchy', {
            'fields': ('company_group', 'parent_company')
        }),
        ('Financial Settings', {
            'fields': ('base_currency', 'currency_code', 'fiscal_year_start', 'fiscal_year_end_date')
        }),
        ('Legal & Tax', {
            'fields': ('registration_number', 'tax_id', 'legal_address', 'registration_country')
        }),
        ('Contact & Governance', {
            'fields': ('owner_user', 'company_admin_user')
        }),
        ('Configuration', {
            'fields': (
                'business_type',
                'industry_category',
                'industry_sub_category',
                'default_data_loaded',
                'default_data_loaded_at',
                'requires_branch_structure',
                'enable_inter_company_transactions',
                'is_active',
                'is_consolidation_enabled'
            ),
            'description': 'Select a Business Type to automatically load industry-specific templates (Chart of Accounts, Categories, etc.)'
        }),
        ('Features', {
            'fields': ('feature_flags', 'settings'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        """Ensure industry_category is set from business_type selection."""
        if form.cleaned_data.get('business_type'):
            obj.industry_category = form.cleaned_data['business_type']

        # Set created_by for new objects
        if not change:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'company', 'branch_type', 'city', 'country', 'is_active', 'departments_count', 'created_at')
    list_filter = ('company', 'branch_type', 'is_active', 'country', 'has_warehouse')
    search_fields = ('code', 'name', 'location', 'city', 'manager_name', 'warehouse_code')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    raw_id_fields = ('company', 'parent_branch', 'branch_head_user', 'created_by')

    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'branch_type')
        }),
        ('Hierarchy', {
            'fields': ('company', 'parent_branch')
        }),
        ('Location', {
            'fields': ('location', 'country', 'city', 'state_province', 'postal_code', 'latitude', 'longitude')
        }),
        ('Contact', {
            'fields': ('branch_head_user', 'manager_name', 'contact_phone', 'contact_email')
        }),
        ('Configuration', {
            'fields': ('has_warehouse', 'warehouse_code', 'is_active', 'operational_start_date', 'operational_end_date')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def departments_count(self, obj):
        return obj.departments.count()
    departments_count.short_description = 'Departments'


class DepartmentMembershipInline(admin.TabularInline):
    model = DepartmentMembership
    extra = 1
    raw_id_fields = ('user',)
    fields = ('user', 'role', 'is_active', 'assigned_date', 'departure_date')
    readonly_fields = ('assigned_date',)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'company', 'branch', 'department_type', 'department_head', 'is_active', 'employees_count', 'created_at')
    list_filter = ('company', 'branch', 'department_type', 'is_active')
    search_fields = ('code', 'name', 'cost_center_code')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    raw_id_fields = ('company', 'branch', 'parent_department', 'department_head', 'deputy_head', 'created_by')
    inlines = [DepartmentMembershipInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'department_type')
        }),
        ('Hierarchy', {
            'fields': ('company', 'branch', 'parent_department')
        }),
        ('Leadership', {
            'fields': ('department_head', 'deputy_head')
        }),
        ('Budget & Cost Allocation', {
            'fields': ('cost_center_code', 'budget_threshold_percent', 'requires_approval_threshold')
        }),
        ('Configuration', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def employees_count(self, obj):
        return obj.employees.filter(departmentmembership__is_active=True).count()
    employees_count.short_description = 'Employees'


@admin.register(DepartmentMembership)
class DepartmentMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'role', 'is_active', 'assigned_date', 'departure_date')
    list_filter = ('role', 'is_active', 'department__company')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'department__name')
    readonly_fields = ('assigned_date',)
    raw_id_fields = ('user', 'department')

    fieldsets = (
        ('Assignment', {
            'fields': ('user', 'department', 'role')
        }),
        ('Status', {
            'fields': ('is_active', 'assigned_date', 'departure_date')
        }),
        ('Permissions', {
            'fields': ('custom_permissions',),
            'classes': ('collapse',)
        }),
    )
