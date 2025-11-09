import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.companies.models import CompanyGroup

def get_group_db_name(group_code):
    try:
        group = CompanyGroup.objects.get(code=group_code)
        print(f"The db_name for group '{group_code}' is: {group.db_name}")
    except CompanyGroup.DoesNotExist:
        print(f"CompanyGroup with code '{group_code}' not found.")

if __name__ == '__main__':
    group_code = 'group-1'
    get_group_db_name(group_code)
