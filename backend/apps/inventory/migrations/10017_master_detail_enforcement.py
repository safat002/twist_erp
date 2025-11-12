from decimal import Decimal

from django.db import migrations, models
from django.db.models import Q


def backfill_budget_links(apps, schema_editor):
    Item = apps.get_model('inventory', 'Item')
    ItemOperationalExtension = apps.get_model('inventory', 'ItemOperationalExtension')
    ItemWarehouseConfig = apps.get_model('inventory', 'ItemWarehouseConfig')
    ItemSupplier = apps.get_model('inventory', 'ItemSupplier')
    ItemFEFOConfig = apps.get_model('inventory', 'ItemFEFOConfig')
    ItemUOMConversion = apps.get_model('inventory', 'ItemUOMConversion')
    BudgetItemCode = apps.get_model('budgeting', 'BudgetItemCode')
    Company = apps.get_model('companies', 'Company')

    company_groups = {}

    def resolve_budget(item):
        if not item.code:
            return None
        qs = BudgetItemCode.objects.filter(code=item.code)
        company_id = item.company_id
        if company_id:
            if company_id not in company_groups:
                company_groups[company_id] = Company.objects.filter(pk=company_id).values_list('company_group_id', flat=True).first()
            company_group_id = company_groups.get(company_id)
            qs = qs.filter(Q(company_id=company_id) | Q(company_id__isnull=True, company_group_id=company_group_id))
        return qs.order_by('-company_id').first()

    def ensure_budget_master(item):
        company = item.company
        company_group_id = None
        if company:
            if company.id not in company_groups:
                company_groups[company.id] = Company.objects.filter(pk=company.id).values_list('company_group_id', flat=True).first()
            company_group_id = company_groups.get(company.id)
        defaults = {
            'company': company,
            'company_group_id': company_group_id,
            'name': item.name or item.code,
            'uom_id': item.uom_id,
            'standard_price': item.standard_cost or item.cost_price or Decimal('0'),
            'category': getattr(item.category, 'name', '') if getattr(item, 'category', None) else '',
        }
        budget, _created = BudgetItemCode.objects.get_or_create(
            company_group_id=company_group_id,
            code=item.code,
            defaults=defaults,
        )
        return budget

    # Ensure every Item is linked to a budgeting master item.
    for item in Item.objects.filter(budget_item__isnull=True).select_related('company').iterator():
        budget = resolve_budget(item) or ensure_budget_master(item)
        Item.objects.filter(pk=item.pk).update(budget_item_id=budget.id)

    def propagate_budget(model, infer_item=False):
        for record in model.objects.filter(budget_item__isnull=True).select_related('item').iterator():
            budget_item_id = getattr(record.item, 'budget_item_id', None)
            if budget_item_id:
                model.objects.filter(pk=record.pk).update(budget_item_id=budget_item_id)
            elif infer_item:
                budget = resolve_budget(record.item) if record.item else None
                if budget:
                    model.objects.filter(pk=record.pk).update(budget_item_id=budget.id)

    propagate_budget(ItemOperationalExtension)
    propagate_budget(ItemWarehouseConfig)
    propagate_budget(ItemSupplier)
    propagate_budget(ItemFEFOConfig)

    for conv in ItemUOMConversion.objects.filter(budget_item__isnull=True).select_related('item').iterator():
        budget_item_id = getattr(conv.item, 'budget_item_id', None)
        if budget_item_id:
            ItemUOMConversion.objects.filter(pk=conv.pk).update(budget_item_id=budget_item_id)
        else:
            budget = resolve_budget(conv.item) if conv.item else None
            if budget:
                ItemUOMConversion.objects.filter(pk=conv.pk).update(budget_item_id=budget.id)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('inventory', '10016_stockmovement_budget_item_related_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemuomconversion',
            name='budget_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.PROTECT, related_name='uom_conversions', to='budgeting.budgetitemcode'),
        ),
        migrations.RunPython(backfill_budget_links, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='item',
            name='budget_item',
            field=models.OneToOneField(help_text='Budget master item reference', on_delete=models.PROTECT, related_name='inventory_extension', to='budgeting.budgetitemcode'),
        ),
        migrations.AlterField(
            model_name='itemoperationalextension',
            name='item',
            field=models.OneToOneField(blank=True, help_text='Deprecated linkage; use budget_item instead', null=True, on_delete=models.CASCADE, related_name='operational_profile', to='inventory.item'),
        ),
        migrations.AlterField(
            model_name='itemoperationalextension',
            name='budget_item',
            field=models.OneToOneField(help_text='Budget master item reference', on_delete=models.PROTECT, related_name='operational_extension', to='budgeting.budgetitemcode'),
        ),
        migrations.AlterField(
            model_name='itemwarehouseconfig',
            name='item',
            field=models.ForeignKey(blank=True, help_text='Deprecated linkage; use budget_item instead', null=True, on_delete=models.CASCADE, related_name='warehouse_configs', to='inventory.item'),
        ),
        migrations.AlterField(
            model_name='itemwarehouseconfig',
            name='budget_item',
            field=models.ForeignKey(help_text='Budget master item reference', on_delete=models.PROTECT, related_name='warehouse_configs', to='budgeting.budgetitemcode'),
        ),
        migrations.AlterUniqueTogether(
            name='itemwarehouseconfig',
            unique_together={('budget_item', 'warehouse', 'is_active')},
        ),
        migrations.AlterField(
            model_name='itemuomconversion',
            name='item',
            field=models.ForeignKey(blank=True, help_text='Deprecated linkage; use budget_item instead', null=True, on_delete=models.CASCADE, related_name='uom_conversions', to='inventory.item'),
        ),
        migrations.AlterField(
            model_name='itemuomconversion',
            name='budget_item',
            field=models.ForeignKey(help_text='Budget master item reference', on_delete=models.PROTECT, related_name='uom_conversions', to='budgeting.budgetitemcode'),
        ),
        migrations.AlterUniqueTogether(
            name='itemuomconversion',
            unique_together={('budget_item', 'from_uom', 'to_uom', 'effective_date', 'precedence')},
        ),
        migrations.AlterField(
            model_name='itemsupplier',
            name='item',
            field=models.ForeignKey(blank=True, help_text='Deprecated linkage; use budget_item instead', null=True, on_delete=models.CASCADE, related_name='supplier_links', to='inventory.item'),
        ),
        migrations.AlterField(
            model_name='itemsupplier',
            name='budget_item',
            field=models.ForeignKey(help_text='Budget master item reference', on_delete=models.PROTECT, related_name='supplier_links', to='budgeting.budgetitemcode'),
        ),
        migrations.AlterUniqueTogether(
            name='itemsupplier',
            unique_together={('budget_item', 'supplier')},
        ),
        migrations.AlterField(
            model_name='itemfefoconfig',
            name='item',
            field=models.ForeignKey(blank=True, help_text='Deprecated linkage; use budget_item instead', null=True, on_delete=models.CASCADE, related_name='fefo_configs', to='inventory.item'),
        ),
        migrations.AlterField(
            model_name='itemfefoconfig',
            name='budget_item',
            field=models.ForeignKey(help_text='Budget master item reference', on_delete=models.PROTECT, related_name='fefo_configs', to='budgeting.budgetitemcode'),
        ),
        migrations.AlterUniqueTogether(
            name='itemfefoconfig',
            unique_together={('budget_item', 'warehouse')},
        ),
    ]
