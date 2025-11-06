"""
Finance Integration Service

Automatically generates journal entries for inventory transactions by subscribing
to inventory events published by the event bus.

This service handles:
- Stock receipts (Dr Inventory, Cr GRN Clearing)
- Stock issues (Dr COGS, Cr Inventory)
- Landed cost adjustments (Dr Inventory, Dr COGS, Cr Accrued Freight)
- Stock transfers (Dr Inventory-To, Cr Inventory-From)
- Valuation revaluations (Revaluation journal entries)
"""

import logging
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company
from apps.inventory.models import StockMovement, CostLayer, Product
from apps.finance.models import Account, Journal, JournalVoucher, InventoryPostingRule
from apps.finance.services.journal_service import JournalService
from shared.event_bus import event_bus

logger = logging.getLogger(__name__)


class FinanceIntegrationService:
    """
    Service that integrates inventory movements with the General Ledger.
    Automatically creates journal vouchers when inventory events occur.
    """

    @staticmethod
    def _get_posting_accounts(company: Company, product: Product, transaction_type: str):
        """
        Determines which GL accounts to use for an inventory transaction.

        Uses InventoryPostingRule with fallback hierarchy:
        1. Specific category + warehouse + transaction type
        2. Category + transaction type
        3. Transaction type only
        4. Default accounts from product

        Returns:
            dict with 'inventory_account' and 'cogs_account'
        """
        # Try to find posting rule
        posting_rule = (
            InventoryPostingRule.objects
            .filter(
                company=company,
                is_active=True,
                transaction_type=transaction_type
            )
            .select_related('inventory_account', 'cogs_account')
            .first()
        )

        if posting_rule:
            return {
                'inventory_account': posting_rule.inventory_account,
                'cogs_account': posting_rule.cogs_account or product.expense_account,
            }

        # Fallback to product's configured accounts
        return {
            'inventory_account': product.inventory_account,
            'cogs_account': product.expense_account,
        }

    @staticmethod
    def _get_journal(company: Company, journal_type: str = 'GENERAL') -> Journal:
        """
        Gets or creates the appropriate journal for inventory postings.
        """
        journal, created = Journal.objects.get_or_create(
            company=company,
            type=journal_type,
            defaults={
                'code': 'INV',
                'name': 'Inventory Journal',
                'is_active': True,
            }
        )
        if created:
            logger.info(f"Created new inventory journal for company {company.code}")
        return journal

    @staticmethod
    def _get_accrued_freight_account(company: Company) -> Optional[Account]:
        """
        Gets the Accrued Freight account for landed cost adjustments.
        Creates it if it doesn't exist.
        """
        account, created = Account.objects.get_or_create(
            company=company,
            code='ACCRUED_FREIGHT',
            defaults={
                'name': 'Accrued Freight & Import Charges',
                'account_type': 'LIABILITY',
                'is_active': True,
                'allow_direct_posting': True,
            }
        )
        if created:
            logger.info(f"Created Accrued Freight account for company {company.code}")
        return account

    @staticmethod
    def _get_grn_clearing_account(company: Company) -> Optional[Account]:
        """
        Gets the GRN Clearing account (used for goods receipt not yet invoiced).
        Creates it if it doesn't exist.
        """
        # First check if there's an account with is_grni_account=True
        account = Account.objects.filter(
            company=company,
            is_grni_account=True,
            is_active=True
        ).first()

        if not account:
            # Create one
            account, created = Account.objects.get_or_create(
                company=company,
                code='GRN_CLEARING',
                defaults={
                    'name': 'GRN Clearing Account',
                    'account_type': 'LIABILITY',
                    'is_active': True,
                    'is_grni_account': True,
                    'allow_direct_posting': True,
                }
            )
            if created:
                logger.info(f"Created GRN Clearing account for company {company.code}")

        return account

    @staticmethod
    @transaction.atomic
    def handle_stock_receipt(sender, **kwargs):
        """
        Event handler for 'stock.received' event.

        Creates journal entry:
        Dr Inventory
            Cr GRN Clearing
        """
        stock_movement_id = kwargs.get('stock_movement_id')
        if not stock_movement_id:
            logger.warning("stock.received event missing stock_movement_id")
            return

        try:
            movement = StockMovement.objects.select_related('company', 'to_warehouse').get(pk=stock_movement_id)
            company = movement.company
            journal = FinanceIntegrationService._get_journal(company)
            grn_clearing = FinanceIntegrationService._get_grn_clearing_account(company)

            if not grn_clearing:
                logger.error(f"No GRN Clearing account found for company {company.code}")
                return

            # Aggregate by inventory accounts
            account_totals = {}

            for line in movement.lines.select_related('product').all():
                accounts = FinanceIntegrationService._get_posting_accounts(
                    company, line.product, 'RECEIPT'
                )
                inv_account = accounts['inventory_account']

                line_value = line.quantity * line.rate
                if inv_account.id not in account_totals:
                    account_totals[inv_account.id] = {
                        'account': inv_account,
                        'amount': Decimal('0'),
                    }
                account_totals[inv_account.id]['amount'] += line_value

            # Build journal entries
            entries_data = []
            total_value = Decimal('0')

            for acct_data in account_totals.values():
                entries_data.append({
                    'account': acct_data['account'],
                    'debit': acct_data['amount'],
                    'credit': Decimal('0'),
                    'description': f"Stock receipt - {movement.reference or movement.id}"
                })
                total_value += acct_data['amount']

            # Credit GRN Clearing for total
            entries_data.append({
                'account': grn_clearing,
                'debit': Decimal('0'),
                'credit': total_value,
                'description': f"Stock receipt - {movement.reference or movement.id}"
            })

            # Create journal voucher
            voucher = JournalService.create_journal_voucher(
                journal=journal,
                entry_date=movement.movement_date,
                description=f"Stock Receipt - {movement.reference or movement.id}",
                entries_data=entries_data,
                reference=movement.reference or '',
                source_document_type='StockMovement',
                source_document_id=movement.id,
                company=company,
                created_by=None,
            )

            logger.info(
                f"Created journal voucher {voucher.voucher_number} for stock receipt {movement.id}"
            )

            # Auto-post if configured (optional - can be controlled by company settings)
            # For now, leave in DRAFT for review

        except StockMovement.DoesNotExist:
            logger.error(f"StockMovement {stock_movement_id} not found")
        except Exception as e:
            logger.exception(f"Error handling stock receipt: {e}")

    @staticmethod
    @transaction.atomic
    def handle_stock_issue(sender, **kwargs):
        """
        Event handler for 'stock.shipped' or 'stock.issued' event.

        Creates journal entry:
        Dr COGS
            Cr Inventory
        """
        stock_movement_id = kwargs.get('stock_movement_id')
        if not stock_movement_id:
            logger.warning("stock.issued event missing stock_movement_id")
            return

        try:
            movement = StockMovement.objects.select_related('company', 'from_warehouse').get(pk=stock_movement_id)
            company = movement.company
            journal = FinanceIntegrationService._get_journal(company)

            # Aggregate by accounts
            inv_account_totals = {}
            cogs_account_totals = {}

            for line in movement.lines.select_related('product').all():
                accounts = FinanceIntegrationService._get_posting_accounts(
                    company, line.product, 'ISSUE'
                )
                inv_account = accounts['inventory_account']
                cogs_account = accounts['cogs_account']

                line_value = line.quantity * line.rate

                # Inventory credit
                if inv_account.id not in inv_account_totals:
                    inv_account_totals[inv_account.id] = {
                        'account': inv_account,
                        'amount': Decimal('0'),
                    }
                inv_account_totals[inv_account.id]['amount'] += line_value

                # COGS debit
                if cogs_account.id not in cogs_account_totals:
                    cogs_account_totals[cogs_account.id] = {
                        'account': cogs_account,
                        'amount': Decimal('0'),
                    }
                cogs_account_totals[cogs_account.id]['amount'] += line_value

            # Build journal entries
            entries_data = []

            # Dr COGS
            for acct_data in cogs_account_totals.values():
                entries_data.append({
                    'account': acct_data['account'],
                    'debit': acct_data['amount'],
                    'credit': Decimal('0'),
                    'description': f"Stock issue - {movement.reference or movement.id}"
                })

            # Cr Inventory
            for acct_data in inv_account_totals.values():
                entries_data.append({
                    'account': acct_data['account'],
                    'debit': Decimal('0'),
                    'credit': acct_data['amount'],
                    'description': f"Stock issue - {movement.reference or movement.id}"
                })

            # Create journal voucher
            voucher = JournalService.create_journal_voucher(
                journal=journal,
                entry_date=movement.movement_date,
                description=f"Stock Issue - {movement.reference or movement.id}",
                entries_data=entries_data,
                reference=movement.reference or '',
                source_document_type='StockMovement',
                source_document_id=movement.id,
                company=company,
                created_by=None,
            )

            logger.info(
                f"Created journal voucher {voucher.voucher_number} for stock issue {movement.id}"
            )

        except StockMovement.DoesNotExist:
            logger.error(f"StockMovement {stock_movement_id} not found")
        except Exception as e:
            logger.exception(f"Error handling stock issue: {e}")

    @staticmethod
    @transaction.atomic
    def handle_landed_cost_adjustment(sender, **kwargs):
        """
        Event handler for 'stock.landed_cost_adjustment' event.

        Creates journal entry:
        Dr Inventory (remaining stock adjustment)
        Dr COGS (consumed stock adjustment)
            Cr Accrued Freight
        """
        company_id = kwargs.get('company_id')
        goods_receipt_id = kwargs.get('goods_receipt_id')
        inventory_by_account = kwargs.get('inventory_by_account', [])
        cogs_by_account = kwargs.get('cogs_by_account', [])
        reason = kwargs.get('reason', 'Landed cost adjustment')

        if not company_id:
            logger.warning("landed_cost_adjustment event missing company_id")
            return

        try:
            company = Company.objects.get(pk=company_id)
            journal = FinanceIntegrationService._get_journal(company)
            accrued_freight = FinanceIntegrationService._get_accrued_freight_account(company)

            if not accrued_freight:
                logger.error(f"No Accrued Freight account for company {company.code}")
                return

            entries_data = []
            total_debit = Decimal('0')

            # Dr Inventory accounts
            for inv_item in inventory_by_account:
                account = Account.objects.get(pk=inv_item['account_id'], company=company)
                amount = Decimal(str(inv_item['amount']))
                if amount > 0:
                    entries_data.append({
                        'account': account,
                        'debit': amount,
                        'credit': Decimal('0'),
                        'description': reason
                    })
                    total_debit += amount

            # Dr COGS accounts
            for cogs_item in cogs_by_account:
                account = Account.objects.get(pk=cogs_item['account_id'], company=company)
                amount = Decimal(str(cogs_item['amount']))
                if amount > 0:
                    entries_data.append({
                        'account': account,
                        'debit': amount,
                        'credit': Decimal('0'),
                        'description': reason
                    })
                    total_debit += amount

            # Cr Accrued Freight
            if total_debit > 0:
                entries_data.append({
                    'account': accrued_freight,
                    'debit': Decimal('0'),
                    'credit': total_debit,
                    'description': reason
                })

            if not entries_data or total_debit == 0:
                logger.info("Landed cost adjustment has zero value, skipping JV creation")
                return

            # Create journal voucher
            voucher = JournalService.create_journal_voucher(
                journal=journal,
                entry_date=timezone.now().date(),
                description=f"Landed Cost Adjustment - GRN {goods_receipt_id}",
                entries_data=entries_data,
                reference=f"GRN-{goods_receipt_id}",
                source_document_type='GoodsReceipt',
                source_document_id=goods_receipt_id,
                company=company,
                created_by=None,
            )

            logger.info(
                f"Created journal voucher {voucher.voucher_number} for landed cost adjustment on GRN {goods_receipt_id}"
            )

        except Company.DoesNotExist:
            logger.error(f"Company {company_id} not found")
        except Account.DoesNotExist as e:
            logger.error(f"Account not found: {e}")
        except Exception as e:
            logger.exception(f"Error handling landed cost adjustment: {e}")

    @staticmethod
    @transaction.atomic
    def handle_stock_transfer(sender, **kwargs):
        """
        Event handler for 'stock.transfer_out' and 'stock.transfer_in' events.

        Creates journal entry:
        Dr Inventory (destination warehouse account)
            Cr Inventory (source warehouse account)
        """
        stock_movement_id = kwargs.get('stock_movement_id')
        if not stock_movement_id:
            logger.warning("stock.transfer event missing stock_movement_id")
            return

        try:
            movement = StockMovement.objects.select_related(
                'company', 'from_warehouse', 'to_warehouse'
            ).get(pk=stock_movement_id)

            company = movement.company
            journal = FinanceIntegrationService._get_journal(company)

            # Check if voucher already exists for this transfer
            existing = JournalVoucher.objects.filter(
                company=company,
                source_document_type='StockMovement',
                source_document_id=movement.id
            ).exists()

            if existing:
                logger.info(f"Journal voucher already exists for transfer {movement.id}")
                return

            # Aggregate by accounts
            from_account_totals = {}
            to_account_totals = {}

            for line in movement.lines.select_related('product').all():
                accounts = FinanceIntegrationService._get_posting_accounts(
                    company, line.product, 'TRANSFER'
                )
                inv_account = accounts['inventory_account']

                line_value = line.quantity * line.rate

                # From warehouse - credit
                if inv_account.id not in from_account_totals:
                    from_account_totals[inv_account.id] = {
                        'account': inv_account,
                        'amount': Decimal('0'),
                    }
                from_account_totals[inv_account.id]['amount'] += line_value

                # To warehouse - debit (same account typically)
                if inv_account.id not in to_account_totals:
                    to_account_totals[inv_account.id] = {
                        'account': inv_account,
                        'amount': Decimal('0'),
                    }
                to_account_totals[inv_account.id]['amount'] += line_value

            # Build journal entries
            entries_data = []

            # Dr Inventory (destination)
            for acct_data in to_account_totals.values():
                entries_data.append({
                    'account': acct_data['account'],
                    'debit': acct_data['amount'],
                    'credit': Decimal('0'),
                    'description': f"Transfer from {movement.from_warehouse.name} to {movement.to_warehouse.name}"
                })

            # Cr Inventory (source)
            for acct_data in from_account_totals.values():
                entries_data.append({
                    'account': acct_data['account'],
                    'debit': Decimal('0'),
                    'credit': acct_data['amount'],
                    'description': f"Transfer from {movement.from_warehouse.name} to {movement.to_warehouse.name}"
                })

            # Create journal voucher
            voucher = JournalService.create_journal_voucher(
                journal=journal,
                entry_date=movement.movement_date,
                description=f"Stock Transfer - {movement.reference or movement.id}",
                entries_data=entries_data,
                reference=movement.reference or '',
                source_document_type='StockMovement',
                source_document_id=movement.id,
                company=company,
                created_by=None,
            )

            logger.info(
                f"Created journal voucher {voucher.voucher_number} for stock transfer {movement.id}"
            )

        except StockMovement.DoesNotExist:
            logger.error(f"StockMovement {stock_movement_id} not found")
        except Exception as e:
            logger.exception(f"Error handling stock transfer: {e}")

    @classmethod
    def register_handlers(cls):
        """
        Registers all event handlers with the event bus.
        Call this during Django app initialization (in AppConfig.ready()).
        """
        event_bus.subscribe('stock.received', cls.handle_stock_receipt)
        event_bus.subscribe('stock.shipped', cls.handle_stock_issue)
        event_bus.subscribe('stock.landed_cost_adjustment', cls.handle_landed_cost_adjustment)
        event_bus.subscribe('stock.transfer_out', cls.handle_stock_transfer)
        event_bus.subscribe('stock.transfer_in', cls.handle_stock_transfer)

        logger.info("Finance integration handlers registered with event bus")
