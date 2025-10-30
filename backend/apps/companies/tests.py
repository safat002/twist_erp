from __future__ import annotations

import datetime
from unittest import mock

from django.test import TestCase

from apps.companies.models import Company, CompanyGroup
from apps.companies.services.provisioning import CompanyGroupProvisioner, ProvisioningError


class CompanyGroupProvisionerTests(TestCase):
    def setUp(self):
        self.provisioner = CompanyGroupProvisioner()

    def test_provision_creates_active_group_and_company(self):
        payload = {
            "code": "ACMEHQ",
            "name": "Acme HQ",
            "legal_name": "Acme Holdings Ltd.",
            "currency_code": "USD",
            "fiscal_year_start": datetime.date(2024, 1, 1),
            "tax_id": "ACME-TAX-001",
            "registration_number": "ACME-REG-001",
        }
        with mock.patch.object(self.provisioner, "_ensure_database_exists") as ensure_db, \
            mock.patch.object(self.provisioner, "_register_database_alias") as register_alias, \
            mock.patch.object(self.provisioner, "_run_migrations") as run_migrations:
            result = self.provisioner.provision(
                group_name="Acme Holdings",
                industry_pack="manufacturing",
                supports_intercompany=True,
                default_company_payload=payload,
            )

        ensure_db.assert_called_once()
        register_alias.assert_called_once()
        run_migrations.assert_called_once()

        self.assertIsNotNone(result.company_group.id)
        self.assertEqual(result.company_group.status, "active")
        self.assertEqual(result.company_group.db_name, "cg_acme-holdings")
        self.assertTrue(result.company_group.supports_intercompany)

        self.assertEqual(result.company.code, "ACMEHQ")
        self.assertEqual(result.company.company_group, result.company_group)
        self.assertTrue(Company.objects.filter(id=result.company.id).exists())

    def test_provision_raises_when_database_collision(self):
        CompanyGroup.objects.create(
            name="Existing Group",
            db_name="cg_acme-holdings",
            industry_pack_type="manufacturing",
        )

        with self.assertRaises(ProvisioningError):
            self.provisioner.provision(group_name="Acme Holdings")

    def test_provision_marks_group_failed_on_error(self):
        with mock.patch.object(self.provisioner, "_ensure_database_exists"), \
            mock.patch.object(self.provisioner, "_register_database_alias"), \
            mock.patch.object(self.provisioner, "_run_migrations"), \
            mock.patch.object(self.provisioner, "_create_company", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                self.provisioner.provision(group_name="Failed Group")

        group = CompanyGroup.objects.get(name="Failed Group")
        self.assertEqual(group.status, "failed")
        self.assertFalse(Company.objects.filter(company_group=group).exists())
