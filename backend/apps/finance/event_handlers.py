
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from apps.finance.services.journal_service import JournalService
from apps.inventory.models import StockMovement
from apps.finance.models import Account, Journal
from apps.finance.services.posting_rules import resolve_inventory_accounts
from shared.event_bus import event_bus


def _line_dimensions(line, movement):
    cost_center = getattr(line, 'cost_center', None) or getattr(movement, 'cost_center', None)
    project = getattr(line, 'project', None) or getattr(movement, 'project', None)
    return cost_center, project

def handle_stock_received(sender, **kwargs):
    """
    Event handler for when stock is received.
    Creates a journal entry to debit Inventory and credit GRNI.
    """
    stock_movement_id = kwargs.get('stock_movement_id')
    if not stock_movement_id:
        return

    with transaction.atomic():
        movement = StockMovement.objects.select_related(
            'company', 'to_warehouse'
        ).prefetch_related(
            'lines__item__inventory_account',
            'lines__cost_center',
            'lines__project',
        ).get(pk=stock_movement_id)

        if not movement or movement.movement_type != 'RECEIPT':
            return

        company = movement.company

        try:
            grni_account = Account.objects.get(company=company, is_grni_account=True)
        except Account.DoesNotExist:
            print(f"Error: GRNI account not configured for company {company.name}")
            return

        try:
            general_journal = Journal.objects.get(company=company, code='GENERAL')
        except Journal.DoesNotExist:
            print(f"Error: General Journal not configured for company {company.name}")
            return

        debit_buckets = defaultdict(Decimal)
        total_credit = Decimal('0')

        for line in movement.lines.all():
            quantity = line.quantity or Decimal('0')
            rate = line.rate or Decimal('0')
            value = quantity * rate
            if value <= 0:
                continue
            product = line.item
            inv_acct, _ = resolve_inventory_accounts(
                company=company,
                product=product,
                warehouse=getattr(movement, 'to_warehouse', None),
                transaction_type='RECEIPT'
            )
            inventory_account = inv_acct or getattr(product, 'inventory_account', None)
            if not inventory_account:
                continue
            cost_center, project = _line_dimensions(line, movement)
            debit_buckets[(inventory_account, cost_center, project)] += value
            total_credit += value

        if total_credit <= 0:
            return

        entries_data = []
        for (account, cost_center, project), amount in debit_buckets.items():
            entries_data.append({
                'account': account,
                'debit': amount,
                'credit': 0,
                'description': f'Inventory from GRN {movement.reference}',
                'cost_center': cost_center,
                'project': project,
            })

        entries_data.append({
            'account': grni_account,
            'debit': 0,
            'credit': total_credit,
            'description': f'GRNI for {movement.reference}',
        })

        JournalService.create_journal_voucher(
            company=company,
            journal=general_journal,
            entry_date=movement.movement_date,
            description=f"Journal entry for stock receipt {movement.reference}",
            entries_data=entries_data,
            source_document_type='StockMovement',
            source_document_id=movement.id
        )

def handle_stock_shipped(sender, **kwargs):
    """
    Event handler for when stock is shipped.
    Creates a journal entry for Cost of Goods Sold (COGS).
    """
    stock_movement_id = kwargs.get('stock_movement_id')
    if not stock_movement_id:
        return

    with transaction.atomic():
        movement = StockMovement.objects.select_related(
            'company'
        ).prefetch_related(
            'lines__item__inventory_account',
            'lines__item__expense_account',
            'lines__cost_center',
            'lines__project',
        ).get(pk=stock_movement_id)

        if not movement or movement.movement_type != 'ISSUE':
            return

        company = movement.company

        try:
            sales_journal = Journal.objects.get(company=company, code='SALES')
        except Journal.DoesNotExist:
            print(f"Error: Sales Journal not configured for company {company.name}")
            return

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
                transaction_type='ISSUE'
            )
            cogs_account = cogs_acct or getattr(product, 'expense_account', None)
            inventory_account = inv_acct or getattr(product, 'inventory_account', None)
            if not cogs_account or not inventory_account:
                continue
            cost_center, project = _line_dimensions(line, movement)
            debit_buckets[(cogs_account, cost_center, project)] += value
            credit_buckets[(inventory_account, cost_center, project)] += value

        if not debit_buckets:
            return

        entries_data = []
        for (account, cost_center, project), amount in debit_buckets.items():
            entries_data.append({
                'account': account,
                'debit': amount,
                'credit': 0,
                'description': f'COGS for shipment {movement.reference}',
                'cost_center': cost_center,
                'project': project,
            })
        for (account, cost_center, project), amount in credit_buckets.items():
            entries_data.append({
                'account': account,
                'debit': 0,
                'credit': amount,
                'description': f'Inventory reduction for shipment {movement.reference}',
                'cost_center': cost_center,
                'project': project,
            })

        JournalService.create_journal_voucher(
            company=company,
            journal=sales_journal,
            entry_date=movement.movement_date,
            description=f"Journal entry for COGS on shipment {movement.reference}",
            entries_data=entries_data,
            source_document_type='StockMovement',
            source_document_id=movement.id
        )


def handle_transfer_out(sender, **kwargs):
    """
    Event handler for stock transfer-out leg.
    Dr In-Transit, Cr Inventory.
    Requires an 'INTRANSIT' account code configured.
    """
    stock_movement_id = kwargs.get('stock_movement_id')
    if not stock_movement_id:
        return

    with transaction.atomic():
        movement = StockMovement.objects.select_related('company').prefetch_related(
            'lines__item__inventory_account',
            'lines__cost_center',
            'lines__project',
        ).get(pk=stock_movement_id)
        if not movement or movement.movement_type != 'TRANSFER':
            return

        company = movement.company
        try:
            intransit_account = Account.objects.get(company=company, code='INTRANSIT')
        except Account.DoesNotExist:
            print(f"Error: In-Transit account (code=INTRANSIT) not configured for company {company.name}")
            return

        try:
            general_journal = Journal.objects.get(company=company, code='GENERAL')
        except Journal.DoesNotExist:
            print(f"Error: General Journal not configured for company {company.name}")
            return

        debit_buckets = defaultdict(Decimal)
        credit_buckets = defaultdict(Decimal)

        for line in movement.lines.all():
            quantity = abs(line.quantity or Decimal('0'))
            rate = line.rate or Decimal('0')
            value = quantity * rate
            if value <= 0:
                continue
            product = line.item
            inv_acct, _ = resolve_inventory_accounts(
                company=company,
                product=product,
                warehouse=getattr(movement, 'from_warehouse', None),
                transaction_type='TRANSFER'
            )
            inventory_account = inv_acct or getattr(product, 'inventory_account', None)
            if not inventory_account:
                continue
            cost_center, project = _line_dimensions(line, movement)
            debit_buckets[(intransit_account, cost_center, project)] += value
            credit_buckets[(inventory_account, cost_center, project)] += value

        if not debit_buckets:
            return

        entries_data = []
        for (account, cost_center, project), amount in debit_buckets.items():
            entries_data.append({
                'account': account,
                'debit': amount,
                'credit': 0,
                'description': f'Transfer Out {movement.reference}',
                'cost_center': cost_center,
                'project': project,
            })
        for (account, cost_center, project), amount in credit_buckets.items():
            entries_data.append({
                'account': account,
                'debit': 0,
                'credit': amount,
                'description': f'Inventory Transfer Out {movement.reference}',
                'cost_center': cost_center,
                'project': project,
            })

        JournalService.create_journal_voucher(
            company=company,
            journal=general_journal,
            entry_date=movement.movement_date,
            description=f"Journal entry for transfer out {movement.reference}",
            entries_data=entries_data,
            source_document_type='StockMovement',
            source_document_id=movement.id
        )


def handle_transfer_in(sender, **kwargs):
    """
    Event handler for stock transfer-in leg.
    Dr Inventory, Cr In-Transit.
    Requires an 'INTRANSIT' account code configured.
    """
    stock_movement_id = kwargs.get('stock_movement_id')
    if not stock_movement_id:
        return

    with transaction.atomic():
        movement = StockMovement.objects.select_related('company').prefetch_related(
            'lines__item__inventory_account',
            'lines__cost_center',
            'lines__project',
        ).get(pk=stock_movement_id)
        if not movement or movement.movement_type != 'TRANSFER':
            return

        company = movement.company
        try:
            intransit_account = Account.objects.get(company=company, code='INTRANSIT')
        except Account.DoesNotExist:
            print(f"Error: In-Transit account (code=INTRANSIT) not configured for company {company.name}")
            return

        try:
            general_journal = Journal.objects.get(company=company, code='GENERAL')
        except Journal.DoesNotExist:
            print(f"Error: General Journal not configured for company {company.name}")
            return

        debit_buckets = defaultdict(Decimal)
        credit_buckets = defaultdict(Decimal)

        for line in movement.lines.all():
            quantity = abs(line.quantity or Decimal('0'))
            rate = line.rate or Decimal('0')
            value = quantity * rate
            if value <= 0:
                continue
            product = line.item
            inv_acct, _ = resolve_inventory_accounts(
                company=company,
                product=product,
                warehouse=getattr(movement, 'to_warehouse', None),
                transaction_type='TRANSFER'
            )
            inventory_account = inv_acct or getattr(product, 'inventory_account', None)
            if not inventory_account:
                continue
            cost_center, project = _line_dimensions(line, movement)
            debit_buckets[(inventory_account, cost_center, project)] += value
            credit_buckets[(intransit_account, cost_center, project)] += value

        if not debit_buckets:
            return

        entries_data = []
        for (account, cost_center, project), amount in debit_buckets.items():
            entries_data.append({
                'account': account,
                'debit': amount,
                'credit': 0,
                'description': f'Transfer In {movement.reference}',
                'cost_center': cost_center,
                'project': project,
            })
        for (account, cost_center, project), amount in credit_buckets.items():
            entries_data.append({
                'account': account,
                'debit': 0,
                'credit': amount,
                'description': f'In-Transit Clearance {movement.reference}',
                'cost_center': cost_center,
                'project': project,
            })

        JournalService.create_journal_voucher(
            company=company,
            journal=general_journal,
            entry_date=movement.movement_date,
            description=f"Journal entry for transfer in {movement.reference}",
            entries_data=entries_data,
            source_document_type='StockMovement',
            source_document_id=movement.id
        )

def subscribe_to_events():
    event_bus.subscribe('stock.received', handle_stock_received)
    event_bus.subscribe('stock.shipped', handle_stock_shipped)
    event_bus.subscribe('stock.transfer_out', handle_transfer_out)
    event_bus.subscribe('stock.transfer_in', handle_transfer_in)
    event_bus.subscribe('stock.landed_cost_adjustment', handle_landed_cost_adjustment)


def handle_landed_cost_adjustment(sender, **kwargs):
    """
    Handle landed cost adjustment JV:
    - Debits Inventory by inventory_by_account
    - Debits COGS by cogs_by_account
    - Credits Accrued Freight (code=ACCRUED_FREIGHT) by total
    """
    company_id = kwargs.get('company_id')
    if not company_id:
        return

    inventory_by_account = kwargs.get('inventory_by_account') or []
    cogs_by_account = kwargs.get('cogs_by_account') or []
    credit_code = kwargs.get('credit_account_code') or 'ACCRUED_FREIGHT'
    reason = kwargs.get('reason') or 'Landed cost adjustment'

    with transaction.atomic():
        try:
            credit_account = Account.objects.get(company_id=company_id, code=credit_code)
        except Account.DoesNotExist:
            print(f"Error: Credit account {credit_code} not configured for company {company_id}")
            return

        try:
            general_journal = Journal.objects.get(company_id=company_id, code='GENERAL')
        except Journal.DoesNotExist:
            print(f"Error: General Journal not configured for company {company_id}")
            return

        total_credit = sum((item.get('amount') or 0) for item in inventory_by_account) + sum((item.get('amount') or 0) for item in cogs_by_account)
        if total_credit <= 0:
            return

        entries_data = []
        for item in inventory_by_account:
            try:
                entries_data.append({'account': Account.objects.get(pk=item['account_id'], company_id=company_id), 'debit': item['amount'], 'credit': 0, 'description': reason})
            except Account.DoesNotExist:
                continue
        for item in cogs_by_account:
            try:
                entries_data.append({'account': Account.objects.get(pk=item['account_id'], company_id=company_id), 'debit': item['amount'], 'credit': 0, 'description': reason})
            except Account.DoesNotExist:
                continue
        entries_data.append({'account': credit_account, 'debit': 0, 'credit': total_credit, 'description': reason})

        JournalService.create_journal_voucher(
            company=credit_account.company,
            journal=general_journal,
            entry_date=timezone.now().date(),
            description=f"Landed cost adjustment",
            entries_data=entries_data,
            source_document_type='GoodsReceipt',
            source_document_id=kwargs.get('goods_receipt_id')
        )
