from __future__ import annotations

from datetime import date

from django.test import TestCase

from rest_framework.test import APIClient

from apps.ai_companion.models import UserAIPreference
from apps.ai_companion.services.context_builder import ContextBuilder
from apps.ai_companion.services.memory import MemoryService
from apps.ai_companion.services.telemetry import TelemetryService
from apps.audit.models import AuditLog
from apps.companies.models import Company, CompanyGroup
from apps.permissions.models import Permission, Role
from apps.users.models import User, UserCompanyRole


class AIPreferenceAPITestCase(TestCase):
    def setUp(self):
        self.group = CompanyGroup.objects.create(
            name="Test Group",
            db_name="cg_test_group",
            industry_pack_type="manufacturing",
        )
        self.company = Company.objects.create(
            company_group=self.group,
            code="TST",
            name="Test Company",
            legal_name="Test Company Ltd.",
            currency_code="USD",
            fiscal_year_start=date(2024, 1, 1),
            tax_id="TEST-TAX",
            registration_number="TEST-REG",
        )
        self.permission = Permission.objects.create(
            code="finance.view_reports",
            name="View Finance Reports",
            module="finance",
        )
        self.role = Role.objects.create(name="Finance Manager", company=self.company)
        self.role.permissions.add(self.permission)

        self.user = User.objects.create_user(username="tester", password="pass1234")
        self.user.company_groups.add(self.group)
        UserCompanyRole.objects.create(
            user=self.user,
            company_group=self.group,
            company=self.company,
            role=self.role,
            is_active=True,
        )

        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.user)
        session = self.api_client.session
        session["active_company_group_id"] = self.group.id
        session["active_company_id"] = self.company.id
        session.save()

    def test_create_company_scoped_preference(self):
        response = self.api_client.post(
            "/api/v1/ai/preferences/",
            {"key": "default_currency", "value": "BDT", "company": self.company.id},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        pref = UserAIPreference.objects.get(user=self.user, key="default_currency")
        self.assertEqual(pref.value, "BDT")
        self.assertEqual(pref.company, self.company)

        audit = AuditLog.objects.filter(
            action="AI_PREF_SET",
            entity_type="AI_PREFERENCE",
            entity_id="default_currency",
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.company, self.company)

    def test_context_builder_includes_preferences_and_permissions(self):
        UserAIPreference.objects.create(user=self.user, key="theme", value="dark")
        UserAIPreference.objects.create(
            user=self.user,
            company=self.company,
            key="default_currency",
            value="BDT",
        )

        builder = ContextBuilder(
            memory_service=MemoryService(),
            telemetry_service=TelemetryService(),
        )
        bundle = builder.build(user=self.user, company=self.company, metadata={})

        short_term = bundle.short_term
        self.assertIn("Finance Manager", short_term.get("user_roles", []))
        self.assertIn("finance.view_reports", short_term.get("user_permissions", []))

        prefs = short_term.get("preferences", {})
        self.assertEqual(prefs.get("global", {}).get("theme"), "dark")
        self.assertEqual(prefs.get("company", {}).get("default_currency"), "BDT")
