from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from apps.companies.models import Company, CompanyGroup

class CompanyContextMiddleware(MiddlewareMixin):
    """
    Automatically injects company and company group context into requests
    based on user session or header, and sets context for dynamic database routing.
    """
    def process_request(self, request):
        # Initialize CURRENT_COMPANY and CURRENT_COMPANY_GROUP to None for each request
        settings.CURRENT_COMPANY = None
        settings.CURRENT_COMPANY_GROUP = None
        settings.CURRENT_COMPANY_ID = None
        settings.CURRENT_COMPANY_GROUP_ID = None

        if request.user.is_authenticated:
            # Get company group from session or user default
            company_group_id = request.session.get('active_company_group_id')
            company_id = request.session.get('active_company_id')

            if not company_group_id:
                user_company_groups = request.user.company_groups.filter(status='active')
                if user_company_groups.exists():
                    company_group_id = user_company_groups.first().id
                    request.session['active_company_group_id'] = company_group_id

            if company_group_id:
                try:
                    company_group = CompanyGroup.objects.get(
                        id=company_group_id,
                        status='active'
                    )
                    request.company_group = company_group
                    settings.CURRENT_COMPANY_GROUP = company_group
                    settings.CURRENT_COMPANY_GROUP_ID = company_group.id

                    # Now try to get company within this group
                    if not company_id:
                        user_companies_in_group = request.user.companies.filter(
                            company_group=company_group,
                            is_active=True
                        )
                        if user_companies_in_group.exists():
                            company_id = user_companies_in_group.first().id
                            request.session['active_company_id'] = company_id

                    if company_id:
                        company = Company.objects.get(
                            id=company_id,
                            company_group=company_group,
                            is_active=True
                        )
                        request.company = company
                        settings.CURRENT_COMPANY = company
                        settings.CURRENT_COMPANY_ID = company.id
                    else:
                        request.company = None
                        settings.CURRENT_COMPANY = None
                        settings.CURRENT_COMPANY_ID = None

                except CompanyGroup.DoesNotExist:
                    request.company_group = None
                    settings.CURRENT_COMPANY_GROUP = None
                    settings.CURRENT_COMPANY_GROUP_ID = None
                    request.company = None
                    settings.CURRENT_COMPANY = None
                    settings.CURRENT_COMPANY_ID = None
            else:
                request.company_group = None
                settings.CURRENT_COMPANY_GROUP = None
                settings.CURRENT_COMPANY_GROUP_ID = None
                request.company = None
                settings.CURRENT_COMPANY = None
                settings.CURRENT_COMPANY_ID = None
        else:
            request.company_group = None
            settings.CURRENT_COMPANY_GROUP = None
            settings.CURRENT_COMPANY_GROUP_ID = None
            request.company = None
            settings.CURRENT_COMPANY = None
            settings.CURRENT_COMPANY_ID = None