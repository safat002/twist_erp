import os
import django
import random
from decimal import Decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.budgeting.models import BudgetItemCode
from apps.inventory.models import UnitOfMeasure

def update_item_codes():
    uoms = list(UnitOfMeasure.objects.all())
    if not uoms:
        print("No UnitOfMeasure objects found. Please create some first.")
        # As a fallback, let's create a default 'EA' uom if none exist
        from apps.companies.models import Company
        company = Company.objects.first()
        if company:
            print("Creating a default 'EA' (Each) Unit of Measure.")
            uom, created = UnitOfMeasure.objects.get_or_create(
                code='EA',
                company=company,
                defaults={'name': 'Each'}
            )
            if created:
                print("Default UOM created.")
            uoms.append(uom)
        else:
            print("Cannot create a default UOM without a company. Aborting.")
            return

    item_codes = BudgetItemCode.objects.filter(uom__isnull=True)
    print(f"Found {item_codes.count()} item codes to update.")

    for item_code in item_codes:
        # Update uom
        item_code.uom = random.choice(uoms)

        # Update standard_price
        item_code.standard_price = Decimal(random.uniform(1, 1000)).quantize(Decimal('0.01'))

        item_code.save(update_fields=['uom', 'standard_price'])
        print(f"Updated item code: {item_code.name} with UOM '{item_code.uom.code}' and Price '{item_code.standard_price}'")

if __name__ == '__main__':
    update_item_codes()
    print('\nItem codes update process finished.')
