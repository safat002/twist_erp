"""
Comprehensive tests for Inventory Valuation Module
Tests FIFO, LIFO, Weighted Average, and Standard Cost methods
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company, CompanyGroup
from apps.inventory.models import (
    Product,
    Warehouse,
    ItemValuationMethod,
    CostLayer,
    ValuationChangeLog,
)
from apps.inventory.services.valuation_service import ValuationService
from apps.inventory.services.stock_service import InventoryService
from apps.finance.models import Account, Journal, JournalVoucher
from types import SimpleNamespace


class ValuationServiceTests(APITestCase):
    """Test the core valuation calculation logic"""

    maxDiff = None

    def setUp(self):
        """Set up test fixtures"""
        self.group = CompanyGroup.objects.create(name="Test Group", db_name="cg_test")
        self.company = Company.objects.create(
            company_group=self.group,
            code="TST",
            name="Test Company",
            legal_name="Test Company Ltd",
            fiscal_year_start=date(2025, 1, 1),
        )

        User = get_user_model()
        self.user = User.objects.create_user(
            username="test-user",
            password="pass123",
            email="test@example.com"
        )
        self.client.force_authenticate(user=self.user)
        self.headers = {"HTTP_X_COMPANY_ID": str(self.company.id)}

        # Create test product and warehouse
        self.product = Product.objects.create(
            company=self.company,
            code="PROD-001",
            name="Test Product",
            category="Test",
            created_by=self.user,
        )

        self.warehouse = Warehouse.objects.create(
            company=self.company,
            code="WH-001",
            name="Main Warehouse",
            created_by=self.user,
        )

    def _create_cost_layer(self, qty, cost_per_unit, fifo_seq, days_ago=0):
        """Helper to create a cost layer"""
        receipt_date = timezone.now() - timedelta(days=days_ago)
        return CostLayer.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            receipt_date=receipt_date,
            qty_received=Decimal(str(qty)),
            cost_per_unit=Decimal(str(cost_per_unit)),
            total_cost=Decimal(str(qty)) * Decimal(str(cost_per_unit)),
            qty_remaining=Decimal(str(qty)),
            cost_remaining=Decimal(str(qty)) * Decimal(str(cost_per_unit)),
            fifo_sequence=fifo_seq,
            is_closed=False,
            source_document_type="TEST",
            source_document_id=1,
        )

    def _create_cost_layer_with_expiry(self, qty, cost_per_unit, fifo_seq, days_until_expiry):
        receipt_date = timezone.now()
        expiry_date = (timezone.now() + timedelta(days=days_until_expiry)).date()
        return CostLayer.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            receipt_date=receipt_date,
            qty_received=Decimal(str(qty)),
            cost_per_unit=Decimal(str(cost_per_unit)),
            total_cost=Decimal(str(qty)) * Decimal(str(cost_per_unit)),
            qty_remaining=Decimal(str(qty)),
            cost_remaining=Decimal(str(qty)) * Decimal(str(cost_per_unit)),
            fifo_sequence=fifo_seq,
            is_closed=False,
            source_document_type="TEST",
            source_document_id=1,
            expiry_date=expiry_date,
            stock_state='RELEASED',
        )

    def test_fifo_single_layer_full_consumption(self):
        """Test FIFO with single layer consumed completely"""
        layer = self._create_cost_layer(qty=100, cost_per_unit=10, fifo_seq=1)

        total_cost, consumed_layers = ValuationService.calculate_fifo_cost(
            self.company, self.product, self.warehouse, Decimal("100")
        )

        self.assertEqual(total_cost, Decimal("1000"))  # 100 * 10
        self.assertEqual(len(consumed_layers), 1)
        self.assertEqual(consumed_layers[0]['qty_consumed'], 100.0)
        self.assertEqual(consumed_layers[0]['cost_per_unit'], 10.0)

    def test_fifo_single_layer_partial_consumption(self):
        """Test FIFO with single layer consumed partially"""
        layer = self._create_cost_layer(qty=100, cost_per_unit=10, fifo_seq=1)

        total_cost, consumed_layers = ValuationService.calculate_fifo_cost(
            self.company, self.product, self.warehouse, Decimal("50")
        )

        self.assertEqual(total_cost, Decimal("500"))  # 50 * 10
        self.assertEqual(len(consumed_layers), 1)
        self.assertEqual(consumed_layers[0]['qty_consumed'], 50.0)

    def test_fifo_multiple_layers_spanning(self):
        """Test FIFO consuming across multiple layers (oldest first)"""
        layer1 = self._create_cost_layer(qty=100, cost_per_unit=10, fifo_seq=1, days_ago=5)
        layer2 = self._create_cost_layer(qty=150, cost_per_unit=12, fifo_seq=2, days_ago=3)
        layer3 = self._create_cost_layer(qty=200, cost_per_unit=15, fifo_seq=3, days_ago=1)

        # Consume 280 units (should take all of layer1, all of layer2, and 30 from layer3)
        total_cost, consumed_layers = ValuationService.calculate_fifo_cost(
            self.company, self.product, self.warehouse, Decimal("280")
        )

        expected_cost = (100 * 10) + (150 * 12) + (30 * 15)  # 1000 + 1800 + 450 = 3250
        self.assertEqual(total_cost, Decimal(str(expected_cost)))
        self.assertEqual(len(consumed_layers), 3)

        # Verify layer consumption order (FIFO - oldest first)
        self.assertEqual(consumed_layers[0]['fifo_sequence'], 1)
        self.assertEqual(consumed_layers[0]['qty_consumed'], 100.0)
        self.assertEqual(consumed_layers[1]['fifo_sequence'], 2)
        self.assertEqual(consumed_layers[1]['qty_consumed'], 150.0)
        self.assertEqual(consumed_layers[2]['fifo_sequence'], 3)
        self.assertEqual(consumed_layers[2]['qty_consumed'], 30.0)

    def test_lifo_multiple_layers_spanning(self):
        """Test LIFO consuming across multiple layers (newest first)"""
        layer1 = self._create_cost_layer(qty=100, cost_per_unit=10, fifo_seq=1, days_ago=5)
        layer2 = self._create_cost_layer(qty=150, cost_per_unit=12, fifo_seq=2, days_ago=3)
        layer3 = self._create_cost_layer(qty=200, cost_per_unit=15, fifo_seq=3, days_ago=1)

        # Consume 280 units (should take all of layer3, all of layer2, and 30 from layer1)
        total_cost, consumed_layers = ValuationService.calculate_lifo_cost(
            self.company, self.product, self.warehouse, Decimal("280")
        )

        expected_cost = (200 * 15) + (150 * 12) + (30 * 10)  # 3000 + 1800 + 300 = 5100
        self.assertEqual(total_cost, Decimal(str(expected_cost)))
        self.assertEqual(len(consumed_layers), 3)

        # Verify layer consumption order (LIFO - newest first)
        self.assertEqual(consumed_layers[0]['fifo_sequence'], 3)
        self.assertEqual(consumed_layers[0]['qty_consumed'], 200.0)
        self.assertEqual(consumed_layers[1]['fifo_sequence'], 2)
        self.assertEqual(consumed_layers[1]['qty_consumed'], 150.0)
        self.assertEqual(consumed_layers[2]['fifo_sequence'], 1)
        self.assertEqual(consumed_layers[2]['qty_consumed'], 30.0)

    def test_weighted_average_calculation(self):
        """Test weighted average cost calculation"""
        layer1 = self._create_cost_layer(qty=100, cost_per_unit=10, fifo_seq=1)
        layer2 = self._create_cost_layer(qty=200, cost_per_unit=15, fifo_seq=2)

        # Total: 100*10 + 200*15 = 1000 + 3000 = 4000
        # Total qty: 300
        # Weighted avg: 4000 / 300 = 13.333...

        total_cost, consumed_layers = ValuationService.calculate_weighted_avg_cost(
            self.company, self.product, self.warehouse, Decimal("150")
        )

        # Expected: 150 * 13.3333... ≈ 2000
        self.assertAlmostEqual(float(total_cost), 2000.0, places=2)

    def test_standard_cost_method(self):
        """Test standard cost method"""
        # Set up valuation method with standard cost
        ItemValuationMethod.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            valuation_method='STANDARD',
            effective_date=date.today(),
            is_active=True,
            created_by=self.user,
        )

        # Create a standard cost layer
        standard_layer = self._create_cost_layer(qty=1000, cost_per_unit=12, fifo_seq=1)
        standard_layer.is_standard_cost = True
        standard_layer.save()

        total_cost, consumed_layers = ValuationService.calculate_standard_cost(
            self.company, self.product, self.warehouse, Decimal("250")
        )

        self.assertEqual(total_cost, Decimal("3000"))  # 250 * 12
        self.assertEqual(len(consumed_layers), 1)

    def test_landed_cost_adjustment(self):
        """Test that landed cost adjustments are included in calculations"""
        layer = self._create_cost_layer(qty=100, cost_per_unit=10, fifo_seq=1)
        layer.landed_cost_adjustment = Decimal("2.50")  # Add $2.50 per unit
        layer.save()

        total_cost, consumed_layers = ValuationService.calculate_fifo_cost(
            self.company, self.product, self.warehouse, Decimal("50")
        )

        # Expected: 50 * (10 + 2.50) = 50 * 12.50 = 625
        self.assertEqual(total_cost, Decimal("625"))
        self.assertEqual(consumed_layers[0]['cost_per_unit'], 12.5)

    def test_expired_stock_blocked_when_prevent_enabled(self):
        """Expired stock should not be issuable when prevention is enabled."""
        # Ensure prevention enabled on product
        if hasattr(self.product, 'prevent_expired_issuance'):
            self.product.prevent_expired_issuance = True
            self.product.save()

        # Create a released layer that already expired yesterday
        receipt_date = timezone.now()
        expired_date = (timezone.now() - timedelta(days=1)).date()
        CostLayer.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            receipt_date=receipt_date,
            qty_received=Decimal('100'),
            cost_per_unit=Decimal('10'),
            total_cost=Decimal('1000'),
            qty_remaining=Decimal('100'),
            cost_remaining=Decimal('1000'),
            fifo_sequence=1,
            is_closed=False,
            source_document_type='TEST',
            source_document_id=1,
            stock_state='RELEASED',
            expiry_date=expired_date,
        )

        with self.assertRaises(ValueError):
            ValuationService.calculate_fifo_cost(
                self.company, self.product, self.warehouse, Decimal('10')
            )

    def test_expired_stock_allowed_when_prevent_disabled(self):
        """Expired stock can be issued when prevention is disabled."""
        if hasattr(self.product, 'prevent_expired_issuance'):
            self.product.prevent_expired_issuance = False
            self.product.save()

        receipt_date = timezone.now()
        expired_date = (timezone.now() - timedelta(days=1)).date()
        layer = CostLayer.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            receipt_date=receipt_date,
            qty_received=Decimal('100'),
            cost_per_unit=Decimal('10'),
            total_cost=Decimal('1000'),
            qty_remaining=Decimal('100'),
            cost_remaining=Decimal('1000'),
            fifo_sequence=1,
            is_closed=False,
            source_document_type='TEST',
            source_document_id=1,
            stock_state='RELEASED',
            expiry_date=expired_date,
        )

        total_cost, consumed_layers = ValuationService.calculate_fifo_cost(
            self.company, self.product, self.warehouse, Decimal('10')
        )
        self.assertEqual(total_cost, Decimal('100'))
        self.assertEqual(consumed_layers[0]['layer_id'], layer.id)

    def test_landed_cost_adjustment_posts_gl_voucher(self):
        """Landed cost adjustment should create a GL JV (Dr Inventory/COGS, Cr Accrued Freight)."""
        # Setup finance accounts and journal
        inv_acct = Account.objects.create(
            company=self.company,
            company_group=self.group,
            code='1100-INV',
            name='Inventory',
            account_type='ASSET',
            allow_direct_posting=True,
        )
        cogs_acct = Account.objects.create(
            company=self.company,
            company_group=self.group,
            code='5000-COGS',
            name='COGS',
            account_type='EXPENSE',
            allow_direct_posting=True,
        )
        accrued_freight = Account.objects.create(
            company=self.company,
            company_group=self.group,
            code='ACCRUED_FREIGHT',
            name='Accrued Freight',
            account_type='LIABILITY',
            allow_direct_posting=True,
        )
        Journal.objects.create(
            company=self.company,
            company_group=self.group,
            code='GENERAL',
            name='General Journal',
            type='GENERAL',
        )

        # Attach accounts to product if supported
        if hasattr(self.product, 'inventory_account'):
            self.product.inventory_account = inv_acct
        if hasattr(self.product, 'expense_account'):
            self.product.expense_account = cogs_acct
        try:
            self.product.save()
        except Exception:
            pass

        # Create two layers (one partially consumed) under a fake GRN id
        grn_id = 9999
        layer1 = CostLayer.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            receipt_date=timezone.now(),
            qty_received=Decimal('100'),
            cost_per_unit=Decimal('10'),
            total_cost=Decimal('1000'),
            qty_remaining=Decimal('60'),  # 40 consumed
            cost_remaining=Decimal('600'),
            fifo_sequence=1,
            is_closed=False,
            source_document_type='GoodsReceipt',
            source_document_id=grn_id,
            stock_state='RELEASED',
        )
        layer2 = CostLayer.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            receipt_date=timezone.now(),
            qty_received=Decimal('50'),
            cost_per_unit=Decimal('12'),
            total_cost=Decimal('600'),
            qty_remaining=Decimal('50'),  # none consumed
            cost_remaining=Decimal('600'),
            fifo_sequence=2,
            is_closed=False,
            source_document_type='GoodsReceipt',
            source_document_id=grn_id,
            stock_state='RELEASED',
        )

        # Fake GRN object with required attributes
        fake_grn = SimpleNamespace(id=grn_id, company=self.company, company_id=self.company.id)

        # Apply landed cost adjustment of 100 apportioned by QUANTITY (150 total qty)
        result = InventoryService.apply_landed_cost_adjustment(
            goods_receipt=fake_grn,
            total_adjustment=Decimal('100'),
            method='QUANTITY',
            reason='Test Freight'
        )

        # Verify a JV was created
        jv = JournalVoucher.objects.filter(company=self.company, description__icontains='Landed cost adjustment').order_by('-created_at').first()
        self.assertIsNotNone(jv)
        # Totals should equal 100
        self.assertEqual(float(jv.total_debit), 100.0)
        self.assertEqual(float(jv.total_credit), 100.0)

    def test_fefo_consumption_prefers_earliest_expiry(self):
        """When expiry dates exist, consumption should prefer earliest expiry first (FEFO)."""
        # Create three layers with different expiry dates (sooner expiry should be consumed first)
        layer_a = self._create_cost_layer_with_expiry(qty=100, cost_per_unit=10, fifo_seq=1, days_until_expiry=10)
        layer_b = self._create_cost_layer_with_expiry(qty=100, cost_per_unit=11, fifo_seq=2, days_until_expiry=5)
        layer_c = self._create_cost_layer_with_expiry(qty=100, cost_per_unit=12, fifo_seq=3, days_until_expiry=20)

        total_cost, consumed_layers = ValuationService.calculate_fifo_cost(
            self.company, self.product, self.warehouse, Decimal("50")
        )

        # First consumed layer must be the one with expiry in 5 days (layer_b)
        self.assertEqual(consumed_layers[0]['layer_id'], layer_b.id)

    def test_insufficient_inventory(self):
        """Test behavior when requesting more than available"""
        layer = self._create_cost_layer(qty=100, cost_per_unit=10, fifo_seq=1)

        total_cost, consumed_layers = ValuationService.calculate_fifo_cost(
            self.company, self.product, self.warehouse, Decimal("150")
        )

        # Should only consume what's available (100 units)
        self.assertEqual(total_cost, Decimal("1000"))
        self.assertEqual(len(consumed_layers), 1)
        self.assertEqual(consumed_layers[0]['qty_consumed'], 100.0)

    def test_create_cost_layer(self):
        """Test cost layer creation"""
        layer = ValuationService.create_cost_layer(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            qty=Decimal("200"),
            cost_per_unit=Decimal("25.50"),
            source_document_type="GoodsReceipt",
            source_document_id=123,
            batch_no="BATCH-001",
            serial_no="SN-12345",
            receipt_date=timezone.now(),
        )

        self.assertIsNotNone(layer)
        self.assertEqual(layer.qty_received, Decimal("200"))
        self.assertEqual(layer.cost_per_unit, Decimal("25.50"))
        self.assertEqual(layer.total_cost, Decimal("5100"))  # 200 * 25.50
        self.assertEqual(layer.batch_no, "BATCH-001")
        self.assertEqual(layer.serial_no, "SN-12345")
        self.assertFalse(layer.is_closed)

    def test_consume_cost_layers_fifo(self):
        """Test the complete consume_cost_layers method with FIFO"""
        # Set up FIFO method
        ItemValuationMethod.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            valuation_method='FIFO',
            effective_date=date.today(),
            is_active=True,
            created_by=self.user,
        )

        layer1 = self._create_cost_layer(qty=100, cost_per_unit=10, fifo_seq=1)
        layer2 = self._create_cost_layer(qty=50, cost_per_unit=12, fifo_seq=2)

        total_cost, consumed_layers, method_used = ValuationService.consume_cost_layers(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            qty=Decimal("120"),
            source_document_type="TEST",
            source_document_id=1,
        )

        self.assertEqual(method_used, 'FIFO')
        self.assertEqual(total_cost, Decimal("1240"))  # 100*10 + 20*12

        # Verify layers were updated
        layer1.refresh_from_db()
        layer2.refresh_from_db()

        self.assertEqual(layer1.qty_remaining, Decimal("0"))
        self.assertTrue(layer1.is_closed)
        self.assertEqual(layer2.qty_remaining, Decimal("30"))
        self.assertFalse(layer2.is_closed)


class ValuationAPITests(APITestCase):
    """Test the valuation API endpoints"""

    maxDiff = None

    def setUp(self):
        """Set up test fixtures"""
        self.group = CompanyGroup.objects.create(name="Test Group", db_name="cg_test")
        self.company = Company.objects.create(
            company_group=self.group,
            code="TST",
            name="Test Company",
            legal_name="Test Company Ltd",
            fiscal_year_start=date(2025, 1, 1),
        )

        User = get_user_model()
        self.user = User.objects.create_user(
            username="test-user",
            password="pass123",
            email="test@example.com"
        )
        self.client.force_authenticate(user=self.user)
        self.headers = {"HTTP_X_COMPANY_ID": str(self.company.id)}

        self.product = Product.objects.create(
            company=self.company,
            code="PROD-001",
            name="Test Product",
            created_by=self.user,
        )

        self.warehouse = Warehouse.objects.create(
            company=self.company,
            code="WH-001",
            name="Main Warehouse",
            created_by=self.user,
        )

    def api_post(self, path: str, payload: dict):
        return self.client.post(path, payload, format="json", **self.headers)

    def api_get(self, path: str):
        return self.client.get(path, format="json", **self.headers)

    def api_put(self, path: str, payload: dict):
        return self.client.put(path, payload, format="json", **self.headers)

    def api_delete(self, path: str):
        return self.client.delete(path, format="json", **self.headers)

    def test_create_valuation_method(self):
        """Test creating a valuation method via API"""
        payload = {
            "product": self.product.id,
            "warehouse": self.warehouse.id,
            "valuation_method": "FIFO",
            "effective_date": date.today().isoformat(),
            "is_active": True,
            "allow_negative_inventory": False,
            "prevent_cost_below_zero": True,
        }

        response = self.api_post("/api/v1/inventory/valuation-methods/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())

        data = response.json()
        self.assertEqual(data['valuation_method'], 'FIFO')
        self.assertEqual(data['product'], self.product.id)
        self.assertTrue(data['is_active'])

    def test_list_valuation_methods(self):
        """Test listing valuation methods"""
        ItemValuationMethod.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            valuation_method='FIFO',
            effective_date=date.today(),
            is_active=True,
            created_by=self.user,
        )

        response = self.api_get("/api/v1/inventory/valuation-methods/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertGreaterEqual(len(data), 1)

    def test_get_valuation_method_by_product_warehouse(self):
        """Test getting specific method by product/warehouse"""
        method = ItemValuationMethod.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            valuation_method='WEIGHTED_AVG',
            avg_period='PERPETUAL',
            effective_date=date.today(),
            is_active=True,
            created_by=self.user,
        )

        url = f"/api/v1/inventory/valuation-methods/by_product_warehouse/?product_id={self.product.id}&warehouse_id={self.warehouse.id}"
        response = self.api_get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['valuation_method'], 'WEIGHTED_AVG')

    def test_list_cost_layers(self):
        """Test listing cost layers"""
        CostLayer.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            receipt_date=timezone.now(),
            qty_received=Decimal("100"),
            cost_per_unit=Decimal("10"),
            total_cost=Decimal("1000"),
            qty_remaining=Decimal("100"),
            cost_remaining=Decimal("1000"),
            fifo_sequence=1,
            source_document_type="TEST",
            source_document_id=1,
        )

        response = self.api_get("/api/v1/inventory/cost-layers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertGreaterEqual(len(data), 1)

    def test_cost_layer_summary(self):
        """Test cost layer summary endpoint"""
        CostLayer.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            receipt_date=timezone.now(),
            qty_received=Decimal("100"),
            cost_per_unit=Decimal("10"),
            total_cost=Decimal("1000"),
            qty_remaining=Decimal("50"),
            cost_remaining=Decimal("500"),
            fifo_sequence=1,
            source_document_type="TEST",
            source_document_id=1,
        )

        url = f"/api/v1/inventory/cost-layers/summary/?product_id={self.product.id}&warehouse_id={self.warehouse.id}"
        response = self.api_get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('inventory_value', data)
        self.assertIn('open_layers', data)

    def test_valuation_report(self):
        """Test valuation report endpoint"""
        # Create a cost layer
        CostLayer.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            receipt_date=timezone.now(),
            qty_received=Decimal("100"),
            cost_per_unit=Decimal("15"),
            total_cost=Decimal("1500"),
            qty_remaining=Decimal("100"),
            cost_remaining=Decimal("1500"),
            fifo_sequence=1,
            source_document_type="TEST",
            source_document_id=1,
        )

        response = self.api_get("/api/v1/inventory/valuation/report/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('items', data)
        self.assertIn('total_value', data)

    def test_current_cost(self):
        """Test current cost endpoint"""
        # Set up method and layer
        ItemValuationMethod.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            valuation_method='FIFO',
            effective_date=date.today(),
            is_active=True,
            created_by=self.user,
        )

        CostLayer.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            receipt_date=timezone.now(),
            qty_received=Decimal("100"),
            cost_per_unit=Decimal("20"),
            total_cost=Decimal("2000"),
            qty_remaining=Decimal("100"),
            cost_remaining=Decimal("2000"),
            fifo_sequence=1,
            source_document_type="TEST",
            source_document_id=1,
        )

        url = f"/api/v1/inventory/valuation/current-cost/?product_id={self.product.id}&warehouse_id={self.warehouse.id}"
        response = self.api_get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('current_cost', data)
        self.assertIn('method_used', data)


class ValuationChangeWorkflowTests(APITestCase):
    """Test valuation change approval workflow"""

    def setUp(self):
        """Set up test fixtures"""
        self.group = CompanyGroup.objects.create(name="Test Group", db_name="cg_test")
        self.company = Company.objects.create(
            company_group=self.group,
            code="TST",
            name="Test Company",
            legal_name="Test Company Ltd",
            fiscal_year_start=date(2025, 1, 1),
        )

        User = get_user_model()
        self.user = User.objects.create_user(
            username="test-user",
            password="pass123",
            email="test@example.com"
        )
        self.approver = User.objects.create_user(
            username="approver",
            password="pass123",
            email="approver@example.com"
        )
        self.client.force_authenticate(user=self.user)
        self.headers = {"HTTP_X_COMPANY_ID": str(self.company.id)}

        self.product = Product.objects.create(
            company=self.company,
            code="PROD-001",
            name="Test Product",
            created_by=self.user,
        )

        self.warehouse = Warehouse.objects.create(
            company=self.company,
            code="WH-001",
            name="Main Warehouse",
            created_by=self.user,
        )

    def api_post(self, path: str, payload: dict):
        return self.client.post(path, payload, format="json", **self.headers)

    def api_get(self, path: str):
        return self.client.get(path, format="json", **self.headers)

    def test_create_valuation_change_request(self):
        """Test creating a valuation change request"""
        payload = {
            "product": self.product.id,
            "warehouse": self.warehouse.id,
            "old_method": "FIFO",
            "new_method": "WEIGHTED_AVG",
            "effective_date": date.today().isoformat(),
            "reason": "Switching to weighted average for better cost stability",
        }

        response = self.api_post("/api/v1/inventory/valuation-changes/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())

        data = response.json()
        self.assertEqual(data['status'], 'PENDING')
        self.assertEqual(data['new_method'], 'WEIGHTED_AVG')

    def test_approve_valuation_change(self):
        """Test approving a valuation change"""
        change_log = ValuationChangeLog.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            old_method='FIFO',
            new_method='LIFO',
            effective_date=date.today(),
            status='PENDING',
            requested_by=self.user,
            reason="Test change",
        )

        # Approve as different user
        self.client.force_authenticate(user=self.approver)
        response = self.api_post(
            f"/api/v1/inventory/valuation-changes/{change_log.id}/approve/",
            {}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        change_log.refresh_from_db()
        self.assertEqual(change_log.status, 'APPROVED')
        self.assertEqual(change_log.approved_by, self.approver)

    def test_reject_valuation_change(self):
        """Test rejecting a valuation change"""
        change_log = ValuationChangeLog.objects.create(
            company=self.company,
            product=self.product,
            warehouse=self.warehouse,
            old_method='FIFO',
            new_method='STANDARD',
            effective_date=date.today(),
            status='PENDING',
            requested_by=self.user,
            reason="Test change",
        )

        # Reject as different user
        self.client.force_authenticate(user=self.approver)
        response = self.api_post(
            f"/api/v1/inventory/valuation-changes/{change_log.id}/reject/",
            {"rejection_reason": "Not aligned with company policy"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        change_log.refresh_from_db()
        self.assertEqual(change_log.status, 'REJECTED')
        self.assertIn("company policy", change_log.rejection_reason)
