from __future__ import annotations

from typing import Dict, List, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.permissions.models import Permission, Role
from apps.companies.models import Company


# Permission catalog aligned to module specs and current enforcement points
DEFAULT_PERMISSIONS: List[Tuple[str, str, str]] = [
    # Finance (codes are enforced in finance.viewsets)
    ("finance_view_coa", "View Chart of Accounts", "finance"),
    ("finance_manage_coa", "Manage Chart of Accounts", "finance"),
    ("finance_close_period", "Close Fiscal Periods", "finance"),
    ("finance_view_journal", "View Journals", "finance"),
    ("finance_manage_journal", "Manage Journals", "finance"),
    ("finance_post_journal", "Post Journals", "finance"),
    ("finance_approve_journal", "Approve Journals", "finance"),
    ("finance_view_invoice", "View Invoices", "finance"),
    ("finance_manage_invoice", "Manage Invoices", "finance"),
    ("finance_view_payment", "View Payments", "finance"),
    ("finance_manage_payment", "Manage Payments", "finance"),
    ("finance_reconcile_bank", "Bank Reconciliation", "finance"),
    ("finance_view_reports", "View Finance Reports", "finance"),
    ("finance_export_reports", "Export Finance Reports", "finance"),
    ("finance_view_trial_balance", "View Trial Balance", "finance"),
    ("finance_view_general_ledger", "View General Ledger", "finance"),
    ("finance_view_ar_aging", "View AR Aging", "finance"),
    ("finance_view_ap_aging", "View AP Aging", "finance"),
    ("finance_view_vat_return", "View VAT/Tax Returns", "finance"),
    ("finance_view_currencies", "View Currencies", "finance"),
    ("finance_manage_currencies", "Manage Currencies", "finance"),
    ("finance_view_exchange_rates", "View Exchange Rates", "finance"),
    ("finance_manage_exchange_rates", "Manage Exchange Rates", "finance"),
    ("finance_view_posting_rules", "View Inventory Posting Rules", "finance"),
    ("finance_manage_posting_rules", "Manage Inventory Posting Rules", "finance"),

    # Budgeting
    ("budgeting_view_budgets", "View Budgets", "budgeting"),
    ("budgeting_manage_budgets", "Manage Budgets", "budgeting"),
    ("budgeting_view_entries", "View Budget Entries", "budgeting"),
    ("budgeting_manage_entries", "Manage Budget Entries", "budgeting"),
    ("budgeting_approve_entries", "Approve Budget Entries", "budgeting"),
    ("budgeting_submit_entries", "Submit Budget Entries", "budgeting"),
    ("budgeting_view_reports", "View Budget Reports", "budgeting"),
    ("budgeting_export_reports", "Export Budget Reports", "budgeting"),

    # Procurement
    ("procurement_view_suppliers", "View Suppliers", "procurement"),
    ("procurement_manage_suppliers", "Manage Suppliers", "procurement"),
    ("procurement_blacklist_supplier", "Blacklist Supplier", "procurement"),
    ("procurement_view_pr", "View Purchase Requisitions", "procurement"),
    ("procurement_manage_pr", "Manage Purchase Requisitions", "procurement"),
    ("procurement_submit_pr", "Submit Purchase Requisition", "procurement"),
    ("procurement_approve_pr", "Approve Purchase Requisition", "procurement"),
    ("procurement_view_po", "View Purchase Orders", "procurement"),
    ("procurement_manage_po", "Manage Purchase Orders", "procurement"),
    ("procurement_approve_po", "Approve Purchase Orders", "procurement"),
    ("procurement_view_grn", "View Goods Receipts", "procurement"),
    ("procurement_manage_grn", "Manage Goods Receipts", "procurement"),
    ("procurement_approve_grn", "Approve Goods Receipts", "procurement"),

    # Inventory
    ("inventory_view_items", "View Items", "inventory"),
    ("inventory_manage_items", "Manage Items", "inventory"),
    ("inventory_view_warehouses", "View Warehouses", "inventory"),
    ("inventory_manage_warehouses", "Manage Warehouses", "inventory"),
    ("inventory_view_movements", "View Stock Movements", "inventory"),
    ("inventory_manage_movements", "Manage Stock Movements", "inventory"),
    ("inventory_manage_valuation", "Manage Valuation Settings", "inventory"),
    ("inventory_manage_landed_cost", "Manage Landed Cost Adjustments", "inventory"),
    ("inventory_view_cost_layers", "View Cost Layers", "inventory"),
    ("inventory_view_valuation_reports", "View Valuation Reports", "inventory"),
    ("inventory_apply_adjustments", "Apply Stock Adjustments", "inventory"),
    ("inventory_manage_qc", "Manage QC/Stock States", "inventory"),
    ("inventory_manage_transfers", "Manage Transfers", "inventory"),
    ("inventory_manage_counts", "Manage Stock Counts", "inventory"),
    ("inventory_view_stock_levels", "View Stock Levels", "inventory"),

    # Workflows / No-code
    ("workflows_manage_templates", "Manage Workflow Templates", "workflows"),
    ("workflows_manage_instances", "Manage Workflow Instances", "workflows"),
    ("workflows_publish_templates", "Publish Workflow Templates", "workflows"),
    ("workflows_approve_instance", "Approve Workflow Instance", "workflows"),
    ("report_builder_manage", "Manage Reports", "report_builder"),
    ("report_builder_publish", "Publish Reports", "report_builder"),
    ("report_builder_view", "View Reports Builder", "report_builder"),
    ("form_builder_manage", "Manage Forms", "form_builder"),
    ("form_builder_publish", "Publish Forms", "form_builder"),
    ("form_builder_view", "View Forms Builder", "form_builder"),

    # Data migration
    ("data_migration_manage", "Manage Data Migration", "data_migration"),
    ("data_migration_view", "View Data Migration", "data_migration"),
    ("data_migration_approve", "Approve Migration Batch", "data_migration"),
    ("data_migration_commit", "Commit Migration", "data_migration"),
    ("data_migration_rollback", "Rollback Migration", "data_migration"),

    # Company admin
    ("companies_view", "View Companies", "companies"),
    ("companies_manage", "Manage Companies", "companies"),
    ("companies_groups_view", "View Company Groups", "companies"),
    ("companies_groups_manage", "Manage Company Groups", "companies"),
]


ROLE_MAP: Dict[str, List[str]] = {
    # Full system access across all companies
    "System Administrator": [code for code, _, _ in DEFAULT_PERMISSIONS],

    # Company wide admin (typical operator role inside one company)
    "Company Administrator": [
\1        "budgeting_view_item_codes", "budgeting_manage_item_codes", "budgeting_view_uoms", "budgeting_manage_uoms",
    ],

    # Finance
    "Finance Manager": [
        "finance_view_coa", "finance_manage_coa", "finance_close_period",
        "finance_view_journal", "finance_manage_journal", "finance_post_journal", "finance_approve_journal",
        "finance_view_invoice", "finance_manage_invoice",
        "finance_view_payment", "finance_manage_payment",
        "finance_reconcile_bank", "finance_view_reports", "finance_export_reports",
        "finance_view_trial_balance", "finance_view_general_ledger", "finance_view_ar_aging", "finance_view_ap_aging", "finance_view_vat_return",
        "finance_view_currencies", "finance_manage_currencies", "finance_view_exchange_rates", "finance_manage_exchange_rates",
        "finance_view_posting_rules", "finance_manage_posting_rules",
    ],
    "Finance Accountant": [
        "finance_view_coa",
        "finance_view_journal", "finance_manage_journal", "finance_post_journal",
        "finance_view_invoice", "finance_manage_invoice",
        "finance_view_payment", "finance_manage_payment",
        "finance_view_reports", "finance_export_reports",
        "finance_view_trial_balance", "finance_view_general_ledger", "finance_view_ar_aging", "finance_view_ap_aging", "finance_view_vat_return",
        "finance_view_currencies", "finance_view_exchange_rates",
    ],

    # Procurement
    "Procurement Manager": [
        "procurement_view_suppliers", "procurement_manage_suppliers", "procurement_blacklist_supplier",
        "procurement_view_pr", "procurement_manage_pr", "procurement_submit_pr", "procurement_approve_pr",
        "procurement_view_po", "procurement_manage_po", "procurement_approve_po",
        "procurement_view_grn", "procurement_manage_grn", "procurement_approve_grn",
    ],
    "Procurement Officer": [
        "procurement_view_suppliers", "procurement_manage_suppliers",
        "procurement_view_pr", "procurement_manage_pr", "procurement_submit_pr",
        "procurement_view_po", "procurement_manage_po",
        "procurement_view_grn", "procurement_manage_grn",
    ],

    # Inventory
    "Inventory Manager": [
        "inventory_view_items", "inventory_manage_items",
        "inventory_view_warehouses", "inventory_manage_warehouses",
        "inventory_view_movements", "inventory_manage_movements",
        "inventory_manage_valuation", "inventory_manage_landed_cost",
        "inventory_view_cost_layers", "inventory_view_valuation_reports",
        "inventory_apply_adjustments", "inventory_manage_qc", "inventory_manage_transfers", "inventory_manage_counts", "inventory_view_stock_levels",
    ],
    "Inventory Clerk": [
        "inventory_view_items",
        "inventory_view_warehouses",
        "inventory_view_movements", "inventory_manage_movements",
        "inventory_view_stock_levels",
    ],

    # Budgeting
    "Budget Manager": [
\1        "budgeting_view_item_codes", "budgeting_manage_item_codes", "budgeting_view_uoms", "budgeting_manage_uoms",
    ],
    "Budget Contributor": [
\1        "budgeting_view_item_codes", "budgeting_view_uoms",
    ],

    # No-code & Workflow
    "Workflow Admin": ["workflows_manage_templates", "workflows_publish_templates", "workflows_manage_instances", "workflows_approve_instance"],
    "Report Builder Admin": ["report_builder_view", "report_builder_manage", "report_builder_publish"],
    "Form Builder Admin": ["form_builder_view", "form_builder_manage", "form_builder_publish"],

    # Data Migration
    "Data Migration Admin": ["data_migration_view", "data_migration_manage", "data_migration_approve", "data_migration_commit", "data_migration_rollback"],
}


class Command(BaseCommand):
    help = "Seed default permissions and roles aligned to module specs. Idempotent and safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument(
            "--company-id",
            type=int,
            default=None,
            help="Optional company id to create company-scoped copies of roles",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        company_id = options.get("company_id")
        company = None
        if company_id is not None:
            company = Company.objects.filter(id=company_id).first()
            if not company:
                self.stderr.write(self.style.ERROR(f"Company id {company_id} not found"))
                return

        # Upsert permissions
        code_to_obj: Dict[str, Permission] = {}
        created_perm = 0
        for code, name, module in DEFAULT_PERMISSIONS:
            obj, created = Permission.objects.update_or_create(
                code=code,
                defaults={"name": name, "module": module},
            )
            code_to_obj[code] = obj
            if created:
                created_perm += 1

        # Upsert roles
        created_roles = 0
        updated_roles = 0
        for role_name, perm_codes in ROLE_MAP.items():
            role, created = Role.objects.get_or_create(
                name=role_name,
                company=company,
                defaults={
                    "description": f"Default role: {role_name}",
                    "is_system_role": True if company is None else False,
                },
            )
            # Set permissions (replace set for idempotency)
            perms = [code_to_obj[c] for c in perm_codes if c in code_to_obj]
            role.permissions.set(perms)
            role.save()
            if created:
                created_roles += 1
            else:
                updated_roles += 1

        scope = "global" if company is None else f"company {company.code}"
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_perm} new permissions; roles created: {created_roles}, updated: {updated_roles} ({scope})."
            )
        )




