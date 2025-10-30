from django.contrib import admin
from .models import Company, CompanyGroup

@admin.register(CompanyGroup)
class CompanyGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'db_name', 'industry_pack_type', 'supports_intercompany', 'status', 'created_at')
    list_filter = ('industry_pack_type', 'supports_intercompany', 'status')
    search_fields = ('name', 'db_name')

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'company_group', 'currency_code', 'is_active', 'created_at')
    list_filter = ('company_group', 'currency_code', 'is_active')
    search_fields = ('code', 'name', 'legal_name', 'tax_id')
    raw_id_fields = ('company_group',)