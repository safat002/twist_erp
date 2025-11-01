from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0004_intercompanylink_groupaccountmap"),
        ("metadata", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportDefinition",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "slug",
                    models.SlugField(blank=True, default="", max_length=255),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "layer",
                    models.CharField(
                        choices=[
                            ("CORE", "Core System"),
                            ("INDUSTRY_PACK", "Industry Pack Baseline"),
                            ("GROUP_CUSTOM", "Group Customization"),
                            ("COMPANY_OVERRIDE", "Company Override"),
                        ],
                        default="COMPANY_OVERRIDE",
                        max_length=20,
                    ),
                ),
                (
                    "scope_type",
                    models.CharField(
                        choices=[
                            ("COMPANY", "Company"),
                            ("GROUP", "Company Group"),
                            ("GLOBAL", "Global"),
                        ],
                        default="COMPANY",
                        max_length=15,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("active", "Active"),
                            ("archived", "Archived"),
                        ],
                        default="draft",
                        max_length=15,
                    ),
                ),
                ("version", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("definition", models.JSONField(blank=True, default=dict)),
                ("summary", models.JSONField(blank=True, default=dict)),
                ("required_permissions", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_published_at", models.DateTimeField(blank=True, null=True)),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="report_definitions",
                        to="companies.company",
                    ),
                ),
                (
                    "company_group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="report_definitions",
                        to="companies.companygroup",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_report_definitions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "metadata",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="report_definitions",
                        to="metadata.metadatadefinition",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="updated_report_definitions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at", "name"],
            },
        ),
        migrations.AddConstraint(
            model_name="reportdefinition",
            constraint=models.UniqueConstraint(
                condition=models.Q(("scope_type", "COMPANY")),
                fields=("slug", "company"),
                name="uniq_report_slug_company",
            ),
        ),
        migrations.AddConstraint(
            model_name="reportdefinition",
            constraint=models.UniqueConstraint(
                condition=models.Q(("scope_type", "GROUP")),
                fields=("slug", "company_group"),
                name="uniq_report_slug_group",
            ),
        ),
        migrations.AddConstraint(
            model_name="reportdefinition",
            constraint=models.UniqueConstraint(
                condition=models.Q(("scope_type", "GLOBAL")),
                fields=("slug",),
                name="uniq_report_slug_global",
            ),
        ),
    ]
