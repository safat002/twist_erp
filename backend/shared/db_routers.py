from django.conf import settings
from apps.companies.models import CompanyGroup

class SystemDatabaseRouter:
    """
    A router to control all database operations for models that belong to the
    core system (e.g., authentication, permissions, company management).
    These models should always reside in the 'default' database (twist_system).
    """
    route_app_labels = {
        'admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles',
        'users', 'companies', 'shared', 'permissions', # Core system apps
    }

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'default'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'default'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (
            obj1._meta.app_label in self.route_app_labels or
            obj2._meta.app_label in self.route_app_labels
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == 'default'
        return None


class CompanyGroupDatabaseRouter:
    """
    A router to control all database operations for models that are
    company-aware and belong to a specific CompanyGroup database.
    """
    route_app_labels = {
        'finance', 'inventory', 'sales', 'form_builder', 'workflows', 'assets',
        'budgeting', 'hr', 'projects', 'procurement', 'quality', 'analytics', 'ai_companion', # CompanyGroup-aware apps
    }

    def _get_db_for_company_group(self):
        current_company_group_id = getattr(settings, 'CURRENT_COMPANY_GROUP_ID', None)
        if current_company_group_id:
            try:
                company_group = CompanyGroup.objects.get(id=current_company_group_id)
                return company_group.db_name
            except CompanyGroup.DoesNotExist:
                pass
        return None

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            db_name = self._get_db_for_company_group()
            if db_name:
                return db_name
            return 'default' # Fallback to default if no company group context
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            db_name = self._get_db_for_company_group()
            if db_name:
                return db_name
            return 'default' # Fallback to default if no company group context
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations between any models if they are both in the same database
        # or if one is a system app and the other is a company app (handled by SystemDatabaseRouter)
        if (
            obj1._meta.app_label in self.route_app_labels or
            obj2._meta.app_label in self.route_app_labels
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            db_name = self._get_db_for_company_group()
            if db_name:
                return db == db_name
            return db == 'default' # If no company group context, migrate to default
        return None
