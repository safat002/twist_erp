from rest_framework.permissions import BasePermission
from .permissions import has_permission

class HasPermission(BasePermission):
    """
    Custom DRF permission class that integrates with the ERP's role-based
    access control system.

    To use this, add it to the `permission_classes` list on a DRF view
    and define a `permission_code` attribute on that view.

    Example:
        class SalesOrderListView(generics.ListAPIView):
            queryset = SalesOrder.objects.all()
            serializer_class = SalesOrderSerializer
            permission_classes = [IsAuthenticated, HasPermission]
            permission_code = 'sales.view_order' # This is the required permission
    """

    def has_permission(self, request, view):
        """
        Checks for the `permission_code` attribute on the view and validates
        it against the user's roles within the active company context.
        """
        permission_code = getattr(view, 'permission_code', None)
        if not permission_code:
            # For security, we deny access if a view using this class doesn't
            # explicitly state which permission is required. This prevents accidental
            # exposure of endpoints.
            return False

        # The active company context is expected to be set on the request object
        # by a middleware (e.g., CompanyContextMiddleware).
        company = getattr(request, 'company', None)
        if not company:
            # A company context is required for all permission checks.
            return False

        # Delegate the actual logic to the central permission checking service.
        return has_permission(request.user, permission_code, company)
