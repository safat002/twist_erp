from __future__ import annotations

from calendar import monthrange
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.analytics.services.etl import run_warehouse_etl
from apps.companies.models import Company
from apps.finance.models import Account, AccountType, Invoice, InvoiceLine, Payment
from apps.inventory.models import Product, ProductCategory, UnitOfMeasure, Warehouse
from apps.assets.models import Asset, AssetMaintenancePlan
from apps.sales.models import Customer, SalesOrder, SalesOrderLine


class Command(BaseCommand):
    help = "Seed demo transactional data so dashboard widgets show sample metrics."

    def add_arguments(self, parser):
        parser.add_argument(
            "--company",
            dest="company_code",
            default="DEMO",
            help="Company code to seed (default: DEMO).",
        )
        parser.add_argument(
            "--months",
            dest="months",
            type=int,
            default=6,
            help="Number of months of sample data to generate.",
        )

    def handle(self, *args, **options):
        company_code = options["company_code"].upper()
        months = max(1, options["months"])

        with transaction.atomic():
            company = self._ensure_company(company_code)
            accounts = self._ensure_chart_of_accounts(company)
            inventory = self._ensure_inventory_master(company, accounts)
            customer = self._ensure_customer(company, accounts["receivable"])

            self._seed_sales_pipeline(
                company=company,
                customer=customer,
                product=inventory["product"],
                warehouse=inventory["warehouse"],
                accounts=accounts,
                months=months,
            )
            self._seed_asset_register(company)

        for period in ["7d", "30d", "90d", "month"]:
            run_warehouse_etl(period=period, companies=[company])

        self.stdout.write(self.style.SUCCESS("Demo dashboard data generated successfully."))
        self.stdout.write(self.style.NOTICE("You can now visit the dashboard to see sample metrics."))

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _ensure_company(self, code: str) -> Company:
        today = timezone.now().date()
        fiscal_start = today.replace(month=7, day=1)
        defaults = {
            "name": "Demo Manufacturing",
            "legal_name": "Demo Manufacturing Ltd.",
            "fiscal_year_start": fiscal_start,
            "tax_id": f"DEMO-TAX-{today.year}",
            "registration_number": "DEM-REG-2025",
            "settings": {"industry": "Manufacturing"},
        }
        company, created = Company.objects.get_or_create(code=code, defaults=defaults)
        if created:
            self.stdout.write(f"Created demo company '{company.name}' ({company.code}).")
        return company

    def _ensure_chart_of_accounts(self, company: Company) -> dict[str, Account]:
        user = get_user_model().objects.filter(is_superuser=True).first()
        created_by = user if user and user.has_company_access(company) else None

        def ensure(code: str, name: str, acc_type: str, **extra) -> Account:
            account, created = Account.objects.get_or_create(
                company=company,
                code=code,
                defaults={
                    "name": name,
                    "account_type": acc_type,
                    "created_by": created_by,
                    **extra,
                },
            )
            if created:
                self.stdout.write(f" - Added account {code} {name}")
            return account

        accounts = {
            "receivable": ensure("1100", "Accounts Receivable", AccountType.ASSET),
            "cash": ensure("1110", "Main Bank Account", AccountType.ASSET, is_bank_account=True),
            "inventory": ensure("1300", "Inventory", AccountType.ASSET),
            "cogs": ensure("5000", "Cost of Goods Sold", AccountType.EXPENSE),
            "revenue": ensure("4000", "Product Sales", AccountType.REVENUE),
            "payable": ensure("2100", "Accounts Payable", AccountType.LIABILITY),
        }
        return accounts

    def _ensure_inventory_master(self, company: Company, accounts: dict[str, Account]) -> dict[str, object]:
        user = get_user_model().objects.filter(is_superuser=True).first()
        created_by = user if user and user.has_company_access(company) else None

        category, _ = ProductCategory.objects.get_or_create(
            company=company,
            code="FG",
            defaults={"name": "Finished Goods", "created_by": created_by},
        )
        uom, _ = UnitOfMeasure.objects.get_or_create(
            company=company,
            code="PCS",
            defaults={"name": "Pieces", "created_by": created_by},
        )
        product, _ = Product.objects.get_or_create(
            company=company,
            code="PROD-001",
            defaults={
                "name": "Demo Widget",
                "description": "Flagship widget used in dashboard demos.",
                "category": category,
                "uom": uom,
                "track_inventory": True,
                "inventory_account": accounts["inventory"],
                "income_account": accounts["revenue"],
                "expense_account": accounts["cogs"],
                "cost_price": Decimal("700.00"),
                "selling_price": Decimal("1200.00"),
                "created_by": created_by,
            },
        )
        warehouse, _ = Warehouse.objects.get_or_create(
            company=company,
            code="MAIN",
            defaults={"name": "Main Warehouse", "created_by": created_by},
        )

        return {"product": product, "warehouse": warehouse}

    def _ensure_customer(self, company: Company, receivable_account: Account) -> Customer:
        customer, created = Customer.objects.get_or_create(
            company=company,
            code="CUST-DEMO",
            defaults={
                "name": "Acme Retail",
                "email": "orders@acme-retail.test",
                "phone": "+880100000001",
                "billing_address": "12 Demo Street, Dhaka",
                "shipping_address": "12 Demo Street, Dhaka",
                "credit_limit": Decimal("50000.00"),
                "payment_terms": 30,
                "receivable_account": receivable_account,
                "customer_status": "ACTIVE",
                "created_by": None,
            },
        )
        if created:
            self.stdout.write("Created demo customer 'Acme Retail'.")
        return customer

    # ------------------------------------------------------------------
    # Seeding transactional data
    # ------------------------------------------------------------------

    def _seed_sales_pipeline(
        self,
        company: Company,
        customer: Customer,
        product: Product,
        warehouse: Warehouse,
        accounts: dict[str, Account],
        months: int,
    ) -> None:
        today = timezone.now().date()
        base_day = min(today.day, 25)

        for idx in range(months):
            order_date = self._shift_months(today.replace(day=base_day), -idx)
            delivery_date = order_date + timedelta(days=7)
            quantity = Decimal("15") + Decimal(idx * 2)
            unit_price = Decimal("1200.00") + Decimal(idx * 25)
            line_total = (quantity * unit_price).quantize(Decimal("0.01"))

            order_number = f"SO-DEMO-{order_date:%Y%m}{idx:02d}"
            sales_order, _ = SalesOrder.objects.get_or_create(
                company=company,
                order_number=order_number,
                defaults={
                    "order_date": order_date,
                    "customer": customer,
                    "delivery_date": delivery_date,
                    "shipping_address": customer.shipping_address,
                    "subtotal": line_total,
                    "tax_amount": Decimal("0.00"),
                    "discount_amount": Decimal("0.00"),
                    "total_amount": line_total,
                    "status": "CONFIRMED",
                    "created_by": None,
                },
            )
            SalesOrderLine.objects.update_or_create(
                order=sales_order,
                line_number=1,
                defaults={
                    "product": product,
                    "description": product.name,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount_percent": Decimal("0.00"),
                    "tax_rate": Decimal("0.00"),
                    "line_total": line_total,
                    "warehouse": warehouse,
                },
            )

            invoice_number = f"INV-DEMO-{order_date:%Y%m}{idx:02d}"
            invoice, _ = Invoice.objects.get_or_create(
                company=company,
                invoice_number=invoice_number,
                defaults={
                    "invoice_type": "AR",
                    "partner_type": "CUSTOMER",
                    "partner_id": customer.id,
                    "invoice_date": delivery_date,
                    "due_date": delivery_date + timedelta(days=30),
                    "subtotal": line_total,
                    "tax_amount": Decimal("0.00"),
                    "discount_amount": Decimal("0.00"),
                    "total_amount": line_total,
                    "paid_amount": Decimal("0.00"),
                    "currency": company.currency_code,
                    "status": "POSTED",
                    "created_by": None,
                },
            )
            InvoiceLine.objects.update_or_create(
                invoice=invoice,
                line_number=1,
                defaults={
                    "description": product.name,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "tax_rate": Decimal("0.00"),
                    "discount_percent": Decimal("0.00"),
                    "line_total": line_total,
                    "product_id": product.id,
                    "account": accounts["revenue"],
                },
            )

            paid_ratio = Decimal("1.0") if idx % 3 else Decimal("0.65")
            paid_amount = (line_total * paid_ratio).quantize(Decimal("0.01"))
            invoice.paid_amount = paid_amount
            invoice.status = "PAID" if paid_amount >= line_total else "PARTIAL"
            invoice.save(update_fields=["paid_amount", "status"])

            if paid_amount > 0:
                Payment.objects.update_or_create(
                    company=company,
                    payment_number=f"RCPT-DEMO-{order_date:%Y%m}{idx:02d}",
                    defaults={
                        "payment_date": delivery_date + timedelta(days=10),
                        "payment_type": "RECEIPT",
                        "payment_method": "BANK",
                        "bank_account": accounts["cash"],
                        "amount": paid_amount,
                        "currency": company.currency_code,
                        "partner_type": "CUSTOMER",
                        "partner_id": customer.id,
                        "reference": invoice.invoice_number,
                        "notes": "Demo customer payment",
                        "status": "POSTED",
                        "created_by": None,
                    },
                )

            self._seed_payable(company, accounts, order_date, idx)

    def _seed_asset_register(self, company: Company) -> None:
        today = timezone.now().date()
        assets_payload = [
            {
                "code": "AST-PLANT-001",
                "name": "High Pressure Boiler",
                "category": "Utilities",
                "location": "Plant A",
                "manufacturer": "Bosch",
                "model_number": "HPB-300",
                "serial_number": "HPB-300-7782",
                "acquisition_date": today - timedelta(days=720),
                "cost": Decimal("1800000.00"),
                "residual_value": Decimal("200000.00"),
                "depreciation_method": Asset.METHOD_SL,
                "useful_life_months": 120,
                "status": Asset.STATUS_ACTIVE,
                "maintenance": [
                    {
                        "title": "Annual safety inspection",
                        "maintenance_type": "Inspection",
                        "scheduled_date": today + timedelta(days=14),
                        "due_date": today + timedelta(days=21),
                        "assigned_to": "Engineering",
                    },
                    {
                        "title": "Burner calibration",
                        "maintenance_type": "Calibration",
                        "scheduled_date": today + timedelta(days=45),
                        "due_date": today + timedelta(days=52),
                        "assigned_to": "Engineering",
                    },
                ],
            },
            {
                "code": "AST-LINE-004",
                "name": "Embroidery Machine A-3",
                "category": "Production",
                "location": "Line 4",
                "manufacturer": "Tajima",
                "model_number": "TMAR-KC",
                "serial_number": "TMAR-3331",
                "acquisition_date": today - timedelta(days=540),
                "cost": Decimal("950000.00"),
                "residual_value": Decimal("150000.00"),
                "depreciation_method": Asset.METHOD_SL,
                "useful_life_months": 96,
                "status": Asset.STATUS_ACTIVE,
                "maintenance": [
                    {
                        "title": "Needle head replacement",
                        "maintenance_type": "Preventive",
                        "scheduled_date": today + timedelta(days=7),
                        "due_date": today + timedelta(days=10),
                        "assigned_to": "Maintenance Crew A",
                    },
                    {
                        "title": "Lubrication cycle",
                        "maintenance_type": "Routine",
                        "scheduled_date": today + timedelta(days=30),
                        "due_date": today + timedelta(days=32),
                        "assigned_to": "Maintenance Crew A",
                    },
                ],
            },
            {
                "code": "AST-LOG-009",
                "name": "Logistics Van 6",
                "category": "Fleet",
                "location": "Logistics Hub",
                "manufacturer": "Toyota",
                "model_number": "HiAce",
                "serial_number": "VH-10339",
                "acquisition_date": today - timedelta(days=365),
                "cost": Decimal("420000.00"),
                "residual_value": Decimal("120000.00"),
                "depreciation_method": Asset.METHOD_DB,
                "useful_life_months": 84,
                "status": Asset.STATUS_ACTIVE,
                "maintenance": [
                    {
                        "title": "Oil & filter change",
                        "maintenance_type": "Routine",
                        "scheduled_date": today + timedelta(days=3),
                        "due_date": today + timedelta(days=5),
                        "assigned_to": "Fleet Services",
                    },
                    {
                        "title": "Tyre rotation",
                        "maintenance_type": "Preventive",
                        "scheduled_date": today + timedelta(days=28),
                        "due_date": today + timedelta(days=30),
                        "assigned_to": "Fleet Services",
                    },
                ],
            },
            {
                "code": "AST-IT-015",
                "name": "Core Application Server",
                "category": "IT Infrastructure",
                "location": "Data Centre - Rack 4",
                "manufacturer": "Dell",
                "model_number": "PowerEdge R750",
                "serial_number": "SRV-2025-8891",
                "acquisition_date": today - timedelta(days=180),
                "cost": Decimal("1250000.00"),
                "residual_value": Decimal("300000.00"),
                "depreciation_method": Asset.METHOD_SL,
                "useful_life_months": 60,
                "status": Asset.STATUS_ACTIVE,
                "maintenance": [
                    {
                        "title": "Firmware update",
                        "maintenance_type": "Upgrade",
                        "scheduled_date": today + timedelta(days=20),
                        "due_date": today + timedelta(days=21),
                        "assigned_to": "IT Ops",
                    },
                    {
                        "title": "Failover drill",
                        "maintenance_type": "Testing",
                        "scheduled_date": today + timedelta(days=55),
                        "due_date": today + timedelta(days=57),
                        "assigned_to": "IT Ops",
                    },
                ],
            },
        ]

        for spec in assets_payload:
            maintenance_definitions = spec.pop("maintenance", [])
            asset, _ = Asset.objects.update_or_create(
                company=company,
                code=spec["code"],
                defaults=spec,
            )
            for task in maintenance_definitions:
                AssetMaintenancePlan.objects.update_or_create(
                    company=company,
                    asset=asset,
                    title=task["title"],
                    scheduled_date=task["scheduled_date"],
                    defaults={
                        "description": "",
                        "maintenance_type": task.get("maintenance_type", ""),
                        "due_date": task["due_date"],
                        "status": AssetMaintenancePlan.STATUS_PLANNED,
                        "assigned_to": task.get("assigned_to", ""),
                    },
                )

    def _seed_payable(self, company: Company, accounts: dict[str, Account], base_date, index: int) -> None:
        amount = Decimal("8000.00") + Decimal(index * 350)
        due_date = base_date + timedelta(days=25)
        invoice, _ = Invoice.objects.get_or_create(
            company=company,
            invoice_number=f"AP-DEMO-{base_date:%Y%m}{index:02d}",
            defaults={
                "invoice_type": "AP",
                "partner_type": "SUPPLIER",
                "partner_id": 1,
                "invoice_date": base_date,
                "due_date": due_date,
                "subtotal": amount,
                "tax_amount": Decimal("0.00"),
                "discount_amount": Decimal("0.00"),
                "total_amount": amount,
                "paid_amount": Decimal("0.00"),
                "currency": company.currency_code,
                "status": "POSTED",
                "created_by": None,
            },
        )
        InvoiceLine.objects.update_or_create(
            invoice=invoice,
            line_number=1,
            defaults={
                "description": "Raw materials",
                "quantity": Decimal("1"),
                "unit_price": amount,
                "tax_rate": Decimal("0.00"),
                "discount_percent": Decimal("0.00"),
                "line_total": amount,
                "product_id": None,
                "account": accounts["cogs"],
            },
        )

        paid_ratio = Decimal("0.5") if index % 2 else Decimal("1.0")
        paid_amount = (amount * paid_ratio).quantize(Decimal("0.01"))
        invoice.paid_amount = paid_amount
        invoice.status = "PAID" if paid_amount >= amount else "PARTIAL"
        invoice.save(update_fields=["paid_amount", "status"])

        if paid_amount > 0:
            Payment.objects.update_or_create(
                company=company,
                payment_number=f"PAY-DEMO-{base_date:%Y%m}{index:02d}",
                defaults={
                    "payment_date": due_date,
                    "payment_type": "PAYMENT",
                    "payment_method": "BANK",
                    "bank_account": accounts["cash"],
                    "amount": paid_amount,
                    "currency": company.currency_code,
                    "partner_type": "SUPPLIER",
                    "partner_id": 1,
                    "reference": invoice.invoice_number,
                    "notes": "Demo supplier payment",
                    "status": "POSTED",
                    "created_by": None,
                },
            )

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _shift_months(base_date, months: int):
        """Return a date shifted by the given number of months (negative allowed)."""
        month = base_date.month - 1 + months
        year = base_date.year + month // 12
        month = month % 12 + 1
        day = min(base_date.day, monthrange(year, month)[1])
        return base_date.replace(year=year, month=month, day=day)

