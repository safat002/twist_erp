from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("companies", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Donor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=30)),
                ("name", models.CharField(max_length=255)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("address", models.TextField(blank=True)),
                ("website", models.URLField(blank=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="donors", to="companies.company")),
            ],
            options={"ordering": ["name"], "unique_together": {("company", "code")}},
        ),
        migrations.CreateModel(
            name="Program",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=30)),
                ("title", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("closed", "Closed")], default="draft", max_length=20)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("total_budget", models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ("currency", models.CharField(default="USD", max_length=8)),
                ("objectives", models.TextField(blank=True)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("compliance_score", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="programs", to="companies.company")),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("donor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="programs", to="ngo.donor")),
            ],
            options={"ordering": ["-created_at"], "unique_together": {("company", "code")}},
        ),
        migrations.CreateModel(
            name="ComplianceRequirement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=30)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("frequency", models.CharField(choices=[("once", "Once"), ("monthly", "Monthly"), ("quarterly", "Quarterly"), ("annual", "Annual")], default="quarterly", max_length=20)),
                ("next_due_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("active", "Active"), ("inactive", "Inactive"), ("closed", "Closed")], default="active", max_length=20)),
                ("program", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="requirements", to="ngo.program")),
            ],
            options={"unique_together": {("program", "code")}},
        ),
        migrations.CreateModel(
            name="ComplianceSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(blank=True, null=True)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("status", models.CharField(choices=[("submitted", "Submitted"), ("accepted", "Accepted"), ("rejected", "Rejected")], default="submitted", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("file", models.FileField(blank=True, null=True, upload_to="ngo/compliance/")),
                ("requirement", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="submissions", to="ngo.compliancerequirement")),
            ],
        ),
    ]

