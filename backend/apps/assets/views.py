from datetime import date, timedelta
from django.utils import timezone

from django.db.models import Count, Q, Sum
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.models import Company
from .models import Asset, AssetMaintenancePlan, DepreciationRun, DowntimeLog, AssetDisposal
from .serializers import (
    AssetRegisterSerializer,
    AssetSerializer,
    MaintenanceTaskSerializer,
    DepreciationRunSerializer,
    DowntimeLogSerializer,
    AssetDisposalSerializer,
    EmployeeAssetAssignmentSerializer,
)


def _resolve_company(request):
    company = getattr(request, "company", None)
    if company:
        return company
    if request.user and request.user.is_authenticated:
        company = request.user.companies.filter(is_active=True).first()
        if company:
            return company
    return Company.objects.filter(is_active=True).first()


class AssetListCreateView(generics.ListCreateAPIView):
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        company = _resolve_company(self.request)
        qs = Asset.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs


class AssetDetailView(generics.RetrieveAPIView):
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        company = _resolve_company(self.request)
        qs = Asset.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs


class AssetRegisterView(generics.ListAPIView):
    serializer_class = AssetRegisterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        company = _resolve_company(self.request)
        qs = (
            Asset.objects.select_related("company")
            .prefetch_related("maintenance_tasks")
        )
        if company:
            qs = qs.filter(company=company)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__iexact=category)
        return qs


class AssetOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = _resolve_company(request)
        if not company:
            return Response(
                {
                    "totals": {"count": 0, "book_value": 0, "depreciation": 0},
                    "by_category": [],
                    "maintenance_alerts": [],
                },
                status=status.HTTP_200_OK,
            )

        qs = Asset.objects.filter(company=company)
        summary = qs.aggregate(
            count=Count("id"),
            cost=Sum("cost"),
            residual=Sum("residual_value"),
        )

        by_category = (
            qs.exclude(category="")
            .values("category")
            .annotate(total=Count("id"), value=Sum("cost"))
            .order_by("-value")
        )

        today = date.today()
        alerts = list(
            AssetMaintenancePlan.objects.filter(
                company=company,
                status__in=[AssetMaintenancePlan.STATUS_PLANNED, AssetMaintenancePlan.STATUS_IN_PROGRESS],
                due_date__lte=today + timedelta(days=30),
            )
            .select_related("asset")
            .order_by("due_date")[:10]
        )

        total_cost = summary.get("cost") or 0
        active_assets = qs.filter(status=Asset.STATUS_ACTIVE).count()
        maintenance_backlog = AssetMaintenancePlan.objects.filter(
            company=company,
            status__in=[AssetMaintenancePlan.STATUS_PLANNED, AssetMaintenancePlan.STATUS_IN_PROGRESS],
        ).count()
        utilization_rate = int(
            round((active_assets / summary.get("count", 1)) * 100)
        ) if summary.get("count") else 0

        upcoming_schedule = list(
            AssetMaintenancePlan.objects.filter(
                company=company,
                status__in=[AssetMaintenancePlan.STATUS_PLANNED, AssetMaintenancePlan.STATUS_IN_PROGRESS],
                scheduled_date__gte=today,
            )
            .select_related("asset")
            .order_by("scheduled_date")[:6]
        )

        payload = {
            "totals": {
                "count": summary.get("count") or 0,
                "book_value": float(summary.get("cost") or 0),
                "depreciation": float((summary.get("cost") or 0) - (summary.get("residual") or 0)),
            },
            "by_category": [
                {
                    "category": item["category"] or "Uncategorised",
                    "count": item["total"] or 0,
                    "value": float(item["value"] or 0),
                }
                for item in by_category
            ],
            "maintenance_alerts": [
                {
                    "id": alert.id,
                    "asset": alert.asset.code,
                    "title": alert.title,
                    "due_date": alert.due_date,
                    "status": alert.status,
                }
                for alert in alerts
            ],
        }
        payload["kpis"] = [
            {
                "key": "book_value",
                "label": "Book Value",
                "value": float(summary.get("cost") or 0),
                "suffix": "BDT",
                "trend": 0,
            },
            {
                "key": "active_assets",
                "label": "Active Assets",
                "value": active_assets,
                "suffix": "",
                "trend": 0,
            },
            {
                "key": "utilization",
                "label": "Utilisation Rate",
                "value": utilization_rate,
                "suffix": "%",
                "trend": 0,
            },
            {
                "key": "maintenance_backlog",
                "label": "Maintenance Backlog",
                "value": maintenance_backlog,
                "suffix": "Jobs",
                "trend": 0,
            },
        ]
        payload["utilization"] = [
            {
                "category": item["category"] or "Uncategorised",
                "value": round((item["value"] or 0) / total_cost * 100, 1) if total_cost else 0,
            }
            for item in by_category
        ]
        payload["maintenance_schedule"] = [
            {
                "id": f"maint-{task.id}",
                "asset": f"{task.asset.name}",
                "window": task.scheduled_date.strftime("%d %b"),
                "supervisor": task.assigned_to or "Unassigned",
                "tasks": [task.title],
            }
            for task in upcoming_schedule
        ]
        payload["alerts"] = payload["maintenance_alerts"]
        payload["automations"] = []
        payload["depreciation_trend"] = []

        return Response(payload)


class MaintenancePlanListCreateView(generics.ListCreateAPIView):
    serializer_class = MaintenanceTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        company = _resolve_company(self.request)
        qs = AssetMaintenancePlan.objects.select_related("asset", "company")
        if company:
            qs = qs.filter(company=company)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        period = self.request.query_params.get("period")
        today = date.today()
        if period == "upcoming":
            qs = qs.filter(
                status__in=[AssetMaintenancePlan.STATUS_PLANNED, AssetMaintenancePlan.STATUS_IN_PROGRESS],
                scheduled_date__gte=today,
            )
        elif period == "overdue":
            qs = qs.filter(
                status__in=[AssetMaintenancePlan.STATUS_PLANNED, AssetMaintenancePlan.STATUS_IN_PROGRESS],
                due_date__lt=today,
            )
        return qs.order_by("scheduled_date")


class MaintenancePlanDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = MaintenanceTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        company = _resolve_company(self.request)
        qs = AssetMaintenancePlan.objects.select_related("asset", "company")
        if company:
            qs = qs.filter(company=company)
        return qs


class MaintenanceSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = _resolve_company(request)
        if not company:
            return Response(
                {
                    "overdue": 0,
                    "this_month": 0,
                    "completed": 0,
                    "total": 0,
                },
                status=status.HTTP_200_OK,
            )

        qs = AssetMaintenancePlan.objects.filter(company=company)
        today = date.today()
        start_of_month = today.replace(day=1)

        end_of_month = start_of_month + timedelta(days=32)
        end_of_month = end_of_month.replace(day=1) - timedelta(days=1)

        summary = {
            "overdue": qs.filter(
                status__in=[AssetMaintenancePlan.STATUS_PLANNED, AssetMaintenancePlan.STATUS_IN_PROGRESS],
                due_date__lt=today,
            ).count(),
            "this_month": qs.filter(
                scheduled_date__gte=start_of_month,
                scheduled_date__lte=end_of_month,
            ).count(),
            "completed": qs.filter(status=AssetMaintenancePlan.STATUS_COMPLETED).count(),
            "total": qs.count(),
        }
        return Response(summary)


class DepreciationRunListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DepreciationRunSerializer

    def get_queryset(self):
        company = _resolve_company(self.request)
        qs = DepreciationRun.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs

    def create(self, request, *args, **kwargs):
        company = _resolve_company(request)
        if not company:
            return Response({"detail": "Active company context required."}, status=400)
        year = int(request.data.get("year") or timezone.now().year)
        month = int(request.data.get("month") or timezone.now().month)
        run = DepreciationRun.run_for_month(company=company, year=year, month=month, user=request.user)
        serializer = self.get_serializer(run)
        return Response(serializer.data, status=status.HTTP_201_CREATED if run.total_amount else status.HTTP_200_OK)


class DowntimeLogListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DowntimeLogSerializer

    def get_queryset(self):
        company = _resolve_company(self.request)
        qs = DowntimeLog.objects.select_related("asset").all()
        if company:
            qs = qs.filter(company=company)
        asset_id = self.request.query_params.get("asset")
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        return qs

    def perform_create(self, serializer):
        company = _resolve_company(self.request)
        if not company:
            raise ValueError("Active company context is required")
        serializer.save(company=company)


class AssetDisposalListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AssetDisposalSerializer

    def get_queryset(self):
        company = _resolve_company(self.request)
        qs = AssetDisposal.objects.select_related("asset", "company", "voucher").all()
        if company:
            qs = qs.filter(company=company)
        return qs


class AssetDisposalDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AssetDisposalSerializer

    def get_queryset(self):
        company = _resolve_company(self.request)
        qs = AssetDisposal.objects.select_related("asset", "company", "voucher")
        if company:
            qs = qs.filter(company=company)
        return qs


class AssetDisposalApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        company = _resolve_company(request)
        disposal = AssetDisposal.objects.select_related("asset", "company").get(pk=pk)
        if company and disposal.company_id != company.id:
            return Response({"detail": "Disposal not in active company."}, status=403)
        try:
            voucher = disposal.post_to_finance(user=request.user)
            return Response({"status": disposal.status, "voucher_id": voucher.id})
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)


class EmployeeAssetAssignmentListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmployeeAssetAssignmentSerializer

    def get_queryset(self):
        from apps.hr.models import EmployeeAssetAssignment
        company = _resolve_company(self.request)
        qs = EmployeeAssetAssignment.objects.select_related("employee")
        if company:
            qs = qs.filter(company=company)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        employee_id = self.request.query_params.get("employee")
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        return qs.order_by("-assignment_date")
