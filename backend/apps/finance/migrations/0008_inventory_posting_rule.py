from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0007_rename_finance_ban_company_10c484_idx_finance_ban_company_307ba9_idx_and_more"),
        ("inventory", "0015_product_expiry_controls"),
    ]

    operations = [
        migrations.CreateModel(
            name='InventoryPostingRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('warehouse_type', models.CharField(blank=True, default='', max_length=20)),
                ('transaction_type', models.CharField(blank=True, choices=[('RECEIPT', 'Stock Receipt'), ('ISSUE', 'Stock Issue'), ('TRANSFER', 'Transfer'), ('ADJUSTMENT', 'Adjustment')], default='', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=models.PROTECT, to='inventory.productcategory')),
                ('company', models.ForeignKey(on_delete=models.PROTECT, related_name='inventory_posting_rules', to='companies.company')),
                ('cogs_account', models.ForeignKey(blank=True, null=True, on_delete=models.PROTECT, related_name='+', to='finance.account')),
                ('inventory_account', models.ForeignKey(on_delete=models.PROTECT, related_name='+', to='finance.account')),
            ],
        ),
        migrations.AddIndex(
            model_name='inventorypostingrule',
            index=models.Index(fields=['company', 'warehouse_type', 'transaction_type'], name='fin_invpost_wh_txn_idx'),
        ),
        migrations.AddIndex(
            model_name='inventorypostingrule',
            index=models.Index(fields=['company', 'category'], name='fin_invpost_cat_idx'),
        ),
    ]

