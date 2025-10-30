from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0001_initial"),
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="category",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="asset",
            name="location",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="asset",
            name="manufacturer",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="asset",
            name="model_number",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="asset",
            name="serial_number",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="asset",
            name="status",
            field=models.CharField(
                choices=[
                    ("ACTIVE", "Active"),
                    ("MAINTENANCE", "In Maintenance"),
                    ("RETIRED", "Retired"),
                ],
                default="ACTIVE",
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="asset",
            options={"ordering": ["-acquisition_date", "code"]},
        ),
        migrations.AddIndex(
            model_name="asset",
            index=models.Index(
                fields=["company", "status"], name="assets_asset_company_ae4bee_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="asset",
            index=models.Index(
                fields=["company", "category"], name="assets_asset_company_aa45ff_idx"
            ),
        ),
        migrations.CreateModel(
            name="AssetMaintenancePlan",
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
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("maintenance_type", models.CharField(blank=True, max_length=120)),
                ("scheduled_date", models.DateField()),
                ("due_date", models.DateField()),
                ("completed_at", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PLANNED", "Planned"),
                            ("IN_PROGRESS", "In Progress"),
                            ("COMPLETED", "Completed"),
                            ("OVERDUE", "Overdue"),
                        ],
                        default="PLANNED",
                        max_length=20,
                    ),
                ),
                ("assigned_to", models.CharField(blank=True, max_length=255)),
                ("frequency_months", models.PositiveIntegerField(default=0)),
                (
                    "cost_estimate",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("0.00"), max_digits=12
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "asset",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="maintenance_tasks",
                        to="assets.asset",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="asset_maintenance",
                        to="companies.company",
                    ),
                ),
            ],
            options={
                "ordering": ["scheduled_date", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="assetmaintenanceplan",
            index=models.Index(
                fields=["company", "status"],
                name="assets_asset_company_648904_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="assetmaintenanceplan",
            index=models.Index(
                fields=["company", "scheduled_date"],
                name="assets_asset_company_135f1c_idx",
            ),
        ),
    ]
