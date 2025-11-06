"""
API Views for GL Reconciliation
"""

import logging
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated

from apps.finance.services.gl_reconciliation_service import GLReconciliationService
from apps.finance.extra_serializers.reconciliation_serializers import (
    ReconciliationReportSerializer,
    ReconciliationDetailSerializer
)
from apps.inventory.models import Warehouse
from apps.finance.models import Account

logger = logging.getLogger(__name__)


class GLReconciliationViewSet(ViewSet):
    """
    ViewSet for GL Reconciliation operations.

    Provides endpoints for:
    - Running reconciliation checks
    - Generating reconciliation reports
    - Getting detailed account breakdowns
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='report')
    def reconciliation_report(self, request):
        """
        GET /api/finance/gl-reconciliation/report/

        Query params:
        - warehouse_id (optional): Filter by warehouse
        - as_of_date (optional): Date for reconciliation (YYYY-MM-DD)

        Returns comprehensive reconciliation report.
        """
        try:
            company = getattr(request, 'company', None)
            if not company:
                return Response(
                    {'error': 'Company context not set'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get query parameters
            warehouse_id = request.query_params.get('warehouse_id')
            as_of_date = request.query_params.get('as_of_date')

            warehouse = None
            if warehouse_id:
                try:
                    warehouse = Warehouse.objects.get(id=warehouse_id, company=company)
                except Warehouse.DoesNotExist:
                    return Response(
                        {'error': f'Warehouse {warehouse_id} not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

            # Generate report
            report_data = GLReconciliationService.generate_reconciliation_report(
                company=company,
                warehouse=warehouse,
                as_of_date=as_of_date
            )

            serializer = ReconciliationReportSerializer(report_data)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error generating reconciliation report")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='unreconciled')
    def unreconciled_accounts(self, request):
        """
        GET /api/finance/gl-reconciliation/unreconciled/

        Returns list of accounts with reconciliation variances.
        """
        try:
            company = getattr(request, 'company', None)
            if not company:
                return Response(
                    {'error': 'Company context not set'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            unreconciled = GLReconciliationService.get_unreconciled_accounts(company)

            results = [
                {
                    'account_code': r.account_code,
                    'account_name': r.account_name,
                    'gl_balance': float(r.gl_balance),
                    'inventory_value': float(r.inventory_value),
                    'variance': float(r.variance),
                    'variance_percent': float(r.variance_percent),
                }
                for r in unreconciled
            ]

            return Response({
                'count': len(results),
                'accounts': results
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error fetching unreconciled accounts")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='detail')
    def account_detail(self, request, pk=None):
        """
        GET /api/finance/gl-reconciliation/{account_id}/detail/

        Query params:
        - warehouse_id (optional): Filter by warehouse

        Returns detailed breakdown for a specific account.
        """
        try:
            company = getattr(request, 'company', None)
            if not company:
                return Response(
                    {'error': 'Company context not set'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get account
            try:
                account = Account.objects.get(id=pk, company=company)
            except Account.DoesNotExist:
                return Response(
                    {'error': f'Account {pk} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get warehouse filter if provided
            warehouse_id = request.query_params.get('warehouse_id')
            warehouse = None
            if warehouse_id:
                try:
                    warehouse = Warehouse.objects.get(id=warehouse_id, company=company)
                except Warehouse.DoesNotExist:
                    return Response(
                        {'error': f'Warehouse {warehouse_id} not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

            # Get detailed breakdown
            detail_data = GLReconciliationService.get_reconciliation_details(
                company=company,
                account=account,
                warehouse=warehouse
            )

            serializer = ReconciliationDetailSerializer(detail_data)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error fetching account reconciliation detail")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='check')
    def quick_check(self, request):
        """
        POST /api/finance/gl-reconciliation/check/

        Performs a quick reconciliation check and returns summary.
        """
        try:
            company = getattr(request, 'company', None)
            if not company:
                return Response(
                    {'error': 'Company context not set'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            results = GLReconciliationService.reconcile_inventory_accounts(company)

            total_variance = sum(abs(r.variance) for r in results)
            unreconciled_count = sum(1 for r in results if not r.is_reconciled)

            return Response({
                'status': 'reconciled' if unreconciled_count == 0 else 'variance_detected',
                'accounts_checked': len(results),
                'accounts_reconciled': len(results) - unreconciled_count,
                'accounts_with_variance': unreconciled_count,
                'total_variance_amount': float(total_variance),
                'message': 'All accounts reconciled' if unreconciled_count == 0 else f'{unreconciled_count} accounts have variances'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error performing quick reconciliation check")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
