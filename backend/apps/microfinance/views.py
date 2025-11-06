from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum, F
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Borrower, LoanProduct, Loan, LoanRepayment, LoanRepaymentSchedule
from .serializers import (
    BorrowerSerializer,
    LoanProductSerializer,
    LoanSerializer,
    LoanRepaymentSerializer,
    LoanRepaymentScheduleSerializer,
)
from apps.permissions.permissions import has_permission


class CompanyScopedQuerysetMixin:
    permission_classes = [IsAuthenticated]

    def get_company(self):
        return getattr(self.request, 'company', None)

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset()
        company = self.get_company()
        if company and hasattr(qs.model, 'company_id'):
            qs = qs.filter(company=company)
        return qs

    def get_serializer_context(self):  # type: ignore[override]
        ctx = super().get_serializer_context()
        ctx.setdefault('request', self.request)
        return ctx


class BorrowerViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Borrower.objects.all().order_by('name')
    serializer_class = BorrowerSerializer

    def _require(self, code: str):
        company = self.get_company()
        if not has_permission(self.request.user, code, company):
            return Response({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)
        return None

    def perform_create(self, serializer):
        denied = self._require("microfinance.create_loan")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        serializer.save()

    def perform_update(self, serializer):
        denied = self._require("microfinance.update_loan")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        serializer.save()

    def perform_destroy(self, instance):
        denied = self._require("microfinance.delete_loan")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        instance.delete()


class LoanProductViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = LoanProduct.objects.all().order_by('name')
    serializer_class = LoanProductSerializer

    def _require(self, code: str):
        company = self.get_company()
        if not has_permission(self.request.user, code, company):
            return Response({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)
        return None

    def perform_create(self, serializer):
        denied = self._require("microfinance.create_loan")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        serializer.save()

    def perform_update(self, serializer):
        denied = self._require("microfinance.update_loan")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        serializer.save()

    def perform_destroy(self, instance):
        denied = self._require("microfinance.delete_loan")
        if denied:
            raise PermissionError(denied.data.get("detail"))
        instance.delete()


class LoanViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Loan.objects.all().select_related('borrower', 'product')
    serializer_class = LoanSerializer

    @action(detail=True, methods=['post'])
    def disburse(self, request, pk=None):
        loan = self.get_object()
        # permission
        company = self.get_company()
        if not has_permission(request.user, "microfinance.disburse_loan", company):
            return Response({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)
        date = request.data.get('date')
        try:
            loan.disburse(date=date)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=400)
        return Response(self.get_serializer(loan).data)

    @action(detail=False, methods=['get'])
    def par(self, request):
        from datetime import datetime, timedelta
        company = self.get_company()
        as_of = request.query_params.get('as_of')
        today = datetime.strptime(as_of, '%Y-%m-%d').date() if as_of else timezone.now().date()
        qs = LoanRepaymentSchedule.objects.filter(loan__company=company)
        total_portfolio = qs.aggregate(total=Sum('total_due'))['total'] or Decimal('0.00')
        def bucket(days):
            overdue = qs.filter(status__in=['pending', 'overdue'], due_date__lte=today - timedelta(days=days))
            value = overdue.aggregate(total=Sum(F('total_due') - F('paid_amount')))['total'] or Decimal('0.00')
            return value
        par30 = bucket(30)
        par60 = bucket(60)
        par90 = bucket(90)
        data = {
            'total_portfolio': f"{total_portfolio}",
            'par30': f"{par30}",
            'par60': f"{par60}",
            'par90': f"{par90}",
            'par30_pct': float(par30 / total_portfolio * 100) if total_portfolio else 0,
            'par60_pct': float(par60 / total_portfolio * 100) if total_portfolio else 0,
            'par90_pct': float(par90 / total_portfolio * 100) if total_portfolio else 0,
        }
        return Response(data)

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        from datetime import timedelta
        company = self.get_company()
        today = timezone.now().date()
        try:
            days = int(request.query_params.get('days') or '30')
        except ValueError:
            days = 30
        qs = (
            LoanRepaymentSchedule.objects
            .filter(loan__company=company, due_date__lt=today - timedelta(days=days), status__in=['pending', 'overdue'])
            .select_related('loan__borrower')
            .values(
                'loan_id', 'loan__number', 'loan__borrower__name', 'installment_number', 'due_date',
            )
            .annotate(
                due_amount=F('total_due') - F('paid_amount')
            )
            .order_by('-due_date')[:50]
        )
        return Response(list(qs))


class LoanRepaymentViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = LoanRepayment.objects.all().select_related('loan')
    serializer_class = LoanRepaymentSerializer

    def perform_create(self, serializer):
        company = self.get_company()
        if not has_permission(self.request.user, "microfinance.record_repayment", company):
            raise PermissionError("Not permitted.")
        serializer.save()
