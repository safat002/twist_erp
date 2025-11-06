from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0002_taskitem_recurrence"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0008_alter_companygroup_base_currency_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserCalendarLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("provider", models.CharField(choices=[("google", "Google"), ("outlook", "Outlook")], default="google", max_length=20)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("is_enabled", models.BooleanField(default=False)),
                ("ics_token", models.CharField(max_length=64, unique=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="companies.company")),
                ("company_group", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="companies.companygroup")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="calendar_links", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "unique_together": {("company", "user", "provider")},
            },
        ),
    ]

