from __future__ import annotations

import datetime

from django.test import TestCase

from apps.companies.models import Company, CompanyGroup
from apps.metadata.services import MetadataScope, create_metadata_version, resolve_metadata


class MetadataResolutionTests(TestCase):
    def setUp(self):
        self.group = CompanyGroup.objects.create(
            name="Test Group",
            db_name="cg_test_group",
            industry_pack_type="manufacturing",
        )
        self.company = Company.objects.create(
            company_group=self.group,
            code="TESTCO",
            name="Test Company",
            legal_name="Test Company Ltd.",
            currency_code="USD",
            fiscal_year_start=datetime.date(2024, 1, 1),
            tax_id="TEST-TAX-001",
            registration_number="TEST-REG-001",
        )

    def test_resolve_metadata_merges_layers(self):
        key = "form.purchase_order"
        kind = "FORM"

        base = create_metadata_version(
            key=key,
            kind=kind,
            layer="CORE",
            scope=MetadataScope.global_scope(),
            definition={
                "form": {
                    "title": "Purchase Order",
                    "sections": {
                        "main": {
                            "label": "Main Section",
                            "fields": ["supplier", "total_amount"],
                        }
                    },
                }
            },
            status="active",
        )
        base.activate()

        group_version = create_metadata_version(
            key=key,
            kind=kind,
            layer="GROUP_CUSTOM",
            scope=MetadataScope.for_group(self.group),
            definition={
                "form": {
                    "title": "PO - Manufacturing Template",
                    "sections": {"approval": {"label": "Approval Routing"}},
                }
            },
            status="active",
        )
        group_version.activate()

        company_version = create_metadata_version(
            key=key,
            kind=kind,
            layer="COMPANY_OVERRIDE",
            scope=MetadataScope.for_company(self.company),
            definition={"form": {"sections": {"main": {"label": "Main (Dhaka)"}}}},
            status="active",
        )
        company_version.activate()

        resolved = resolve_metadata(
            key=key,
            kind=kind,
            company=self.company,
            company_group=self.group,
        )

        definition = resolved["definition"]
        self.assertEqual(definition["form"]["title"], "PO - Manufacturing Template")
        self.assertEqual(
            definition["form"]["sections"]["main"]["label"],
            "Main (Dhaka)",
        )
        self.assertEqual(
            definition["form"]["sections"]["main"]["fields"],
            ["supplier", "total_amount"],
        )
        self.assertEqual(
            definition["form"]["sections"]["approval"]["label"],
            "Approval Routing",
        )
        self.assertEqual(
            resolved["sources"],
            {
                "GLOBAL": base.version,
                "GROUP": group_version.version,
                "COMPANY": company_version.version,
            },
        )

    def test_resolve_metadata_handles_missing_layers(self):
        key = "form.customer"
        kind = "FORM"
        definition = {"form": {"title": "Customer Form"}}
        version = create_metadata_version(
            key=key,
            kind=kind,
            layer="CORE",
            scope=MetadataScope.global_scope(),
            definition=definition,
            status="active",
        )
        version.activate()

        resolved = resolve_metadata(key=key, kind=kind, company_group=self.group)

        self.assertEqual(resolved["definition"], definition)
        self.assertEqual(resolved["sources"], {"GLOBAL": version.version})
