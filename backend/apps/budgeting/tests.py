from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.budgeting.models import (
    Budget,
    BudgetLine,
    BudgetOverrideRequest,
    BudgetUsage,
    CostCenter,
)
from apps.companies.models import Company, CompanyGroup
from apps.users.models import User


class BudgetingModelTests(TestCase):
    def setUp(self):
        self.group = CompanyGroup.objects.create(name="UnitTest Group", db_name="cg_test")
        self.company = Company.objects.create(
            company_group=self.group,
            code="UNIT",
            name="UnitTest Co",
            legal_name="UnitTest Co",
            currency_code="USD",
            fiscal_year_start="2025-01-01",
            tax_id="UT-1",
            registration_number="UT-REG",
        )
        self.user = User.objects.create_user(username="budget-user", password="pass1234")
        self.cost_center = CostCenter.objects.create(
            code="OPS",
            name="Operations",
            company=self.company,
            company_group=self.group,
            owner=self.user,
        )
        self.budget = Budget.objects.create(
            company=self.company,
            cost_center=self.cost_center,
            name="FY25 Operations",
            budget_type=Budget.TYPE_OPERATIONAL,
            period_start="2025-01-01",
            period_end="2025-12-31",
            amount=Decimal("0"),
            status=Budget.STATUS_ACTIVE,
        )
        self.line = BudgetLine.objects.create(
            budget=self.budget,
            sequence=1,
            procurement_class=BudgetLine.ProcurementClass.STOCK_ITEM,
            item_name="Raw materials",
            qty_limit=Decimal("100"),
            value_limit=Decimal("10000"),
            tolerance_percent=5,
        )

    def test_budget_usage_updates_totals(self):
        BudgetUsage.objects.create(
            budget_line=self.line,
            usage_type="stock_issue",
            quantity=Decimal("10"),
            amount=Decimal("2500"),
            reference_type="PO",
            reference_id="PO-1",
        )
        self.line.refresh_from_db()
        self.budget.refresh_from_db()
        self.assertEqual(self.line.consumed_value, Decimal("2500"))
        self.assertEqual(self.budget.consumed, Decimal("2500"))
        self.assertEqual(self.budget.amount, Decimal("10000"))
        self.assertEqual(self.line.remaining_value, Decimal("7500"))

    def test_override_request_status_flow(self):
        override = BudgetOverrideRequest.objects.create(
            company=self.company,
            cost_center=self.cost_center,
            budget_line=self.line,
            requested_by=self.user,
            status=BudgetOverrideRequest.STATUS_PENDING,
            reason="Emergency purchase",
            requested_amount=Decimal("1200"),
        )
        override.mark(BudgetOverrideRequest.STATUS_APPROVED, user=self.user, notes="Approved for urgent demand")
        override.refresh_from_db()
        self.assertEqual(override.status, BudgetOverrideRequest.STATUS_APPROVED)
        self.assertIsNotNone(override.approved_at)


class BudgetingAPIViewTests(TestCase):
    def setUp(self):
        self.group = CompanyGroup.objects.create(name="API Group", db_name="cg_api")
        self.company = Company.objects.create(
            company_group=self.group,
            code="API",
            name="API Company",
            legal_name="API Company",
            currency_code="USD",
            fiscal_year_start="2025-01-01",
            tax_id="API-1",
            registration_number="API-REG",
        )
        self.user = User.objects.create_user(username="api-user", password="pass1234")
        self.user.is_staff = True
        self.user.is_system_admin = True
        self.user.save(update_fields=["is_staff", "is_system_admin"])
        token = RefreshToken.for_user(self.user).access_token
        self.client.defaults['HTTP_AUTHORIZATION'] = f"Bearer {token}"
        self.client.defaults['HTTP_X_COMPANY_ID'] = str(self.company.id)

        self.cost_center = CostCenter.objects.create(
            code="FIN",
            name="Finance",
            company=self.company,
            company_group=self.group,
        )
        self.budget = Budget.objects.create(
            company=self.company,
            cost_center=self.cost_center,
            name="Finance FY25",
            budget_type=Budget.TYPE_OPEX,
            period_start="2025-01-01",
            period_end="2025-12-31",
            amount=Decimal("0"),
            status=Budget.STATUS_ACTIVE,
        )
        self.line = BudgetLine.objects.create(
            budget=self.budget,
            sequence=1,
            procurement_class=BudgetLine.ProcurementClass.SERVICE_ITEM,
            item_name="Audit fees",
            value_limit=Decimal("5000"),
        )

    def test_workspace_summary_endpoint(self):
        BudgetUsage.objects.create(
            budget_line=self.line,
            usage_type="service_receipt",
            amount=Decimal("800"),
            quantity=Decimal("1"),
            reference_type="BILL",
            reference_id="BILL-1",
        )
        url = reverse('budget-workspace-summary')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('budget_count', data)
        self.assertIn('pending_override_count', data)

    def test_override_request_api(self):
        create_url = '/api/v1/budgets/overrides/'
        payload = {
            'cost_center': self.cost_center.id,
            'budget_line': self.line.id,
            'reason': 'Unexpected compliance audit',
            'requested_amount': '1200',
            'requested_quantity': '1',
        }
        response = self.client.post(create_url, payload, format='json')
        self.assertEqual(response.status_code, 201)
        override_id = response.json()['id']

        approve_url = f'/api/v1/budgets/overrides/{override_id}/approve/'
        response = self.client.post(approve_url, {'notes': 'Approved'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], BudgetOverrideRequest.STATUS_APPROVED)
