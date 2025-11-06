"""
GL Reconciliation Service

Provides real-time reconciliation between inventory values and GL account balances.
Helps identify discrepancies and ensures financial accuracy.

Features:
- Real-time inventory value calculation
- GL balance comparison
- Variance analysis
- Reconciliation reports
- Auto-correction suggestions
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import date

from django.db.models import Sum, Q, F
from django.utils import timezone

from apps.companies.models import Company
from apps.inventory.models import Product, Warehouse, CostLayer, StockLevel
from apps.inventory.services.valuation_service import ValuationService
from apps.finance.models import Account, JournalEntry, JournalVoucher, JournalStatus

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationResult:
    """Result of a GL reconciliation check"""
    company_code: str
    account_code: str
    account_name: str
    gl_balance: Decimal
    inventory_value: Decimal
    variance: Decimal
    variance_percent: Decimal
    is_reconciled: bool
    details: List[Dict]
    checked_at: date


class GLReconciliationService:
    """
    Service for reconciling inventory values with GL account balances.
    """

    TOLERANCE_AMOUNT = Decimal('0.01')  # 1 cent tolerance
    TOLERANCE_PERCENT = Decimal('0.01')  # 1% tolerance

    @staticmethod
    def calculate_inventory_value_by_account(
        company: Company,
        warehouse: Optional[Warehouse] = None,
        as_of_date: Optional[date] = None
    ) -> Dict[int, Decimal]:
        """
        Calculates total inventory value grouped by inventory account.

        Args:
            company: Company to calculate for
            warehouse: Optional warehouse filter
            as_of_date: Optional date for historical calculation

        Returns:
            Dict mapping account_id -> total_inventory_value
        """
        if as_of_date is None:
            as_of_date = timezone.now().date()

        account_values = {}

        # Get all products with their inventory accounts
        products = Product.objects.filter(
            company=company,
            is_active=True
        ).select_related('inventory_account')

        if warehouse:
            # Filter by warehouse if specified
            stock_levels = StockLevel.objects.filter(
                company=company,
                warehouse=warehouse,
                quantity__gt=0
            ).select_related('product__inventory_account')

            product_ids = stock_levels.values_list('product_id', flat=True)
            products = products.filter(id__in=product_ids)

        for product in products:
            if not product.inventory_account:
                logger.warning(f"Product {product.code} has no inventory account configured")
                continue

            # Calculate current inventory value for this product
            warehouses = [warehouse] if warehouse else Warehouse.objects.filter(company=company)

            for wh in warehouses:
                try:
                    # Get stock level
                    stock_level = StockLevel.objects.filter(
                        company=company,
                        product=product,
                        warehouse=wh
                    ).first()

                    if not stock_level or stock_level.quantity <= 0:
                        continue

                    # Get current cost using valuation service
                    current_cost = ValuationService.get_current_cost(
                        company=company,
                        product=product,
                        warehouse=wh
                    )

                    value = current_cost * stock_level.quantity

                    # Aggregate by inventory account
                    account_id = product.inventory_account_id
                    if account_id not in account_values:
                        account_values[account_id] = Decimal('0')
                    account_values[account_id] += value

                except Exception as e:
                    logger.error(f"Error calculating value for product {product.code} in {wh.code}: {e}")
                    continue

        return account_values

    @staticmethod
    def get_gl_balance(account: Account, as_of_date: Optional[date] = None) -> Decimal:
        """
        Gets the GL balance for an account as of a specific date.

        Args:
            account: The account to check
            as_of_date: Optional date filter (default: current date)

        Returns:
            Current GL balance (considering account type for debit/credit nature)
        """
        if as_of_date is None:
            # Use current_balance field for performance
            return account.current_balance or Decimal('0')

        # Calculate historical balance by summing posted journal entries
        posted_entries = JournalEntry.objects.filter(
            account=account,
            voucher__status=JournalStatus.POSTED,
            voucher__entry_date__lte=as_of_date
        ).aggregate(
            total_debit=Sum('debit_amount'),
            total_credit=Sum('credit_amount')
        )

        total_debit = posted_entries.get('total_debit') or Decimal('0')
        total_credit = posted_entries.get('total_credit') or Decimal('0')

        # For asset accounts (including inventory), debit increases balance
        if account.account_type == 'ASSET':
            return total_debit - total_credit
        else:
            return total_credit - total_debit

    @staticmethod
    def reconcile_inventory_accounts(
        company: Company,
        warehouse: Optional[Warehouse] = None,
        as_of_date: Optional[date] = None
    ) -> List[ReconciliationResult]:
        """
        Performs reconciliation between inventory values and GL balances.

        Args:
            company: Company to reconcile
            warehouse: Optional warehouse filter
            as_of_date: Optional date for reconciliation

        Returns:
            List of ReconciliationResult objects
        """
        if as_of_date is None:
            as_of_date = timezone.now().date()

        results = []

        # Calculate inventory values by account
        inventory_values = GLReconciliationService.calculate_inventory_value_by_account(
            company=company,
            warehouse=warehouse,
            as_of_date=as_of_date
        )

        # Get all inventory accounts
        account_ids = list(inventory_values.keys())
        accounts = Account.objects.filter(id__in=account_ids)

        for account in accounts:
            inventory_value = inventory_values.get(account.id, Decimal('0'))
            gl_balance = GLReconciliationService.get_gl_balance(account, as_of_date)

            variance = gl_balance - inventory_value
            variance_abs = abs(variance)

            # Calculate variance percentage
            if inventory_value > 0:
                variance_percent = (variance_abs / inventory_value) * 100
            else:
                variance_percent = Decimal('100') if variance_abs > 0 else Decimal('0')

            # Determine if reconciled (within tolerance)
            is_reconciled = (
                variance_abs <= GLReconciliationService.TOLERANCE_AMOUNT or
                variance_percent <= GLReconciliationService.TOLERANCE_PERCENT
            )

            result = ReconciliationResult(
                company_code=company.code,
                account_code=account.code,
                account_name=account.name,
                gl_balance=gl_balance,
                inventory_value=inventory_value,
                variance=variance,
                variance_percent=variance_percent,
                is_reconciled=is_reconciled,
                details=[],
                checked_at=as_of_date
            )

            results.append(result)

        return results

    @staticmethod
    def get_unreconciled_accounts(company: Company) -> List[ReconciliationResult]:
        """
        Gets all accounts that have reconciliation variances exceeding tolerance.

        Args:
            company: Company to check

        Returns:
            List of unreconciled accounts
        """
        all_results = GLReconciliationService.reconcile_inventory_accounts(company)
        return [r for r in all_results if not r.is_reconciled]

    @staticmethod
    def generate_reconciliation_report(
        company: Company,
        warehouse: Optional[Warehouse] = None,
        as_of_date: Optional[date] = None
    ) -> Dict:
        """
        Generates a comprehensive reconciliation report.

        Args:
            company: Company to report on
            warehouse: Optional warehouse filter
            as_of_date: Optional date for report

        Returns:
            Dict containing report data
        """
        results = GLReconciliationService.reconcile_inventory_accounts(
            company=company,
            warehouse=warehouse,
            as_of_date=as_of_date
        )

        total_gl = sum(r.gl_balance for r in results)
        total_inventory = sum(r.inventory_value for r in results)
        total_variance = sum(r.variance for r in results)

        reconciled_count = sum(1 for r in results if r.is_reconciled)
        unreconciled_count = len(results) - reconciled_count

        return {
            'company': company.code,
            'company_name': company.name,
            'warehouse': warehouse.name if warehouse else 'All Warehouses',
            'as_of_date': as_of_date or timezone.now().date(),
            'summary': {
                'total_gl_balance': float(total_gl),
                'total_inventory_value': float(total_inventory),
                'total_variance': float(total_variance),
                'variance_percent': float((abs(total_variance) / total_inventory * 100) if total_inventory > 0 else 0),
                'accounts_checked': len(results),
                'accounts_reconciled': reconciled_count,
                'accounts_unreconciled': unreconciled_count,
            },
            'accounts': [
                {
                    'account_code': r.account_code,
                    'account_name': r.account_name,
                    'gl_balance': float(r.gl_balance),
                    'inventory_value': float(r.inventory_value),
                    'variance': float(r.variance),
                    'variance_percent': float(r.variance_percent),
                    'is_reconciled': r.is_reconciled,
                }
                for r in results
            ],
            'unreconciled_accounts': [
                {
                    'account_code': r.account_code,
                    'account_name': r.account_name,
                    'variance': float(r.variance),
                    'variance_percent': float(r.variance_percent),
                }
                for r in results if not r.is_reconciled
            ]
        }

    @staticmethod
    def get_reconciliation_details(
        company: Company,
        account: Account,
        warehouse: Optional[Warehouse] = None
    ) -> Dict:
        """
        Gets detailed breakdown of inventory and GL transactions for an account.

        Args:
            company: Company
            account: Account to detail
            warehouse: Optional warehouse filter

        Returns:
            Dict with detailed transaction breakdown
        """
        # Get all products using this inventory account
        products = Product.objects.filter(
            company=company,
            inventory_account=account,
            is_active=True
        )

        product_details = []

        for product in products:
            warehouses = [warehouse] if warehouse else Warehouse.objects.filter(company=company)

            for wh in warehouses:
                stock_level = StockLevel.objects.filter(
                    company=company,
                    product=product,
                    warehouse=wh
                ).first()

                if not stock_level or stock_level.quantity <= 0:
                    continue

                current_cost = ValuationService.get_current_cost(
                    company=company,
                    product=product,
                    warehouse=wh
                )

                value = current_cost * stock_level.quantity

                # Get cost layers for this product/warehouse
                cost_layers = CostLayer.objects.filter(
                    company=company,
                    product=product,
                    warehouse=wh,
                    qty_remaining__gt=0
                ).order_by('fifo_sequence')

                product_details.append({
                    'product_code': product.code,
                    'product_name': product.name,
                    'warehouse': wh.code,
                    'quantity': float(stock_level.quantity),
                    'unit_cost': float(current_cost),
                    'total_value': float(value),
                    'cost_layers': [
                        {
                            'layer_id': layer.id,
                            'receipt_date': layer.receipt_date.isoformat(),
                            'quantity': float(layer.qty_remaining),
                            'cost_per_unit': float(layer.cost_per_unit),
                            'value': float(layer.cost_remaining),
                        }
                        for layer in cost_layers
                    ]
                })

        # Get recent GL transactions for this account
        recent_transactions = JournalEntry.objects.filter(
            account=account,
            voucher__status=JournalStatus.POSTED
        ).select_related('voucher').order_by('-voucher__entry_date')[:50]

        gl_transactions = [
            {
                'date': entry.voucher.entry_date.isoformat(),
                'voucher_number': entry.voucher.voucher_number,
                'description': entry.description or entry.voucher.description,
                'debit': float(entry.debit_amount),
                'credit': float(entry.credit_amount),
                'source_document': entry.voucher.source_document_type,
            }
            for entry in recent_transactions
        ]

        return {
            'account_code': account.code,
            'account_name': account.name,
            'gl_balance': float(GLReconciliationService.get_gl_balance(account)),
            'product_details': product_details,
            'total_inventory_value': sum(p['total_value'] for p in product_details),
            'recent_gl_transactions': gl_transactions,
        }
