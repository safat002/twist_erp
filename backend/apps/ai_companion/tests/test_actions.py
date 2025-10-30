from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient

from apps.ai_companion.models import AIActionExecution, AITelemetryEvent
from apps.ai_companion.services.rate_limiter import RateLimitState
from apps.audit.models import AuditLog
from apps.companies.models import Company, CompanyGroup
from apps.dashboard.models import DashboardLayout
from apps.finance.models import Account, AccountType, Invoice
from apps.metadata.models import MetadataDefinition
from apps.metadata.services import MetadataScope, create_metadata_version
from apps.permissions.models import Permission, Role
from apps.users.models import User, UserCompanyRole
from apps.workflows.models import WorkflowInstance, WorkflowTemplate


class AIActionExecuteTests(TestCase):
    def setUp(self):
        self.group = CompanyGroup.objects.create(
            name="Action Group",
            db_name="cg_action_group",
            industry_pack_type="services",
        )
        self.company = Company.objects.create(
            company_group=self.group,
            code="ACT",
            name="Action Co",
            legal_name="Action Company Ltd.",
            currency_code="USD",
            fiscal_year_start=date(2024, 1, 1),
            tax_id="ACT-TAX",
            registration_number="ACT-REG",
        )
        self.user = User.objects.create_user(username="action-user", password="pass1234")
        self.user.company_groups.add(self.group)

        perm = Permission.objects.create(code="finance.view_reports", name="View Finance", module="finance")
        role = Role.objects.create(name="Finance Manager", company=self.company)
        role.permissions.add(perm)
        UserCompanyRole.objects.create(
            user=self.user,
            company_group=self.group,
            company=self.company,
            role=role,
            is_active=True,
        )

        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.user)
        session = self.api_client.session
        session["active_company_group_id"] = self.group.id
        session["active_company_id"] = self.company.id
        session.save()

        receivable = Account.objects.create(
            company_group=self.group,
            company=self.company,
            created_by=None,
            code="AR01",
            name="Accounts Receivable",
            account_type=AccountType.ASSET,
            currency="USD",
        )
        self.invoice = Invoice.objects.create(
            company_group=self.group,
            company=self.company,
            created_by=self.user,
            invoice_number="INV-1001",
            invoice_type="AR",
            partner_type="customer",
            partner_id=1,
            invoice_date=date(2025, 1, 1),
            due_date=date(2025, 1, 15),
            subtotal=Decimal("1000"),
            tax_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            total_amount=Decimal("1000"),
            paid_amount=Decimal("0"),
            currency="USD",
            exchange_rate=Decimal("1"),
            status="POSTED",
            notes="",
            journal_voucher=None,
        )

        self.workflow_template = WorkflowTemplate.objects.create(
            name="Invoice Approval",
            definition={
                "states": ["draft", "submitted", "approved"],
                "transitions": {"draft": ["submitted"], "submitted": ["approved", "draft"]},
                "approvals": {"submitted": ["Finance Manager"]},
            },
            company=self.company,
            status="active",
        )
        self.workflow_instance = WorkflowInstance.objects.create(
            template=self.workflow_template,
            state="submitted",
            company=self.company,
            context={"invoice_id": self.invoice.id},
        )
        scope = MetadataScope.for_company(self.company)
        metadata = create_metadata_version(
            key="form.inventory_item",
            kind="FORM",
            layer="COMPANY_OVERRIDE",
            scope=scope,
            definition={"fields": []},
            status="active",
            user=self.user,
        )
        metadata.activate(user=self.user)
        self.metadata_key = metadata.key

    def test_execute_finance_followup_action(self):
        response = self.api_client.post(
            "/api/v1/ai/actions/",
            {
                "action": "finance.mark_receivable_followup",
                "payload": {"invoice_id": self.invoice.id, "note": "Customer contacted."},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertIn("Customer contacted.", self.invoice.notes)

        execution = AIActionExecution.objects.get(action_name="finance.mark_receivable_followup")
        self.assertEqual(execution.status, "success")
        self.assertEqual(execution.user, self.user)

        audit = AuditLog.objects.filter(
            action="AI_ACTION",
            entity_type="AI_ACTION",
            entity_id="finance.mark_receivable_followup",
        ).first()
        self.assertIsNotNone(audit)

    def test_unknown_action_returns_error(self):
        response = self.api_client.post(
            "/api/v1/ai/actions/",
            {"action": "unknown.action", "payload": {}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_metadata_promote_field_action(self):
        response = self.api_client.post(
            "/api/v1/ai/actions/",
            {
                "action": "metadata.promote_field",
                "payload": {
                    "definition_key": self.metadata_key,
                    "field": {
                        "name": "priority_flag",
                        "label": "Priority Flag",
                        "type": "boolean",
                    },
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        latest = (
            MetadataDefinition.objects.filter(key=self.metadata_key)
            .order_by("-version")
            .first()
        )
        self.assertIsNotNone(latest)
        field_names = [field.get("name") for field in latest.definition.get("fields", [])]
        self.assertIn("priority_flag", field_names)
        self.assertTrue(
            AITelemetryEvent.objects.filter(
                event_type="metadata.field_promoted",
                payload__definition_key=self.metadata_key,
            ).exists()
        )

    def test_metadata_create_dashboard_widget_action(self):
        DashboardLayout.objects.create(user=self.user, company=self.company, layout={}, widgets=[])
        response = self.api_client.post(
            "/api/v1/ai/actions/",
            {
                "action": "metadata.create_dashboard_widget",
                "payload": {
                    "widget": {
                        "id": "kpi-critical",
                        "title": "Critical KPI",
                    },
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        layout = DashboardLayout.objects.get(user=self.user, company=self.company)
        self.assertIn("kpi-critical", layout.widgets)
        self.assertTrue(
            AITelemetryEvent.objects.filter(
                event_type="metadata.dashboard_widget_added",
                payload__widget_id="kpi-critical",
            ).exists()
        )

    @mock.patch("apps.ai_companion.views.ACTION_RATE_LIMITER")
    def test_ai_action_rate_limited(self, mock_limiter):
        reset_at = timezone.now() + timedelta(seconds=30)
        mock_limiter.check.return_value = RateLimitState(False, 0, reset_at)
        response = self.api_client.post(
            "/api/v1/ai/actions/",
            {
                "action": "metadata.create_dashboard_widget",
                "payload": {"widget": {"id": "kpi-test"}},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)
        self.assertEqual(
            response.data.get("detail"),
            "Too many AI actions. Please wait before retrying.",
        )
    def test_workflow_explain_action(self):
        response = self.api_client.post(
            "/api/v1/ai/actions/",
            {
                "action": "workflows.explain_instance",
                "payload": {"workflow_instance_id": self.workflow_instance.id},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        result = response.data.get("result", {})
        self.assertEqual(result.get("details", {}).get("state"), "submitted")

    def test_workflow_explain_api(self):
        response = self.api_client.get(
            f"/api/v1/ai/workflows/explain/?instance_id={self.workflow_instance.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("state"), "submitted")
