from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0001_initial'),
        ('procurement', '0007_supplier_block_reason_supplier_is_blocked_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PurchaseRequisitionDraft',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('requisition_number', models.CharField(blank=True, db_index=True, max_length=50)),
                ('request_date', models.DateField()),
                ('needed_by', models.DateField(blank=True, null=True)),
                ('purpose', models.TextField(blank=True)),
                ('status', models.CharField(default='SUBMITTED', max_length=20)),
                ('lines', models.JSONField(blank=True, default=list)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='purchase_requisition_drafts', to='companies.company')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='purchaserequisitiondraft',
            index=models.Index(fields=['company', 'status'], name='proc_pr_draft_compan_bf18f3_idx'),
        ),
        migrations.AddIndex(
            model_name='purchaserequisitiondraft',
            index=models.Index(fields=['company', 'requisition_number'], name='proc_pr_draft_compan_2dfc7a_idx'),
        ),
    ]

