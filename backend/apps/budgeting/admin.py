from django.contrib import admin
import json
from django.contrib import messages
from django.utils import timezone
from .models import (
    Budget,
    BudgetConsumptionSnapshot,
    BudgetLine,
    BudgetOverrideRequest,
    CostCenter,
    BudgetItemCode,
    BudgetItemCategory,
    BudgetItemSubCategory,
)
from apps.inventory.models import UnitOfMeasure as InventoryUnitOfMeasure
from apps.inventory.admin import UnitOfMeasureAdmin as BaseUOMAdmin
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError
from django.db.models import Max
from django import forms
from apps.companies.models import Company, CompanyGroup

class BudgetUnitOfMeasure(InventoryUnitOfMeasure):
    class Meta:
        proxy = True
        verbose_name = 'Unit of Measure'
        verbose_name_plural = 'Units of Measure'


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "cost_center_type", "owner", "company", "is_active"]
    list_filter = ["company", "cost_center_type", "is_active"]
    search_fields = ["code", "name", "owner__username", "owner__email"]
    ordering = ["code"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("company", "company_group", "code", "name", "cost_center_type", "parent")}),
        ("Ownership", {"fields": ("owner", "deputy_owner", "default_currency", "tags")}),
        ("Status", {"fields": ("is_active", "description", "kpi_snapshot", "created_at", "updated_at")}),
    )


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ["name", "cost_center", "budget_type", "period_start", "period_end", "amount", "consumed", "status", "company"]
    list_filter = ["company", "budget_type", "status", "period_start"]
    search_fields = ["name", "cost_center__code", "cost_center__name"]
    readonly_fields = ["amount", "consumed", "created_at", "updated_at", "approved_by", "approved_at", "locked_at"]
    actions = ["mark_active", "lock_budgets", "close_budgets", "reopen_budgets", "recalculate_totals"]

    def mark_active(self, request, queryset):
        updated = 0
        for budget in queryset:
            budget.mark_active(user=request.user)
            updated += 1
        self.message_user(request, f"{updated} budget(s) marked ACTIVE.", level=messages.SUCCESS)

    mark_active.short_description = "Activate selected budgets"

    def lock_budgets(self, request, queryset):
        updated = queryset.update(status=Budget.STATUS_LOCKED, locked_at=timezone.now())
        self.message_user(request, f"{updated} budget(s) locked.", level=messages.INFO)

    lock_budgets.short_description = "Lock selected budgets"

    def close_budgets(self, request, queryset):
        updated = queryset.update(status=Budget.STATUS_CLOSED, updated_at=timezone.now())
        self.message_user(request, f"{updated} budget(s) marked as CLOSED.", level=messages.SUCCESS)

    close_budgets.short_description = "Mark selected budgets as CLOSED"

    close_budgets.short_description = "Mark selected budgets as CLOSED"

    def reopen_budgets(self, request, queryset):
        updated = queryset.update(status=Budget.STATUS_ACTIVE)
        self.message_user(request, f"{updated} budget(s) reopened (ACTIVE).", level=messages.SUCCESS)

    reopen_budgets.short_description = "Reopen selected budgets (ACTIVE)"

    def recalculate_totals(self, request, queryset):
        for budget in queryset:
            budget.recalculate_totals(commit=True)
        self.message_user(request, "Recalculated totals for selected budgets.", level=messages.SUCCESS)

    recalculate_totals.short_description = "Recalculate totals from budget lines"


@admin.register(BudgetLine)
class BudgetLineAdmin(admin.ModelAdmin):
    list_display = ["budget", "budget_line_id", "item_name", "procurement_class", "value_limit", "consumed_value", "remaining_value", "is_active"]
    list_filter = ["procurement_class", "is_active", "budget__company"]
    search_fields = ["item_name", "item_code", "budget__name"]
    readonly_fields = ["consumed_quantity", "consumed_value", "created_at", "updated_at"]
    ordering = ["budget", "sequence"]

    def budget_line_id(self, obj):
        return obj.sequence
    budget_line_id.short_description = "Budget Line ID"
    budget_line_id.admin_order_field = "sequence"

    class AddForm(forms.ModelForm):
        class Meta:
            model = BudgetLine
            exclude = ["sequence", "procurement_class", "item_name"]  # make Item Name driven by Item dropdown

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            try:
                bfield = self.fields.get('budget')
                if bfield is not None:
                    qs = bfield.queryset
                    mapping = {}
                    for b in qs:
                        mapping[str(b.id)] = getattr(b, 'budget_type', '')
                    bfield.widget.attrs['data-budget-types'] = json.dumps(mapping)
                    # initial selection type
                    initial = self.initial.get('budget') or (self.instance.budget_id if getattr(self.instance, 'budget_id', None) else None)
                    if initial:
                        try:
                            init_bt = mapping.get(str(initial)) or getattr(qs.filter(id=initial).first(), 'budget_type', '')
                            bfield.widget.attrs['data-initial-type'] = init_bt or ''
                        except Exception:
                            pass
            except Exception:
                pass
            # Rename item field label to "Item Name" and keep item_code visible
            try:
                if 'item' in self.fields:
                    self.fields['item'].label = 'Item Name'
            except Exception:
                pass

    class ChangeForm(forms.ModelForm):
        class Meta:
            model = BudgetLine
            exclude = ["sequence", "procurement_class", "item_name"]  # make Item Name driven by Item dropdown

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            try:
                bfield = self.fields.get('budget')
                if bfield is not None:
                    qs = bfield.queryset
                    mapping = {}
                    for b in qs:
                        mapping[str(b.id)] = getattr(b, 'budget_type', '')
                    bfield.widget.attrs['data-budget-types'] = json.dumps(mapping)
                    initial = self.initial.get('budget') or (self.instance.budget_id if getattr(self.instance, 'budget_id', None) else None)
                    if initial:
                        try:
                            init_bt = mapping.get(str(initial)) or getattr(qs.filter(id=initial).first(), 'budget_type', '')
                            bfield.widget.attrs['data-initial-type'] = init_bt or ''
                        except Exception:
                            pass
            except Exception:
                pass
            # Rename item field label to "Item Name"
            try:
                if 'item' in self.fields:
                    self.fields['item'].label = 'Item Name'
            except Exception:
                pass

    form = AddForm

    def get_form(self, request, obj=None, **kwargs):
        original_form = self.form
        try:
            self.form = self.AddForm if obj is None else self.ChangeForm
            return super().get_form(request, obj, **kwargs)
        finally:
            self.form = original_form

    def save_model(self, request, obj, form, change):
        # Auto-generate sequence per budget on create (Budget Line ID)
        if not change:
            try:
                if getattr(obj, 'budget_id', None):
                    next_seq = (BudgetLine.objects.filter(budget=obj.budget).aggregate(m=Max('sequence'))['m'] or 0) + 1
                    obj.sequence = next_seq
            except Exception:
                # As a safe fallback, leave default or let DB enforce uniqueness
                pass
        # Derive procurement class from selected budget's type and hide from form
        try:
            if getattr(obj, 'budget_id', None):
                bt = getattr(obj.budget, 'budget_type', None)
                if bt:
                    from .models import Budget
                    pc_map = {
                        getattr(Budget, 'TYPE_OPEX', 'opex'): BudgetLine.ProcurementClass.SERVICE_ITEM,
                        getattr(Budget, 'TYPE_CAPEX', 'capex'): BudgetLine.ProcurementClass.CAPEX_ITEM,
                    }
                    obj.procurement_class = pc_map.get(bt, BudgetLine.ProcurementClass.STOCK_ITEM)
        except Exception:
            pass
        # Enforce required fields for Operational/Production budgets
        try:
            from .models import Budget
            if getattr(obj, 'budget_id', None) and obj.budget.budget_type == getattr(Budget, 'TYPE_OPERATIONAL', 'operational'):
                missing = {}
                if not getattr(obj, 'product_id', None):
                    missing['product'] = 'Product is required for operational/production budgets.'
                if not getattr(obj, 'item_id', None):
                    missing['item'] = 'Item is required for operational/production budgets.'
                if missing:
                    raise ValidationError(missing)
        except ValidationError:
            raise
        except Exception:
            pass
        # If item is selected, set item_code and item_name automatically
        try:
            if getattr(obj, 'item_id', None):
                obj.item_code = getattr(obj.item, 'code', obj.item_code)
                obj.item_name = getattr(obj.item, 'name', obj.item_name)
        except Exception:
            pass
        try:
            super().save_model(request, obj, form, change)
        except IntegrityError:
            # In rare race, recompute and retry once
            if getattr(obj, 'budget_id', None):
                next_seq = (BudgetLine.objects.filter(budget=obj.budget).aggregate(m=Max('sequence'))['m'] or 0) + 1
                obj.sequence = next_seq
            super().save_model(request, obj, form, change)

    # Ensure the Budget field shows a dropdown of Budgets (ordered by name)
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'budget':
            try:
                from .models import Budget
                qs = Budget.objects.order_by('name')
                # Prefer active company context if available (middleware)
                company = getattr(request, 'company', None)
                if company is not None:
                    qs = qs.filter(company=company)
                else:
                    # Fallback: limit to companies the user has access to (unless superuser)
                    if not (getattr(request.user, 'is_superuser', False) or getattr(request.user, 'is_system_admin', False)):
                        companies_rel = getattr(request.user, 'companies', None)
                        if companies_rel is not None:
                            try:
                                qs = qs.filter(company__in=companies_rel.all())
                            except Exception:
                                # If relation not available, leave unfiltered
                                pass
                kwargs['queryset'] = qs
            except Exception:
                pass
        if db_field.name == 'item':
            try:
                from apps.inventory.models import Item
                qs = Item.objects.order_by('code')
                company = getattr(request, 'company', None)
                if company is not None:
                    qs = qs.filter(company=company)
                kwargs['queryset'] = qs
            except Exception:
                pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(BudgetOverrideRequest)
class BudgetOverrideRequestAdmin(admin.ModelAdmin):
    list_display = ["reference_id", "cost_center", "requested_amount", "status", "requested_by", "approver", "created_at"]
    list_filter = ["status", "company"]
    search_fields = ["reference_id", "reason", "cost_center__name", "requested_by__username"]
    readonly_fields = ["created_at", "updated_at", "approved_at"]
    actions = ["mark_approved", "mark_rejected"]

    def mark_approved(self, request, queryset):
        updated = queryset.filter(status=BudgetOverrideRequest.STATUS_PENDING).update(
            status=BudgetOverrideRequest.STATUS_APPROVED,
            approver=request.user,
            approved_at=timezone.now(),
        )
        self.message_user(request, f"{updated} override request(s) marked approved.", level=messages.SUCCESS)

    mark_approved.short_description = "Approve selected override requests"

    def mark_rejected(self, request, queryset):
        updated = queryset.filter(status=BudgetOverrideRequest.STATUS_PENDING).update(
            status=BudgetOverrideRequest.STATUS_REJECTED,
            approver=request.user,
            approved_at=timezone.now(),
        )
        self.message_user(request, f"{updated} override request(s) rejected.", level=messages.WARNING)

    mark_rejected.short_description = "Reject selected override requests"


@admin.register(BudgetConsumptionSnapshot)
class BudgetConsumptionSnapshotAdmin(admin.ModelAdmin):
    list_display = ["budget", "snapshot_date", "total_limit", "total_consumed", "total_remaining"]
    list_filter = ["snapshot_date", "budget__company"]
    search_fields = ["budget__name", "budget__cost_center__name"]


@admin.register(BudgetItemCode)
class BudgetItemCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "category", "uom", "standard_price", "is_active", "company_group", "category_ref", "sub_category_ref"]
    list_filter = ["company__company_group", "category", "category_ref", "sub_category_ref", "is_active"]
    search_fields = ["code", "name", "category"]
    ordering = ["code"]

    class AddForm(forms.ModelForm):
        group = forms.ModelChoiceField(queryset=CompanyGroup.objects.all(), required=True, label="Company Group")

        class Meta:
            model = BudgetItemCode
            fields = ['name', 'category', 'category_ref', 'sub_category_ref', 'uom', 'standard_price', 'is_active']  # Hide code on create

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            qs = CompanyGroup.objects.all()
            if qs.count() == 1:
                self.fields['group'].initial = qs.first()

    class ChangeForm(forms.ModelForm):
        class Meta:
            model = BudgetItemCode
            fields = ['code', 'name', 'category', 'category_ref', 'sub_category_ref', 'uom', 'standard_price', 'is_active']  # Show code on edit

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if self.instance and getattr(self.instance, 'pk', None):
                # Surface company group context for display-only via initial on a non-model field if needed
                pass

    form = AddForm

    def get_form(self, request, obj=None, **kwargs):
        original_form = self.form
        try:
            self.form = self.AddForm if obj is None else self.ChangeForm
            return super().get_form(request, obj, **kwargs)
        finally:
            self.form = original_form

    def company_group(self, obj):
        return getattr(getattr(obj, 'company', None), 'company_group', None)
    company_group.short_description = "Company Group"

    def _generate_item_code(self, group: CompanyGroup) -> str:
        prefix = "IC"
        width = 6
        existing = BudgetItemCode.objects.filter(
            company__company_group=group,
            code__startswith=prefix,
        ).values_list('code', flat=True)
        max_num = 0
        for code in existing:
            suffix = code[len(prefix):]
            if suffix.isdigit():
                try:
                    max_num = max(max_num, int(suffix))
                except ValueError:
                    pass
        i = max_num + 1
        while True:
            candidate = f"{prefix}{i:06d}"
            if not BudgetItemCode.objects.filter(company__company_group=group, code=candidate).exists():
                return candidate
            i += 1

    def save_model(self, request, obj, form, change):
        if not getattr(obj, 'company_id', None):
            group = form.cleaned_data.get('group') if form else None
            if not group:
                raise ValidationError({"group": "Please select a company group."})
            company = Company.objects.filter(company_group=group, is_active=True).first() or Company.objects.filter(company_group=group).first()
            if not company:
                raise ValidationError({"group": "Selected company group has no companies. Create a company first."})
            if not getattr(obj, 'code', None):
                obj.code = self._generate_item_code(group)
            exists = BudgetItemCode.objects.filter(company__company_group=group, code=obj.code).exists()
            if exists:
                raise ValidationError({"code": "An item code with this code already exists for this group."})
            obj.company = company
        super().save_model(request, obj, form, change)


@admin.register(BudgetItemCategory)
class BudgetItemCategoryAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active", "company_group"]
    list_filter = ["is_active", "company__company_group"]
    search_fields = ["code", "name"]
    exclude = ["company_group"]

    class AddForm(forms.ModelForm):
        group = forms.ModelChoiceField(queryset=CompanyGroup.objects.all(), required=True, label="Company Group")

        class Meta:
            model = BudgetItemCategory
            fields = ['name', 'is_active']  # Hide code on create

    class ChangeForm(forms.ModelForm):
        class Meta:
            model = BudgetItemCategory
            fields = ['code', 'name', 'is_active']  # Show code on edit

    form = AddForm

    def get_form(self, request, obj=None, **kwargs):
        original_form = self.form
        try:
            self.form = self.AddForm if obj is None else self.ChangeForm
            return super().get_form(request, obj, **kwargs)
        finally:
            self.form = original_form

    def _generate_category_code(self, group: CompanyGroup) -> str:
        prefix = "CAT"
        width = 4
        existing = BudgetItemCategory.objects.filter(
            company__company_group=group,
            code__startswith=prefix,
        ).values_list('code', flat=True)
        max_num = 0
        for code in existing:
            suffix = code[len(prefix):]
            if suffix.isdigit():
                try:
                    max_num = max(max_num, int(suffix))
                except ValueError:
                    pass
        i = max_num + 1
        while True:
            candidate = f"{prefix}{i:04d}"
            if not BudgetItemCategory.objects.filter(company__company_group=group, code=candidate).exists():
                return candidate
            i += 1

    def has_add_permission(self, request):
        # Only users with model add permission can create categories
        return request.user.has_perm("budgeting.add_budgetitemcategory")

    def save_model(self, request, obj, form, change):
        # Enforce create permission at save time as a safety net
        if not change and not request.user.has_perm("budgeting.add_budgetitemcategory"):
            raise PermissionDenied("You do not have permission to create categories.")
        if not getattr(obj, 'company_id', None):
            group = form.cleaned_data.get('group') if form else None
            if not group:
                raise ValidationError({"group": "Please select a company group."})
            company = Company.objects.filter(company_group=group, is_active=True).first() or Company.objects.filter(company_group=group).first()
            if not company:
                raise ValidationError({"group": "Selected company group has no companies. Create a company first."})
            if not getattr(obj, 'code', None):
                obj.code = self._generate_category_code(group)
            exists = BudgetItemCategory.objects.filter(company__company_group=group, code=obj.code).exists()
            if exists:
                raise ValidationError({"code": "A category with this code already exists for this group."})
            obj.company = company
        super().save_model(request, obj, form, change)


@admin.register(BudgetItemSubCategory)
class BudgetItemSubCategoryAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "category", "is_active", "company_group"]
    list_filter = ["is_active", "company__company_group", "category"]
    search_fields = ["code", "name", "category__name", "category__code"]
    exclude = ["company_group"]

    class AddForm(forms.ModelForm):
        class Meta:
            model = BudgetItemSubCategory
            fields = ['category', 'name', 'is_active']  # Hide code on create; group derived from category

    class ChangeForm(forms.ModelForm):
        class Meta:
            model = BudgetItemSubCategory
            fields = ['category', 'code', 'name', 'is_active']

    form = AddForm

    def _generate_subcategory_code(self, category: BudgetItemCategory) -> str:
        prefix = "SC"
        width = 4
        existing = BudgetItemSubCategory.objects.filter(
            category=category,
            code__startswith=prefix,
        ).values_list('code', flat=True)
        max_num = 0
        for code in existing:
            suffix = code[len(prefix):]
            if suffix.isdigit():
                try:
                    max_num = max(max_num, int(suffix))
                except ValueError:
                    pass
        i = max_num + 1
        while True:
            candidate = f"{prefix}{i:04d}"
            if not BudgetItemSubCategory.objects.filter(category=category, code=candidate).exists():
                return candidate
            i += 1

    def has_add_permission(self, request):
        # Only users with model add permission can create sub-categories
        return request.user.has_perm("budgeting.add_budgetitemsubcategory")

    def get_form(self, request, obj=None, **kwargs):
        original_form = self.form
        try:
            self.form = self.AddForm if obj is None else self.ChangeForm
            form = super().get_form(request, obj, **kwargs)
            # Respect add permission for related Category (hides green plus if not allowed)
            if 'category' in form.base_fields:
                widget = form.base_fields['category'].widget
                try:
                    widget.can_add_related = request.user.has_perm("budgeting.add_budgetitemcategory")
                except Exception:
                    pass
            return form
        finally:
            self.form = original_form

    def save_model(self, request, obj, form, change):
        # Enforce create permission at save time as a safety net
        if not change and not request.user.has_perm("budgeting.add_budgetitemsubcategory"):
            raise PermissionDenied("You do not have permission to create sub-categories.")
        if not getattr(obj, 'company_id', None):
            # Derive company/group from the selected Category
            if not getattr(obj, 'category_id', None):
                raise ValidationError({"category": "Please select a Category."})
            company = getattr(obj.category, 'company', None)
            if not company:
                raise ValidationError({"category": "Selected Category is not linked to a company."})
            if not getattr(obj, 'code', None):
                obj.code = self._generate_subcategory_code(obj.category)
            exists = BudgetItemSubCategory.objects.filter(category=obj.category, code=obj.code).exists()
            if exists:
                raise ValidationError({"code": "A sub-category with this code already exists under the selected category."})
            obj.company = company
        super().save_model(request, obj, form, change)


@admin.register(BudgetUnitOfMeasure)
class BudgetUnitOfMeasureAdmin(BaseUOMAdmin):
    list_display = ["code", "name", "is_active", "company_group"]
    list_filter = ["is_active", "company__company_group"]
    # Hide company on the form; it is auto-resolved on save
    exclude = getattr(BaseUOMAdmin, 'exclude', []) + ["company"]
    # Show group context read-only alongside standard read-only fields
    readonly_fields = getattr(BaseUOMAdmin, 'readonly_fields', []) + ["company_group"]

    def company_group(self, obj):
        return getattr(getattr(obj, "company", None), "company_group", None)
    company_group.short_description = "Company Group"

    class Form(forms.ModelForm):
        group = forms.ModelChoiceField(queryset=CompanyGroup.objects.all(), required=True, label="Company Group")

        class Meta(BaseUOMAdmin.form.Meta if hasattr(BaseUOMAdmin, 'form') and hasattr(BaseUOMAdmin.form, 'Meta') else type('Meta', (), {})):
            model = BudgetUnitOfMeasure
            fields = ['code', 'name', 'short_name', 'is_active']

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            qs = CompanyGroup.objects.all()
            if qs.count() == 1:
                self.fields['group'].initial = qs.first()
            if self.instance and getattr(self.instance, 'pk', None):
                cg = getattr(getattr(self.instance, 'company', None), 'company_group', None)
                if cg:
                    self.fields['group'].initial = cg

    form = Form

    def save_model(self, request, obj, form, change):
        # Assign company from selected group on create
        if not getattr(obj, 'company_id', None):
            group = form.cleaned_data.get('group') if form else None
            if not group:
                raise ValidationError({"group": "Please select a company group."})
            company = Company.objects.filter(company_group=group, is_active=True).first() or Company.objects.filter(company_group=group).first()
            if not company:
                raise ValidationError({"group": "Selected company group has no companies. Create a company first."})
            exists = InventoryUnitOfMeasure.objects.filter(company__company_group=group, code=obj.code).exists()
            if exists:
                raise ValidationError({"code": "A UOM with this code already exists for this group."})
            obj.company = company
        super().save_model(request, obj, form, change)
