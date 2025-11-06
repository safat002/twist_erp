from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0001_initial"),
        ("metadata", "0003_alter_metadatadefinition_kind"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentSequence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("doc_type", models.CharField(help_text="Short document code, e.g., PO, PR, DO, GRN, JV", max_length=20)),
                ("fiscal_year", models.CharField(help_text="Fiscal year or period key, e.g., 2025 or 25", max_length=10)),
                ("current_value", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="document_sequences", to="companies.company")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["company", "doc_type", "fiscal_year"], name="metadata_docseq_idx"),
                ],
                "unique_together": {("company", "doc_type", "fiscal_year")},
            },
        ),
    ]

