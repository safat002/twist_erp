# Enhanced Implementation Plan - Complete ERP Refactoring

**Date**: November 5, 2025
**Version**: 2.0 - Enhanced
**Status**: Ready for Implementation

---

## 📋 Overview of All Requirements

### ✅ Confirmed Requirements

1. **Product to Item Separation**
   - Products in Sales/CRM module (saleable items)
   - Items in Inventory module (operational items)
   - Revenue budgets use Products, other budgets use Items

2. **Industry-Specific Default Master Data**
   - Different templates for Manufacturing, Trading, Services, NGO, etc.
   - Auto-assigned based on Company Category
   - Auto-migrate all existing companies

3. **Multi-Currency Support**
   - Default accounts support multi-currency from start
   - Currency conversion in financial statements

4. **On-Demand Financial Statements** (NEW)
   - Profit & Loss Statement (IAS 1 format)
   - Balance Sheet / Statement of Financial Position (IAS 1 format)
   - Cash Flow Statement (IAS 7 format)
   - Statement of Changes in Equity
   - User-defined time periods
   - Export to Excel, PDF, CSV
   - Comparison periods (YoY, QoQ)

5. **Item Sub-Categories** (NEW)
   - Hierarchical category structure
   - Multiple levels: Category → Sub-Category → Sub-Sub-Category

---

## Part 1: Industry-Specific Default Master Data

### 1.1 Company Category Enhancement

**File**: `backend/apps/companies/models.py`

```python
class CompanyCategory(models.TextChoices):
    MANUFACTURING = 'MANUFACTURING', 'Manufacturing'
    TRADING = 'TRADING', 'Trading/Wholesale'
    RETAIL = 'RETAIL', 'Retail'
    SERVICE = 'SERVICE', 'Service Provider'
    CONSTRUCTION = 'CONSTRUCTION', 'Construction'
    HEALTHCARE = 'HEALTHCARE', 'Healthcare'
    EDUCATION = 'EDUCATION', 'Education'
    NGO = 'NGO', 'Non-Profit/NGO'
    AGRICULTURE = 'AGRICULTURE', 'Agriculture'
    TECHNOLOGY = 'TECHNOLOGY', 'Technology/Software'
    HOSPITALITY = 'HOSPITALITY', 'Hospitality'
    TRANSPORT = 'TRANSPORT', 'Transportation/Logistics'
    REAL_ESTATE = 'REAL_ESTATE', 'Real Estate'
    FINANCIAL = 'FINANCIAL', 'Financial Services'
    OTHER = 'OTHER', 'Other'

class Company(models.Model):
    # ... existing fields ...

    # ENHANCED: Industry category
    industry_category = models.CharField(
        max_length=50,
        choices=CompanyCategory.choices,
        default=CompanyCategory.OTHER,
        help_text="Company industry category - determines default master data"
    )

    # NEW: Currency settings
    base_currency = models.CharField(
        max_length=3,
        default='BDT',
        help_text="Base currency for this company"
    )

    secondary_currencies = models.JSONField(
        default=list,
        blank=True,
        help_text="List of additional currencies used: ['USD', 'EUR', 'GBP']"
    )

    enable_multi_currency = models.BooleanField(
        default=False,
        help_text="Enable multi-currency transactions"
    )
```

### 1.2 Industry-Specific Default Data Structure

```
backend/apps/metadata/fixtures/defaults/
├── common/
│   ├── uom.json                          # Common to all industries
│   └── fiscal_periods.json
├── manufacturing/
│   ├── chart_of_accounts.json
│   ├── item_categories.json
│   ├── product_categories.json
│   ├── departments.json
│   ├── cost_centers.json
│   └── industry_config.json
├── trading/
│   ├── chart_of_accounts.json
│   ├── item_categories.json
│   ├── product_categories.json
│   ├── departments.json
│   └── cost_centers.json
├── service/
│   ├── chart_of_accounts.json
│   ├── item_categories.json
│   ├── product_categories.json
│   ├── departments.json
│   └── cost_centers.json
├── ngo/
│   ├── chart_of_accounts.json            # Donor accounting
│   ├── program_areas.json                # Instead of item categories
│   ├── departments.json
│   └── cost_centers.json
├── retail/
│   └── ...
└── construction/
    └── ...
```

### 1.3 Industry-Specific Chart of Accounts

#### Manufacturing COA
**File**: `fixtures/defaults/manufacturing/chart_of_accounts.json`

```json
{
  "industry": "MANUFACTURING",
  "accounts": [
    // ASSETS
    {"code": "1000", "name": "ASSETS", "type": "ASSET"},
    {"code": "1100", "name": "Current Assets", "type": "ASSET", "parent": "1000"},
    {"code": "1130", "name": "Inventory", "type": "ASSET", "parent": "1100"},
    {"code": "1131", "name": "Raw Materials Inventory", "type": "ASSET", "parent": "1130"},
    {"code": "1132", "name": "Work in Progress", "type": "ASSET", "parent": "1130"},
    {"code": "1133", "name": "Finished Goods Inventory", "type": "ASSET", "parent": "1130"},
    {"code": "1134", "name": "Consumables & Supplies", "type": "ASSET", "parent": "1130"},
    {"code": "1135", "name": "Packing Materials", "type": "ASSET", "parent": "1130"},

    // EXPENSES - Manufacturing Specific
    {"code": "5100", "name": "Cost of Goods Sold", "type": "EXPENSE", "parent": "5000"},
    {"code": "5110", "name": "Direct Materials", "type": "EXPENSE", "parent": "5100"},
    {"code": "5120", "name": "Direct Labor", "type": "EXPENSE", "parent": "5100"},
    {"code": "5130", "name": "Manufacturing Overhead", "type": "EXPENSE", "parent": "5100"},
    {"code": "5131", "name": "Factory Rent", "type": "EXPENSE", "parent": "5130"},
    {"code": "5132", "name": "Factory Utilities", "type": "EXPENSE", "parent": "5130"},
    {"code": "5133", "name": "Machine Maintenance", "type": "EXPENSE", "parent": "5130"},
    {"code": "5134", "name": "Factory Depreciation", "type": "EXPENSE", "parent": "5130"}
  ]
}
```

#### Trading COA
**File**: `fixtures/defaults/trading/chart_of_accounts.json`

```json
{
  "industry": "TRADING",
  "accounts": [
    // ASSETS
    {"code": "1000", "name": "ASSETS", "type": "ASSET"},
    {"code": "1130", "name": "Inventory", "type": "ASSET", "parent": "1100"},
    {"code": "1131", "name": "Trading Goods", "type": "ASSET", "parent": "1130"},
    {"code": "1132", "name": "Goods in Transit", "type": "ASSET", "parent": "1130"},

    // EXPENSES - Trading Specific
    {"code": "5100", "name": "Cost of Goods Sold", "type": "EXPENSE", "parent": "5000"},
    {"code": "5110", "name": "Purchase Cost", "type": "EXPENSE", "parent": "5100"},
    {"code": "5120", "name": "Freight Inward", "type": "EXPENSE", "parent": "5100"},
    {"code": "5130", "name": "Import Duty & Taxes", "type": "EXPENSE", "parent": "5100"},
    {"code": "5210", "name": "Distribution Expenses", "type": "EXPENSE", "parent": "5200"},
    {"code": "5211", "name": "Delivery & Logistics", "type": "EXPENSE", "parent": "5210"}
  ]
}
```

#### Service COA
**File**: `fixtures/defaults/service/chart_of_accounts.json`

```json
{
  "industry": "SERVICE",
  "accounts": [
    // No Inventory for service companies
    {"code": "1100", "name": "Current Assets", "type": "ASSET", "parent": "1000"},
    {"code": "1140", "name": "Unbilled Revenue", "type": "ASSET", "parent": "1100"},
    {"code": "1150", "name": "Deferred Expenses", "type": "ASSET", "parent": "1100"},

    // REVENUE - Service Specific
    {"code": "4100", "name": "Service Revenue", "type": "REVENUE", "parent": "4000"},
    {"code": "4110", "name": "Consulting Services", "type": "REVENUE", "parent": "4100"},
    {"code": "4120", "name": "Subscription Revenue", "type": "REVENUE", "parent": "4100"},
    {"code": "4130", "name": "Maintenance Contracts", "type": "REVENUE", "parent": "4100"},

    // EXPENSES - Service Specific
    {"code": "5100", "name": "Cost of Services", "type": "EXPENSE", "parent": "5000"},
    {"code": "5110", "name": "Professional Staff Costs", "type": "EXPENSE", "parent": "5100"},
    {"code": "5120", "name": "Subcontractor Costs", "type": "EXPENSE", "parent": "5100"}
  ]
}
```

#### NGO COA
**File**: `fixtures/defaults/ngo/chart_of_accounts.json`

```json
{
  "industry": "NGO",
  "accounts": [
    // ASSETS - NGO specific
    {"code": "1100", "name": "Current Assets", "type": "ASSET"},
    {"code": "1110", "name": "Unrestricted Funds", "type": "ASSET", "parent": "1100"},
    {"code": "1120", "name": "Restricted Funds", "type": "ASSET", "parent": "1100"},
    {"code": "1130", "name": "Donor Receivables", "type": "ASSET", "parent": "1100"},

    // EQUITY - NGO terminology
    {"code": "3000", "name": "NET ASSETS", "type": "EQUITY"},
    {"code": "3100", "name": "Unrestricted Net Assets", "type": "EQUITY", "parent": "3000"},
    {"code": "3200", "name": "Temporarily Restricted Net Assets", "type": "EQUITY", "parent": "3000"},
    {"code": "3300", "name": "Permanently Restricted Net Assets", "type": "EQUITY", "parent": "3000"},

    // REVENUE - NGO terminology
    {"code": "4000", "name": "SUPPORT AND REVENUE", "type": "REVENUE"},
    {"code": "4100", "name": "Grants & Donations", "type": "REVENUE", "parent": "4000"},
    {"code": "4110", "name": "Government Grants", "type": "REVENUE", "parent": "4100"},
    {"code": "4120", "name": "Corporate Donations", "type": "REVENUE", "parent": "4100"},
    {"code": "4130", "name": "Individual Donations", "type": "REVENUE", "parent": "4100"},
    {"code": "4140", "name": "Foundation Grants", "type": "REVENUE", "parent": "4100"},

    // EXPENSES - NGO program accounting
    {"code": "5000", "name": "EXPENSES", "type": "EXPENSE"},
    {"code": "5100", "name": "Program Expenses", "type": "EXPENSE", "parent": "5000"},
    {"code": "5110", "name": "Education Program", "type": "EXPENSE", "parent": "5100"},
    {"code": "5120", "name": "Healthcare Program", "type": "EXPENSE", "parent": "5100"},
    {"code": "5200", "name": "Administrative Expenses", "type": "EXPENSE", "parent": "5000"},
    {"code": "5300", "name": "Fundraising Expenses", "type": "EXPENSE", "parent": "5000"}
  ]
}
```

### 1.4 Industry-Specific Item Categories

#### Manufacturing Item Categories
```json
{
  "industry": "MANUFACTURING",
  "categories": [
    {"code": "RM", "name": "Raw Materials", "sub_categories": [
      {"code": "RM-MTL", "name": "Metals & Alloys"},
      {"code": "RM-CHM", "name": "Chemicals"},
      {"code": "RM-PLT", "name": "Plastics & Polymers"},
      {"code": "RM-TXT", "name": "Textiles"}
    ]},
    {"code": "COMP", "name": "Components", "sub_categories": [
      {"code": "COMP-ELC", "name": "Electronic Components"},
      {"code": "COMP-MCH", "name": "Mechanical Parts"},
      {"code": "COMP-HYD", "name": "Hydraulic Components"}
    ]},
    {"code": "CONS", "name": "Consumables", "sub_categories": [
      {"code": "CONS-TOL", "name": "Tools & Dies"},
      {"code": "CONS-LUB", "name": "Lubricants & Oils"},
      {"code": "CONS-CLN", "name": "Cleaning Materials"}
    ]},
    {"code": "PKG", "name": "Packing Materials", "sub_categories": [
      {"code": "PKG-BOX", "name": "Boxes & Cartons"},
      {"code": "PKG-WRAP", "name": "Wrapping Materials"}
    ]},
    {"code": "SF", "name": "Semi-Finished Goods"},
    {"code": "FG", "name": "Finished Goods"},
    {"code": "FA", "name": "Fixed Assets", "sub_categories": [
      {"code": "FA-MCH", "name": "Machinery"},
      {"code": "FA-VEH", "name": "Vehicles"}
    ]}
  ]
}
```

#### Trading Item Categories
```json
{
  "industry": "TRADING",
  "categories": [
    {"code": "TG", "name": "Trading Goods", "sub_categories": [
      {"code": "TG-ELC", "name": "Electronics"},
      {"code": "TG-APP", "name": "Appliances"},
      {"code": "TG-FUR", "name": "Furniture"},
      {"code": "TG-TEX", "name": "Textiles & Garments"}
    ]},
    {"code": "CONS", "name": "Consumables", "sub_categories": [
      {"code": "CONS-OFF", "name": "Office Supplies"},
      {"code": "CONS-PKG", "name": "Packing Materials"}
    ]},
    {"code": "FA", "name": "Fixed Assets"}
  ]
}
```

#### Service Item Categories (Minimal)
```json
{
  "industry": "SERVICE",
  "categories": [
    {"code": "SERV", "name": "Service Items", "sub_categories": [
      {"code": "SERV-SUB", "name": "Subcontracted Services"},
      {"code": "SERV-SUP", "name": "Service Supplies"}
    ]},
    {"code": "CONS", "name": "Consumables", "sub_categories": [
      {"code": "CONS-OFF", "name": "Office Supplies"}
    ]},
    {"code": "FA", "name": "Fixed Assets", "sub_categories": [
      {"code": "FA-IT", "name": "IT Equipment"},
      {"code": "FA-FUR", "name": "Office Furniture"}
    ]}
  ]
}
```

### 1.5 Enhanced Default Data Service

**File**: `backend/apps/metadata/services/default_data_service.py`

```python
"""
Enhanced service to populate industry-specific default master data
"""
import json
import os
from decimal import Decimal
from django.db import transaction
from apps.finance.models import Account, Currency, ExchangeRate
from apps.inventory.models import ItemCategory
from apps.sales.models import ProductCategory
from apps.companies.models import Department, Company, CompanyCategory
from apps.budgeting.models import CostCenter


class DefaultDataService:

    # Industry to fixture mapping
    INDUSTRY_FIXTURES = {
        CompanyCategory.MANUFACTURING: 'manufacturing',
        CompanyCategory.TRADING: 'trading',
        CompanyCategory.RETAIL: 'retail',
        CompanyCategory.SERVICE: 'service',
        CompanyCategory.NGO: 'ngo',
        CompanyCategory.CONSTRUCTION: 'construction',
        CompanyCategory.HEALTHCARE: 'healthcare',
        CompanyCategory.EDUCATION: 'education',
        CompanyCategory.AGRICULTURE: 'agriculture',
        CompanyCategory.TECHNOLOGY: 'technology',
        CompanyCategory.HOSPITALITY: 'hospitality',
        CompanyCategory.TRANSPORT: 'transport',
        CompanyCategory.REAL_ESTATE: 'real_estate',
        CompanyCategory.FINANCIAL: 'financial',
        CompanyCategory.OTHER: 'common',
    }

    @classmethod
    @transaction.atomic
    def populate_defaults_for_company(cls, company, force_refresh=False):
        """
        Populate industry-specific default master data for a company

        Args:
            company: Company instance
            force_refresh: If True, deletes existing defaults and recreates

        Returns:
            dict: Summary of created records
        """
        industry = company.industry_category
        industry_folder = cls.INDUSTRY_FIXTURES.get(industry, 'common')

        summary = {
            'industry': industry,
            'currencies_created': 0,
            'accounts_created': 0,
            'item_categories_created': 0,
            'product_categories_created': 0,
            'departments_created': 0,
            'cost_centers_created': 0,
        }

        # 1. Create currencies (if multi-currency enabled)
        if company.enable_multi_currency:
            summary['currencies_created'] = cls._create_default_currencies(company)

        # 2. Create industry-specific chart of accounts
        summary['accounts_created'] = cls._create_industry_accounts(
            company, industry_folder
        )

        # 3. Create industry-specific item categories
        summary['item_categories_created'] = cls._create_industry_item_categories(
            company, industry_folder
        )

        # 4. Create industry-specific product categories
        summary['product_categories_created'] = cls._create_industry_product_categories(
            company, industry_folder
        )

        # 5. Create industry-specific departments
        summary['departments_created'] = cls._create_industry_departments(
            company, industry_folder
        )

        # 6. Create industry-specific cost centers
        summary['cost_centers_created'] = cls._create_industry_cost_centers(
            company, industry_folder
        )

        return summary

    @classmethod
    def _create_default_currencies(cls, company):
        """Create default currencies with base currency"""
        from apps.finance.models import Currency, ExchangeRate
        from datetime import date

        # Standard currencies
        default_currencies = [
            {'code': 'BDT', 'name': 'Bangladeshi Taka', 'symbol': '৳'},
            {'code': 'USD', 'name': 'US Dollar', 'symbol': '$'},
            {'code': 'EUR', 'name': 'Euro', 'symbol': '€'},
            {'code': 'GBP', 'name': 'British Pound', 'symbol': '£'},
            {'code': 'INR', 'name': 'Indian Rupee', 'symbol': '₹'},
            {'code': 'JPY', 'name': 'Japanese Yen', 'symbol': '¥'},
            {'code': 'CNY', 'name': 'Chinese Yuan', 'symbol': '¥'},
        ]

        created_count = 0
        for curr_data in default_currencies:
            currency, created = Currency.objects.get_or_create(
                company=company,
                code=curr_data['code'],
                defaults={
                    'name': curr_data['name'],
                    'symbol': curr_data['symbol'],
                    'is_active': True,
                    'is_base_currency': (curr_data['code'] == company.base_currency)
                }
            )
            if created:
                created_count += 1

                # Create initial exchange rate (base currency = 1.0)
                if curr_data['code'] == company.base_currency:
                    ExchangeRate.objects.create(
                        company=company,
                        from_currency=currency,
                        to_currency=currency,
                        rate=Decimal('1.0'),
                        effective_date=date.today()
                    )

        return created_count

    @classmethod
    def _create_industry_accounts(cls, company, industry_folder):
        """Create industry-specific chart of accounts"""
        fixture_path = os.path.join(
            os.path.dirname(__file__),
            f'../fixtures/defaults/{industry_folder}/chart_of_accounts.json'
        )

        if not os.path.exists(fixture_path):
            # Fallback to common
            fixture_path = os.path.join(
                os.path.dirname(__file__),
                '../fixtures/defaults/common/chart_of_accounts.json'
            )

        with open(fixture_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        account_map = {}
        created_count = 0

        # Create in hierarchical order
        for level in range(6):  # Support up to 6 levels
            for acc_data in data.get('accounts', []):
                if acc_data.get('level', 0) == level:
                    parent = None
                    if acc_data.get('parent'):
                        parent = account_map.get(acc_data['parent'])

                    # Multi-currency support
                    account = Account.objects.create(
                        company_group=company.company_group,
                        company=company,
                        code=acc_data['code'],
                        name=acc_data['name'],
                        account_type=acc_data['type'],
                        parent_account=parent,
                        currency=company.base_currency,
                        is_multi_currency=company.enable_multi_currency,
                        is_active=True,
                        is_default_template=True,
                        allow_direct_posting=acc_data.get('allow_posting', True)
                    )
                    account_map[acc_data['code']] = account
                    created_count += 1

        return created_count

    @classmethod
    def _create_industry_item_categories(cls, company, industry_folder):
        """Create industry-specific item categories with sub-categories"""
        fixture_path = os.path.join(
            os.path.dirname(__file__),
            f'../fixtures/defaults/{industry_folder}/item_categories.json'
        )

        if not os.path.exists(fixture_path):
            fixture_path = os.path.join(
                os.path.dirname(__file__),
                '../fixtures/defaults/common/item_categories.json'
            )

        with open(fixture_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        category_map = {}
        created_count = 0

        # Create parent categories first
        for cat_data in data.get('categories', []):
            category = ItemCategory.objects.create(
                company=company,
                code=cat_data['code'],
                name=cat_data['name'],
                description=cat_data.get('description', ''),
                is_active=True,
                is_default_template=True
            )
            category_map[cat_data['code']] = category
            created_count += 1

            # Create sub-categories
            for sub_data in cat_data.get('sub_categories', []):
                sub_category = ItemCategory.objects.create(
                    company=company,
                    code=sub_data['code'],
                    name=sub_data['name'],
                    description=sub_data.get('description', ''),
                    parent_category=category,
                    is_active=True,
                    is_default_template=True
                )
                category_map[sub_data['code']] = sub_category
                created_count += 1

                # Create sub-sub-categories (3rd level)
                for subsub_data in sub_data.get('sub_categories', []):
                    ItemCategory.objects.create(
                        company=company,
                        code=subsub_data['code'],
                        name=subsub_data['name'],
                        description=subsub_data.get('description', ''),
                        parent_category=sub_category,
                        is_active=True,
                        is_default_template=True
                    )
                    created_count += 1

        return created_count

    @classmethod
    def _create_industry_product_categories(cls, company, industry_folder):
        """Create industry-specific product categories"""
        # Similar implementation to item categories
        # ... code here ...
        return 0

    @classmethod
    def _create_industry_departments(cls, company, industry_folder):
        """Create industry-specific departments"""
        # ... code here ...
        return 0

    @classmethod
    def _create_industry_cost_centers(cls, company, industry_folder):
        """Create industry-specific cost centers"""
        # ... code here ...
        return 0
```

---

## Part 2: Multi-Currency Support

### 2.1 Enhanced Account Model

**File**: `backend/apps/finance/models.py`

```python
class Account(models.Model):
    # ... existing fields ...

    # NEW: Multi-currency fields
    currency = models.CharField(
        max_length=3,
        default='BDT',
        help_text="Primary currency for this account"
    )

    is_multi_currency = models.BooleanField(
        default=False,
        help_text="If True, can have transactions in multiple currencies"
    )

    # Balances
    current_balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text="Balance in primary currency"
    )

    # NEW: Currency-specific balances (JSON)
    currency_balances = models.JSONField(
        default=dict,
        blank=True,
        help_text="Balances by currency: {'USD': 1000.00, 'EUR': 500.00}"
    )
```

### 2.2 Currency Models

**File**: `backend/apps/finance/models.py`

```python
class Currency(models.Model):
    """Currency master data"""
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    code = models.CharField(max_length=3, help_text="ISO 4217 code: USD, EUR, BDT")
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    decimal_places = models.IntegerField(default=2)
    is_active = models.BooleanField(default=True)
    is_base_currency = models.BooleanField(default=False)

    class Meta:
        unique_together = ('company', 'code')
        verbose_name_plural = 'Currencies'

    def __str__(self):
        return f"{self.code} - {self.name}"


class ExchangeRate(models.Model):
    """Exchange rates between currencies"""
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    from_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='rates_from'
    )
    to_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='rates_to'
    )
    rate = models.DecimalField(max_digits=20, decimal_places=6)
    effective_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:
        unique_together = ('company', 'from_currency', 'to_currency', 'effective_date')
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.from_currency.code} → {self.to_currency.code}: {self.rate}"


class CurrencyConversionService:
    """Service for currency conversion"""

    @staticmethod
    def convert(
        amount,
        from_currency_code,
        to_currency_code,
        company,
        as_of_date=None
    ):
        """
        Convert amount from one currency to another

        Args:
            amount: Decimal amount to convert
            from_currency_code: Source currency code (e.g., 'USD')
            to_currency_code: Target currency code (e.g., 'BDT')
            company: Company instance
            as_of_date: Date for exchange rate (defaults to today)

        Returns:
            Decimal: Converted amount
        """
        from datetime import date
        from decimal import Decimal

        if from_currency_code == to_currency_code:
            return amount

        if as_of_date is None:
            as_of_date = date.today()

        # Get exchange rate
        try:
            from_curr = Currency.objects.get(company=company, code=from_currency_code)
            to_curr = Currency.objects.get(company=company, code=to_currency_code)

            rate = ExchangeRate.objects.filter(
                company=company,
                from_currency=from_curr,
                to_currency=to_curr,
                effective_date__lte=as_of_date
            ).order_by('-effective_date').first()

            if not rate:
                raise ValueError(
                    f"No exchange rate found for {from_currency_code} → "
                    f"{to_currency_code} as of {as_of_date}"
                )

            return amount * rate.rate

        except Currency.DoesNotExist:
            raise ValueError(f"Currency not found: {from_currency_code} or {to_currency_code}")
```

---

## Part 3: On-Demand Financial Statements (IAS Format)

### 3.1 Financial Statement Models

**NEW FILE**: `backend/apps/finance/models/financial_statements.py`

```python
"""
Models for on-demand financial statement generation
"""
from django.db import models
from django.conf import settings


class FinancialStatementType(models.TextChoices):
    PROFIT_LOSS = 'PROFIT_LOSS', 'Profit & Loss Statement (IAS 1)'
    BALANCE_SHEET = 'BALANCE_SHEET', 'Statement of Financial Position (IAS 1)'
    CASH_FLOW = 'CASH_FLOW', 'Cash Flow Statement (IAS 7)'
    CHANGES_EQUITY = 'CHANGES_EQUITY', 'Statement of Changes in Equity'
    COMPREHENSIVE_INCOME = 'COMPREHENSIVE_INCOME', 'Statement of Comprehensive Income'


class FinancialStatementTemplate(models.Model):
    """
    Templates for financial statement generation
    Based on IAS/IFRS standards
    """
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    statement_type = models.CharField(
        max_length=30,
        choices=FinancialStatementType.choices
    )

    # IAS format configuration
    format_standard = models.CharField(
        max_length=20,
        choices=[
            ('IAS_1', 'IAS 1 - Presentation of Financial Statements'),
            ('IAS_7', 'IAS 7 - Cash Flow Statements'),
            ('IFRS', 'IFRS Standards'),
            ('GAAP', 'US GAAP'),
            ('CUSTOM', 'Custom Format'),
        ],
        default='IAS_1'
    )

    # Template structure (JSON)
    structure = models.JSONField(
        default=dict,
        help_text="Statement structure with line items and account mappings"
    )

    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company', 'name')


class FinancialStatementReport(models.Model):
    """
    Generated financial statement reports
    """
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    report_name = models.CharField(max_length=255)
    statement_type = models.CharField(
        max_length=30,
        choices=FinancialStatementType.choices
    )

    # Time period
    period_start = models.DateField()
    period_end = models.DateField()

    # Comparison period (optional)
    comparison_period_start = models.DateField(null=True, blank=True)
    comparison_period_end = models.DateField(null=True, blank=True)

    # Currency
    reporting_currency = models.CharField(max_length=3, default='BDT')

    # Generated data (JSON)
    report_data = models.JSONField(
        default=dict,
        help_text="Complete report data with all line items"
    )

    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    # Export tracking
    exported_to_excel = models.BooleanField(default=False)
    exported_to_pdf = models.BooleanField(default=False)

    class Meta:
        ordering = ['-generated_at']
```

### 3.2 Financial Statement Service

**NEW FILE**: `backend/apps/finance/services/financial_statement_service.py`

```python
"""
Service for generating financial statements
Compliant with IAS/IFRS standards
"""
from decimal import Decimal
from datetime import date, datetime
from django.db.models import Sum, Q
from apps.finance.models import (
    Account, AccountType, JournalVoucherLine,
    FinancialStatementReport, Currency
)
from apps.finance.services.currency_conversion_service import CurrencyConversionService


class FinancialStatementService:
    """
    Generate IAS-compliant financial statements on demand
    """

    @classmethod
    def generate_profit_loss_statement(
        cls,
        company,
        period_start,
        period_end,
        comparison_period_start=None,
        comparison_period_end=None,
        reporting_currency=None,
        format_type='FUNCTION'  # or 'NATURE'
    ):
        """
        Generate Profit & Loss Statement (IAS 1 compliant)

        Format options:
        - FUNCTION: Classification by function (COGS, Admin, Selling)
        - NATURE: Classification by nature (Materials, Labor, Depreciation)

        Returns:
            dict: Complete P&L statement with all line items
        """
        if reporting_currency is None:
            reporting_currency = company.base_currency

        # Initialize structure
        statement = {
            'company': company.name,
            'statement_type': 'Profit & Loss Statement',
            'format': f'IAS 1 - Classification by {format_type.title()}',
            'period': {
                'start': period_start.isoformat(),
                'end': period_end.isoformat(),
            },
            'currency': reporting_currency,
            'line_items': []
        }

        if comparison_period_start and comparison_period_end:
            statement['comparison_period'] = {
                'start': comparison_period_start.isoformat(),
                'end': comparison_period_end.isoformat(),
            }

        # Get revenue
        revenue = cls._get_account_balance(
            company,
            AccountType.REVENUE,
            period_start,
            period_end,
            reporting_currency
        )

        statement['line_items'].append({
            'line': 'Revenue',
            'amount': float(revenue),
            'level': 1
        })

        if format_type == 'FUNCTION':
            # Cost of Goods Sold
            cogs = cls._get_cogs_balance(
                company, period_start, period_end, reporting_currency
            )
            statement['line_items'].append({
                'line': 'Cost of Goods Sold',
                'amount': float(cogs),
                'level': 1
            })

            # Gross Profit
            gross_profit = revenue + cogs  # COGS is negative
            statement['line_items'].append({
                'line': 'Gross Profit',
                'amount': float(gross_profit),
                'level': 1,
                'is_subtotal': True,
                'style': 'bold'
            })

            # Operating Expenses
            selling_expenses = cls._get_selling_expenses(
                company, period_start, period_end, reporting_currency
            )
            statement['line_items'].append({
                'line': 'Selling Expenses',
                'amount': float(selling_expenses),
                'level': 1
            })

            admin_expenses = cls._get_admin_expenses(
                company, period_start, period_end, reporting_currency
            )
            statement['line_items'].append({
                'line': 'Administrative Expenses',
                'amount': float(admin_expenses),
                'level': 1
            })

            # Operating Profit
            operating_profit = gross_profit + selling_expenses + admin_expenses
            statement['line_items'].append({
                'line': 'Operating Profit',
                'amount': float(operating_profit),
                'level': 1,
                'is_subtotal': True,
                'style': 'bold'
            })

        else:  # NATURE
            # Classification by expense nature
            materials_expense = cls._get_materials_expense(
                company, period_start, period_end, reporting_currency
            )
            statement['line_items'].append({
                'line': 'Raw Materials & Consumables',
                'amount': float(materials_expense),
                'level': 1
            })

            # Employee benefits
            employee_benefits = cls._get_employee_benefits(
                company, period_start, period_end, reporting_currency
            )
            statement['line_items'].append({
                'line': 'Employee Benefits Expense',
                'amount': float(employee_benefits),
                'level': 1
            })

            # Depreciation
            depreciation = cls._get_depreciation(
                company, period_start, period_end, reporting_currency
            )
            statement['line_items'].append({
                'line': 'Depreciation & Amortization',
                'amount': float(depreciation),
                'level': 1
            })

            # Other expenses
            other_expenses = cls._get_other_expenses(
                company, period_start, period_end, reporting_currency
            )
            statement['line_items'].append({
                'line': 'Other Operating Expenses',
                'amount': float(other_expenses),
                'level': 1
            })

        # Finance costs
        finance_costs = cls._get_finance_costs(
            company, period_start, period_end, reporting_currency
        )
        statement['line_items'].append({
            'line': 'Finance Costs',
            'amount': float(finance_costs),
            'level': 1
        })

        # Profit Before Tax
        total_expenses = sum(
            item['amount'] for item in statement['line_items']
            if not item.get('is_subtotal') and item['line'] != 'Revenue'
        )
        profit_before_tax = revenue + total_expenses  # Expenses are negative
        statement['line_items'].append({
            'line': 'Profit Before Tax',
            'amount': float(profit_before_tax),
            'level': 1,
            'is_subtotal': True,
            'style': 'bold'
        })

        # Tax expense
        tax_expense = cls._get_tax_expense(
            company, period_start, period_end, reporting_currency
        )
        statement['line_items'].append({
            'line': 'Income Tax Expense',
            'amount': float(tax_expense),
            'level': 1
        })

        # Net Profit
        net_profit = profit_before_tax + tax_expense
        statement['line_items'].append({
            'line': 'Net Profit for the Period',
            'amount': float(net_profit),
            'level': 1,
            'is_total': True,
            'style': 'bold_underline'
        })

        # Add comparison column if requested
        if comparison_period_start and comparison_period_end:
            cls._add_comparison_column(
                statement,
                company,
                comparison_period_start,
                comparison_period_end,
                reporting_currency
            )

        return statement

    @classmethod
    def generate_balance_sheet(
        cls,
        company,
        as_of_date,
        comparison_date=None,
        reporting_currency=None
    ):
        """
        Generate Statement of Financial Position (Balance Sheet)
        IAS 1 compliant format

        Returns:
            dict: Complete balance sheet with assets, liabilities, equity
        """
        if reporting_currency is None:
            reporting_currency = company.base_currency

        statement = {
            'company': company.name,
            'statement_type': 'Statement of Financial Position',
            'format': 'IAS 1',
            'as_of_date': as_of_date.isoformat(),
            'currency': reporting_currency,
            'assets': [],
            'liabilities': [],
            'equity': []
        }

        # ASSETS
        # Current Assets
        cash_balance = cls._get_cash_balance(company, as_of_date, reporting_currency)
        statement['assets'].append({
            'line': 'Cash and Cash Equivalents',
            'amount': float(cash_balance),
            'level': 2,
            'category': 'current'
        })

        receivables = cls._get_receivables_balance(company, as_of_date, reporting_currency)
        statement['assets'].append({
            'line': 'Trade and Other Receivables',
            'amount': float(receivables),
            'level': 2,
            'category': 'current'
        })

        inventory = cls._get_inventory_balance(company, as_of_date, reporting_currency)
        statement['assets'].append({
            'line': 'Inventories',
            'amount': float(inventory),
            'level': 2,
            'category': 'current'
        })

        current_assets_total = cash_balance + receivables + inventory
        statement['assets'].append({
            'line': 'Total Current Assets',
            'amount': float(current_assets_total),
            'level': 1,
            'is_subtotal': True,
            'style': 'bold'
        })

        # Non-Current Assets
        ppe = cls._get_ppe_balance(company, as_of_date, reporting_currency)
        statement['assets'].append({
            'line': 'Property, Plant and Equipment',
            'amount': float(ppe),
            'level': 2,
            'category': 'non_current'
        })

        intangibles = cls._get_intangibles_balance(company, as_of_date, reporting_currency)
        statement['assets'].append({
            'line': 'Intangible Assets',
            'amount': float(intangibles),
            'level': 2,
            'category': 'non_current'
        })

        non_current_assets_total = ppe + intangibles
        statement['assets'].append({
            'line': 'Total Non-Current Assets',
            'amount': float(non_current_assets_total),
            'level': 1,
            'is_subtotal': True,
            'style': 'bold'
        })

        total_assets = current_assets_total + non_current_assets_total
        statement['assets'].append({
            'line': 'TOTAL ASSETS',
            'amount': float(total_assets),
            'level': 0,
            'is_total': True,
            'style': 'bold_underline'
        })

        # LIABILITIES
        # Current Liabilities
        payables = cls._get_payables_balance(company, as_of_date, reporting_currency)
        statement['liabilities'].append({
            'line': 'Trade and Other Payables',
            'amount': float(payables),
            'level': 2,
            'category': 'current'
        })

        current_liabilities_total = payables
        statement['liabilities'].append({
            'line': 'Total Current Liabilities',
            'amount': float(current_liabilities_total),
            'level': 1,
            'is_subtotal': True,
            'style': 'bold'
        })

        # Non-Current Liabilities
        long_term_loans = cls._get_long_term_loans(company, as_of_date, reporting_currency)
        statement['liabilities'].append({
            'line': 'Long-term Loans',
            'amount': float(long_term_loans),
            'level': 2,
            'category': 'non_current'
        })

        non_current_liabilities_total = long_term_loans
        statement['liabilities'].append({
            'line': 'Total Non-Current Liabilities',
            'amount': float(non_current_liabilities_total),
            'level': 1,
            'is_subtotal': True,
            'style': 'bold'
        })

        total_liabilities = current_liabilities_total + non_current_liabilities_total
        statement['liabilities'].append({
            'line': 'TOTAL LIABILITIES',
            'amount': float(total_liabilities),
            'level': 0,
            'is_total': True,
            'style': 'bold_underline'
        })

        # EQUITY
        share_capital = cls._get_share_capital(company, as_of_date, reporting_currency)
        statement['equity'].append({
            'line': 'Share Capital',
            'amount': float(share_capital),
            'level': 2
        })

        retained_earnings = cls._get_retained_earnings(company, as_of_date, reporting_currency)
        statement['equity'].append({
            'line': 'Retained Earnings',
            'amount': float(retained_earnings),
            'level': 2
        })

        total_equity = share_capital + retained_earnings
        statement['equity'].append({
            'line': 'TOTAL EQUITY',
            'amount': float(total_equity),
            'level': 0,
            'is_total': True,
            'style': 'bold_underline'
        })

        # Total Liabilities + Equity (should equal Total Assets)
        statement['total_liabilities_equity'] = float(total_liabilities + total_equity)
        statement['balances_match'] = abs(total_assets - (total_liabilities + total_equity)) < 0.01

        return statement

    @classmethod
    def generate_cash_flow_statement(
        cls,
        company,
        period_start,
        period_end,
        reporting_currency=None,
        method='INDIRECT'  # or 'DIRECT'
    ):
        """
        Generate Cash Flow Statement (IAS 7 compliant)

        Methods:
        - INDIRECT: Start with net profit, adjust for non-cash items
        - DIRECT: Show actual cash receipts and payments

        Returns:
            dict: Cash flow statement with operating, investing, financing activities
        """
        if reporting_currency is None:
            reporting_currency = company.base_currency

        statement = {
            'company': company.name,
            'statement_type': 'Cash Flow Statement',
            'format': f'IAS 7 - {method.title()} Method',
            'period': {
                'start': period_start.isoformat(),
                'end': period_end.isoformat(),
            },
            'currency': reporting_currency,
            'operating_activities': [],
            'investing_activities': [],
            'financing_activities': []
        }

        if method == 'INDIRECT':
            # Start with net profit
            net_profit = cls._get_net_profit(
                company, period_start, period_end, reporting_currency
            )
            statement['operating_activities'].append({
                'line': 'Net Profit',
                'amount': float(net_profit),
                'level': 1
            })

            # Adjustments for non-cash items
            depreciation = cls._get_depreciation(
                company, period_start, period_end, reporting_currency
            )
            statement['operating_activities'].append({
                'line': 'Add: Depreciation & Amortization',
                'amount': float(depreciation),
                'level': 2
            })

            # Working capital changes
            receivables_change = cls._get_receivables_change(
                company, period_start, period_end, reporting_currency
            )
            statement['operating_activities'].append({
                'line': '(Increase)/Decrease in Receivables',
                'amount': float(receivables_change),
                'level': 2
            })

            inventory_change = cls._get_inventory_change(
                company, period_start, period_end, reporting_currency
            )
            statement['operating_activities'].append({
                'line': '(Increase)/Decrease in Inventory',
                'amount': float(inventory_change),
                'level': 2
            })

            payables_change = cls._get_payables_change(
                company, period_start, period_end, reporting_currency
            )
            statement['operating_activities'].append({
                'line': 'Increase/(Decrease) in Payables',
                'amount': float(payables_change),
                'level': 2
            })

            net_cash_operating = (
                net_profit + depreciation +
                receivables_change + inventory_change + payables_change
            )
            statement['operating_activities'].append({
                'line': 'Net Cash from Operating Activities',
                'amount': float(net_cash_operating),
                'level': 1,
                'is_subtotal': True,
                'style': 'bold'
            })

        # Investing Activities
        capex = cls._get_capex(company, period_start, period_end, reporting_currency)
        statement['investing_activities'].append({
            'line': 'Purchase of Property, Plant & Equipment',
            'amount': float(capex),
            'level': 2
        })

        net_cash_investing = capex
        statement['investing_activities'].append({
            'line': 'Net Cash from Investing Activities',
            'amount': float(net_cash_investing),
            'level': 1,
            'is_subtotal': True,
            'style': 'bold'
        })

        # Financing Activities
        loan_proceeds = cls._get_loan_proceeds(
            company, period_start, period_end, reporting_currency
        )
        statement['financing_activities'].append({
            'line': 'Proceeds from Loans',
            'amount': float(loan_proceeds),
            'level': 2
        })

        loan_repayments = cls._get_loan_repayments(
            company, period_start, period_end, reporting_currency
        )
        statement['financing_activities'].append({
            'line': 'Repayment of Loans',
            'amount': float(loan_repayments),
            'level': 2
        })

        net_cash_financing = loan_proceeds + loan_repayments
        statement['financing_activities'].append({
            'line': 'Net Cash from Financing Activities',
            'amount': float(net_cash_financing),
            'level': 1,
            'is_subtotal': True,
            'style': 'bold'
        })

        # Net Increase in Cash
        net_cash_change = net_cash_operating + net_cash_investing + net_cash_financing
        statement['net_cash_change'] = float(net_cash_change)

        # Cash at beginning
        cash_beginning = cls._get_cash_balance(company, period_start, reporting_currency)
        statement['cash_beginning'] = float(cash_beginning)

        # Cash at end
        cash_end = cash_beginning + net_cash_change
        statement['cash_end'] = float(cash_end)

        return statement

    # Helper methods for calculating balances
    @classmethod
    def _get_account_balance(
        cls,
        company,
        account_type,
        start_date,
        end_date,
        reporting_currency
    ):
        """Get total balance for accounts of given type"""
        accounts = Account.objects.filter(
            company=company,
            account_type=account_type,
            is_active=True
        )

        total = Decimal('0.00')
        for account in accounts:
            balance = cls._calculate_account_balance(
                account, start_date, end_date, reporting_currency
            )
            total += balance

        return total

    @classmethod
    def _calculate_account_balance(
        cls,
        account,
        start_date,
        end_date,
        reporting_currency
    ):
        """Calculate balance for a specific account in given currency"""
        lines = JournalVoucherLine.objects.filter(
            account=account,
            journal_voucher__journal_date__gte=start_date,
            journal_voucher__journal_date__lte=end_date,
            journal_voucher__status='POSTED'
        )

        debit_total = Decimal('0.00')
        credit_total = Decimal('0.00')

        for line in lines:
            # Convert to reporting currency if needed
            if line.currency != reporting_currency:
                debit_amount = CurrencyConversionService.convert(
                    line.debit_amount,
                    line.currency,
                    reporting_currency,
                    account.company,
                    line.journal_voucher.journal_date
                )
                credit_amount = CurrencyConversionService.convert(
                    line.credit_amount,
                    line.currency,
                    reporting_currency,
                    account.company,
                    line.journal_voucher.journal_date
                )
            else:
                debit_amount = line.debit_amount
                credit_amount = line.credit_amount

            debit_total += debit_amount
            credit_total += credit_amount

        # Return net balance based on account type
        if account.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
            return debit_total - credit_total
        else:
            return credit_total - debit_total

    # ... more helper methods for specific line items ...
```

### 3.3 Financial Statement Export Service

**NEW FILE**: `backend/apps/finance/services/financial_statement_export_service.py`

```python
"""
Export financial statements to Excel, PDF, CSV
"""
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import io


class FinancialStatementExportService:
    """Export financial statements to various formats"""

    @classmethod
    def export_to_excel(cls, statement_data, file_name="financial_statement.xlsx"):
        """
        Export financial statement to Excel with professional formatting

        Args:
            statement_data: Dictionary with statement data
            file_name: Output file name

        Returns:
            BytesIO: Excel file in memory
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = statement_data['statement_type'][:31]  # Max 31 chars

        # Styles
        title_font = Font(name='Arial', size=14, bold=True)
        header_font = Font(name='Arial', size=11, bold=True)
        subtotal_font = Font(name='Arial', size=10, bold=True)
        total_font = Font(name='Arial', size=11, bold=True)
        border_bottom = Border(bottom=Side(style='thin'))
        border_double = Border(bottom=Side(style='double'))

        # Header
        ws['A1'] = statement_data['company']
        ws['A1'].font = title_font

        ws['A2'] = statement_data['statement_type']
        ws['A2'].font = header_font

        period_text = f"Period: {statement_data['period']['start']} to {statement_data['period']['end']}"
        ws['A3'] = period_text

        ws['A4'] = f"Currency: {statement_data['currency']}"

        # Column headers
        row = 6
        ws[f'A{row}'] = 'Line Item'
        ws[f'B{row}'] = 'Amount'
        ws[f'A{row}'].font = header_font
        ws[f'B{row}'].font = header_font

        if 'comparison_period' in statement_data:
            ws[f'C{row}'] = 'Prior Period'
            ws[f'C{row}'].font = header_font

        # Data rows
        row += 1
        for item in statement_data['line_items']:
            # Indent based on level
            indent = '  ' * item.get('level', 0)
            ws[f'A{row}'] = indent + item['line']
            ws[f'B{row}'] = item['amount']

            # Formatting based on item type
            if item.get('is_total'):
                ws[f'A{row}'].font = total_font
                ws[f'B{row}'].font = total_font
                ws[f'B{row}'].border = border_double
            elif item.get('is_subtotal'):
                ws[f'A{row}'].font = subtotal_font
                ws[f'B{row}'].font = subtotal_font
                ws[f'B{row}'].border = border_bottom

            # Number formatting
            ws[f'B{row}'].number_format = '#,##0.00'

            if 'comparison_amount' in item:
                ws[f'C{row}'] = item['comparison_amount']
                ws[f'C{row}'].number_format = '#,##0.00'

            row += 1

        # Column widths
        ws.column_dimensions['A'].width = 50
        ws.column_dimensions['B'].width = 20
        if 'comparison_period' in statement_data:
            ws.column_dimensions['C'].width = 20

        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return output

    @classmethod
    def export_to_pdf(cls, statement_data, file_name="financial_statement.pdf"):
        """
        Export financial statement to PDF

        Returns:
            BytesIO: PDF file in memory
        """
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()

        # Title
        title = Paragraph(
            f"<b>{statement_data['company']}</b>",
            styles['Title']
        )
        story.append(title)

        subtitle = Paragraph(
            statement_data['statement_type'],
            styles['Heading2']
        )
        story.append(subtitle)

        # Period info
        period_text = f"Period: {statement_data['period']['start']} to {statement_data['period']['end']}"
        story.append(Paragraph(period_text, styles['Normal']))
        story.append(Paragraph(f"Currency: {statement_data['currency']}", styles['Normal']))
        story.append(Paragraph("<br/>", styles['Normal']))

        # Table data
        table_data = [['Line Item', 'Amount']]

        for item in statement_data['line_items']:
            indent = '    ' * item.get('level', 0)
            line_text = indent + item['line']
            amount_text = f"{item['amount']:,.2f}"
            table_data.append([line_text, amount_text])

        # Create table
        table = Table(table_data, colWidths=[400, 100])

        # Table style
        table_style = TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 11),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ])

        # Add bold for subtotals and totals
        for i, item in enumerate(statement_data['line_items'], start=1):
            if item.get('is_subtotal'):
                table_style.add('FONT', (0, i), (-1, i), 'Helvetica-Bold', 10)
                table_style.add('LINEABOVE', (0, i), (-1, i), 1, colors.black)
            elif item.get('is_total'):
                table_style.add('FONT', (0, i), (-1, i), 'Helvetica-Bold', 11)
                table_style.add('LINEABOVE', (0, i), (-1, i), 2, colors.black)
                table_style.add('LINEBELOW', (0, i), (-1, i), 2, colors.black)

        table.setStyle(table_style)
        story.append(table)

        # Build PDF
        doc.build(story)
        output.seek(0)

        return output
```

### 3.4 Financial Statement API Views

**NEW FILE**: `backend/apps/finance/views/financial_statement_views.py`

```python
"""
API views for on-demand financial statement generation
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from datetime import datetime, date

from apps.finance.services.financial_statement_service import FinancialStatementService
from apps.finance.services.financial_statement_export_service import FinancialStatementExportService


class FinancialStatementViewSet(ViewSet):
    """
    ViewSet for generating and exporting financial statements
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='profit-loss')
    def profit_loss_statement(self, request):
        """
        POST /api/finance/statements/profit-loss/

        Body:
        {
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "comparison_period_start": "2024-01-01",  // optional
            "comparison_period_end": "2024-12-31",    // optional
            "reporting_currency": "USD",               // optional
            "format_type": "FUNCTION",                 // FUNCTION or NATURE
            "export_format": "json"                    // json, excel, pdf
        }
        """
        company = getattr(request, 'company', None)
        if not company:
            return Response(
                {'error': 'Company context not set'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse dates
        period_start = datetime.strptime(
            request.data['period_start'], '%Y-%m-%d'
        ).date()
        period_end = datetime.strptime(
            request.data['period_end'], '%Y-%m-%d'
        ).date()

        comparison_start = None
        comparison_end = None
        if request.data.get('comparison_period_start'):
            comparison_start = datetime.strptime(
                request.data['comparison_period_start'], '%Y-%m-%d'
            ).date()
            comparison_end = datetime.strptime(
                request.data['comparison_period_end'], '%Y-%m-%d'
            ).date()

        # Generate statement
        statement_data = FinancialStatementService.generate_profit_loss_statement(
            company=company,
            period_start=period_start,
            period_end=period_end,
            comparison_period_start=comparison_start,
            comparison_period_end=comparison_end,
            reporting_currency=request.data.get('reporting_currency'),
            format_type=request.data.get('format_type', 'FUNCTION')
        )

        # Export if requested
        export_format = request.data.get('export_format', 'json')

        if export_format == 'excel':
            output = FinancialStatementExportService.export_to_excel(statement_data)
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="profit_loss_statement.xlsx"'
            return response

        elif export_format == 'pdf':
            output = FinancialStatementExportService.export_to_pdf(statement_data)
            response = HttpResponse(output.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="profit_loss_statement.pdf"'
            return response

        else:  # json
            return Response(statement_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='balance-sheet')
    def balance_sheet(self, request):
        """
        POST /api/finance/statements/balance-sheet/

        Body:
        {
            "as_of_date": "2025-12-31",
            "comparison_date": "2024-12-31",  // optional
            "reporting_currency": "USD",       // optional
            "export_format": "json"            // json, excel, pdf
        }
        """
        company = getattr(request, 'company', None)
        if not company:
            return Response(
                {'error': 'Company context not set'},
                status=status.HTTP_400_BAD_REQUEST
            )

        as_of_date = datetime.strptime(
            request.data['as_of_date'], '%Y-%m-%d'
        ).date()

        comparison_date = None
        if request.data.get('comparison_date'):
            comparison_date = datetime.strptime(
                request.data['comparison_date'], '%Y-%m-%d'
            ).date()

        # Generate statement
        statement_data = FinancialStatementService.generate_balance_sheet(
            company=company,
            as_of_date=as_of_date,
            comparison_date=comparison_date,
            reporting_currency=request.data.get('reporting_currency')
        )

        # Handle export
        export_format = request.data.get('export_format', 'json')

        if export_format == 'excel':
            output = FinancialStatementExportService.export_to_excel(statement_data)
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="balance_sheet.xlsx"'
            return response

        elif export_format == 'pdf':
            output = FinancialStatementExportService.export_to_pdf(statement_data)
            response = HttpResponse(output.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="balance_sheet.pdf"'
            return response

        else:
            return Response(statement_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='cash-flow')
    def cash_flow_statement(self, request):
        """
        POST /api/finance/statements/cash-flow/

        Body:
        {
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "method": "INDIRECT",              // INDIRECT or DIRECT
            "reporting_currency": "USD",        // optional
            "export_format": "json"             // json, excel, pdf
        }
        """
        company = getattr(request, 'company', None)
        if not company:
            return Response(
                {'error': 'Company context not set'},
                status=status.HTTP_400_BAD_REQUEST
            )

        period_start = datetime.strptime(
            request.data['period_start'], '%Y-%m-%d'
        ).date()
        period_end = datetime.strptime(
            request.data['period_end'], '%Y-%m-%d'
        ).date()

        # Generate statement
        statement_data = FinancialStatementService.generate_cash_flow_statement(
            company=company,
            period_start=period_start,
            period_end=period_end,
            reporting_currency=request.data.get('reporting_currency'),
            method=request.data.get('method', 'INDIRECT')
        )

        # Handle export
        export_format = request.data.get('export_format', 'json')

        if export_format == 'excel':
            output = FinancialStatementExportService.export_to_excel(statement_data)
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="cash_flow_statement.xlsx"'
            return response

        elif export_format == 'pdf':
            output = FinancialStatementExportService.export_to_pdf(statement_data)
            response = HttpResponse(output.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="cash_flow_statement.pdf"'
            return response

        else:
            return Response(statement_data, status=status.HTTP_200_OK)
```

---

## Part 4: Item Sub-Categories (Multi-Level Hierarchy)

### 4.1 Enhanced ItemCategory Model

**File**: `backend/apps/inventory/models.py`

```python
class ItemCategory(models.Model):
    """
    Hierarchical item categories with unlimited depth
    Supports: Category → Sub-Category → Sub-Sub-Category → ...
    """
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Hierarchical structure
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='sub_categories'
    )

    # Hierarchy path for efficient queries
    hierarchy_path = models.CharField(
        max_length=500,
        editable=False,
        blank=True,
        help_text='Path: 1/2/3/4 for efficient hierarchy queries'
    )

    # Level in hierarchy (0 = root, 1 = sub, 2 = sub-sub, etc.)
    level = models.IntegerField(default=0, editable=False)

    is_active = models.BooleanField(default=True)
    is_default_template = models.BooleanField(default=False)

    class Meta:
        unique_together = ('company', 'code')
        verbose_name_plural = 'Item Categories'
        ordering = ['hierarchy_path']

    def save(self, *args, **kwargs):
        # Calculate level and hierarchy path
        if self.parent_category:
            self.level = self.parent_category.level + 1
            parent_path = self.parent_category.hierarchy_path or str(self.parent_category.id)
            self.hierarchy_path = f"{parent_path}/{self.id or 'new'}"
        else:
            self.level = 0
            self.hierarchy_path = str(self.id or 'new')

        super().save(*args, **kwargs)

        # Update hierarchy path if this is a new record
        if 'new' in self.hierarchy_path:
            self.hierarchy_path = self.hierarchy_path.replace('new', str(self.id))
            ItemCategory.objects.filter(pk=self.pk).update(hierarchy_path=self.hierarchy_path)

    def get_ancestors(self):
        """Get all parent categories up to root"""
        ancestors = []
        current = self.parent_category
        while current:
            ancestors.insert(0, current)
            current = current.parent_category
        return ancestors

    def get_descendants(self):
        """Get all child categories (recursive)"""
        return ItemCategory.objects.filter(
            company=self.company,
            hierarchy_path__startswith=self.hierarchy_path + '/'
        )

    def get_full_path(self):
        """Get full category path: 'Raw Materials / Metals / Steel'"""
        ancestors = self.get_ancestors()
        path_parts = [a.name for a in ancestors] + [self.name]
        return ' / '.join(path_parts)

    def __str__(self):
        return self.get_full_path()
```

---

## Implementation Timeline (Enhanced)

### Week 1: Foundation
**Day 1-2**: Models & Migrations
- Create Item, Product, ProductCategory models
- Add multi-currency fields to Account
- Add industry_category to Company
- Create Currency, ExchangeRate models
- Add hierarchy_path to ItemCategory
- Create all migrations

**Day 3**: Industry-Specific Fixtures
- Create 15 industry-specific fixture files
- Manufacturing COA (80+ accounts)
- Trading COA (60+ accounts)
- Service COA (50+ accounts)
- NGO COA (70+ accounts)
- Item/Product categories for each industry

**Day 4-5**: Default Data Service
- Implement DefaultDataService
- Industry detection and fixture loading
- Multi-currency setup
- Hierarchical category creation
- Company creation signal

### Week 2: Financial Statements
**Day 6-7**: Financial Statement Service
- FinancialStatementService implementation
- Profit & Loss (both FUNCTION and NATURE format)
- Balance Sheet
- Cash Flow Statement (INDIRECT and DIRECT)
- Multi-currency conversion in statements

**Day 8-9**: Export Services
- Excel export with professional formatting
- PDF export with IAS-compliant layout
- CSV export for data analysis
- Export templates and styling

**Day 10**: Financial Statement API
- ViewSet for statement generation
- Query parameter validation
- Export format handling
- Error handling and logging

### Week 3: Data Migration & Backend
**Day 11-12**: Data Migration
- Split existing Product → Item + Product
- Migrate all ForeignKey references
- Update BudgetLine (product vs item)
- Data validation and integrity checks

**Day 13-14**: Backend Code Updates
- Update all views to use Item/Product correctly
- Update all serializers
- Update services (ValuationService, etc.)
- Update URL patterns

**Day 15**: Testing Framework
- Unit tests for all new services
- Integration tests for financial statements
- Migration tests

### Week 4: Frontend & Testing
**Day 16-18**: Frontend Implementation
- Item selector component
- Product selector component
- Financial statement generation UI
- Statement viewer with export buttons
- Currency selector

**Day 19**: Integration Testing
- End-to-end testing
- Financial statement accuracy validation
- Export format testing
- Multi-currency testing

**Day 20**: Documentation & Deployment
- User documentation
- API documentation
- Deployment to staging
- Production deployment

---

## Summary of All Files to Create/Modify

### New Files (47 total)
1. `backend/apps/inventory/models/item.py`
2. `backend/apps/sales/models/product.py`
3. `backend/apps/sales/models/product_category.py`
4. `backend/apps/finance/models/currency.py`
5. `backend/apps/finance/models/exchange_rate.py`
6. `backend/apps/finance/models/financial_statements.py`
7. `backend/apps/finance/services/currency_conversion_service.py`
8. `backend/apps/finance/services/financial_statement_service.py`
9. `backend/apps/finance/services/financial_statement_export_service.py`
10. `backend/apps/finance/views/financial_statement_views.py`
11. `backend/apps/metadata/services/default_data_service.py`
12-26. Industry-specific fixture files (15 files):
   - `fixtures/defaults/manufacturing/*.json` (5 files)
   - `fixtures/defaults/trading/*.json` (5 files)
   - `fixtures/defaults/service/*.json` (3 files)
   - `fixtures/defaults/ngo/*.json` (2 files)
27-40. Migration files (14 files)
41-47. Frontend components (7 files)

### Files to Modify (35+ files)
- All models with Product ForeignKey (10 files)
- All views using Product (10 files)
- All serializers using Product (8 files)
- Company model (1 file)
- Account model (1 file)
- BudgetLine model (1 file)
- Company signals (1 file)
- Finance URLs (1 file)
- Various service files (5+ files)

---

## Total Effort Estimate

**Backend Development**: 12-14 days
**Frontend Development**: 4-5 days
**Testing**: 3-4 days
**Documentation**: 2 days
**Deployment**: 1-2 days

**Total**: 22-27 days (4.5-5.5 weeks)

**Team Required**:
- 1 Senior Backend Developer (Full-time)
- 1 Junior Backend Developer (Support)
- 1 Frontend Developer (Full-time)
- 1 QA Engineer (Full-time)
- 1 DevOps Engineer (Part-time)

---

## Ready to Start?

This plan covers:
✅ Product to Item separation with revenue vs other budget split
✅ Industry-specific default master data (15 industries)
✅ Multi-currency support in accounts and statements
✅ On-demand IAS-compliant financial statements
✅ Export to Excel, PDF, CSV
✅ Multi-level item sub-categories

**Shall I begin implementation?**
