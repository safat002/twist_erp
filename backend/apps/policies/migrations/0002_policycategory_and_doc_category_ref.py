from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("policies", "0001_initial"),
    ]

    operations = [
        # Avoid recreating the table if it already exists in some databases.
        # We still update the state so Django is aware of the model definition.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="PolicyCategory",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("code", models.CharField(max_length=32, unique=True)),
                        ("name", models.CharField(max_length=100)),
                        ("is_active", models.BooleanField(default=True)),
                    ],
                    options={"ordering": ["code"]},
                ),
            ],
            database_operations=[],
        ),
        # Add the foreign key only to the migration state; the column may already
        # exist on some databases, so we skip database operations here.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="policydocument",
                    name="category_ref",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="policies",
                        to="policies.policycategory",
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
