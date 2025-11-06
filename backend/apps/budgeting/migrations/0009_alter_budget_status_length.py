from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("budgeting", "0008_budget_approval_and_entry_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="budget",
            name="status",
            field=models.CharField(max_length=32, choices=[
                ("DRAFT", "Draft"),
                ("ENTRY_OPEN", "Entry Open"),
                ("PENDING_CC_APPROVAL", "Pending CC Approval"),
                ("CC_APPROVED", "CC Approved"),
                ("PENDING_FINAL_APPROVAL", "Pending Final Approval"),
                ("APPROVED", "Approved"),
                ("ACTIVE", "Active"),
                ("EXPIRED", "Expired"),
                ("CLOSED", "Closed"),
            ]),
        ),
    ]

