from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.budgeting.models import Budget, BudgetLine, BudgetUsage, CostCenter
from apps.companies.models import Company, CompanyGroup
from apps.hr.models import (
    Department,
    Employee,
    EmploymentGrade,
    OvertimeEntry,
    OvertimePolicy,
    SalaryStructure,
)
from apps.hr.models import OvertimeRequestStatus
from apps.hr.views import OvertimeEntryViewSet
from apps.hr.services.payroll import PayrollService


class HROvertimeIntegrationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="approver", password="test123", email="approver@example.com")

        self.group = CompanyGroup.objects.create(name="Test Group", db_name="cg_test")
        self.company = Company.objects.create(
            company_group=self.group,
            code="TCO",
            name="Test Company",
            legal_name="Test Company Ltd",
            fiscal_year_start=date(2025, 1, 1),
            tax_id="TAX12345",
            registration_number="REG12345",
        )

        self.cost_center = CostCenter.objects.create(
            code="HR",
            name="Human Resources",
            company=self.company,
            company_group=self.group,
        )

        self.department = Department.objects.create(
            company=self.company,
            company_group=self.group,
            code="HR",
            name="Human Resources",
            created_by=self.user,
        )
        self.grade = EmploymentGrade.objects.create(
            company=self.company,
            company_group=self.group,
            code="G1",
            name="Grade 1",
            created_by=self.user,
        )
        self.salary_structure = SalaryStructure.objects.create(
            company=self.company,
            company_group=self.group,
            code="STD",
            name="Standard",
            overtime_rate=Decimal("120.00"),
            created_by=self.user,
        )

        self.employee = Employee.objects.create(
            company=self.company,
            employee_id="EMP001",
            first_name="Test",
            last_name="Employee",
            department=self.department,
            grade=self.grade,
            salary_structure=self.salary_structure,
            cost_center=self.cost_center,
            is_active=True,
        )

        self.budget = Budget.objects.create(
            cost_center=self.cost_center,
            company=self.company,
            name="HR Overtime",
            budget_type=Budget.TYPE_OPERATIONAL,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 12, 31),
            amount=Decimal("100000"),
        )
        self.budget_line = BudgetLine.objects.create(
            budget=self.budget,
            item_code="OT-LABOUR",
            item_name="Labour Overtime",
            value_limit=Decimal("100000"),
        )

        self.policy = OvertimePolicy.objects.create(
            company=self.company,
            company_group=self.group,
            code="OT",
            name="Default OT",
            auto_apply_budget=True,
            default_budget_line=self.budget_line,
            rate_multiplier=Decimal("1.50"),
            created_by=self.user,
        )

        self.factory = APIRequestFactory()

    def _create_overtime_entry(self, status="SUBMITTED", approved_hours=None):
        entry = OvertimeEntry.objects.create(
            company=self.company,
            employee=self.employee,
            policy=self.policy,
            date=date(2025, 10, 1),
            requested_hours=Decimal("4.0"),
            status=status,
            hourly_rate=Decimal("120.00"),
            created_by=self.user,
        )
        if approved_hours is not None:
            entry.approved_hours = Decimal(str(approved_hours))
            entry.save(update_fields=["approved_hours", "updated_at"])
        return entry

    def test_approve_overtime_entry_creates_budget_usage(self):
        entry = self._create_overtime_entry(status="SUBMITTED")

        request = self.factory.post(f"/api/v1/hr/overtime-entries/{entry.id}/approve/", data={})
        request.user = self.user
        request.company = self.company

        response = OvertimeEntryViewSet.as_view({"post": "approve_entry"})(request, pk=entry.pk)
        self.assertEqual(response.status_code, 200)

        entry.refresh_from_db()
        self.assertFalse(entry.posted_to_payroll)
        self.assertEqual(entry.status, OvertimeRequestStatus.APPROVED)

        usage = BudgetUsage.objects.get(reference_type="hr.OvertimeEntry", reference_id=str(entry.id))
        self.assertEqual(usage.amount, entry.amount)
        self.assertEqual(usage.usage_type, "overtime")

    def test_payroll_generation_marks_overtime_consumed(self):
        # Approve entry and ensure it is included in payroll
        entry = self._create_overtime_entry(status=OvertimeRequestStatus.APPROVED, approved_hours=3)
        entry.budget_line = self.budget_line
        entry.save(update_fields=["budget_line"])

        run = PayrollService.generate_payroll_run(
            company=self.company,
            period_start=date(2025, 10, 1),
            period_end=date(2025, 10, 31),
            created_by=self.user,
        )

        entry.refresh_from_db()
        self.assertTrue(entry.posted_to_payroll)
        self.assertEqual(entry.payroll_run, run)

        lines = list(run.lines.all())
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].employee, self.employee)
        self.assertEqual(lines[0].overtime_hours, Decimal("3"))
        self.assertGreater(lines[0].overtime_pay, Decimal("0"))
