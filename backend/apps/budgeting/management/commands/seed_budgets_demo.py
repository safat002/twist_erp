from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.companies.models import Department
from apps.budgeting.models import CostCenter, Budget, BudgetLine


class Command(BaseCommand):
    help = "Seed demo cost center + budget with lines (Phase 6/7 UAT)."

    def add_arguments(self, parser):
        parser.add_argument('--company-id', type=int, required=True)

    def handle(self, *args, **options):
        company_id = options['company_id']

        # Ensure a department exists
        dept, _ = Department.objects.get_or_create(
            company_id=company_id, code="OPS", defaults={'name': 'Operations'}
        )

        # Cost center
        cc, _ = CostCenter.objects.get_or_create(
            company_id=company_id, code="OPS-IT", defaults={'name': 'IT Operations', 'department': dept}
        )
        if not cc.department_id:
            cc.department = dept
            cc.save(update_fields=['department'])

        # Budget
        start = date.today().replace(month=1, day=1)
        end = start.replace(month=12, day=31)
        budget, _ = Budget.objects.get_or_create(
            company_id=company_id,
            cost_center=cc,
            name="FY Demo OPEX",
            defaults={
                'budget_type': Budget.TYPE_OPEX,
                'duration_type': Budget.DURATION_YEARLY,
                'period_start': start,
                'period_end': end,
                'status': Budget.STATUS_ENTRY_OPEN,
            }
        )

        # Lines
        lines = [
            (1, BudgetLine.ProcurementClass.SERVICE_ITEM, "Cloud Subscriptions", Decimal("12"), Decimal("200.00")),
            (2, BudgetLine.ProcurementClass.STOCK_ITEM, "Laptops", Decimal("10"), Decimal("1000.00")),
            (3, BudgetLine.ProcurementClass.CAPEX_ITEM, "Server Upgrade", Decimal("1"), Decimal("5000.00")),
        ]
        created = 0
        for seq, pclass, name, qty, price in lines:
            _, is_new = BudgetLine.objects.get_or_create(
                budget=budget,
                sequence=seq,
                item_name=name,
                defaults={
                    'procurement_class': pclass,
                    'original_qty_limit': qty,
                    'original_unit_price': price,
                    'original_value_limit': (qty * price),
                    'qty_limit': qty,
                    'value_limit': (qty * price),
                    'standard_price': price,
                    'qty_variance': Decimal("0"),
                    'price_variance': Decimal("0"),
                    'value_variance': Decimal("0"),
                    'variance_percent': Decimal("0"),
                }
            )
            if is_new:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded budget '{budget.name}' and {created} lines (company={company_id})."
        ))
