
from django.db import transaction
from django.utils import timezone
from apps.finance.services.journal_service import JournalService
from apps.inventory.models import StockMovement
from apps.finance.models import Account, Journal
from apps.finance.services.posting_rules import resolve_inventory_accounts
from shared.event_bus import event_bus

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
        ).prefetch_related('lines__product__inventory_account').get(pk=stock_movement_id)

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

        total_value = sum(line.quantity * line.rate for line in movement.lines.all())

        if total_value <= 0:
            return

        # Resolve inventory account via posting rules
        first_line = movement.lines.first()
        inv_acct, _ = resolve_inventory_accounts(
            company=company,
            product=getattr(first_line, 'product', None),
            warehouse=getattr(movement, 'to_warehouse', None),
            transaction_type='RECEIPT'
        )
        inventory_account = inv_acct or first_line.product.inventory_account

        entries_data = [
            {
                'account': inventory_account,
                'debit': total_value,
                'credit': 0,
                'description': f'Inventory from GRN {movement.reference}'
            },
            {
                'account': grni_account,
                'debit': 0,
                'credit': total_value,
                'description': f'GRNI for {movement.reference}'
            }
        ]

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
        ).prefetch_related('lines__product__inventory_account', 'lines__product__expense_account').get(pk=stock_movement_id)

        if not movement or movement.movement_type != 'ISSUE':
            return

        company = movement.company

        try:
            sales_journal = Journal.objects.get(company=company, code='SALES')
        except Journal.DoesNotExist:
            print(f"Error: Sales Journal not configured for company {company.name}")
            return

        total_cost = sum(abs(line.quantity) * line.rate for line in movement.lines.all())

        if total_cost <= 0:
            return

        # For simplicity, we use the accounts from the first product line.
        # A more robust implementation would group by different expense/inventory accounts.
        product = movement.lines.first().product
        # Resolve via rules for ISSUE
        inv_acct, cogs_acct = resolve_inventory_accounts(
            company=company,
            product=product,
            warehouse=getattr(movement, 'from_warehouse', None),
            transaction_type='ISSUE'
        )
        cogs_account = cogs_acct or product.expense_account
        inventory_account = inv_acct or product.inventory_account

        entries_data = [
            {
                'account': cogs_account,
                'debit': total_cost,
                'credit': 0,
                'description': f'COGS for shipment {movement.reference}'
            },
            {
                'account': inventory_account,
                'debit': 0,
                'credit': total_cost,
                'description': f'Inventory reduction for shipment {movement.reference}'
            }
        ]

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
        movement = StockMovement.objects.select_related('company').prefetch_related('lines__product__inventory_account').get(pk=stock_movement_id)
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

        total_value = sum(abs(line.quantity) * line.rate for line in movement.lines.all())
        if total_value <= 0:
            return

        first_line = movement.lines.first()
        inv_acct, _ = resolve_inventory_accounts(
            company=company,
            product=getattr(first_line, 'product', None),
            warehouse=getattr(movement, 'from_warehouse', None),
            transaction_type='TRANSFER'
        )
        inventory_account = inv_acct or first_line.product.inventory_account
        entries_data = [
            { 'account': intransit_account, 'debit': total_value, 'credit': 0, 'description': f'Transfer Out {movement.reference}' },
            { 'account': inventory_account, 'debit': 0, 'credit': total_value, 'description': f'Inventory Transfer Out {movement.reference}' },
        ]

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
        movement = StockMovement.objects.select_related('company').prefetch_related('lines__product__inventory_account').get(pk=stock_movement_id)
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

        total_value = sum(abs(line.quantity) * line.rate for line in movement.lines.all())
        if total_value <= 0:
            return

        first_line = movement.lines.first()
        inv_acct, _ = resolve_inventory_accounts(
            company=company,
            product=getattr(first_line, 'product', None),
            warehouse=getattr(movement, 'to_warehouse', None),
            transaction_type='TRANSFER'
        )
        inventory_account = inv_acct or first_line.product.inventory_account
        entries_data = [
            { 'account': inventory_account, 'debit': total_value, 'credit': 0, 'description': f'Transfer In {movement.reference}' },
            { 'account': intransit_account, 'debit': 0, 'credit': total_value, 'description': f'In-Transit Clearance {movement.reference}' },
        ]

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
