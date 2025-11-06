from django.db import migrations, models


def backfill_company_group(apps, schema_editor):
    Category = apps.get_model('budgeting', 'BudgetItemCategory')
    SubCategory = apps.get_model('budgeting', 'BudgetItemSubCategory')
    Company = apps.get_model('companies', 'Company')
    for model in (Category, SubCategory):
        for row in model.objects.all().only('id', 'company_id'):
            company = Company.objects.filter(id=row.company_id).select_related('company_group').first()
            if company and getattr(company, 'company_group_id', None):
                model.objects.filter(id=row.id).update(company_group_id=company.company_group_id)


class Migration(migrations.Migration):

    dependencies = [
        ('budgeting', '0018_itemcode_add_group_unique'),
        ('companies', '__latest__'),
    ]

    operations = [
        migrations.CreateModel(
            name='BudgetItemCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=models.deletion.PROTECT, related_name='budget_item_categories', to='companies.company')),
                ('company_group', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, related_name='+', to='companies.companygroup')),
            ],
            options={
                'ordering': ['code'],
            },
        ),
        migrations.AddConstraint(
            model_name='budgetitemcategory',
            constraint=models.UniqueConstraint(fields=('company', 'code'), name='uniq_budget_cat_company_code'),
        ),
        migrations.CreateModel(
            name='BudgetItemSubCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=models.deletion.PROTECT, related_name='budget_item_subcategories', to='companies.company')),
                ('company_group', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, related_name='+', to='companies.companygroup')),
                ('category', models.ForeignKey(on_delete=models.deletion.PROTECT, related_name='subcategories', to='budgeting.budgetitemcategory')),
            ],
            options={
                'ordering': ['category_id', 'code'],
            },
        ),
        migrations.AddConstraint(
            model_name='budgetitemsubcategory',
            constraint=models.UniqueConstraint(fields=('category', 'code'), name='uniq_budget_subcat_category_code'),
        ),
        migrations.AddField(
            model_name='budgetitemcode',
            name='category_ref',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, related_name='item_codes', to='budgeting.budgetitemcategory'),
        ),
        migrations.AddField(
            model_name='budgetitemcode',
            name='sub_category_ref',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, related_name='item_codes', to='budgeting.budgetitemsubcategory'),
        ),
        migrations.RunPython(backfill_company_group, migrations.RunPython.noop),
    ]

