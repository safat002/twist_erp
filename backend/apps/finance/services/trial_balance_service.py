"""
Trial Balance Service.

Generates trial balance reports with multi-currency support.
"""
from decimal import Decimal
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
from django.db.models import Q, Sum, F
from django.db.models.functions import Coalesce

from apps.finance.models import Account, JournalEntry, Currency, ExchangeRate
from apps.companies.models import Company


class TrialBalanceService:
    """Service for generating trial balance reports."""

    def __init__(self, company: Company, as_of_date: Optional[date] = None, currency: str = 'BDT'):
        """
        Initialize the trial balance service.

        Args:
            company: Company to generate trial balance for
            as_of_date: Date to generate trial balance as of (defaults to today)
            currency: Currency code for reporting (defaults to base currency)
        """
        self.company = company
        self.as_of_date = as_of_date or date.today()
        self.currency = currency

    def generate(self) -> Dict:
        """
        Generate trial balance.

        Returns:
            {
                'company': Company instance,
                'as_of_date': date,
                'currency': 'BDT',
                'accounts': [
                    {
                        'account': Account instance,
                        'code': '1000',
                        'name': 'Assets',
                        'level': 0,
                        'debit': Decimal('1000000.00'),
                        'credit': Decimal('0.00'),
                        'balance': Decimal('1000000.00')
                    },
                    ...
                ],
                'total_debit': Decimal('5000000.00'),
                'total_credit': Decimal('5000000.00'),
                'difference': Decimal('0.00')
            }
        """
        # Get all active accounts with hierarchy
        accounts = Account.objects.filter(
            company=self.company,
            is_active=True
        ).order_by('code')

        account_balances = []
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')

        for account in accounts:
            debit, credit = self._get_account_balance(account)
            balance = debit - credit

            # For certain account types, credit is positive
            if account.account_type in ['LIABILITY', 'EQUITY', 'REVENUE']:
                balance = credit - debit

            account_balances.append({
                'account': account,
                'code': account.code,
                'name': account.name,
                'account_type': account.account_type,
                'level': self._get_account_level(account),
                'debit': debit,
                'credit': credit,
                'balance': balance,
                'is_parent': self._has_children(account),
            })

            total_debit += debit
            total_credit += credit

        return {
            'company': self.company,
            'as_of_date': self.as_of_date,
            'currency': self.currency,
            'accounts': account_balances,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'difference': total_debit - total_credit,
            'is_balanced': abs(total_debit - total_credit) < Decimal('0.01'),
        }

    def _get_account_balance(self, account: Account) -> Tuple[Decimal, Decimal]:
        """
        Get debit and credit totals for an account.

        Returns:
            (debit_total, credit_total)
        """
        # Get all journal entries for this account up to as_of_date
        lines = JournalEntry.objects.filter(
            account=account,
            voucher__entry_date__lte=self.as_of_date,
            voucher__status='POSTED'
        ).aggregate(
            total_debit=Coalesce(Sum('debit_amount'), Decimal('0.00')),
            total_credit=Coalesce(Sum('credit_amount'), Decimal('0.00'))
        )

        debit = lines['total_debit'] or Decimal('0.00')
        credit = lines['total_credit'] or Decimal('0.00')

        return debit, credit

    def _get_account_level(self, account: Account) -> int:
        """Get the hierarchy level of an account."""
        level = 0
        current = account
        while current.parent_account:
            level += 1
            current = current.parent_account
        return level

    def _has_children(self, account: Account) -> bool:
        """Check if account has child accounts."""
        return Account.objects.filter(parent_account=account).exists()

    def export_to_dict(self) -> Dict:
        """Export trial balance to dictionary for serialization."""
        data = self.generate()

        # Convert to serializable format
        return {
            'company_name': data['company'].name,
            'as_of_date': data['as_of_date'].isoformat(),
            'currency': data['currency'],
            'accounts': [
                {
                    'code': acc['code'],
                    'name': acc['name'],
                    'account_type': acc['account_type'],
                    'level': acc['level'],
                    'debit': str(acc['debit']),
                    'credit': str(acc['credit']),
                    'balance': str(acc['balance']),
                    'is_parent': acc['is_parent'],
                }
                for acc in data['accounts']
            ],
            'total_debit': str(data['total_debit']),
            'total_credit': str(data['total_credit']),
            'difference': str(data['difference']),
            'is_balanced': data['is_balanced'],
        }
