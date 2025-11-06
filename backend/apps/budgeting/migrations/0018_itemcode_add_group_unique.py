from django.db import migrations, models


def backfill_itemcode_group(apps, schema_editor):
    BudgetItemCode = apps.get_model('budgeting', 'BudgetItemCode')
    Company = apps.get_model('companies', 'Company')
    for row in BudgetItemCode.objects.all().only('id', 'company_id'):
        company = Company.objects.filter(id=row.company_id).select_related('company_group').first()
        if company and getattr(company, 'company_group_id', None):
            BudgetItemCode.objects.filter(id=row.id).update(company_group_id=company.company_group_id)


class Migration(migrations.Migration):

    dependencies = [
        ('budgeting', '0017_budgetline_item_budgetline_sub_category_and_more'),
        ('companies', '__latest__'),
    ]

    operations = [
        migrations.AddField(
            model_name='budgetitemcode',
            name='company_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, related_name='+', to='companies.companygroup'),
        ),
        migrations.RunPython(backfill_itemcode_group, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='budgetitemcode',
            name='company_group',
            field=models.ForeignKey(on_delete=models.deletion.PROTECT, related_name='+', to='companies.companygroup'),
        ),
        migrations.AddConstraint(
            model_name='budgetitemcode',
            constraint=models.UniqueConstraint(fields=('company_group', 'code'), name='itemcode_unique_per_group_code'),
        ),
    ]

