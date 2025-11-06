
from django.test import TestCase
from apps.admin_settings.models import ModuleFeatureToggle
from apps.admin_settings.services import FeatureService
from apps.companies.models import Company, CompanyGroup
from apps.users.models import User

class FeatureServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='testuser')
        self.company_group = CompanyGroup.objects.create(name='Test Group')
        self.company = Company.objects.create(
            name='Test Company',
            code='TC',
            company_group=self.company_group,
            fiscal_year_start='2025-01-01',
            tax_id='123',
            registration_number='123'
        )

        # Create some feature toggles
        ModuleFeatureToggle.objects.create(
            module_name='finance',
            feature_key='module',
            feature_name='Finance',
            is_enabled=True,
            scope_type='GLOBAL'
        )
        ModuleFeatureToggle.objects.create(
            module_name='inventory',
            feature_key='module',
            feature_name='Inventory',
            is_enabled=True,
            scope_type='GLOBAL'
        )
        ModuleFeatureToggle.objects.create(
            module_name='procurement',
            feature_key='module',
            feature_name='Procurement',
            is_enabled=True,
            scope_type='GLOBAL',
            depends_on=['finance.module', 'inventory.module']
        )

    def test_dependents_calculation(self):
        features = FeatureService.get_features_for_company(self.company)

        # Check that 'finance.module' has 'Procurement' as a dependent
        self.assertIn('Procurement', features['finance.module']['dependents'])

        # Check that 'inventory.module' has 'Procurement' as a dependent
        self.assertIn('Procurement', features['inventory.module']['dependents'])

        # Check that 'procurement.module' has no dependents
        self.assertEqual(len(features['procurement.module']['dependents']), 0)
