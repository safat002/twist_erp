from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('companies', '0002_company_external_db_connection'),
    ]

    operations = [
        migrations.CreateModel(
            name='DashboardLayout',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('layout', models.JSONField(blank=True, default=dict)),
                ('widgets', models.JSONField(blank=True, default=list)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dashboard_layouts', to='companies.company')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dashboard_layouts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AlterModelTable(
            name='dashboardlayout',
            table='dashboard_layout',
        ),
        migrations.AlterUniqueTogether(
            name='dashboardlayout',
            unique_together={('user', 'company')},
        ),
    ]
