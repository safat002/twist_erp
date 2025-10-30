from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company, CompanyGroup
from apps.finance.models import Account, AccountType, Journal, JournalVoucher
from apps.inventory.models import Product, ProductCategory, StockLevel, StockMovement, UnitOfMeasure, Warehouse


class ProductionModuleAPITests(APITestCase):
    def setUp(self):
        self.group = CompanyGroup.objects.create(name="Manufacturing Group", db_name="cg_mfg_test")
        self.company = Company.objects.create(
            company_group=self.group,
            code="MFG01",
            name="Manufacturing Co",
            legal_name="Manufacturing Company Ltd",
            fiscal_year_start=date(2025, 1, 1),
            tax_id="TAX123",
            registration_number="REG123",
        )
        User = get_user_model()
        self.user = User.objects.create_user(username="planner", password="pass123", email="planner@example.com")
        self.client.force_authenticate(user=self.user)
        self.headers = {"HTTP_X_COMPANY_ID": str(self.company.id)}

        # Finance accounts required for inventory products
        self.inventory_account = Account.objects.create(
            company=self.company,
            company_group=self.group,
            created_by=self.user,
            code="1500",
            name="Finished Goods Inventory",
            account_type=AccountType.ASSET,
        )
        self.expense_account = Account.objects.create(
            company=self.company,
            company_group=self.group,
            created_by=self.user,
            code="5100",
            name="Manufacturing Expense",
            account_type=AccountType.EXPENSE,
        )
        self.income_account = Account.objects.create(
            company=self.company,
            company_group=self.group,
            created_by=self.user,
            code="4100",
            name="Sales Revenue",
            account_type=AccountType.REVENUE,
        )

        self.category = ProductCategory.objects.create(
            company=self.company,
            created_by=self.user,
            code="FG",
            name="Finished Goods",
        )
        self.uom = UnitOfMeasure.objects.create(company=self.company, created_by=self.user, code="PCS", name="Pieces")
        self.component_category = ProductCategory.objects.create(
            company=self.company,
            created_by=self.user,
            code="RM",
            name="Raw Materials",
        )
        self.raw_uom = UnitOfMeasure.objects.create(company=self.company, created_by=self.user, code="KG", name="Kilogram")

        self.finished_product = Product.objects.create(
            company=self.company,
            created_by=self.user,
            code="FG-100",
            name="Finished Product",
            category=self.category,
            uom=self.uom,
            cost_price=Decimal("120"),
            expense_account=self.expense_account,
            income_account=self.income_account,
            inventory_account=self.inventory_account,
        )
        self.component_product = Product.objects.create(
            company=self.company,
            created_by=self.user,
            code="RM-001",
            name="Component A",
            category=self.component_category,
            uom=self.raw_uom,
            cost_price=Decimal("50"),
            expense_account=self.expense_account,
            income_account=self.income_account,
            inventory_account=self.inventory_account,
        )

        self.warehouse = Warehouse.objects.create(
            company=self.company,
            created_by=self.user,
            code="MAIN",
            name="Main Plant",
        )

        StockLevel.objects.create(
            company=self.company,
            created_by=self.user,
            product=self.component_product,
            warehouse=self.warehouse,
            quantity=Decimal("100"),
        )

        Journal.objects.create(
            company=self.company,
            company_group=self.group,
            created_by=self.user,
            code="GENERAL",
            name="General Journal",
            type="GENERAL",
        )

    def test_bom_workorder_issue_and_receipt_flow(self):
        # Create BOM
        bom_payload = {
            "product": self.finished_product.id,
            "name": "FG Master BOM",
            "version": "1.0",
            "status": "ACTIVE",
            "components": [
                {
                    "component": self.component_product.id,
                    "quantity": "2.5",
                    "uom": self.raw_uom.id,
                    "scrap_percent": "0.00",
                    "warehouse": self.warehouse.id,
                }
            ],
        }
        response = self.client.post(
            "/api/v1/production/boms/",
            bom_payload,
            format="json",
            **self.headers,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        bom_id = response.json()["id"]

        # Create work order
        work_order_payload = {
            "product": self.finished_product.id,
            "bom": bom_id,
            "quantity_planned": "10",
            "priority": "HIGH",
            "warehouse": self.warehouse.id,
            "scheduled_start": "2025-02-01",
            "scheduled_end": "2025-02-05",
        }
        wo_response = self.client.post(
            "/api/v1/production/work-orders/",
            work_order_payload,
            format="json",
            **self.headers,
        )
        self.assertEqual(wo_response.status_code, status.HTTP_201_CREATED, wo_response.json())
        work_order = wo_response.json()
        work_order_id = work_order["id"]
        self.assertEqual(len(work_order["components"]), 1)
        component_id = work_order["components"][0]["id"]

        # Issue material
        issue_payload = {
            "issue_date": "2025-02-01",
            "lines": [
                {"component": component_id, "quantity": "20", "warehouse": self.warehouse.id},
            ],
        }
        issue_response = self.client.post(
            f"/api/v1/production/work-orders/{work_order_id}/issue-materials/",
            issue_payload,
            format="json",
            **self.headers,
        )
        self.assertEqual(issue_response.status_code, status.HTTP_201_CREATED, issue_response.json())
        self.assertEqual(issue_response.json()["lines"][0]["quantity"], "20.000")

        # Record receipt
        receipt_payload = {
            "receipt_date": "2025-02-06",
            "quantity_good": "9.5",
            "quantity_scrap": "0.5",
        }
        receipt_response = self.client.post(
            f"/api/v1/production/work-orders/{work_order_id}/record-receipt/",
            receipt_payload,
            format="json",
            **self.headers,
        )
        self.assertEqual(receipt_response.status_code, status.HTTP_201_CREATED, receipt_response.json())
        self.assertEqual(receipt_response.json()["quantity_good"], "9.500")

        # Fetch work order to confirm status/completion
        detail = self.client.get(
            f"/api/v1/production/work-orders/{work_order_id}/",
            format="json",
            **self.headers,
        )
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        data = detail.json()
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["quantity_completed"], "9.500")

        component_level = StockLevel.objects.get(
            company=self.company, product=self.component_product, warehouse=self.warehouse
        )
        self.assertEqual(str(component_level.quantity.quantize(Decimal("0.001"))), "80.000")

        finished_level = StockLevel.objects.get(
            company=self.company, product=self.finished_product, warehouse=self.warehouse
        )
        self.assertEqual(str(finished_level.quantity.quantize(Decimal("0.001"))), "9.500")

        self.assertGreaterEqual(
            JournalVoucher.objects.filter(company=self.company).count(),
            2,
        )
        self.assertGreaterEqual(
            StockMovement.objects.filter(company=self.company, reference=data["number"]).count(),
            2,
        )
