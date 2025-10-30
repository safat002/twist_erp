from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('form_builder', '0001_initial'),
        ('companies', '0002_company_external_db_connection'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DynamicEntity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('slug', models.SlugField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('fields', models.JSONField(blank=True, default=list)),
                ('model_name', models.CharField(max_length=255)),
                ('table_name', models.CharField(max_length=255)),
                ('api_path', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='dynamic_entities', to='companies.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_dynamic_entities', to=settings.AUTH_USER_MODEL)),
                ('template', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='entity', to='form_builder.formtemplate')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='dynamicentity',
            unique_together={('company', 'slug')},
        ),
    ]
