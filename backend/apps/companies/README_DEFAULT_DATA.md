# Industry-Specific Default Data

This module provides automatic loading of industry-specific master data for new companies.

## Features

When a new company is created, the system automatically loads:

1. **Currencies** (BDT, USD, EUR with exchange rates)
2. **Chart of Accounts** (Industry-specific, IAS/IFRS compliant)
3. **Item Categories** (Hierarchical categories for operational items)
4. **Product Categories** (Categories for saleable products)
5. **Tax Categories** (VAT rates)
6. **Cost Centers** (Default organizational units)
7. **Units of Measure** (KG, PCS, LTR, etc.)

## Supported Industries

The system includes templates for 3 industries:

- **MANUFACTURING** - Full manufacturing CoA with WIP, Raw Materials, etc.
- **SERVICE** - Service-oriented CoA with professional fees, consultancy
- **TRADING** - Trading/wholesale CoA with merchandise inventory

All other industries fall back to the SERVICE template as a base.

## Automatic Loading (Signal-based)

Default data is automatically loaded when a new company is created via Django signals.

```python
# When you create a company:
company = Company.objects.create(
    name="ABC Manufacturing Ltd",
    industry_category=CompanyCategory.MANUFACTURING,
    created_by=user
)
# Default data is automatically loaded!
```

## Manual Loading (Management Command)

You can also manually load defaults using the management command:

### Load for a specific company:
```bash
python manage.py load_company_defaults --company=1
```

### Load for all companies without defaults:
```bash
python manage.py load_company_defaults --all
```

### Load for specific industry:
```bash
python manage.py load_company_defaults --industry=MANUFACTURING
```

### Force reload (WARNING: May create duplicates):
```bash
python manage.py load_company_defaults --company=1 --force
```

## Programmatic Usage

```python
from apps.companies.services import DefaultDataService
from apps.companies.models import Company

company = Company.objects.get(id=1)
service = DefaultDataService(company, created_by=request.user)

# Load all defaults
results = service.load_all_defaults()
# Returns: {'currencies': 3, 'accounts': 48, 'item_categories': 12, ...}

# Or load specific components
service._load_currencies()
service._load_chart_of_accounts()
service._load_item_categories()
```

## Adding New Industries

To add a new industry template:

1. Create fixture files in `fixtures/industry_defaults/`:
   - `{industry_name}_accounts.json`
   - `{industry_name}_item_categories.json`
   - `{industry_name}_product_categories.json`

2. Follow the JSON structure in existing files:

**accounts.json:**
```json
[
  {
    "code": "1000",
    "name": "Assets",
    "account_type": "ASSET",
    "parent_code": null
  },
  {
    "code": "1100",
    "name": "Current Assets",
    "account_type": "ASSET",
    "parent_code": "1000"
  }
]
```

**item_categories.json:**
```json
[
  {
    "code": "RM",
    "name": "Raw Materials",
    "parent_code": null,
    "level": 0
  },
  {
    "code": "RM-CHEM",
    "name": "Chemicals",
    "parent_code": "RM",
    "level": 1
  }
]
```

## Data Integrity

- Default data is marked with `is_default_template=True`
- Companies track loading status with `default_data_loaded` and `default_data_loaded_at`
- Prevents duplicate loading unless explicitly forced
- Transactions are atomic - all or nothing

## Customization After Loading

Users can:
- Activate/deactivate default accounts
- Add custom accounts to the hierarchy
- Rename default accounts
- Add more categories
- Modify tax rates

Default data provides a starting point and can be fully customized per company.
