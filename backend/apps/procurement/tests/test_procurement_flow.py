from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.budgeting.models import Budget, BudgetCommitment, BudgetLine, BudgetUsage, CostCenter
from apps.companies.models import Company, CompanyGroup
from apps.finance.models import Account, AccountType
from apps.inventory.models import GoodsReceipt, GoodsReceiptLine, Product, ProductCategory, UnitOfMeasure, Warehouse
from apps.procurement.models import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequisition,
    PurchaseRequisitionLine,
    Supplier,
)
from apps.users.models import User


class ProcurementFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="buyer", password="pass123")
        self.company_group = CompanyGroup.objects.create(name="Test Group", db_name="cg_test")
        self.company = Company.objects.create(
            company_group=self.company_group,
            code="TST",
            name="Test Company",
            legal_name="Test Company Ltd",
            currency_code="USD",
            fiscal_year_start="2025-01-01",
            tax_id="TAX",
            registration_number="REG",
        )
        self.cost_center = CostCenter.objects.create(
            company=self.company,
            company_group=self.company_group,
            code="OPS",
            name="Operations",
        )
        self.budget = Budget.objects.create(
            company=self.company,
            cost_center=self.cost_center,
            name="Ops Budget",
            budget_type=Budget.TYPE_OPEX,
            period_start="2025-01-01",
            period_end="2025-12-31",
            amount=Decimal("10000"),
            status=Budget.STATUS_ACTIVE,
        )
        self.budget_line = BudgetLine.objects.create(
            budget=self.budget,
            sequence=1,
            procurement_class=BudgetLine.ProcurementClass.STOCK_ITEM,
            item_name="Test Item",
            qty_limit=Decimal("1000"),
            value_limit=Decimal("10000"),
            standard_price=Decimal("100"),
            tolerance_percent=10,
        )

        self.payable_account = Account.objects.create(
            company_group=self.company_group,
            company=self.company,
            code="2100",
            name="Accounts Payable",
            account_type=AccountType.LIABILITY,
        )
        self.expense_account = Account.objects.create(
            company_group=self.company_group,
            company=self.company,
            code="5100",
            name="Expense",
            account_type=AccountType.EXPENSE,
        )
        self.income_account = Account.objects.create(
            company_group=self.company_group,
            company=self.company,
            code="4100",
            name="Revenue",
            account_type=AccountType.REVENUE,
        )
        self.inventory_account = Account.objects.create(
            company_group=self.company_group,
            company=self.company,
            code="1100",
            name="Inventory",
            account_type=AccountType.ASSET,
        )

        self.supplier = Supplier.objects.create(
            company=self.company,
            created_by=self.user,
            code="SUP-1",
            name="Primary Supplier",
            payable_account=self.payable_account,
        )
        self.category = ProductCategory.objects.create(company=self.company, created_by=self.user, code="RAW", name="Raw Material")
        self.uom = UnitOfMeasure.objects.create(company=self.company, created_by=self.user, code="KG", name="Kilogram")
        self.product = Product.objects.create(
            company=self.company,
            created_by=self.user,
            code="RM-001",
            name="Raw Material",
            category=self.category,
            uom=self.uom,
            expense_account=self.expense_account,
            income_account=self.income_account,
            inventory_account=self.inventory_account,
        )
        self.warehouse = Warehouse.objects.create(company=self.company, created_by=self.user, code="MAIN", name="Main Warehouse")

    def _create_requisition(self) -> PurchaseRequisition:
        requisition = PurchaseRequisition.objects.create(
            company=self.company,
            cost_center=self.cost_center,
            requested_by=self.user,
            request_type=BudgetLine.ProcurementClass.STOCK_ITEM,
            priority=PurchaseRequisition.Priority.NORMAL,
        )
        PurchaseRequisitionLine.objects.create(
            requisition=requisition,
            line_number=1,
            budget_line=self.budget_line,
            item=self.product,
            description="Raw material replenishment",
            quantity=Decimal("10"),
            estimated_unit_cost=Decimal("100"),
        )
        requisition.refresh_totals(commit=True)
        return requisition

    def _create_purchase_order(self, requisition: PurchaseRequisition) -> tuple[PurchaseOrder, PurchaseOrderLine]:
        purchase_order = PurchaseOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            requisition=requisition,
            cost_center=self.cost_center,
            created_by=self.user,
            order_date=timezone.now().date(),
            currency="USD",
            delivery_address=self.warehouse,
        )
        requisition_line = requisition.lines.first()
        po_line = PurchaseOrderLine.objects.create(
            purchase_order=purchase_order,
            line_number=1,
            requisition_line=requisition_line,
            budget_line=self.budget_line,
            item=self.product,
            description=requisition_line.description,
            quantity=Decimal("10"),
            unit_price=Decimal("100"),
            expected_delivery_date=timezone.now().date(),
            tolerance_percent=self.budget_line.tolerance_percent,
        )
        purchase_order.refresh_totals(commit=True)
        requisition.mark_converted()
        return purchase_order, po_line

    def test_requisition_approval_creates_commitment(self):
        requisition = self._create_requisition()
        requisition.submit(self.user)
        requisition.approve(self.user)

        requisition_line = requisition.lines.first()
        commitment = BudgetCommitment.objects.get(source_type="PR_LINE", source_reference=str(requisition_line.id))
        self.assertEqual(commitment.status, BudgetCommitment.Status.RESERVED)
        self.assertEqual(commitment.committed_value, Decimal("1000"))

        self.budget_line.refresh_from_db()
        self.assertEqual(self.budget_line.committed_value, Decimal("1000"))

    def test_convert_requisition_to_po_releases_requisition_commitment(self):
        requisition = self._create_requisition()
        requisition.submit(self.user)
        requisition.approve(self.user)
        requisition_line = requisition.lines.first()
        BudgetCommitment.objects.get(source_type="PR_LINE", source_reference=str(requisition_line.id))

        purchase_order, po_line = self._create_purchase_order(requisition)

        # Requisition commitment should be released after conversion
        with self.assertRaises(BudgetCommitment.DoesNotExist):
            BudgetCommitment.objects.get(source_type="PR_LINE", source_reference=str(requisition_line.id), status__in=BudgetCommitment.ACTIVE_STATUSES)

        # Purchase order commitment should exist
        po_commitment = BudgetCommitment.objects.get(source_type="PO_LINE", source_reference=str(po_line.id))
        self.assertEqual(po_commitment.status, BudgetCommitment.Status.CONVERTED)
        self.assertEqual(po_commitment.committed_value, Decimal("1000"))

    def test_goods_receipt_consumes_budget_and_updates_commitment(self):
        requisition = self._create_requisition()
        requisition.submit(self.user)
        requisition.approve(self.user)
        purchase_order, po_line = self._create_purchase_order(requisition)

        goods_receipt = GoodsReceipt.objects.create(
            company=self.company,
            created_by=self.user,
            receipt_number="GR-0001",
            receipt_date=timezone.now().date(),
            status="DRAFT",
            supplier=self.supplier,
            purchase_order=purchase_order,
        )
        GoodsReceiptLine.objects.create(
            goods_receipt=goods_receipt,
            item=self.product,
            purchase_order_line=po_line,
            quantity_received=Decimal("10"),
        )

        goods_receipt.status = "POSTED"
        goods_receipt.save()

        self.budget_line.refresh_from_db()
        self.assertEqual(self.budget_line.consumed_value, Decimal("1000"))

        po_commitment = BudgetCommitment.objects.get(source_type="PO_LINE", source_reference=str(po_line.id))
        self.assertEqual(po_commitment.status, BudgetCommitment.Status.CONSUMED)
        self.assertEqual(po_commitment.remaining_value, Decimal("0"))

        usage = BudgetUsage.objects.get(reference_type="GoodsReceipt", reference_id=f"{goods_receipt.id}:{po_line.id}")
        self.assertEqual(usage.amount, Decimal("1000"))
        self.assertEqual(usage.usage_type, "procurement_receipt")

        purchase_order.refresh_from_db()
        self.assertEqual(purchase_order.status, PurchaseOrder.Status.RECEIVED)
