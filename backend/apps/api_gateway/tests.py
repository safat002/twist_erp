from rest_framework.test import APITestCase
from rest_framework import status
from apps.companies.models import Company
from apps.users.models import User

class CompanyAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_company_list(self):
        """Test retrieving company list"""
        response = self.client.get('/api/v1/companies/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_company_isolation(self):
        """Test company data isolation"""
        # Create two companies
        company1 = Company.objects.create(
            code='C1', name='Company 1', tax_id='T1', fiscal_year_start='2024-01-01'
        )
        company2 = Company.objects.create(
            code='C2', name='Company 2', tax_id='T2', fiscal_year_start='2024-01-01'
        )
        # User only has access to company1
        self.user.companies.add(company1)

        # Verify they can't access company2 data
        response = self.client.get('/api/v1/companies/')
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['code'], 'C1')
