from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0001_initial'),
        ('inventory', '0007_merge_20251101_0939'),
    ]

    operations = [
        migrations.CreateModel(
            name='InternalRequisition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('requisition_number', models.CharField(blank=True, db_index=True, max_length=50)),
                ('request_date', models.DateField()),
                ('needed_by', models.DateField(blank=True, null=True)),
                ('purpose', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('SUBMITTED', 'Submitted'), ('APPROVED', 'Approved'), ('CANCELLED', 'Cancelled')], default='SUBMITTED', max_length=20)),
                ('lines', models.JSONField(blank=True, default=list)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='companies.company')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('warehouse', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='inventory.warehouse')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='internalrequisition',
            index=models.Index(fields=['company', 'status'], name='inventory_intern_compan_b7c2c8_idx'),
        ),
        migrations.AddIndex(
            model_name='internalrequisition',
            index=models.Index(fields=['company', 'requisition_number'], name='inventory_intern_compan_3c7a6d_idx'),
        ),
    ]

