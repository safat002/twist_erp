from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company, CompanyGroup
from apps.finance.models import Account, AccountType, Invoice, InvoiceStatus, Journal, Payment
from apps.sales.models import Customer


class FinanceModuleAPITests(APITestCase):
    maxDiff = None

    def setUp(self):
        self.group = CompanyGroup.objects.create(name="Twist Group", db_name="cg_twist_test")
        self.company = Company.objects.create(
            company_group=self.group,
            code="TWST",
            name="Twist Manufacturing",
            legal_name="Twist Manufacturing Ltd",
            fiscal_year_start=date(2025, 1, 1),
            tax_id="TAX-001",
            registration_number="REG-001",
        )

        User = get_user_model()
        self.user = User.objects.create_user(username="finance-admin", password="pass123", email="finance@example.com")
        self.client.force_authenticate(user=self.user)

        self.headers = {"HTTP_X_COMPANY_ID": str(self.company.id)}

        # Core chart of accounts
        self.receivable_account = Account.objects.create(
            company=self.company,
            company_group=self.group,
            created_by=self.user,
            code="1100",
            name="Accounts Receivable",
            account_type=AccountType.ASSET,
            allow_direct_posting=True,
        )
        self.revenue_account = Account.objects.create(
            company=self.company,
            company_group=self.group,
            created_by=self.user,
            code="4100",
            name="Services Revenue",
            account_type=AccountType.REVENUE,
        )
        self.bank_account = Account.objects.create(
            company=self.company,
            company_group=self.group,
            created_by=self.user,
            code="1001",
            name="City Bank Current",
            account_type=AccountType.ASSET,
            is_bank_account=True,
        )

        # Journals required for postings
        Journal.objects.create(company=self.company, company_group=self.group, created_by=self.user, code="GENERAL", name="General Journal", type="GENERAL")
        Journal.objects.create(company=self.company, company_group=self.group, created_by=self.user, code="SALES", name="Sales Journal", type="SALES")
        Journal.objects.create(company=self.company, company_group=self.group, created_by=self.user, code="PURCHASE", name="Purchase Journal", type="PURCHASE")
        Journal.objects.create(company=self.company, company_group=self.group, created_by=self.user, code="BANK", name="Bank Journal", type="BANK")
        Journal.objects.create(company=self.company, company_group=self.group, created_by=self.user, code="CASH", name="Cash Journal", type="CASH")

        self.customer = Customer.objects.create(
            company=self.company,
            created_by=self.user,
            code="CUST1",
            name="Acme Imports",
            email="billing@acme.test",
            phone="0123",
            receivable_account=self.receivable_account,
        )

    def api_post(self, path: str, payload: dict) -> "Response":
        return self.client.post(path, payload, format="json", **self.headers)

    def api_get(self, path: str) -> "Response":
        return self.client.get(path, format="json", **self.headers)

    def test_account_creation_and_summary(self):
        payload = {
            "code": "5100",
            "name": "Marketing Expense",
            "account_type": AccountType.EXPENSE,
            "currency": "BDT",
            "is_active": True,
        }
        response = self.api_post("/api/v1/finance/accounts/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())

        list_response = self.api_get("/api/v1/finance/accounts/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        data = list_response.json()
        self.assertIn("summary", data)
        self.assertGreaterEqual(data["summary"]["total"], 1)
        codes = [account["code"] for account in data["results"]]
        self.assertIn("5100", codes)

    def test_ar_invoice_to_receipt_flow(self):
        invoice_payload = {
            "invoice_type": "AR",
            "partner_type": "customer",
            "partner_id": self.customer.id,
            "invoice_date": "2025-01-10",
            "due_date": "2025-01-20",
            "currency": "BDT",
            "lines": [
                {
                    "description": "Consulting services",
                    "quantity": "1",
                    "unit_price": "5000",
                    "tax_rate": "0",
                    "discount_percent": "0",
                    "account": self.revenue_account.id,
                }
            ],
        }

        create_response = self.api_post("/api/v1/finance/invoices/", invoice_payload)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED, create_response.json())
        invoice_data = create_response.json()
        invoice_id = invoice_data["id"]
        self.assertEqual(invoice_data["status"], "DRAFT")
        total_amount = Decimal(invoice_data["total_amount"])

        post_response = self.client.post(
            f"/api/v1/finance/invoices/{invoice_id}/post/",
            {},
            format="json",
            **self.headers,
        )
        self.assertEqual(post_response.status_code, status.HTTP_200_OK)
        self.assertEqual(post_response.json()["status"], "POSTED")

        payment_payload = {
            "payment_date": "2025-01-25",
            "payment_type": "RECEIPT",
            "payment_method": "BANK",
            "amount": str(total_amount),
            "currency": "BDT",
            "partner_type": "customer",
            "partner_id": self.customer.id,
            "bank_account": self.bank_account.id,
            "allocations": [
                {"invoice": invoice_id, "allocated_amount": str(total_amount)}
            ],
        }

        payment_create = self.api_post("/api/v1/finance/payments/", payment_payload)
        self.assertEqual(payment_create.status_code, status.HTTP_201_CREATED)
        payment_id = payment_create.json()["id"]

        payment_post = self.client.post(
            f"/api/v1/finance/payments/{payment_id}/post/",
            {},
            format="json",
            **self.headers,
        )
        self.assertEqual(payment_post.status_code, status.HTTP_200_OK)
        payment_data = payment_post.json()
        self.assertEqual(payment_data["status"], "POSTED")
        self.assertIsNotNone(payment_data["journal_voucher"])

        refreshed_invoice = Invoice.objects.get(pk=invoice_id)
        self.assertEqual(refreshed_invoice.status, InvoiceStatus.PAID)
        self.assertEqual(refreshed_invoice.balance_due, Decimal("0.00"))

        refreshed_bank = Account.objects.get(pk=self.bank_account.pk)
        self.assertEqual(refreshed_bank.current_balance, total_amount)

        refreshed_payment = Payment.objects.get(pk=payment_id)
        self.assertEqual(refreshed_payment.status, "POSTED")
