from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0004_intercompanylink_groupaccountmap"),
        ("ai_companion", "0002_aifeedback_feedback_type_aifeedback_payload_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AIGuardrailTestCase",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("policy_name", models.CharField(max_length=255)),
                ("prompt", models.TextField()),
                ("expected_phrases", models.JSONField(blank=True, default=list)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("disabled", "Disabled")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("last_run_at", models.DateTimeField(blank=True, null=True)),
                (
                    "last_result",
                    models.CharField(
                        choices=[("not_run", "Not Run"), ("pass", "Pass"), ("fail", "Fail")],
                        default="not_run",
                        max_length=20,
                    ),
                ),
                ("last_output", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_guardrail_tests",
                        to="companies.company",
                    ),
                ),
            ],
            options={
                "ordering": ("policy_name", "company"),
                "unique_together": {("company", "policy_name")},
            },
        ),
        migrations.AddIndex(
            model_name="aiguardrailtestcase",
            index=models.Index(fields=["company", "status"], name="ai_guardra_company_7375f1_idx"),
        ),
        migrations.AddIndex(
            model_name="aiguardrailtestcase",
            index=models.Index(fields=["policy_name"], name="ai_guardra_policy__974369_idx"),
        ),
    ]
