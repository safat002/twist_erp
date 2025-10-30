from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company, CompanyGroup
from apps.permissions.models import Role
from apps.users.models import UserCompanyRole


User = get_user_model()


class CurrentUserProfileAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice",
            password="pass12345",
            email="alice@example.com",
            first_name="Alice",
            last_name="Anderson",
        )
        self.group = CompanyGroup.objects.create(name="Group A", db_name="cg_a")
        self.company = Company.objects.create(
            company_group=self.group,
            code="COMP",
            name="Primary Company",
            legal_name="Primary Company Ltd",
            currency_code="USD",
            fiscal_year_start="2025-01-01",
            tax_id="TAX-001",
            registration_number="REG-001",
        )
        self.role = Role.objects.create(name="Manager", company=self.company)
        UserCompanyRole.objects.create(
            user=self.user,
            company_group=self.group,
            company=self.company,
            role=self.role,
        )
        self.user.company_groups.add(self.group)
        self.user.default_company = self.company
        self.user.default_company_group = self.group
        self.user.save(update_fields=["default_company", "default_company_group"])

        self.client.force_authenticate(self.user)
        # reverse may not include the api prefix during tests; use explicit path for clarity
        self.url = "/api/v1/users/me/"

    def test_retrieve_current_user_profile(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.user.username)
        self.assertEqual(response.data["default_company"]["id"], self.company.id)
        self.assertIn("memberships", response.data)
        self.assertGreaterEqual(len(response.data["memberships"]), 1)

    def test_update_profile_and_default_company(self):
        secondary_company = Company.objects.create(
            company_group=self.group,
            code="COMP2",
            name="Secondary Company",
            legal_name="Secondary Company Ltd",
            currency_code="USD",
            fiscal_year_start="2025-01-01",
            tax_id="TAX-002",
            registration_number="REG-002",
        )
        secondary_role = Role.objects.create(name="Supervisor", company=secondary_company)
        UserCompanyRole.objects.create(
            user=self.user,
            company_group=self.group,
            company=secondary_company,
            role=secondary_role,
        )

        payload = {
            "first_name": "Alicia",
            "phone": "+8801555123456",
            "default_company_id": secondary_company.id,
        }
        response = self.client.patch(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Alicia")
        self.assertEqual(self.user.phone, "+8801555123456")
        self.assertEqual(self.user.default_company_id, secondary_company.id)

    def test_setting_non_member_company_fails(self):
        unauthorized_company = Company.objects.create(
            company_group=self.group,
            code="COMPX",
            name="Unauthorized Company",
            legal_name="Unauthorized Company Ltd",
            currency_code="USD",
            fiscal_year_start="2025-01-01",
            tax_id="TAX-999",
            registration_number="REG-999",
        )

        response = self.client.patch(
            self.url,
            {"default_company_id": unauthorized_company.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("default_company_id", response.data)
