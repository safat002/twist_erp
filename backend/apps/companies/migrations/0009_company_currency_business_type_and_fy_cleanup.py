from django.db import migrations, models


def copy_fy_start_date_to_start(apps, schema_editor):
    Company = apps.get_model('companies', 'Company')
    for c in Company.objects.all():
        if not c.fiscal_year_start and getattr(c, 'fiscal_year_start_date', None):
            c.fiscal_year_start = c.fiscal_year_start_date
            c.save(update_fields=['fiscal_year_start'])


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0008_alter_companygroup_base_currency_and_more"),
    ]

    operations = [
        migrations.RunPython(copy_fy_start_date_to_start, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='company',
            name='fiscal_year_start_date',
        ),
        migrations.AddField(
            model_name='company',
            name='business_type',
            field=models.CharField(blank=True, help_text='Business type derived from industry packs', max_length=50),
        ),
        migrations.AlterField(
            model_name='company',
            name='base_currency',
            field=models.CharField(choices=[('USD', 'US Dollar'), ('EUR', 'Euro'), ('GBP', 'British Pound'), ('BDT', 'Bangladeshi Taka'), ('INR', 'Indian Rupee'), ('PKR', 'Pakistani Rupee'), ('LKR', 'Sri Lankan Rupee'), ('CNY', 'Chinese Yuan'), ('JPY', 'Japanese Yen'), ('AUD', 'Australian Dollar'), ('CAD', 'Canadian Dollar'), ('SGD', 'Singapore Dollar'), ('MYR', 'Malaysian Ringgit'), ('THB', 'Thai Baht'), ('IDR', 'Indonesian Rupiah'), ('PHP', 'Philippine Peso'), ('AED', 'UAE Dirham'), ('SAR', 'Saudi Riyal'), ('KWD', 'Kuwaiti Dinar'), ('OMR', 'Omani Rial'), ('QAR', 'Qatari Riyal'), ('ZAR', 'South African Rand'), ('NGN', 'Nigerian Naira'), ('GHS', 'Ghanaian Cedi'), ('KES', 'Kenyan Shilling')], default='USD', max_length=3),
        ),
        migrations.AlterField(
            model_name='company',
            name='currency_code',
            field=models.CharField(choices=[('USD', 'US Dollar'), ('EUR', 'Euro'), ('GBP', 'British Pound'), ('BDT', 'Bangladeshi Taka'), ('INR', 'Indian Rupee'), ('PKR', 'Pakistani Rupee'), ('LKR', 'Sri Lankan Rupee'), ('CNY', 'Chinese Yuan'), ('JPY', 'Japanese Yen'), ('AUD', 'Australian Dollar'), ('CAD', 'Canadian Dollar'), ('SGD', 'Singapore Dollar'), ('MYR', 'Malaysian Ringgit'), ('THB', 'Thai Baht'), ('IDR', 'Indonesian Rupiah'), ('PHP', 'Philippine Peso'), ('AED', 'UAE Dirham'), ('SAR', 'Saudi Riyal'), ('KWD', 'Kuwaiti Dinar'), ('OMR', 'Omani Rial'), ('QAR', 'Qatari Riyal'), ('ZAR', 'South African Rand'), ('NGN', 'Nigerian Naira'), ('GHS', 'Ghanaian Cedi'), ('KES', 'Kenyan Shilling')], default='BDT', max_length=3),
        ),
    ]

