from decimal import Decimal

from django.db import migrations, models


def sync_budget_master_fields(apps, schema_editor):
    Item = apps.get_model('inventory', 'Item')
    items = Item.objects.select_related('budget_item').filter(budget_item__isnull=False)
    zero = Decimal('0')
    for item in items.iterator():
        budget = item.budget_item
        if not budget:
            continue
        updates = {}
        if budget.company_id and item.company_id != budget.company_id:
            updates['company_id'] = budget.company_id
        if budget.code and item.code != budget.code:
            updates['code'] = budget.code
        if budget.name and item.name != budget.name:
            updates['name'] = budget.name
        if budget.uom_id and item.uom_id != budget.uom_id:
            updates['uom_id'] = budget.uom_id
        if budget.standard_price and (item.standard_cost is None or item.standard_cost == zero):
            updates['standard_cost'] = budget.standard_price
        if updates:
            Item.objects.filter(pk=item.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '10014_link_budget_items'),
    ]

    operations = [
        migrations.RunPython(sync_budget_master_fields, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='item',
            constraint=models.UniqueConstraint(
                condition=models.Q(budget_item__isnull=False),
                fields=('company', 'budget_item'),
                name='inventory_item_company_budget_item_unique',
            ),
        ),
    ]
