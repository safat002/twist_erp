from django.db import migrations


def add_phase4_permissions(apps, schema_editor):
    Permission = apps.get_model('permissions', 'Permission')
    permissions = [
        ('can_design_forms', 'Design form layouts', 'form_builder'),
        ('can_build_modules', 'Build custom modules', 'form_builder'),
        ('can_edit_workflows', 'Edit workflow definitions', 'workflows'),
        ('can_build_dashboards', 'Build dashboards', 'dashboard'),
    ]
    for code, name, module in permissions:
        Permission.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'module': module,
                'description': f'Automatically provisioned permission for {module} builder.',
            },
        )


def remove_phase4_permissions(apps, schema_editor):
    Permission = apps.get_model('permissions', 'Permission')
    Permission.objects.filter(
        code__in=[
            'can_design_forms',
            'can_build_modules',
            'can_edit_workflows',
            'can_build_dashboards',
        ]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('permissions', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_phase4_permissions, remove_phase4_permissions),
    ]
