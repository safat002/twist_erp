from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Company
from .serializers import (
    CompanyGroupSerializer,
    CompanyProvisionSerializer,
    CompanySerializer,
)
from .services.provisioning import CompanyGroupProvisioner, ProvisioningError


class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.companies.filter(is_active=True)

    @action(detail=False, methods=["get"], url_path="active")
    def active(self, request):
        company_id = request.session.get("active_company_id")
        queryset = self.get_queryset()
        company = queryset.filter(id=company_id).first() if company_id else None

        if not company:
            company = queryset.first()
            if company:
                request.session["active_company_id"] = str(company.id)

        if not company:
            return Response(
                {"detail": "No companies available for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(company)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        company = self.get_queryset().filter(id=pk).first()
        if not company:
            return Response(
                {"detail": "Company not found or not assigned to this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        request.session["active_company_id"] = str(company.id)
        serializer = self.get_serializer(company)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ActiveCompanyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = request.user.companies.filter(is_active=True)
        company_id = request.session.get("active_company_id")
        company = queryset.filter(id=company_id).first() if company_id else None

        if not company:
            company = queryset.first()
            if company:
                request.session["active_company_id"] = str(company.id)

        if not company:
            return Response(
                {"detail": "No companies available for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CompanySerializer(company)
        return Response(serializer.data)


class ActivateCompanyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        queryset = request.user.companies.filter(is_active=True)
        company = queryset.filter(id=pk).first()

        if not company:
            return Response(
                {"detail": "Company not found or not assigned to this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        request.session["active_company_id"] = str(company.id)
        serializer = CompanySerializer(company)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CompanyGroupProvisionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CompanyProvisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provisioner = CompanyGroupProvisioner()
        payload = serializer.validated_data
        try:
            result = provisioner.provision(
                group_name=payload["group_name"],
                industry_pack=payload.get("industry_pack_type", ""),
                supports_intercompany=payload.get("supports_intercompany", False),
                default_company_payload=payload.get("company"),
                admin_user=request.user,
            )
        except ProvisioningError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_payload = {
            "company_group": CompanyGroupSerializer(result.company_group).data,
            "company": CompanySerializer(result.company).data,
        }
        return Response(response_payload, status=status.HTTP_201_CREATED)
