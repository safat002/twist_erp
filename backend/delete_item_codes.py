import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.budgeting.models import BudgetItemCode

def delete_item_codes():
    """
    Deletes all BudgetItemCode objects from the database.
    """
    print("Deleting all existing BudgetItemCode objects...")
    count, deleted_dict = BudgetItemCode.objects.all().delete()
    print(f"Successfully deleted {count} item codes.")
    if deleted_dict:
        for model, num_deleted in deleted_dict.items():
            print(f"  - {model}: {num_deleted}")

if __name__ == '__main__':
    # WARNING: This script will permanently delete all item codes.
    # Make sure you have a backup if this data is critical.
    confirmation = input("Are you sure you want to delete all item codes? This action cannot be undone. (yes/no): ")
    if confirmation.lower() == 'yes':
        delete_item_codes()
        print('\nAll item codes have been deleted.')
    else:
        print("Operation cancelled.")
