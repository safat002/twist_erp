from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.procurement.models import Supplier, PurchaseOrder, PurchaseOrderLine
from apps.inventory.models import Warehouse, Item, GoodsReceipt, GoodsReceiptLine
from apps.budgeting.models import Budget, BudgetLine, CostCenter
from apps.finance.models import Account, AccountType
from apps.companies.models import Department


class Command(BaseCommand):
    help = "Seed demo supplier, purchase order, and goods receipt to drive inventory and budget usage."

    def add_arguments(self, parser):
        parser.add_argument('--company-id', type=int, required=True)

    def handle(self, *args, **options):
        company_id = options['company_id']

        # Ensure AP account
        ap_acct, _ = Account.objects.get_or_create(
            company_id=company_id, code='2100-AP',
            defaults={'name': 'Accounts Payable', 'account_type': AccountType.LIABILITY}
        )

        # Ensure item + warehouse exist (from inventory seeder)
        wh, _ = Warehouse.objects.get_or_create(
            company_id=company_id, code='MAIN', defaults={'name': 'Main Warehouse', 'warehouse_type': 'MAIN'}
        )
        item = Item.objects.filter(company_id=company_id).order_by('code').first()
        if item is None:
            self.stderr.write(self.style.WARNING('No item found; run seed_inventory_demo first. Creating minimal items.'))
            from apps.inventory.management.commands.seed_inventory_demo import Command as InvSeed
            InvSeed().handle(company_id=company_id)
            item = Item.objects.filter(company_id=company_id).order_by('code').first()

        # Ensure a budget line exists
        budget_line = BudgetLine.objects.filter(budget__company_id=company_id).first()
        if budget_line is None:
            # Create minimal CC + Budget + Line
            dept, _ = Department.objects.get_or_create(company_id=company_id, code='OPS', defaults={'name': 'Operations'})
            cc, _ = CostCenter.objects.get_or_create(company_id=company_id, code='OPS-IT', defaults={'name': 'IT Operations', 'department': dept})
            start = date.today().replace(month=1, day=1)
            end = start.replace(month=12, day=31)
            budget, _ = Budget.objects.get_or_create(
                company_id=company_id,
                cost_center=cc,
                name='FY Demo OPEX',
                defaults={'budget_type': Budget.TYPE_OPEX, 'duration_type': Budget.DURATION_YEARLY, 'period_start': start, 'period_end': end, 'status': Budget.STATUS_ENTRY_OPEN}
            )
            budget_line, _ = BudgetLine.objects.get_or_create(
                budget=budget, sequence=1, item_name='Cloud Subscriptions',
                defaults={'procurement_class': BudgetLine.ProcurementClass.SERVICE_ITEM, 'original_qty_limit': Decimal('12'), 'original_unit_price': Decimal('200.00'), 'original_value_limit': Decimal('2400.00'), 'qty_limit': Decimal('12'), 'value_limit': Decimal('2400.00'), 'standard_price': Decimal('200.00')}
            )

        # Supplier
        supplier, _ = Supplier.objects.get_or_create(
            company_id=company_id, code='SUP-ACME',
            defaults={'name': 'ACME Supplies', 'status': Supplier.Status.ACTIVE, 'supplier_type': Supplier.SupplierType.LOCAL, 'payable_account': ap_acct}
        )

        # Purchase Order
        po, _ = PurchaseOrder.objects.get_or_create(
            company_id=company_id,
            supplier=supplier,
            defaults={'order_date': date.today(), 'delivery_address': wh, 'status': PurchaseOrder.Status.DRAFT}
        )
        if po.lines.count() == 0:
            # Use bulk_create to bypass model save() that references legacy fields
            pol = PurchaseOrderLine(
                purchase_order=po,
                line_number=1,
                budget_line=budget_line,
                product=item,
                description=f"{item.name}",
                quantity=Decimal('20.000'),
                unit_price=item.cost_price or Decimal('10.00'),
                expected_delivery_date=date.today() + timedelta(days=7),
                tax_rate=Decimal('0'),
                line_total=(item.cost_price or Decimal('10.00')) * Decimal('20.000'),
                tax_value=Decimal('0'),
            )
            PurchaseOrderLine.objects.bulk_create([pol])
            po.refresh_totals(commit=True)
            po.mark_submitted()
            po.mark_approved(user=None)
            po.mark_issued()

        # Goods Receipt against PO
        grn, created = GoodsReceipt.objects.get_or_create(
            company_id=company_id,
            supplier=supplier,
            purchase_order=po,
            defaults={'receipt_number': 'GRN-DEMO', 'receipt_date': date.today(), 'status': 'DRAFT', 'notes': 'Demo GRN'}
        )
        if created or grn.lines.count() == 0:
            po_line = po.lines.first()
            qty = po_line.quantity
            GoodsReceiptLine.objects.create(
                goods_receipt=grn, purchase_order_line=po_line, item=item, quantity_received=qty
            )
            # Trigger posting side-effects directly to avoid workflow gating
            grn._on_posted()

        self.stdout.write(self.style.SUCCESS(
            f"Seeded procurement demo for company={company_id}: PO {po.order_number} and GRN {grn.receipt_number}."
        ))
