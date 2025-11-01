from apps.security.services.permission_service import PermissionService

class PermissionContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Attach effective permissions to the request.user object
            # This will be lazy-loaded or cached by the PermissionService
            request.user.effective_permissions = PermissionService.get_user_effective_permissions(request.user)
        else:
            # Ensure effective_permissions attribute exists even for anonymous users
            if hasattr(request, 'user'):
                request.user.effective_permissions = {}

        response = self.get_response(request)
        return response
