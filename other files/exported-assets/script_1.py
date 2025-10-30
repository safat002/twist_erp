
# Create Django app configuration files

# Finance apps.py
finance_apps = """from django.apps import AppConfig

class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.finance'
    verbose_name = 'Finance & Accounting'
    
    def ready(self):
        import apps.finance.signals
"""

# Inventory apps.py
inventory_apps = """from django.apps import AppConfig

class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inventory'
    verbose_name = 'Inventory & Warehouse'
    
    def ready(self):
        import apps.inventory.signals
"""

# Sales apps.py
sales_apps = """from django.apps import AppConfig

class SalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sales'
    verbose_name = 'Sales & CRM'
    
    def ready(self):
        import apps.sales.signals
"""

# Procurement apps.py
procurement_apps = """from django.apps import AppConfig

class ProcurementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.procurement'
    verbose_name = 'Procurement'
    
    def ready(self):
        import apps.procurement.signals
"""

# Data Migration apps.py
data_migration_apps = """from django.apps import AppConfig

class DataMigrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.data_migration'
    verbose_name = 'Data Migration'
    
    def ready(self):
        import apps.data_migration.signals
"""

files = {
    'finance_apps.py': finance_apps,
    'inventory_apps.py': inventory_apps,
    'sales_apps.py': sales_apps,
    'procurement_apps.py': procurement_apps,
    'data_migration_apps.py': data_migration_apps,
}

for filename, content in files.items():
    with open(filename, 'w') as f:
        f.write(content)

print("✓ Created Django app configuration files:")
for f in files.keys():
    print(f"  - {f}")
