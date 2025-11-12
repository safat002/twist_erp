from django.db import migrations, models
from django.db.models import Q


def link_budget_items(apps, schema_editor):
    Item = apps.get_model('inventory', 'Item')
    ItemOperationalExtension = apps.get_model('inventory', 'ItemOperationalExtension')
    ItemWarehouseConfig = apps.get_model('inventory', 'ItemWarehouseConfig')
    ItemSupplier = apps.get_model('inventory', 'ItemSupplier')
    ItemFEFOConfig = apps.get_model('inventory', 'ItemFEFOConfig')
    BudgetItemCode = apps.get_model('budgeting', 'BudgetItemCode')
    Company = apps.get_model('companies', 'Company')

    company_groups = {}

    def resolve_budget_item(item):
        if not item.code:
            return None
        qs = BudgetItemCode.objects.filter(code=item.code)
        company_id = item.company_id
        if company_id:
            if company_id not in company_groups:
                company_groups[company_id] = Company.objects.filter(pk=company_id).values_list('company_group_id', flat=True).first()
            company_group_id = company_groups.get(company_id)
            qs = qs.filter(Q(company_id=company_id) | Q(company_id__isnull=True, company_group_id=company_group_id))
        match = qs.order_by('-company_id').first()
        return match.id if match else None

    for item in Item.objects.all().iterator():
        if item.budget_item_id:
            continue
        budget_item_id = resolve_budget_item(item)
        if budget_item_id:
            Item.objects.filter(pk=item.pk).update(budget_item_id=budget_item_id)

    def propagate_budget_item(model):
        for record in model.objects.select_related('item').all().iterator():
            if record.budget_item_id:
                continue
            budget_item_id = getattr(record.item, 'budget_item_id', None)
            if budget_item_id:
                model.objects.filter(pk=record.pk).update(budget_item_id=budget_item_id)

    propagate_budget_item(ItemOperationalExtension)
    propagate_budget_item(ItemWarehouseConfig)
    propagate_budget_item(ItemSupplier)
    propagate_budget_item(ItemFEFOConfig)


class Migration(migrations.Migration):

    dependencies = [
        ('budgeting', '0028_line_workflow_backfill'),
        ('inventory', '10013_intransitshipmentline_cost_center_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='budget_item',
            field=models.ForeignKey(blank=True, help_text='Budget master item reference', null=True, on_delete=models.PROTECT, related_name='inventory_items', to='budgeting.budgetitemcode'),
        ),
        migrations.AddField(
            model_name='itemoperationalextension',
            name='budget_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.PROTECT, related_name='operational_extensions', to='budgeting.budgetitemcode'),
        ),
        migrations.AddField(
            model_name='itemwarehouseconfig',
            name='budget_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.PROTECT, related_name='warehouse_configs', to='budgeting.budgetitemcode'),
        ),
        migrations.AddField(
            model_name='itemsupplier',
            name='budget_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.PROTECT, related_name='supplier_links', to='budgeting.budgetitemcode'),
        ),
        migrations.AddField(
            model_name='itemfefoconfig',
            name='budget_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.PROTECT, related_name='fefo_configs', to='budgeting.budgetitemcode'),
        ),
        migrations.RunPython(link_budget_items, migrations.RunPython.noop),
    ]
