from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0014_stockmovementline_expiry"),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='prevent_expired_issuance',
            field=models.BooleanField(default=True, help_text='Block issuing expired stock (when expiry is tracked)'),
        ),
        migrations.AddField(
            model_name='product',
            name='expiry_warning_days',
            field=models.PositiveIntegerField(default=0, help_text='Warn when stock will expire within N days'),
        ),
    ]

