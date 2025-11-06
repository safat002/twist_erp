"""
Financial Statement Service.

Generates IAS/IFRS compliant financial statements:
- Balance Sheet (Statement of Financial Position) - IAS 1
- Income Statement (Statement of Comprehensive Income) - IAS 1
- Cash Flow Statement (placeholder)
"""
from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, List, Optional
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce

from apps.finance.models import Account, JournalEntry
from apps.companies.models import Company


class FinancialStatementService:
    """Service for generating financial statements."""

    def __init__(
        self,
        company: Company,
        start_date: date,
        end_date: date,
        currency: str = 'BDT',
        comparative_period: bool = False
    ):
        """
        Initialize the financial statement service.

        Args:
            company: Company to generate statements for
            start_date: Start date of the reporting period
            end_date: End date of the reporting period
            currency: Currency code for reporting
            comparative_period: Include comparative period data
        """
        self.company = company
        self.start_date = start_date
        self.end_date = end_date
        self.currency = currency
        self.comparative_period = comparative_period

    def generate_balance_sheet(self) -> Dict:
        """
        Generate Balance Sheet (Statement of Financial Position) - IAS 1 format.

        Returns:
            {
                'company': Company instance,
                'as_of_date': date,
                'currency': 'BDT',
                'assets': {
                    'current': [
                        {'name': 'Cash and Cash Equivalents', 'amount': Decimal('1000000.00')},
                        ...
                    ],
                    'non_current': [...],
                    'total_current': Decimal('5000000.00'),
                    'total_non_current': Decimal('3000000.00'),
                    'total': Decimal('8000000.00')
                },
                'liabilities': {...},
                'equity': {...},
                'total_liabilities_and_equity': Decimal('8000000.00')
            }
        """
        # Get account balances as of end_date
        assets = self._get_assets()
        liabilities = self._get_liabilities()
        equity = self._get_equity()

        return {
            'company': self.company,
            'as_of_date': self.end_date,
            'currency': self.currency,
            'assets': assets,
            'liabilities': liabilities,
            'equity': equity,
            'total_assets': assets['total'],
            'total_liabilities_and_equity': liabilities['total'] + equity['total'],
            'is_balanced': abs(assets['total'] - (liabilities['total'] + equity['total'])) < Decimal('0.01'),
        }

    def generate_income_statement(self) -> Dict:
        """
        Generate Income Statement (Statement of Comprehensive Income) - multi-step format.

        Returns:
            {
                'company': Company instance,
                'period': {'start': date, 'end': date},
                'currency': 'BDT',
                'revenue': {
                    'sales_revenue': Decimal('10000000.00'),
                    'other_income': Decimal('50000.00'),
                    'total': Decimal('10050000.00')
                },
                'cost_of_sales': Decimal('6000000.00'),
                'gross_profit': Decimal('4050000.00'),
                'operating_expenses': {...},
                'operating_profit': Decimal('1500000.00'),
                'finance_costs': Decimal('50000.00'),
                'profit_before_tax': Decimal('1450000.00'),
                'tax_expense': Decimal('200000.00'),
                'net_profit': Decimal('1250000.00')
            }
        """
        revenue = self._get_revenue()
        cost_of_sales = self._get_cost_of_sales()
        operating_expenses = self._get_operating_expenses()
        finance_costs = self._get_finance_costs()
        tax_expense = self._get_tax_expense()

        gross_profit = revenue['total'] - cost_of_sales
        operating_profit = gross_profit - operating_expenses['total']
        profit_before_tax = operating_profit - finance_costs
        net_profit = profit_before_tax - tax_expense

        return {
            'company': self.company,
            'period': {
                'start': self.start_date,
                'end': self.end_date
            },
            'currency': self.currency,
            'revenue': revenue,
            'cost_of_sales': cost_of_sales,
            'gross_profit': gross_profit,
            'gross_profit_margin': (gross_profit / revenue['total'] * 100) if revenue['total'] > 0 else Decimal('0.00'),
            'operating_expenses': operating_expenses,
            'operating_profit': operating_profit,
            'operating_profit_margin': (operating_profit / revenue['total'] * 100) if revenue['total'] > 0 else Decimal('0.00'),
            'finance_costs': finance_costs,
            'profit_before_tax': profit_before_tax,
            'tax_expense': tax_expense,
            'net_profit': net_profit,
            'net_profit_margin': (net_profit / revenue['total'] * 100) if revenue['total'] > 0 else Decimal('0.00'),
        }

    def _get_assets(self) -> Dict:
        """Get asset balances (current and non-current)."""
        asset_accounts = Account.objects.filter(
            company=self.company,
            account_type='ASSET',
            is_active=True
        )

        current_assets = []
        non_current_assets = []

        for account in asset_accounts:
            balance = self._get_account_balance(account, self.end_date)

            if balance != Decimal('0.00'):
                account_data = {
                    'code': account.code,
                    'name': account.name,
                    'amount': balance
                }

                # Simple classification: accounts starting with 11xx are current
                if account.code.startswith('11'):
                    current_assets.append(account_data)
                elif account.code.startswith('12'):
                    non_current_assets.append(account_data)

        total_current = sum(acc['amount'] for acc in current_assets)
        total_non_current = sum(acc['amount'] for acc in non_current_assets)

        return {
            'current': current_assets,
            'non_current': non_current_assets,
            'total_current': total_current,
            'total_non_current': total_non_current,
            'total': total_current + total_non_current
        }

    def _get_liabilities(self) -> Dict:
        """Get liability balances (current and non-current)."""
        liability_accounts = Account.objects.filter(
            company=self.company,
            account_type='LIABILITY',
            is_active=True
        )

        current_liabilities = []
        non_current_liabilities = []

        for account in liability_accounts:
            balance = self._get_account_balance(account, self.end_date)

            if balance != Decimal('0.00'):
                account_data = {
                    'code': account.code,
                    'name': account.name,
                    'amount': balance
                }

                # Simple classification: accounts starting with 21xx are current
                if account.code.startswith('21'):
                    current_liabilities.append(account_data)
                elif account.code.startswith('22'):
                    non_current_liabilities.append(account_data)

        total_current = sum(acc['amount'] for acc in current_liabilities)
        total_non_current = sum(acc['amount'] for acc in non_current_liabilities)

        return {
            'current': current_liabilities,
            'non_current': non_current_liabilities,
            'total_current': total_current,
            'total_non_current': total_non_current,
            'total': total_current + total_non_current
        }

    def _get_equity(self) -> Dict:
        """Get equity balances."""
        equity_accounts = Account.objects.filter(
            company=self.company,
            account_type='EQUITY',
            is_active=True
        )

        equity_items = []

        for account in equity_accounts:
            balance = self._get_account_balance(account, self.end_date)

            if balance != Decimal('0.00'):
                equity_items.append({
                    'code': account.code,
                    'name': account.name,
                    'amount': balance
                })

        total = sum(item['amount'] for item in equity_items)

        return {
            'items': equity_items,
            'total': total
        }

    def _get_revenue(self) -> Dict:
        """Get revenue for the period."""
        revenue_accounts = Account.objects.filter(
            company=self.company,
            account_type='REVENUE',
            is_active=True
        )

        revenue_items = []
        total = Decimal('0.00')

        for account in revenue_accounts:
            amount = self._get_period_movement(account)

            if amount != Decimal('0.00'):
                revenue_items.append({
                    'code': account.code,
                    'name': account.name,
                    'amount': amount
                })
                total += amount

        return {
            'items': revenue_items,
            'total': total
        }

    def _get_cost_of_sales(self) -> Decimal:
        """Get cost of sales/COGS for the period."""
        # Accounts typically starting with 5xxx
        cogs_accounts = Account.objects.filter(
            company=self.company,
            account_type='EXPENSE',
            code__startswith='5',
            is_active=True
        )

        total = Decimal('0.00')
        for account in cogs_accounts:
            total += self._get_period_movement(account)

        return total

    def _get_operating_expenses(self) -> Dict:
        """Get operating expenses for the period."""
        # Accounts typically starting with 6xxx
        expense_accounts = Account.objects.filter(
            company=self.company,
            account_type='EXPENSE',
            code__startswith='6',
            is_active=True
        )

        expense_items = []
        total = Decimal('0.00')

        for account in expense_accounts:
            amount = self._get_period_movement(account)

            if amount != Decimal('0.00'):
                expense_items.append({
                    'code': account.code,
                    'name': account.name,
                    'amount': amount
                })
                total += amount

        return {
            'items': expense_items,
            'total': total
        }

    def _get_finance_costs(self) -> Decimal:
        """Get finance costs for the period."""
        # Accounts typically starting with 7xxx
        finance_accounts = Account.objects.filter(
            company=self.company,
            account_type='EXPENSE',
            code__startswith='7',
            is_active=True
        )

        total = Decimal('0.00')
        for account in finance_accounts:
            total += self._get_period_movement(account)

        return total

    def _get_tax_expense(self) -> Decimal:
        """Get tax expense for the period."""
        # Find tax expense accounts (usually in expenses with 'tax' in name)
        tax_accounts = Account.objects.filter(
            company=self.company,
            account_type='EXPENSE',
            name__icontains='tax',
            is_active=True
        ).exclude(
            name__icontains='vat'  # Exclude VAT
        )

        total = Decimal('0.00')
        for account in tax_accounts:
            total += self._get_period_movement(account)

        return total

    def _get_account_balance(self, account: Account, as_of_date: date) -> Decimal:
        """
        Get account balance as of a specific date.

        For assets: Debit - Credit
        For liabilities/equity/revenue: Credit - Debit
        """
        lines = JournalEntry.objects.filter(
            account=account,
            voucher__entry_date__lte=as_of_date,
            voucher__status='POSTED'
        ).aggregate(
            total_debit=Coalesce(Sum('debit_amount'), Decimal('0.00')),
            total_credit=Coalesce(Sum('credit_amount'), Decimal('0.00'))
        )

        debit = lines['total_debit'] or Decimal('0.00')
        credit = lines['total_credit'] or Decimal('0.00')

        # Assets are debit balance accounts
        if account.account_type == 'ASSET':
            return debit - credit
        # Liabilities, Equity, Revenue are credit balance accounts
        else:
            return credit - debit

    def _get_period_movement(self, account: Account) -> Decimal:
        """
        Get account movement during the period (for P&L accounts).

        Returns positive number representing the absolute movement.
        """
        lines = JournalEntry.objects.filter(
            account=account,
            voucher__entry_date__gte=self.start_date,
            voucher__entry_date__lte=self.end_date,
            voucher__status='POSTED'
        ).aggregate(
            total_debit=Coalesce(Sum('debit_amount'), Decimal('0.00')),
            total_credit=Coalesce(Sum('credit_amount'), Decimal('0.00'))
        )

        debit = lines['total_debit'] or Decimal('0.00')
        credit = lines['total_credit'] or Decimal('0.00')

        # For Revenue accounts, credit is positive
        if account.account_type == 'REVENUE':
            return credit - debit
        # For Expense accounts, debit is positive
        elif account.account_type == 'EXPENSE':
            return debit - credit
        else:
            return abs(debit - credit)
