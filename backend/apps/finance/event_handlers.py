
from django.db import transaction
from apps.finance.services.journal_service import JournalService
from apps.inventory.models.movement import StockMovement
from apps.finance.models.accounts import Account
from apps.finance.models.journal import Journal
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

        inventory_account = movement.lines.first().product.inventory_account

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
        cogs_account = product.expense_account
        inventory_account = product.inventory_account

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

def subscribe_to_events():
    event_bus.subscribe('stock.received', handle_stock_received)
    event_bus.subscribe('stock.shipped', handle_stock_shipped)

