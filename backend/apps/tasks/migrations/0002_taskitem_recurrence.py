from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="taskitem",
            name="recurrence",
            field=models.CharField(
                choices=[("none", "None"), ("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")],
                default="none",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="taskitem",
            name="recurrence_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

