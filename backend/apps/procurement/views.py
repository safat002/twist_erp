from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.db.models import Sum
from django.db.models.functions import TruncWeek
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.utils import log_audit_event

from .models import PurchaseOrder, PurchaseOrderLine, PurchaseRequisition, Supplier
from .serializers import (
    PurchaseOrderLineSerializer,
    PurchaseOrderSerializer,
    PurchaseRequisitionSerializer,
    SupplierSerializer,
)


class CompanyScopedQuerysetMixin:
    permission_classes = [IsAuthenticated]

    def get_company(self):
        return getattr(self.request, "company", None)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class SupplierViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = SupplierSerializer

    def get_queryset(self):
        company = self.get_company()
        qs = Supplier.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs


class PurchaseRequisitionViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = PurchaseRequisitionSerializer

    def get_queryset(self):
        company = self.get_company()
        qs = (
            PurchaseRequisition.objects.select_related("cost_center", "requested_by", "approved_by")
            .prefetch_related("lines__budget_line")
            .order_by("-created_at")
        )
        if company:
            qs = qs.filter(company=company)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        requisition = serializer.save()
        log_audit_event(
            user=self.request.user,
            company=self.get_company(),
            company_group=getattr(self.get_company(), "company_group", None),
            action="PR_CREATED",
            entity_type="PurchaseRequisition",
            entity_id=str(requisition.id),
            description=f"Purchase requisition {requisition.requisition_number} created.",
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        requisition = self.get_object()
        try:
            requisition.submit(request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        log_audit_event(
            user=request.user,
            company=self.get_company(),
            company_group=getattr(self.get_company(), "company_group", None),
            action="PR_SUBMITTED",
            entity_type="PurchaseRequisition",
            entity_id=str(requisition.id),
            description=f"Requisition {requisition.requisition_number} submitted.",
        )
        return Response(self.get_serializer(requisition).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        requisition = self.get_object()
        try:
            requisition.approve(request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        log_audit_event(
            user=request.user,
            company=self.get_company(),
            company_group=getattr(self.get_company(), "company_group", None),
            action="PR_APPROVED",
            entity_type="PurchaseRequisition",
            entity_id=str(requisition.id),
            description=f"Requisition {requisition.requisition_number} approved.",
        )
        return Response(self.get_serializer(requisition).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        requisition = self.get_object()
        reason = request.data.get("reason", "")
        try:
            requisition.reject(request.user, reason=reason)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        log_audit_event(
            user=request.user,
            company=self.get_company(),
            company_group=getattr(self.get_company(), "company_group", None),
            action="PR_REJECTED",
            entity_type="PurchaseRequisition",
            entity_id=str(requisition.id),
            description=f"Requisition {requisition.requisition_number} rejected.",
            after={"reason": reason},
        )
        return Response(self.get_serializer(requisition).data)

    @action(detail=True, methods=["post"])
    def convert_to_po(self, request, pk=None):
        requisition = self.get_object()
        if requisition.status != PurchaseRequisition.Status.APPROVED:
            return Response({"detail": "Only approved requisitions can be converted to purchase orders."}, status=status.HTTP_400_BAD_REQUEST)
        if "supplier" not in request.data:
            return Response({"detail": "Supplier is required to create a purchase order."}, status=status.HTTP_400_BAD_REQUEST)

        payload = request.data.copy()
        payload["requisition"] = requisition.id
        payload.setdefault("cost_center", requisition.cost_center_id)
        payload.setdefault("order_date", timezone.now().date())
        payload.setdefault("currency", requisition.company.currency_code if hasattr(requisition.company, "currency_code") else "USD")

        if "lines" not in payload or not payload["lines"]:
            payload["lines"] = []
            for idx, line in enumerate(requisition.lines.select_related("budget_line", "product"), start=1):
                payload["lines"].append(
                    {
                        "requisition_line": line.id,
                        "budget_line": line.budget_line_id,
                        "product": line.product_id,
                        "description": line.description,
                        "quantity_ordered": line.quantity,
                        "unit_price": line.estimated_unit_cost,
                        "expected_delivery_date": payload.get("expected_delivery_date") or requisition.required_by,
                        "tolerance_percent": line.budget_line.tolerance_percent,
                    }
                )

        serializer = PurchaseOrderSerializer(data=payload, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        purchase_order = serializer.save()
        log_audit_event(
            user=request.user,
            company=self.get_company(),
            company_group=getattr(self.get_company(), "company_group", None),
            action="PO_CREATED_FROM_PR",
            entity_type="PurchaseOrder",
            entity_id=str(purchase_order.id),
            description=f"Purchase order {purchase_order.order_number} created from requisition {requisition.requisition_number}.",
        )
        response_serializer = PurchaseOrderSerializer(purchase_order, context=self.get_serializer_context())
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class PurchaseOrderViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = PurchaseOrderSerializer

    def get_queryset(self):
        company = self.get_company()
        qs = (
            PurchaseOrder.objects.select_related("supplier", "requisition", "cost_center", "created_by")
            .prefetch_related("lines__budget_line", "lines__product")
            .order_by("-order_date", "-created_at")
        )
        if company:
            qs = qs.filter(company=company)
        return qs

    def filter_queryset(self, queryset):
        status_filter = self.request.query_params.get("status")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if date_from:
            queryset = queryset.filter(order_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(order_date__lte=date_to)
        return super().filter_queryset(queryset)

    def perform_create(self, serializer):
        purchase_order = serializer.save()
        log_audit_event(
            user=self.request.user,
            company=self.get_company(),
            company_group=getattr(self.get_company(), "company_group", None),
            action="PO_CREATED",
            entity_type="PurchaseOrder",
            entity_id=str(purchase_order.id),
            description=f"Purchase order {purchase_order.order_number} created.",
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
        else:
            serializer = self.get_serializer(queryset, many=True)

        base_queryset = self.get_queryset()
        company = self.get_company()
        if company:
            base_queryset = base_queryset.filter(company=company)
        totals = base_queryset.aggregate(
            total_value=Sum("total_amount"),
            approved=Sum(
                models.Case(
                    models.When(status=PurchaseOrder.Status.APPROVED, then=1),
                    default=0,
                    output_field=models.IntegerField(),
                )
            ),
            awaiting=Sum(
                models.Case(
                    models.When(status=PurchaseOrder.Status.PENDING_APPROVAL, then=1),
                    default=0,
                    output_field=models.IntegerField(),
                )
            ),
            received=Sum(
                models.Case(
                    models.When(status=PurchaseOrder.Status.RECEIVED, then=1),
                    default=0,
                    output_field=models.IntegerField(),
                )
            ),
        )
        metrics = {
            "total": float(totals.get("total_value") or 0),
            "approved": int(totals.get("approved") or 0),
            "awaiting": int(totals.get("awaiting") or 0),
            "received": int(totals.get("received") or 0),
        }

        recent_start = timezone.now().date() - timedelta(days=28)
        spend_trend = (
            base_queryset.filter(order_date__gte=recent_start)
            .annotate(week=TruncWeek("order_date"))
            .values("week")
            .annotate(amount=Sum("total_amount"))
            .order_by("week")
        )
        spend_trend_payload = [
            {"week": entry["week"].strftime("%Y-%m-%d"), "amount": float(entry["amount"] or 0)} for entry in spend_trend
        ]

        if page is not None:
            paginated = self.get_paginated_response(serializer.data)
            paginated.data["metrics"] = metrics
            paginated.data["spend_trend"] = spend_trend_payload
            return paginated
        return Response(
            {
                "results": serializer.data,
                "metrics": metrics,
                "spend_trend": spend_trend_payload,
            }
        )


class PurchaseOrderLineViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = PurchaseOrderLineSerializer

    def get_queryset(self):
        company = self.get_company()
        qs = PurchaseOrderLine.objects.select_related("purchase_order", "budget_line", "product")
        if company:
            qs = qs.filter(purchase_order__company=company)
        return qs
