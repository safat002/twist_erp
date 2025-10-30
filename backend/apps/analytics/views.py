from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CashflowSnapshot, SalesPerformanceSnapshot, WarehouseRunLog
from .serializers import (
    CashflowSnapshotSerializer,
    SalesPerformanceSnapshotSerializer,
)
from .services.etl import get_warehouse_alias, resolve_period, run_warehouse_etl


class SalesPerformanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, 'company', None)
        if not company:
            return Response({'detail': 'Company context missing'}, status=status.HTTP_400_BAD_REQUEST)

        period_param = request.query_params.get('period', '30d')
        pr = resolve_period(period_param)
        warehouse_alias = get_warehouse_alias('default')
        snapshot = (
            SalesPerformanceSnapshot.objects.using(warehouse_alias)
            .filter(company_id=company.id, period=pr.label)
            .order_by('-snapshot_date')
            .first()
        )

        if snapshot is None:
            # Attempt to backfill on-demand for the requested period
            run_warehouse_etl(period=pr.label, companies=[company])
            warehouse_alias = get_warehouse_alias('default')
            snapshot = (
                SalesPerformanceSnapshot.objects.using(warehouse_alias)
                .filter(company_id=company.id, period=pr.label)
                .order_by('-snapshot_date')
                .first()
            )

        if snapshot is None:
            return Response(
                {
                    'detail': 'No analytics data available yet.',
                    'period': pr.label,
                    'company_id': company.id,
                },
                status=status.HTTP_204_NO_CONTENT,
            )

        serializer = SalesPerformanceSnapshotSerializer(snapshot)
        return Response(serializer.data)


class CashflowView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, 'company', None)
        if not company:
            return Response({'detail': 'Company context missing'}, status=status.HTTP_400_BAD_REQUEST)

        period_param = request.query_params.get('period', '30d')
        pr = resolve_period(period_param)
        warehouse_alias = get_warehouse_alias('default')
        snapshot = (
            CashflowSnapshot.objects.using(warehouse_alias)
            .filter(company_id=company.id, period=pr.label)
            .order_by('-snapshot_date')
            .first()
        )

        if snapshot is None:
            run_warehouse_etl(period=pr.label, companies=[company])
            warehouse_alias = get_warehouse_alias('default')
            snapshot = (
                CashflowSnapshot.objects.using(warehouse_alias)
                .filter(company_id=company.id, period=pr.label)
                .order_by('-snapshot_date')
                .first()
            )

        if snapshot is None:
            return Response(
                {
                    'detail': 'No analytics data available yet.',
                    'period': pr.label,
                    'company_id': company.id,
                },
                status=status.HTTP_204_NO_CONTENT,
            )

        serializer = CashflowSnapshotSerializer(snapshot)
        return Response(serializer.data)


class WarehouseStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, 'company', None)
        warehouse_alias = get_warehouse_alias('default')
        logs_qs = WarehouseRunLog.objects.using(warehouse_alias).all().order_by('-run_at')[:20]
        if company:
            logs_qs = logs_qs.filter(company_id=company.id)

        logs = [
            {
                'run_at': log.run_at.isoformat(),
                'status': log.status,
                'company_id': log.company_id,
                'company_code': log.company_code,
                'message': log.message,
                'processed_records': log.processed_records,
                'run_type': log.run_type,
            }
            for log in logs_qs
        ]
        return Response({'logs': logs})
