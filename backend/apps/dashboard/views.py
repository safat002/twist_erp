from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.models import Company
from apps.permissions.drf_permissions import HasPermission
from .models import DashboardDefinition, DashboardLayout
from .serializers import DashboardDefinitionSerializer, DashboardLayoutSerializer
from .services import load_dashboard, save_layout


class DashboardDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, 'company', None)
        if not company:
            company = request.user.companies.filter(is_active=True).first()
        if not company:
            company = Company.objects.filter(is_active=True).first()
        if not company:
            return Response(
                {
                    'period': request.query_params.get('period', '30d'),
                    'widgets': [],
                    'available_widgets': [],
                    'layout': {},
                    'currency': 'BDT',
                },
                status=status.HTTP_200_OK,
            )

        period = request.query_params.get('period', '30d')
        payload = load_dashboard(request.user, company, period=period)
        return Response(payload)


class DashboardLayoutView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, 'company', None)
        if not company:
            company = request.user.companies.filter(is_active=True).first()
        if not company:
            company = Company.objects.filter(is_active=True).first()
        if not company:
            return Response({'detail': 'No companies configured'}, status=status.HTTP_200_OK)

        layout = DashboardLayout.objects.filter(user=request.user, company=company).first()
        if not layout:
            layout = save_layout(request.user, company, layout=None, widgets=None)
        serializer = DashboardLayoutSerializer(layout)
        return Response(serializer.data)

    def put(self, request):
        company = getattr(request, 'company', None)
        if not company:
            company = request.user.companies.filter(is_active=True).first()
        if not company:
            company = Company.objects.filter(is_active=True).first()
        if not company:
            return Response({'detail': 'No companies configured'}, status=status.HTTP_400_BAD_REQUEST)

        layout_payload = request.data.get('layout')
        widgets_payload = request.data.get('widgets')
        layout = save_layout(request.user, company, layout=layout_payload, widgets=widgets_payload)
        serializer = DashboardLayoutSerializer(layout)
        return Response(serializer.data)


class DashboardDefinitionListCreateView(generics.ListCreateAPIView):
    serializer_class = DashboardDefinitionSerializer
    permission_classes = [IsAuthenticated, HasPermission]
    permission_code = "can_build_dashboards"

    def get_queryset(self):
        company = getattr(self.request, 'company', None)
        qs = DashboardDefinition.objects.all().select_related('metadata')
        if company:
            qs = qs.filter(
                Q(scope_type="GLOBAL")
                | Q(scope_type="GROUP", company_group=company.company_group)
                | Q(scope_type="COMPANY", company=company)
            )
        return qs
