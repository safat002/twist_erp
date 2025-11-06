"""
Service for loading industry-specific default master data.

This service loads default Chart of Accounts, Item Categories, Product Categories,
and Tax Categories based on the company's industry category.
"""
import json
import os
from pathlib import Path
from decimal import Decimal
from typing import Dict, List, Optional, Any
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.companies.models import Company
from apps.finance.models import Account, Currency, ExchangeRate
from apps.inventory.models import ItemCategory, UnitOfMeasure
from apps.sales.models import ProductCategory, TaxCategory
from apps.budgeting.models import CostCenter

User = get_user_model()


class DefaultDataService:
    """Service for loading industry-specific default data."""

    # Path to fixture files
    FIXTURES_DIR = Path(__file__).parent.parent / 'fixtures' / 'industry_defaults'

    def __init__(self, company: Company, created_by: Optional[User] = None):
        """
        Initialize the service.

        Args:
            company: Company instance to load defaults for
            created_by: User who triggered the loading (optional)
        """
        self.company = company
        self.created_by = created_by or company.created_by
        self.industry = company.industry_category

    @transaction.atomic
    def load_all_defaults(self) -> Dict[str, int]:
        """
        Load all default data for the company's industry.

        Returns:
            Dictionary with counts of created records:
            {
                'currencies': 3,
                'accounts': 45,
                'item_categories': 12,
                'product_categories': 8,
                'tax_categories': 5,
                'cost_centers': 4,
                'uoms': 10
            }
        """
        if self.company.default_data_loaded:
            raise ValueError(f"Default data already loaded for {self.company.name}")

        results = {}

        # Load in specific order (due to dependencies)
        results['currencies'] = self._load_currencies()
        results['uoms'] = self._load_uoms()
        results['accounts'] = self._load_chart_of_accounts()
        results['item_categories'] = self._load_item_categories()
        results['product_categories'] = self._load_product_categories()
        results['tax_categories'] = self._load_tax_categories()
        # Cost centers require departments - skip for now
        # results['cost_centers'] = self._load_cost_centers()

        # Mark as loaded
        self.company.default_data_loaded = True
        self.company.default_data_loaded_at = timezone.now()
        self.company.save(update_fields=['default_data_loaded', 'default_data_loaded_at'])

        return results

    def _load_currencies(self) -> int:
        """Load default currencies (BDT, USD, EUR)."""
        currencies_data = [
            {
                'code': 'BDT',
                'name': 'Bangladeshi Taka',
                'symbol': '৳',
                'is_base_currency': True,
                'decimal_places': 2
            },
            {
                'code': 'USD',
                'name': 'US Dollar',
                'symbol': '$',
                'is_base_currency': False,
                'decimal_places': 2
            },
            {
                'code': 'EUR',
                'name': 'Euro',
                'symbol': '€',
                'is_base_currency': False,
                'decimal_places': 2
            }
        ]

        count = 0
        for data in currencies_data:
            currency, created = Currency.objects.get_or_create(
                company=self.company,
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'symbol': data['symbol'],
                    'is_base_currency': data['is_base_currency'],
                    'decimal_places': data['decimal_places'],
                    'is_active': True,
                    'created_by': self.created_by
                }
            )
            if created:
                count += 1

        # Create default exchange rates
        base_currency = Currency.objects.get(company=self.company, code='BDT')
        usd = Currency.objects.get(company=self.company, code='USD')
        eur = Currency.objects.get(company=self.company, code='EUR')

        ExchangeRate.objects.get_or_create(
            company=self.company,
            from_currency=base_currency,
            to_currency=usd,
            effective_date=timezone.now().date(),
            defaults={
                'rate': Decimal('0.0093'),  # 1 BDT = 0.0093 USD (approximate)
                'rate_type': 'SPOT',
                'is_active': True,
                'created_by': self.created_by
            }
        )

        ExchangeRate.objects.get_or_create(
            company=self.company,
            from_currency=base_currency,
            to_currency=eur,
            effective_date=timezone.now().date(),
            defaults={
                'rate': Decimal('0.0085'),  # 1 BDT = 0.0085 EUR (approximate)
                'rate_type': 'SPOT',
                'is_active': True,
                'created_by': self.created_by
            }
        )

        return count

    def _load_uoms(self) -> int:
        """Load default Units of Measure."""
        uoms_data = [
            {'code': 'PCS', 'name': 'Pieces', 'short_name': 'Pcs'},
            {'code': 'KG', 'name': 'Kilograms', 'short_name': 'Kg'},
            {'code': 'LTR', 'name': 'Liters', 'short_name': 'Ltr'},
            {'code': 'MTR', 'name': 'Meters', 'short_name': 'M'},
            {'code': 'BOX', 'name': 'Box', 'short_name': 'Box'},
            {'code': 'DOZEN', 'name': 'Dozen', 'short_name': 'Dzn'},
            {'code': 'HOUR', 'name': 'Hours', 'short_name': 'Hr'},
            {'code': 'DAY', 'name': 'Days', 'short_name': 'Day'},
            {'code': 'SQM', 'name': 'Square Meters', 'short_name': 'SqM'},
            {'code': 'TON', 'name': 'Metric Ton', 'short_name': 'Ton'},
        ]

        count = 0
        for data in uoms_data:
            uom, created = UnitOfMeasure.objects.get_or_create(
                company=self.company,
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'short_name': data.get('short_name', ''),
                    'is_active': True,
                    'created_by': self.created_by
                }
            )
            if created:
                count += 1

        return count

    def _load_chart_of_accounts(self) -> int:
        """Load industry-specific Chart of Accounts from JSON fixture."""
        fixture_file = self.FIXTURES_DIR / f'{self.industry.lower()}_accounts.json'

        if not fixture_file.exists():
            # Fall back to generic service industry template
            fixture_file = self.FIXTURES_DIR / 'service_accounts.json'

        if not fixture_file.exists():
            # Create minimal default accounts if no fixture exists
            return self._create_minimal_accounts()

        with open(fixture_file, 'r', encoding='utf-8') as f:
            accounts_data = json.load(f)

        return self._create_accounts_from_data(accounts_data)

    def _create_accounts_from_data(self, accounts_data: List[Dict]) -> int:
        """Create accounts from JSON data structure."""
        count = 0
        account_map = {}  # Maps code -> Account instance

        # Sort by hierarchy (parents first)
        accounts_data.sort(key=lambda x: len(x.get('code', '').split('-')))

        for account_data in accounts_data:
            parent = None
            parent_code = account_data.get('parent_code')
            if parent_code:
                parent = account_map.get(parent_code)

            account, created = Account.objects.get_or_create(
                company=self.company,
                code=account_data['code'],
                defaults={
                    'name': account_data['name'],
                    'account_type': account_data['account_type'],
                    'parent_account': parent,
                    'currency': account_data.get('currency', 'BDT'),
                    'is_active': account_data.get('is_active', True),
                    'is_default_template': True,
                    'created_by': self.created_by
                }
            )

            account_map[account_data['code']] = account
            if created:
                count += 1

        return count

    def _create_minimal_accounts(self) -> int:
        """Create minimal default accounts (fallback)."""
        minimal_accounts = [
            # Assets
            {'code': '1000', 'name': 'Assets', 'account_type': 'ASSET', 'parent_code': None},
            {'code': '1100', 'name': 'Current Assets', 'account_type': 'ASSET', 'parent_code': '1000'},
            {'code': '1110', 'name': 'Cash and Bank', 'account_type': 'ASSET', 'parent_code': '1100'},
            {'code': '1120', 'name': 'Accounts Receivable', 'account_type': 'ASSET', 'parent_code': '1100'},
            {'code': '1130', 'name': 'Inventory', 'account_type': 'ASSET', 'parent_code': '1100'},

            # Liabilities
            {'code': '2000', 'name': 'Liabilities', 'account_type': 'LIABILITY', 'parent_code': None},
            {'code': '2100', 'name': 'Current Liabilities', 'account_type': 'LIABILITY', 'parent_code': '2000'},
            {'code': '2110', 'name': 'Accounts Payable', 'account_type': 'LIABILITY', 'parent_code': '2100'},

            # Equity
            {'code': '3000', 'name': 'Equity', 'account_type': 'EQUITY', 'parent_code': None},
            {'code': '3100', 'name': 'Share Capital', 'account_type': 'EQUITY', 'parent_code': '3000'},

            # Revenue
            {'code': '4000', 'name': 'Revenue', 'account_type': 'REVENUE', 'parent_code': None},
            {'code': '4100', 'name': 'Sales Revenue', 'account_type': 'REVENUE', 'parent_code': '4000'},

            # Expenses
            {'code': '5000', 'name': 'Expenses', 'account_type': 'EXPENSE', 'parent_code': None},
            {'code': '5100', 'name': 'Cost of Sales', 'account_type': 'EXPENSE', 'parent_code': '5000'},
            {'code': '5200', 'name': 'Operating Expenses', 'account_type': 'EXPENSE', 'parent_code': '5000'},
        ]

        return self._create_accounts_from_data(minimal_accounts)

    def _load_item_categories(self) -> int:
        """Load industry-specific item categories."""
        fixture_file = self.FIXTURES_DIR / f'{self.industry.lower()}_item_categories.json'

        if not fixture_file.exists():
            return self._create_minimal_item_categories()

        with open(fixture_file, 'r', encoding='utf-8') as f:
            categories_data = json.load(f)

        return self._create_item_categories_from_data(categories_data)

    def _create_item_categories_from_data(self, categories_data: List[Dict]) -> int:
        """Create item categories from JSON data."""
        count = 0
        category_map = {}

        # Sort by level (parents first)
        categories_data.sort(key=lambda x: x.get('level', 0))

        for cat_data in categories_data:
            parent = None
            parent_code = cat_data.get('parent_code')
            if parent_code:
                parent = category_map.get(parent_code)

            category, created = ItemCategory.objects.get_or_create(
                company=self.company,
                code=cat_data['code'],
                defaults={
                    'name': cat_data['name'],
                    'parent_category': parent,
                    'is_active': True,
                    'is_default_template': True,
                    'created_by': self.created_by
                }
            )

            category_map[cat_data['code']] = category
            if created:
                count += 1

        return count

    def _create_minimal_item_categories(self) -> int:
        """Create minimal default item categories."""
        minimal_categories = [
            {'code': 'RAW', 'name': 'Raw Materials', 'parent_code': None, 'level': 0},
            {'code': 'CONS', 'name': 'Consumables', 'parent_code': None, 'level': 0},
            {'code': 'PKG', 'name': 'Packaging Materials', 'parent_code': None, 'level': 0},
            {'code': 'SPARE', 'name': 'Spare Parts', 'parent_code': None, 'level': 0},
        ]

        return self._create_item_categories_from_data(minimal_categories)

    def _load_product_categories(self) -> int:
        """Load industry-specific product categories (for saleable items)."""
        fixture_file = self.FIXTURES_DIR / f'{self.industry.lower()}_product_categories.json'

        if not fixture_file.exists():
            return self._create_minimal_product_categories()

        with open(fixture_file, 'r', encoding='utf-8') as f:
            categories_data = json.load(f)

        return self._create_product_categories_from_data(categories_data)

    def _create_product_categories_from_data(self, categories_data: List[Dict]) -> int:
        """Create product categories from JSON data."""
        count = 0
        category_map = {}

        categories_data.sort(key=lambda x: x.get('level', 0))

        for cat_data in categories_data:
            parent = None
            parent_code = cat_data.get('parent_code')
            if parent_code:
                parent = category_map.get(parent_code)

            category, created = ProductCategory.objects.get_or_create(
                company=self.company,
                code=cat_data['code'],
                defaults={
                    'name': cat_data['name'],
                    'description': cat_data.get('description', ''),
                    'parent_category': parent,
                    'is_active': True,
                    'is_featured': cat_data.get('is_featured', False),
                    'is_default_template': True,
                    'created_by': self.created_by
                }
            )

            category_map[cat_data['code']] = category
            if created:
                count += 1

        return count

    def _create_minimal_product_categories(self) -> int:
        """Create minimal default product categories."""
        minimal_categories = [
            {'code': 'PROD', 'name': 'Products', 'parent_code': None, 'level': 0},
            {'code': 'SERV', 'name': 'Services', 'parent_code': None, 'level': 0},
        ]

        return self._create_product_categories_from_data(minimal_categories)

    def _load_tax_categories(self) -> int:
        """Load default tax categories."""
        tax_categories = [
            {
                'code': 'VAT-15',
                'name': 'VAT 15%',
                'tax_rate': Decimal('15.00'),
                'description': 'Standard VAT rate'
            },
            {
                'code': 'VAT-7.5',
                'name': 'VAT 7.5%',
                'tax_rate': Decimal('7.50'),
                'description': 'Reduced VAT rate'
            },
            {
                'code': 'VAT-0',
                'name': 'Zero-rated VAT',
                'tax_rate': Decimal('0.00'),
                'description': 'Zero-rated items'
            },
            {
                'code': 'EXEMPT',
                'name': 'VAT Exempt',
                'tax_rate': Decimal('0.00'),
                'description': 'VAT exempt items'
            },
        ]

        count = 0
        for tax_data in tax_categories:
            tax_cat, created = TaxCategory.objects.get_or_create(
                company=self.company,
                code=tax_data['code'],
                defaults={
                    'name': tax_data['name'],
                    'tax_rate': tax_data['tax_rate'],
                    'description': tax_data['description'],
                    'is_active': True,
                    'created_by': self.created_by
                }
            )
            if created:
                count += 1

        return count

    def _load_cost_centers(self) -> int:
        """
        Load default cost centers.

        NOTE: Cost centers require departments, which are company-specific.
        This method is currently disabled in load_all_defaults().
        Companies should create their own organizational structure.
        """
        # Cost centers require departments - not suitable for default loading
        return 0
