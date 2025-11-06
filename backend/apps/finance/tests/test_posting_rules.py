from decimal import Decimal

from django.test import TestCase

from apps.companies.models import CompanyGroup, Company
from apps.finance.models import Account, AccountType, InventoryPostingRule
from apps.finance.services.posting_rules import resolve_inventory_accounts
from apps.inventory.models import ProductCategory


class PostingRulesResolutionTests(TestCase):
    def setUp(self):
        self.group = CompanyGroup.objects.create(name="Demo Group", code="DEMO-G")
        self.company = Company.objects.create(name="Demo Co", code="DEMO", company_group=self.group)
        # Accounts
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
        # Category
        self.cat = ProductCategory.objects.create(
            company=self.company,
            code="RM",
            name="Raw Material",
            is_active=True,
        )
        # Rules
        InventoryPostingRule.objects.create(
            company=self.company,
            category=self.cat,
            rule_name="RM Receipts",
            transaction_type="RECEIPT",
            inventory_account=self.inv,
            cogs_account=None,
            is_active=True,
        )
        InventoryPostingRule.objects.create(
            company=self.company,
            category=self.cat,
            rule_name="RM Issues",
            transaction_type="ISSUE",
            inventory_account=self.inv,
            cogs_account=self.cogs,
            is_active=True,
        )

    def test_resolve_receipt_accounts(self):
        inv_acct, cogs_acct = resolve_inventory_accounts(
            company=self.company, product=None, warehouse=None, transaction_type='RECEIPT', category=self.cat
        )
        self.assertIsNotNone(inv_acct)
        self.assertEqual(inv_acct.id, self.inv.id)
        self.assertIsNone(cogs_acct)

    def test_resolve_issue_accounts(self):
        inv_acct, cogs_acct = resolve_inventory_accounts(
            company=self.company, product=None, warehouse=None, transaction_type='ISSUE', category=self.cat
        )
        self.assertIsNotNone(inv_acct)
        self.assertIsNotNone(cogs_acct)
        self.assertEqual(cogs_acct.id, self.cogs.id)

