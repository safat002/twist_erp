# Generated migration for ABC/VED classification fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),  # Update this to your latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='abc_classification',
            field=models.CharField(
                max_length=1,
                choices=[('A', 'A - High Value'), ('B', 'B - Medium Value'), ('C', 'C - Low Value')],
                null=True,
                blank=True,
                help_text='ABC classification based on consumption value'
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='abc_classification_date',
            field=models.DateField(
                null=True,
                blank=True,
                help_text='Date of last ABC classification'
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='ved_classification',
            field=models.CharField(
                max_length=1,
                choices=[('V', 'V - Vital'), ('E', 'E - Essential'), ('D', 'D - Desirable')],
                null=True,
                blank=True,
                help_text='VED classification based on criticality'
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='ved_classification_date',
            field=models.DateField(
                null=True,
                blank=True,
                help_text='Date of last VED classification'
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='standard_cost',
            field=models.DecimalField(
                max_digits=20,
                decimal_places=2,
                null=True,
                blank=True,
                help_text='Standard cost for standard cost valuation method'
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='valuation_method',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('FIFO', 'First In, First Out'),
                    ('LIFO', 'Last In, First Out'),
                    ('WEIGHTED_AVG', 'Weighted Average'),
                    ('STANDARD_COST', 'Standard Cost'),
                ],
                default='FIFO',
                help_text='Default valuation method for this product'
            ),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['company', 'abc_classification'], name='inv_prod_abc_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['company', 'ved_classification'], name='inv_prod_ved_idx'),
        ),
    ]
