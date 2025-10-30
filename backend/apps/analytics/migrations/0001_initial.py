from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='CashflowSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('snapshot_date', models.DateField()),
                ('period', models.CharField(default='30d', max_length=20)),
                ('company_id', models.IntegerField()),
                ('company_code', models.CharField(max_length=50)),
                ('company_name', models.CharField(max_length=255)),
                ('timeframe_start', models.DateField()),
                ('timeframe_end', models.DateField()),
                ('cash_in', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('cash_out', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('net_cash', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('cash_trend', models.JSONField(blank=True, default=list)),
                ('receivables_balance', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('payables_balance', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('bank_balances', models.JSONField(blank=True, default=list)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-snapshot_date', '-created_at'],
                'db_table': 'dw_cashflow_snapshot',
                'unique_together': {('snapshot_date', 'period', 'company_id')},
            },
        ),
        migrations.CreateModel(
            name='SalesPerformanceSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('snapshot_date', models.DateField()),
                ('period', models.CharField(default='30d', max_length=20)),
                ('company_id', models.IntegerField()),
                ('company_code', models.CharField(max_length=50)),
                ('company_name', models.CharField(max_length=255)),
                ('timeframe_start', models.DateField()),
                ('timeframe_end', models.DateField()),
                ('total_orders', models.IntegerField(default=0)),
                ('total_revenue', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('avg_order_value', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('sales_trend', models.JSONField(blank=True, default=list)),
                ('top_customers', models.JSONField(blank=True, default=list)),
                ('top_products', models.JSONField(blank=True, default=list)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-snapshot_date', '-created_at'],
                'db_table': 'dw_sales_performance',
                'unique_together': {('snapshot_date', 'period', 'company_id')},
            },
        ),
        migrations.CreateModel(
            name='WarehouseRunLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('run_at', models.DateTimeField(auto_now_add=True)),
                ('company_id', models.IntegerField(blank=True, null=True)),
                ('company_code', models.CharField(blank=True, max_length=50)),
                ('company_name', models.CharField(blank=True, max_length=255)),
                ('run_type', models.CharField(default='nightly', max_length=50)),
                ('status', models.CharField(choices=[('SUCCESS', 'Success'), ('FAILED', 'Failed')], max_length=20)),
                ('processed_records', models.IntegerField(default=0)),
                ('message', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-run_at'],
                'db_table': 'dw_run_log',
            },
        ),
        migrations.AddIndex(
            model_name='salesperformancesnapshot',
            index=models.Index(fields=['company_id', 'period', 'snapshot_date'], name='analytics__company_5aafe1_idx'),
        ),
        migrations.AddIndex(
            model_name='cashflowsnapshot',
            index=models.Index(fields=['company_id', 'period', 'snapshot_date'], name='analytics__company_07286d_idx'),
        ),
    ]
