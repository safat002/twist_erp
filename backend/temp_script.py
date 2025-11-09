import os
import django
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.budgeting.models import Budget, CostCenter

try:
    budget = Budget.objects.get(id=14)
    cost_center = CostCenter.objects.get(id=5)
    budget.cost_center = cost_center
    budget.save()
    print('Successfully updated Budget 14 with Cost Center 5')
except ObjectDoesNotExist:
    print('Budget with ID 14 or Cost Center with ID 5 does not exist.')