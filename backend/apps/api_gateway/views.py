from django.http import JsonResponse
from django.urls import reverse


def api_root(request):
    base = request.build_absolute_uri('/')[:-1]
    def url(p):
        return f"{base}{p}"

    return JsonResponse(
        {
            "message": "TWIST ERP API",
            "version": "v1",
            "docs": url(reverse('swagger-ui')),
            "schema": url(reverse('schema')),
            "endpoints": {
                "auth": url('/api/v1/auth/'),
                "companies": url('/api/v1/companies/'),
                "users": url('/api/v1/users/'),
                "forms": url('/api/v1/forms/'),
                "workflows": url('/api/v1/workflows/'),
                "ai": url('/api/v1/ai/'),
                "assets": url('/api/v1/assets/'),
                "budgets": url('/api/v1/budgets/'),
                "hr": url('/api/v1/hr/'),
                "projects": url('/api/v1/projects/'),
            },
        }
    )

