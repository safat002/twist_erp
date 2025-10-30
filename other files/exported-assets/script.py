
# Create Django app initialization files for Phase 2 modules

# Finance app __init__.py
finance_init = """\"\"\"
TWIST ERP - Finance Module
Handles accounting, GL, AP, AR, payments
\"\"\"

default_app_config = 'apps.finance.apps.FinanceConfig'
"""

# Inventory app __init__.py
inventory_init = """\"\"\"
TWIST ERP - Inventory Module
Handles products, warehouses, stock movements
\"\"\"

default_app_config = 'apps.inventory.apps.InventoryConfig'
"""

# Sales app __init__.py
sales_init = """\"\"\"
TWIST ERP - Sales & CRM Module
Handles customers, sales orders, deliveries
\"\"\"

default_app_config = 'apps.sales.apps.SalesConfig'
"""

# Procurement app __init__.py
procurement_init = """\"\"\"
TWIST ERP - Procurement Module
Handles suppliers, purchase orders, receipts
\"\"\"

default_app_config = 'apps.procurement.apps.ProcurementConfig'
"""

#Data migration app __init__.py
migration_init = """\"\"\"
TWIST ERP - Data Migration Module
AI-powered data import from Excel, CSV, databases
\"\"\"

default_app_config = 'apps.data_migration.apps.DataMigrationConfig'
"""

files_created = []

with open('finance_init.py', 'w') as f:
    f.write(finance_init)
    files_created.append('finance_init.py')

with open('inventory_init.py', 'w') as f:
    f.write(inventory_init)
    files_created.append('inventory_init.py')

with open('sales_init.py', 'w') as f:
    f.write(sales_init)
    files_created.append('sales_init.py')

with open('procurement_init.py', 'w') as f:
    f.write(procurement_init)
    files_created.append('procurement_init.py')

with open('data_migration_init.py', 'w') as f:
    f.write(migration_init)
    files_created.append('data_migration_init.py')

print("✓ Created app initialization files:")
for f in files_created:
    print(f"  - {f}")
