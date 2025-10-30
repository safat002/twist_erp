from django.contrib import admin
from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "acquisition_date",
        "cost",
        "depreciation_method",
        "useful_life_months",
        "company",
        "is_active",
    ]
    list_filter = ["company", "depreciation_method", "is_active"]
    search_fields = ["code", "name", "barcode"]
    date_hierarchy = "acquisition_date"

