from decimal import Decimal

from django.test import TestCase

from apps.companies.models import CompanyGroup, Company
from apps.finance.models import Account, AccountType, InventoryPostingRule
from apps.finance.services.posting_rules import resolve_inventory_accounts
from apps.inventory.models import ItemCategory, Item, Warehouse, UnitOfMeasure


class PostingRulesResolutionTests(TestCase):
    def setUp(self):
        self.group = CompanyGroup.objects.create(name="Demo Group", code="DEMO-G")
        self.company = Company.objects.create(name="Demo Co", code="DEMO", company_group=self.group)
        self.inv = Account.objects.create(
            company_group=self.group,
            company=self.company,
            code="1300-INVENTORY",
            name="Inventory",
            account_type=AccountType.ASSET,
        )
        self.cogs = Account.objects.create(
            company_group=self.group,
            company=self.company,
            code="5000-COGS",
            name="COGS",
            account_type=AccountType.EXPENSE,
        )
        self.default_inv = Account.objects.create(
            company_group=self.group,
            company=self.company,
            code="1399-INV-DEFAULT",
            name="Inventory Default",
            account_type=AccountType.ASSET,
        )
        self.default_cogs = Account.objects.create(
            company_group=self.group,
            company=self.company,
            code="5099-COGS-DEFAULT",
            name="COGS Default",
            account_type=AccountType.EXPENSE,
        )
        self.parent_cat = ItemCategory.objects.create(
            company=self.company,
            code="RM",
            name="Raw Material",
        )
        self.child_cat = ItemCategory.objects.create(
            company=self.company,
            code="RM-CHEM",
            name="Raw Material / Chemicals",
            parent_category=self.parent_cat,
        )
        self.uom = UnitOfMeasure.objects.create(
            company=self.company,
            code="KG",
            name="Kilogram",
        )
        self.item = Item.objects.create(
            company=self.company,
            code="CHEM-01",
            name="Dye Base",
            category=self.child_cat,
            uom=self.uom,
            inventory_account=self.default_inv,
            expense_account=self.default_cogs,
            track_inventory=True,
        )
        self.wh_main = Warehouse.objects.create(
            company=self.company,
            code="WH-MAIN",
            name="Main Warehouse",
            warehouse_type="MAIN",
        )
        self.wh_backup = Warehouse.objects.create(
            company=self.company,
            code="WH-B",
            name="Backup Warehouse",
            warehouse_type="MAIN",
        )
        InventoryPostingRule.objects.create(
            company=self.company,
            category=self.parent_cat,
            sub_category=self.child_cat,
            warehouse=self.wh_main,
            transaction_type="RECEIPT",
            inventory_account=self.inv,
            cogs_account=None,
            priority=10,
        )
        InventoryPostingRule.objects.create(
            company=self.company,
            category=self.parent_cat,
            warehouse=self.wh_backup,
            transaction_type="RECEIPT",
            inventory_account=self.inv,
            cogs_account=None,
            priority=20,
        )
        InventoryPostingRule.objects.create(
            company=self.company,
            category=self.parent_cat,
            transaction_type="ISSUE",
            inventory_account=self.inv,
            cogs_account=self.cogs,
            priority=30,
        )

    def test_matrix_level_one_preferred(self):
        inv_acct, cogs_acct = resolve_inventory_accounts(
            company=self.company,
            product=self.item,
            warehouse=self.wh_main,
            transaction_type='RECEIPT',
        )
        self.assertEqual(inv_acct, self.inv)
        self.assertIsNone(cogs_acct)

    def test_fallback_to_category_transaction(self):
        inv_acct, cogs_acct = resolve_inventory_accounts(
            company=self.company,
            product=self.item,
            warehouse=self.wh_backup,
            transaction_type='ISSUE',
        )
        self.assertEqual(inv_acct, self.inv)
        self.assertEqual(cogs_acct, self.cogs)

    def test_fallback_to_item_accounts(self):
        InventoryPostingRule.objects.all().delete()
        inv_acct, cogs_acct = resolve_inventory_accounts(
            company=self.company,
            product=self.item,
            warehouse=None,
            transaction_type='ISSUE',
        )
        self.assertEqual(inv_acct, self.default_inv)
        self.assertEqual(cogs_acct, self.default_cogs)
