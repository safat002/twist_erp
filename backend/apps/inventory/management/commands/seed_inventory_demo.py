from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.inventory.models import UnitOfMeasure, ItemCategory, Item, Warehouse, StockMovement, StockMovementLine
from apps.finance.models import Account, AccountType


class Command(BaseCommand):
    help = "Seed demo inventory master data and a basic stock receipt."

    def add_arguments(self, parser):
        parser.add_argument('--company-id', type=int, required=True)

    def handle(self, *args, **options):
        company_id = options['company_id']

        # Finance accounts for product linkage
        inv_acct, _ = Account.objects.get_or_create(
            company_id=company_id, code='1300-INVENTORY',
            defaults={'name': 'Inventory', 'account_type': AccountType.ASSET}
        )
        exp_acct, _ = Account.objects.get_or_create(
            company_id=company_id, code='5000-COGS',
            defaults={'name': 'Cost of Goods Sold', 'account_type': AccountType.EXPENSE}
        )
        inc_acct, _ = Account.objects.get_or_create(
            company_id=company_id, code='4000-SALES',
            defaults={'name': 'Sales Revenue', 'account_type': AccountType.REVENUE}
        )

        # UOM
        uom, _ = UnitOfMeasure.objects.get_or_create(
            company_id=company_id, code='PCS', defaults={'name': 'Pieces', 'short_name': 'pcs'}
        )

        # Category
        cat, _ = ItemCategory.objects.get_or_create(
            company_id=company_id, code='RAW', defaults={'name': 'Raw Material'}
        )

        # Warehouse
        wh, _ = Warehouse.objects.get_or_create(
            company_id=company_id, code='MAIN', defaults={'name': 'Main Warehouse', 'warehouse_type': 'MAIN'}
        )

        # Items
        p1, _ = Item.objects.get_or_create(
            company_id=company_id, code='RM-001',
            defaults={
                'name': 'Raw Material A', 'uom': uom, 'category': cat,
                'track_inventory': True, 'cost_price': Decimal('10.00'),
                'inventory_account': inv_acct, 'expense_account': exp_acct,
                'valuation_method': 'FIFO',
            }
        )
        p2, _ = Item.objects.get_or_create(
            company_id=company_id, code='RM-002',
            defaults={
                'name': 'Raw Material B', 'uom': uom, 'category': cat,
                'track_inventory': True, 'cost_price': Decimal('20.00'),
                'inventory_account': inv_acct, 'expense_account': exp_acct,
                'valuation_method': 'FIFO',
            }
        )

        # Simple stock receipt via StockMovement (not tied to PO)
        sm, _ = StockMovement.objects.get_or_create(
            company_id=company_id,
            movement_number='SM-DEMO',
            defaults={
                'movement_date': date.today(), 'movement_type': 'RECEIPT', 'to_warehouse': wh,
                'reference': 'Demo Receipt', 'status': 'DRAFT'
            }
        )
        if sm.status == 'DRAFT' and sm.lines.count() == 0:
            StockMovementLine.objects.create(movement=sm, line_number=1, item=p1, quantity=Decimal('50.000'), rate=Decimal('10.00'))
            StockMovementLine.objects.create(movement=sm, line_number=2, item=p2, quantity=Decimal('30.000'), rate=Decimal('20.00'))

            # Post using internal service to update ledger/layers
            from apps.inventory.services.stock_service import InventoryService
            InventoryService._post_stock_movement(sm, receipt_stock_state='RELEASED')

        self.stdout.write(self.style.SUCCESS(
            f"Seeded inventory demo for company={company_id}: products {p1.code}, {p2.code} and receipt posted."
        ))
