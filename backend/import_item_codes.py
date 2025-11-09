import csv
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.budgeting.models import BudgetItemCode, BudgetItemCategory, BudgetItemSubCategory
from apps.companies.models import CompanyGroup, Company

def get_next_item_code(group):
    prefix = "IC-"
    last_code = BudgetItemCode.objects.filter(company_group=group, code__startswith=prefix).order_by('code').last()
    if last_code:
        try:
            last_number = int(last_code.code.split('-')[1])
            new_number = last_number + 1
        except (IndexError, ValueError):
            # Fallback if the last code is not in the expected format
            new_number = (BudgetItemCode.objects.filter(company_group=group, code__startswith=prefix).count() or 0) + 1
    else:
        new_number = 1
    return f"{prefix}{new_number:06d}"

def import_item_codes(file_path, group_id):
    try:
        group = CompanyGroup.objects.get(id=group_id)
    except CompanyGroup.DoesNotExist:
        print(f"CompanyGroup with id {group_id} not found.")
        return

    # Get a default company from the group to satisfy the model's company field
    company = Company.objects.filter(company_group=group).first()
    if not company:
        print(f"No companies found for group {group.name}. Please add a company to the group first.")
        return

    with open(file_path, 'r', encoding='latin-1') as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header row

        for row in reader:
            item_name, category_name, sub_category_name = row

            # Get or create category
            category, _ = BudgetItemCategory.objects.get_or_create(
                name=category_name.strip(),
                company_group=group,
                defaults={'code': category_name.strip().upper()[:10], 'company': company}
            )

            # Get or create sub-category
            sub_category, _ = BudgetItemSubCategory.objects.get_or_create(
                name=sub_category_name.strip(),
                category=category,
                company_group=group,
                defaults={'code': sub_category_name.strip().upper()[:10], 'company': company}
            )

            # Check if item with the same name already exists for the group
            item_code, created = BudgetItemCode.objects.get_or_create(
                name=item_name.strip(),
                company_group=group,
                defaults={
                    'category_ref': category,
                    'sub_category_ref': sub_category,
                    'company': company,
                    'code': get_next_item_code(group)
                }
            )
            if created:
                print(f"Created item code: {item_code.code} - {item_code.name}")
            else:
                print(f"Item code already exists: {item_code.name} ({item_code.code})")

if __name__ == '__main__':
    # IMPORTANT: Replace 1 with the ID of the company group you want to associate these item codes with.
    # You can find the company group ID in the admin panel or by querying the CompanyGroup model.
    COMPANY_GROUP_ID = 1
    
    # The path to the CSV file is relative to the project root directory
    file_path = 'other files/itemcode_test.csv'
    
    import_item_codes(file_path, COMPANY_GROUP_ID)
    print('Item codes import process finished.')