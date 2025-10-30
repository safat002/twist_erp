from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ai_companion", "0004_ailorarun"),
    ]

    operations = [
        migrations.AddField(
            model_name="aitrainingexample",
            name="review_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="aitrainingexample",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="aitrainingexample",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ai_training_reviews",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name="aitrainingexample",
            index=models.Index(fields=["reviewed_by", "reviewed_at"], name="ai_trainin_reviewe_83f33c_idx"),
        ),
    ]
