from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.exceptions import PermissionDenied
from apps.companies.models import Company, CompanyGroup, Branch, Department


def get_current_company(request):
    """
    Helper function to get the current company from the request.

    Args:
        request: Django request object

    Returns:
        Company instance or None
    """
    return getattr(request, 'company', None)


def get_current_company_group(request):
    """
    Helper function to get the current company group from the request.

    Args:
        request: Django request object

    Returns:
        CompanyGroup instance or None
    """
    return getattr(request, 'company_group', None)


def get_current_branch(request):
    """
    Helper function to get the current branch from the request.

    Args:
        request: Django request object

    Returns:
        Branch instance or None
    """
    return getattr(request, 'current_branch', None)


def get_current_department(request):
    """
    Helper function to get the current department from the request.

    Args:
        request: Django request object

    Returns:
        Department instance or None
    """
    return getattr(request, 'current_department', None)


class CompanyContextMiddleware(MiddlewareMixin):
    """
    Automatically injects full organizational hierarchy context into requests:
    - Company Group
    - Company
    - Branch (optional)
    - Department (optional)

    Based on user session, headers, or user's default organizational access.
    """
    def process_request(self, request):
        # Initialize organizational context
        self._init_context(request)

        if request.user.is_authenticated:
            # Extract context from headers or session
            context_ids = self._extract_context_ids(request)

            # Validate and set organizational context
            self._set_organizational_context(request, context_ids)
        else:
            # Anonymous users get no organizational context
            self._clear_context(request)

    def _init_context(self, request):
        """Initialize all organizational context variables."""
        settings.CURRENT_COMPANY_GROUP = None
        settings.CURRENT_COMPANY_GROUP_ID = None
        settings.CURRENT_COMPANY = None
        settings.CURRENT_COMPANY_ID = None
        settings.CURRENT_BRANCH = None
        settings.CURRENT_BRANCH_ID = None
        settings.CURRENT_DEPARTMENT = None
        settings.CURRENT_DEPARTMENT_ID = None

    def _clear_context(self, request):
        """Clear all organizational context."""
        request.company_group = None
        request.company = None
        request.current_branch = None
        request.current_department = None

        settings.CURRENT_COMPANY_GROUP = None
        settings.CURRENT_COMPANY_GROUP_ID = None
        settings.CURRENT_COMPANY = None
        settings.CURRENT_COMPANY_ID = None
        settings.CURRENT_BRANCH = None
        settings.CURRENT_BRANCH_ID = None
        settings.CURRENT_DEPARTMENT = None
        settings.CURRENT_DEPARTMENT_ID = None

    def _extract_context_ids(self, request):
        """Extract organizational context IDs from headers or session."""
        # Priority: Headers > Session > User defaults
        context = {
            'company_group_id': (
                request.META.get('HTTP_X_COMPANY_GROUP_ID') or
                request.session.get('active_company_group_id')
            ),
            'company_id': (
                request.META.get('HTTP_X_COMPANY_ID') or
                request.session.get('active_company_id')
            ),
            'branch_id': (
                request.META.get('HTTP_X_BRANCH_ID') or
                request.session.get('active_branch_id')
            ),
            'department_id': (
                request.META.get('HTTP_X_DEPARTMENT_ID') or
                request.session.get('active_department_id')
            ),
        }
        return context

    def _set_organizational_context(self, request, context_ids):
        """Validate and set the full organizational hierarchy."""
        user = request.user

        # Get user's organizational access if it exists
        try:
            org_access = user.org_access
        except:
            org_access = None

        # 1. Set Company Group
        company_group = self._set_company_group(
            request, context_ids.get('company_group_id'), org_access
        )

        # if not company_group:
        #     self._clear_context(request)
        #     return

        # 2. Set Company (must belong to the group)
        company = self._set_company(
            request, context_ids.get('company_id'), company_group, org_access
        )

        if not company:
            return

        # 3. Set Branch (optional, must belong to company)
        branch = self._set_branch(
            request, context_ids.get('branch_id'), company, org_access
        )

        # 4. Set Department (optional, must belong to company/branch)
        self._set_department(
            request, context_ids.get('department_id'), company, branch, org_access
        )

    def _set_company_group(self, request, group_id, org_access):
        """Set company group context."""
        if not group_id:
            # Fall back to user's primary group
            if org_access and org_access.primary_group:
                group_id = org_access.primary_group_id
            elif request.user.company_groups.filter(is_active=True).exists():
                group_id = request.user.company_groups.filter(is_active=True).first().id

        if group_id:
            try:
                company_group = CompanyGroup.objects.get(id=group_id, is_active=True)

                # Validate user has access
                if org_access:
                    if not org_access.access_groups.filter(id=company_group.id).exists():
                        company_group = None
                
                if company_group and not request.user.company_groups.filter(id=company_group.id).exists():
                    company_group = None

                if company_group:
                    request.company_group = company_group
                    settings.CURRENT_COMPANY_GROUP = company_group
                    settings.CURRENT_COMPANY_GROUP_ID = company_group.id
                    request.session['active_company_group_id'] = str(company_group.id)
                    return company_group
            except CompanyGroup.DoesNotExist:
                pass
        
        return None

    def _set_company(self, request, company_id, company_group, org_access):
        """Set company context."""
        if not company_id:
            # Fall back to user's primary company in this group
            if org_access and org_access.primary_company and company_group and org_access.primary_company.company_group_id == company_group.id:
                company_id = org_access.primary_company_id
            elif company_group:
                # Get user's first accessible company in this group
                accessible_companies = request.user.companies.filter(
                    company_group=company_group,
                    is_active=True
                )
                if accessible_companies.exists():
                    company_id = accessible_companies.first().id

        if company_id:
            try:
                company = Company.objects.get(
                    id=company_id,
                    is_active=True
                )
                if company_group and company.company_group != company_group:
                    return None

                # Validate user has access
                if not request.user.companies.filter(id=company.id).exists():
                    if org_access and not org_access.access_companies.filter(id=company.id).exists():
                        return None

                request.company = company
                settings.CURRENT_COMPANY = company
                settings.CURRENT_COMPANY_ID = company.id
                request.session['active_company_id'] = str(company.id)
                
                # After setting company, also set company_group from the company object if it wasn't set before
                if not getattr(request, 'company_group', None) and company.company_group:
                    request.company_group = company.company_group
                    settings.CURRENT_COMPANY_GROUP = company.company_group
                    settings.CURRENT_COMPANY_GROUP_ID = company.company_group.id
                    request.session['active_company_group_id'] = str(company.company_group.id)

                return company
            except Company.DoesNotExist:
                pass

        return None

    def _set_branch(self, request, branch_id, company, org_access):
        """Set branch context (optional)."""
        if not branch_id:
            # Fall back to user's primary branch if it belongs to this company
            if org_access and org_access.primary_branch and org_access.primary_branch.company_id == company.id:
                branch_id = org_access.primary_branch_id

        if branch_id:
            try:
                branch = Branch.objects.get(
                    id=branch_id,
                    company=company,
                    is_active=True
                )

                # Validate user has access (if org_access is used)
                if org_access and org_access.access_branches.exists():
                    if not org_access.access_branches.filter(id=branch.id).exists():
                        return None

                request.current_branch = branch
                settings.CURRENT_BRANCH = branch
                settings.CURRENT_BRANCH_ID = branch.id
                request.session['active_branch_id'] = str(branch.id)
                return branch
            except Branch.DoesNotExist:
                pass

        return None

    def _set_department(self, request, dept_id, company, branch, org_access):
        """Set department context (optional)."""
        if not dept_id:
            # Fall back to user's primary department
            if org_access and org_access.primary_department and org_access.primary_department.company_id == company.id:
                dept_id = org_access.primary_department_id

        if dept_id:
            try:
                department = Department.objects.get(
                    id=dept_id,
                    company=company,
                    is_active=True
                )

                # Validate department matches branch if branch is set
                if branch and department.branch_id != branch.id:
                    return None

                # Validate user has access
                if org_access and org_access.access_departments.exists():
                    if not org_access.access_departments.filter(id=department.id).exists():
                        return None

                request.current_department = department
                settings.CURRENT_DEPARTMENT = department
                settings.CURRENT_DEPARTMENT_ID = department.id
                request.session['active_department_id'] = str(department.id)
                return department
            except Department.DoesNotExist:
                pass

        return None
