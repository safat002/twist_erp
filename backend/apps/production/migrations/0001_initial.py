from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0004_intercompanylink_groupaccountmap"),
        ("inventory", "0005_goodsreceipt_hold_reason_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="BillOfMaterial",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("code", models.CharField(blank=True, max_length=32)),
                ("version", models.CharField(default="1.0", max_length=16)),
                ("name", models.CharField(blank=True, max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[("DRAFT", "Draft"), ("ACTIVE", "Active"), ("ARCHIVED", "Archived")],
                        default="DRAFT",
                        max_length=16,
                    ),
                ),
                ("is_primary", models.BooleanField(default=False)),
                ("effective_from", models.DateField(blank=True, null=True)),
                ("effective_to", models.DateField(blank=True, null=True)),
                ("revision_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="companies.company"),
                ),
                (
                    "company_group",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="companies.companygroup"),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="boms", to="inventory.product"),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("product", "version"),
                "unique_together": {("company", "code")},
            },
        ),
        migrations.CreateModel(
            name="BillOfMaterialComponent",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("sequence", models.PositiveIntegerField(default=1)),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=15)),
                ("scrap_percent", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=5)),
                (
                    "bom",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="components",
                        to="production.billofmaterial",
                    ),
                ),
                (
                    "component",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bom_components",
                        to="inventory.product",
                    ),
                ),
                (
                    "uom",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="inventory.unitofmeasure",
                    ),
                ),
                (
                    "warehouse",
                    models.ForeignKey(
                        blank=True,
                        help_text="Preferred warehouse to issue from",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="inventory.warehouse",
                    ),
                ),
            ],
            options={
                "ordering": ("sequence", "component__code"),
            },
        ),
        migrations.CreateModel(
            name="WorkOrder",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("number", models.CharField(blank=True, max_length=40)),
                ("quantity_planned", models.DecimalField(decimal_places=3, max_digits=15)),
                ("quantity_completed", models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=15)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PLANNED", "Planned"),
                            ("RELEASED", "Released"),
                            ("IN_PROGRESS", "In Progress"),
                            ("COMPLETED", "Completed"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        default="PLANNED",
                        max_length=16,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[("LOW", "Low"), ("NORMAL", "Normal"), ("HIGH", "High"), ("CRITICAL", "Critical")],
                        default="NORMAL",
                        max_length=12,
                    ),
                ),
                ("scheduled_start", models.DateField(blank=True, null=True)),
                ("scheduled_end", models.DateField(blank=True, null=True)),
                ("actual_start", models.DateTimeField(blank=True, null=True)),
                ("actual_end", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "bom",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="work_orders",
                        to="production.billofmaterial",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="companies.company"),
                ),
                (
                    "company_group",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="companies.companygroup"),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="work_orders",
                        to="inventory.product",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "warehouse",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="inventory.warehouse",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
                "unique_together": {("company", "number")},
            },
        ),
        migrations.CreateModel(
            name="ProductionReceipt",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("receipt_number", models.CharField(blank=True, max_length=40)),
                ("receipt_date", models.DateField(default=django.utils.timezone.now)),
                ("quantity_good", models.DecimalField(decimal_places=3, max_digits=15)),
                ("quantity_scrap", models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=15)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "warehouse",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="inventory.warehouse",
                    ),
                ),
                (
                    "work_order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="receipts",
                        to="production.workorder",
                    ),
                ),
            ],
            options={
                "ordering": ("-receipt_date", "-created_at"),
            },
        ),
        migrations.CreateModel(
            name="MaterialIssue",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("issue_number", models.CharField(blank=True, max_length=40)),
                ("issue_date", models.DateField(default=django.utils.timezone.now)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "work_order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="issues",
                        to="production.workorder",
                    ),
                ),
            ],
            options={
                "ordering": ("-issue_date", "-created_at"),
            },
        ),
        migrations.CreateModel(
            name="WorkOrderComponent",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("required_quantity", models.DecimalField(decimal_places=3, max_digits=15)),
                ("issued_quantity", models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=15)),
                ("scrap_percent", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=5)),
                (
                    "component",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="inventory.product"),
                ),
                (
                    "preferred_warehouse",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="inventory.warehouse",
                    ),
                ),
                (
                    "uom",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="inventory.unitofmeasure",
                    ),
                ),
                (
                    "work_order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="components",
                        to="production.workorder",
                    ),
                ),
            ],
            options={
                "ordering": ("component__code",),
            },
        ),
        migrations.CreateModel(
            name="MaterialIssueLine",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=15)),
                (
                    "component",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="issues",
                        to="production.workordercomponent",
                    ),
                ),
                (
                    "issue",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lines",
                        to="production.materialissue",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="inventory.product"),
                ),
                (
                    "warehouse",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="inventory.warehouse",
                    ),
                ),
            ],
            options={
                "ordering": ("issue", "product__code"),
            },
        ),
    ]
