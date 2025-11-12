from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Dict, List

from apps.finance.models import Account
from apps.finance.services.posting_rules import resolve_inventory_accounts


class StockGLPreviewService:
    @staticmethod
    def preview_stock_movement(movement) -> Dict:
        movement_type = (movement.movement_type or '').upper()
        if movement_type == 'RECEIPT':
            return StockGLPreviewService._preview_receipt(movement)
        if movement_type == 'ISSUE':
            return StockGLPreviewService._preview_issue(movement)
        if movement_type == 'TRANSFER':
            return StockGLPreviewService._preview_transfer(movement)
        return {
            'movement_id': movement.id,
            'movement_type': movement.movement_type,
            'entries': [],
            'warnings': ['Preview not available for this movement type.'],
        }

    @staticmethod
    def _preview_receipt(movement) -> Dict:
        company = movement.company
        warnings: List[str] = []
        try:
            grni_account = Account.objects.get(company=company, is_grni_account=True)
        except Account.DoesNotExist:
            warnings.append('GRNI account is not configured for this company.')
            grni_account = None

        debit_buckets = defaultdict(Decimal)
        total_credit = Decimal('0')

        for line in movement.lines.all():
            quantity = line.quantity or Decimal('0')
            rate = line.rate or Decimal('0')
            value = quantity * rate
            if value <= 0:
                continue
            inv_acct, _ = resolve_inventory_accounts(
                company=company,
                product=line.item,
                warehouse=getattr(movement, 'to_warehouse', None),
                transaction_type='RECEIPT',
            )
            account = inv_acct or getattr(line.item, 'inventory_account', None)
            if not account:
                warnings.append(f'No inventory account found for item {line.item.code}.')
                continue
            cost_center = getattr(line, 'cost_center', None) or getattr(movement, 'cost_center', None)
            project = getattr(line, 'project', None) or getattr(movement, 'project', None)
            debit_buckets[(account, cost_center, project)] += value
            total_credit += value

        entries = []
        for (account, cost_center, project), amount in debit_buckets.items():
            entries.append(StockGLPreviewService._entry(account, amount, Decimal('0'), 'Inventory receipt', cost_center, project))

        if grni_account and total_credit > 0:
            entries.append(StockGLPreviewService._entry(grni_account, Decimal('0'), total_credit, 'GRNI clearing', None, None))

        return {
            'movement_id': movement.id,
            'movement_type': movement.movement_type,
            'entries': entries,
            'warnings': warnings,
        }

    @staticmethod
    def _preview_issue(movement) -> Dict:
        company = movement.company
        warnings: List[str] = []
        debit_buckets = defaultdict(Decimal)
        credit_buckets = defaultdict(Decimal)

        for line in movement.lines.all():
            quantity = abs(line.quantity or Decimal('0'))
            rate = line.rate or Decimal('0')
            value = quantity * rate
            if value <= 0:
                continue
            product = line.item
            inv_acct, cogs_acct = resolve_inventory_accounts(
                company=company,
                product=product,
                warehouse=getattr(movement, 'from_warehouse', None),
                transaction_type='ISSUE',
            )
            inventory_account = inv_acct or getattr(product, 'inventory_account', None)
            cogs_account = cogs_acct or getattr(product, 'expense_account', None)
            if not inventory_account or not cogs_account:
                warnings.append(f'Missing accounts for item {product.code}.')
                continue
            cost_center = getattr(line, 'cost_center', None) or getattr(movement, 'cost_center', None)
            project = getattr(line, 'project', None) or getattr(movement, 'project', None)
            debit_buckets[(cogs_account, cost_center, project)] += value
            credit_buckets[(inventory_account, cost_center, project)] += value

        entries = []
        for (account, cost_center, project), amount in debit_buckets.items():
            entries.append(StockGLPreviewService._entry(account, amount, Decimal('0'), 'COGS', cost_center, project))
        for (account, cost_center, project), amount in credit_buckets.items():
            entries.append(StockGLPreviewService._entry(account, Decimal('0'), amount, 'Inventory issue', cost_center, project))

        return {
            'movement_id': movement.id,
            'movement_type': movement.movement_type,
            'entries': entries,
            'warnings': warnings,
        }

    @staticmethod
    def _preview_transfer(movement) -> Dict:
        company = movement.company
        warnings: List[str] = []
        try:
            intransit_account = Account.objects.get(company=company, code='INTRANSIT')
        except Account.DoesNotExist:
            intransit_account = None
            warnings.append('In-Transit account (code=INTRANSIT) is not configured.')

        debit_buckets = defaultdict(Decimal)
        credit_buckets = defaultdict(Decimal)
        for line in movement.lines.all():
            quantity = abs(line.quantity or Decimal('0'))
            rate = line.rate or Decimal('0')
            value = quantity * rate
            if value <= 0:
                continue
            inv_acct, _ = resolve_inventory_accounts(
                company=company,
                product=line.item,
                warehouse=getattr(movement, 'from_warehouse', None),
                transaction_type='TRANSFER',
            )
            inventory_account = inv_acct or getattr(line.item, 'inventory_account', None)
            if not inventory_account:
                warnings.append(f'No inventory account for item {line.item.code}.')
                continue
            cost_center = getattr(line, 'cost_center', None) or getattr(movement, 'cost_center', None)
            project = getattr(line, 'project', None) or getattr(movement, 'project', None)
            if intransit_account:
                debit_buckets[(intransit_account, cost_center, project)] += value
            credit_buckets[(inventory_account, cost_center, project)] += value

        entries = []
        for (account, cost_center, project), amount in debit_buckets.items():
            entries.append(StockGLPreviewService._entry(account, amount, Decimal('0'), 'Transfer Out', cost_center, project))
        for (account, cost_center, project), amount in credit_buckets.items():
            entries.append(StockGLPreviewService._entry(account, Decimal('0'), amount, 'Inventory Transfer', cost_center, project))

        return {
            'movement_id': movement.id,
            'movement_type': movement.movement_type,
            'entries': entries,
            'warnings': warnings,
        }

    @staticmethod
    def _entry(account, debit: Decimal, credit: Decimal, description: str, cost_center, project):
        return {
            'account_id': getattr(account, 'id', None),
            'account_code': getattr(account, 'code', None),
            'account_name': getattr(account, 'name', None),
            'debit': float(debit or 0),
            'credit': float(credit or 0),
            'description': description,
            'cost_center_id': getattr(cost_center, 'id', None),
            'project_id': getattr(project, 'id', None),
        }
