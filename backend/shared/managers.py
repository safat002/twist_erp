from django.db import models

class CompanyQuerySet(models.QuerySet):
    def for_company(self, company):
        """Filter by company"""
        return self.filter(company=company)

    def for_user(self, user):
        """Filter by user's accessible companies"""
        return self.filter(company__in=user.companies.all())

class CompanyManager(models.Manager):
    def get_queryset(self):
        return CompanyQuerySet(self.model, using=self._db)

    def for_company(self, company):
        return self.get_queryset().for_company(company)

    def for_user(self, user):
        return self.get_queryset().for_user(user)
