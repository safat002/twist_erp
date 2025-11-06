from rest_framework import generics, permissions
from rest_framework.response import Response
from .models import Role


class RoleListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Role.objects.all().order_by('name')
        company_id = self.request.query_params.get('company')
        scope = (self.request.query_params.get('scope') or '').lower()
        if company_id:
            qs = qs.filter(company_id=company_id)
        elif scope == 'global':
            qs = qs.filter(company__isnull=True)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        data = [
            {
                'id': r.id,
                'name': r.name,
                'company': r.company_id,
                'is_system_role': r.is_system_role,
                'description': r.description,
            }
            for r in qs
        ]
        return Response({'results': data})

