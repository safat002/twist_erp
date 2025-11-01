from django.db import migrations


def add_report_builder_permission(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Permission.objects.get_or_create(
        code="can_build_reports",
        defaults={
            "name": "Design and run reports",
            "module": "report_builder",
            "description": "Allows access to the metadata-driven report builder.",
        },
    )


def remove_report_builder_permission(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Permission.objects.filter(code="can_build_reports").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("permissions", "0002_add_phase4_permissions"),
    ]

    operations = [
        migrations.RunPython(add_report_builder_permission, remove_report_builder_permission),
    ]
