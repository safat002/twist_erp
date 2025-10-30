from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ai_companion", "0003_aiguardrailtestcase"),
    ]

    operations = [
        migrations.CreateModel(
            name="AILoRARun",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("run_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("adapter_type", models.CharField(default="lora", max_length=32)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("success", "Success"),
                            ("failed", "Failed"),
                        ],
                        default="queued",
                        max_length=20,
                    ),
                ),
                ("dataset_size", models.PositiveIntegerField(default=0)),
                ("dataset_snapshot", models.JSONField(blank=True, default=list)),
                ("training_args", models.JSONField(blank=True, default=dict)),
                ("metrics", models.JSONField(blank=True, default=dict)),
                ("artifact_path", models.CharField(blank=True, max_length=512)),
                ("error", models.TextField(blank=True)),
                ("scheduled_for", models.DateTimeField(blank=True, null=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "triggered_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_lora_runs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="ailorarun",
            index=models.Index(fields=["status", "created_at"], name="ai_loraru_status_4ee31b_idx"),
        ),
        migrations.AddIndex(
            model_name="ailorarun",
            index=models.Index(fields=["adapter_type", "created_at"], name="ai_loraru_adapter_458b42_idx"),
        ),
    ]
