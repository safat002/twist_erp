from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_user_company_groups_user_default_company_group_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="admin_theme",
            field=models.CharField(max_length=20, default="default"),
        ),
    ]

