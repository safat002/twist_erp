from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0004_usercalendarlink_created_by_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0008_alter_companygroup_base_currency_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserCalendarCredential",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("provider", models.CharField(choices=[("google", "Google"), ("outlook", "Outlook")], default="outlook", max_length=20)),
                ("access_token", models.TextField()),
                ("refresh_token", models.TextField()),
                ("expires_at", models.DateTimeField()),
                ("scope", models.CharField(blank=True, max_length=255)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="companies.company")),
                ("company_group", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="companies.companygroup")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="calendar_credentials", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "unique_together": {("company", "user", "provider")},
            },
        ),
    ]

