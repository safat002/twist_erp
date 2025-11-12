from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '10017_master_detail_enforcement'),
    ]

    operations = [
        migrations.AddField(
            model_name='movementevent',
            name='movement',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.CASCADE, related_name='movement_events', to='inventory.stockmovement'),
        ),
        migrations.AddField(
            model_name='movementevent',
            name='movement_line',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.CASCADE, related_name='movement_events', to='inventory.stockmovementline'),
        ),
        migrations.AddField(
            model_name='stockledger',
            name='movement_event',
            field=models.OneToOneField(blank=True, null=True, on_delete=models.SET_NULL, related_name='stock_ledger_entry', to='inventory.movementevent'),
        ),
        migrations.AddField(
            model_name='intransitshipmentline',
            name='movement_event',
            field=models.OneToOneField(blank=True, null=True, on_delete=models.SET_NULL, related_name='in_transit_snapshot', to='inventory.movementevent'),
        ),
    ]
