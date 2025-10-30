from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.ai_companion.models import AIProactiveSuggestion
from apps.ai_companion.services.alert_engine import AlertEngine
from apps.budgeting.models import Budget, CostCenter
from apps.companies.models import Company, CompanyGroup
from apps.finance.models import Account, AccountType, Invoice
from apps.inventory.models import Product, ProductCategory, StockLevel, UnitOfMeasure, Warehouse
from apps.permissions.models import Permission, Role
from apps.users.models import User, UserCompanyRole


class AlertEngineTestCase(TestCase):
    def setUp(self):
        self.group = CompanyGroup.objects.create(
            name="Alert Group",
            db_name="cg_alert_group",
            industry_pack_type="manufacturing",
        )
        self.company = Company.objects.create(
            company_group=self.group,
            code="ALERT",
            name="Alert Company",
            legal_name="Alert Company Ltd.",
            currency_code="USD",
            fiscal_year_start=date(2024, 1, 1),
            tax_id="ALERT-TAX",
            registration_number="ALERT-REG",
        )
        self.user = User.objects.create_user(username="alert-user", password="pass1234", is_active=True)
        self.user.company_groups.add(self.group)

        # permissions & roles
        self.perm_finance = Permission.objects.create(code="finance.view_reports", name="View Finance", module="finance")
        self.perm_inventory = Permission.objects.create(code="inventory.view_stock", name="View Stock", module="inventory")
        self.perm_budget = Permission.objects.create(code="budgeting.view_budgets", name="View Budgets", module="budgeting")

        finance_role = Role.objects.create(name="Finance Manager", company=self.company)
        finance_role.permissions.add(self.perm_finance)
        inventory_role = Role.objects.create(name="Inventory Manager", company=self.company)
        inventory_role.permissions.add(self.perm_inventory)
        budget_role = Role.objects.create(name="Budget Owner", company=self.company)
        budget_role.permissions.add(self.perm_budget)

        UserCompanyRole.objects.create(user=self.user, company_group=self.group, company=self.company, role=finance_role, is_active=True)
        UserCompanyRole.objects.create(user=self.user, company_group=self.group, company=self.company, role=inventory_role, is_active=True)
        UserCompanyRole.objects.create(user=self.user, company_group=self.group, company=self.company, role=budget_role, is_active=True)

        # Finance data: overdue invoice
        account = Account.objects.create(
            company_group=self.group,
            company=self.company,
            created_by=None,
            code="AR-100",
            name="Accounts Receivable",
            account_type=AccountType.ASSET,
            currency="USD",
        )
        self.invoice = Invoice.objects.create(
            company_group=self.group,
            company=self.company,
            created_by=self.user,
            invoice_number="INV-001",
            invoice_type="AR",
            partner_type="customer",
            partner_id=1,
            invoice_date=timezone.now().date() - timedelta(days=30),
            due_date=timezone.now().date() - timedelta(days=20),
            subtotal=Decimal("60000"),
            tax_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            total_amount=Decimal("60000"),
            paid_amount=Decimal("0"),
            currency="USD",
            exchange_rate=Decimal("1"),
            status="POSTED",
            notes="Overdue invoice",
            journal_voucher=None,
        )

        # Inventory data: low stock product
        category = ProductCategory.objects.create(company=self.company, code="RM", name="Raw Material")
        uom = UnitOfMeasure.objects.create(company=self.company, code="KG", name="Kilogram")
        expense_account = Account.objects.create(
            company_group=self.group,
            company=self.company,
            created_by=None,
            code="EXP-100",
            name="Expense",
            account_type=AccountType.EXPENSE,
            currency="USD",
        )
        income_account = Account.objects.create(
            company_group=self.group,
            company=self.company,
            created_by=None,
            code="INC-100",
            name="Income",
            account_type=AccountType.REVENUE,
            currency="USD",
        )
        inventory_account = Account.objects.create(
            company_group=self.group,
            company=self.company,
            created_by=None,
            code="INV-100",
            name="Inventory",
            account_type=AccountType.ASSET,
            currency="USD",
        )
        product = Product.objects.create(
            company=self.company,
            created_by=self.user,
            code="RM-001",
            name="Raw Material",
            product_type="GOODS",
            track_inventory=True,
            cost_price=Decimal("10"),
            selling_price=Decimal("12"),
            reorder_level=Decimal("5"),
            reorder_quantity=Decimal("20"),
            category=category,
            uom=uom,
            expense_account=expense_account,
            income_account=income_account,
            inventory_account=inventory_account,
        )
        warehouse = Warehouse.objects.create(company=self.company, created_by=self.user, code="MAIN", name="Main Warehouse")
        StockLevel.objects.create(company=self.company, created_by=self.user, product=product, warehouse=warehouse, quantity=Decimal("0"))

        # Budget data: threshold breach
        cost_center = CostCenter.objects.create(company=self.company, code="CC-001", name="Operations")
        Budget.objects.create(
            company=self.company,
            cost_center=cost_center,
            fiscal_year="2025",
            amount=Decimal("100000"),
            consumed=Decimal("95000"),
            threshold_percent=90,
            status=Budget.STATUS_ACTIVE,
        )

    def test_alert_engine_generates_alerts(self):
        engine = AlertEngine()
        created = engine.run(company=self.company)
        self.assertGreaterEqual(created, 3)

        finance_alert = AIProactiveSuggestion.objects.get(metadata__rule_code=AlertEngine.RULE_OVERDUE_AR)
        self.assertEqual(finance_alert.alert_type, "finance")
        self.assertEqual(finance_alert.severity, AIProactiveSuggestion.AlertSeverity.CRITICAL)
        self.assertEqual(finance_alert.user, self.user)

        inventory_alert = AIProactiveSuggestion.objects.get(metadata__rule_code=AlertEngine.RULE_LOW_STOCK)
        self.assertEqual(inventory_alert.alert_type, "inventory")
        self.assertEqual(inventory_alert.severity, AIProactiveSuggestion.AlertSeverity.CRITICAL)

        budget_alert = AIProactiveSuggestion.objects.get(metadata__rule_code=AlertEngine.RULE_BUDGET_THRESHOLD)
        self.assertEqual(budget_alert.alert_type, "budget")
        self.assertEqual(budget_alert.severity, AIProactiveSuggestion.AlertSeverity.WARNING)

        # Running engine again should update existing alerts, not duplicate
        engine.run(company=self.company)
        self.assertEqual(
            AIProactiveSuggestion.objects.filter(user=self.user, company=self.company, status="pending").count(),
            3,
        )
