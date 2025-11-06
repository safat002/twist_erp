from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0001_initial"),
        ("permissions", "0001_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="workflowtemplate",
            name="approver_role",
            field=models.ForeignKey(
                to="permissions.role",
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True,
                related_name="workflow_templates_as_approver",
                help_text="Role responsible for approving instances of this workflow",
            ),
        ),
        migrations.AddField(
            model_name="workflowinstance",
            name="approver_role",
            field=models.ForeignKey(
                to="permissions.role",
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True,
                related_name="workflow_instances",
            ),
        ),
        migrations.AddField(
            model_name="workflowinstance",
            name="assigned_to",
            field=models.ForeignKey(
                to="users.user",
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True,
                related_name="assigned_workflow_instances",
            ),
        ),
    ]

