from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.utils import log_audit_event
from apps.inventory.models import StockLevel
from apps.sales.models import SalesOrderLine

TWOPLACES = Decimal("0.01")

from .models import (
    BillOfMaterial,
    MaterialIssue,
    ProductionReceipt,
    WorkOrder,
    WorkOrderStatus,
)
from .serializers import (
    BillOfMaterialSerializer,
    MaterialIssueCreateSerializer,
    MaterialIssueSerializer,
    ProductionReceiptCreateSerializer,
    ProductionReceiptSerializer,
    WorkOrderSerializer,
)


class CompanyScopedMixin:
    permission_classes = [IsAuthenticated]

    def get_company(self, *, required: bool = False):
        company = getattr(self.request, "company", None)
        if company is None:
            company_id = self.request.META.get("HTTP_X_COMPANY_ID")
            if company_id:
                from apps.companies.models import Company

                company = Company.objects.filter(pk=company_id).first()
                if company:
                    setattr(self.request, "company", company)
        if required and company is None:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("Active company context is required.")
        return company

    def get_queryset(self):  # type: ignore[override]
        queryset = super().get_queryset()
        company = self.get_company()
        if company:
            return queryset.filter(company=company)
        return queryset.none()

    def get_serializer_context(self):  # type: ignore[override]
        context = super().get_serializer_context()
        context.setdefault("request", self.request)
        return context


class BillOfMaterialViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = BillOfMaterialSerializer
    queryset = BillOfMaterial.objects.select_related("product")

    def perform_create(self, serializer):
        bom = serializer.save()
        company = self.get_company(required=True)
        log_audit_event(
            user=self.request.user,
            company=company,
            company_group=company.company_group,
            action="BOM_CREATED",
            entity_type="BillOfMaterial",
            entity_id=bom.pk,
            description=f"BOM {bom.code} created.",
        )

    def perform_update(self, serializer):
        bom = serializer.save()
        company = self.get_company(required=True)
        log_audit_event(
            user=self.request.user,
            company=company,
            company_group=company.company_group,
            action="BOM_UPDATED",
            entity_type="BillOfMaterial",
            entity_id=bom.pk,
            description=f"BOM {bom.code} updated.",
        )


class WorkOrderViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = WorkOrderSerializer
    queryset = (
        WorkOrder.objects.select_related("product", "bom", "warehouse")
        .prefetch_related("components__component", "issues__lines", "receipts")
        .order_by("-created_at")
    )

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        status_filter = request.query_params.get("status")
        queryset = self.filter_queryset(self.get_queryset())
        if status_filter and status_filter != "ALL":
            queryset = queryset.filter(status=status_filter)
        serializer = self.get_serializer(queryset, many=True)
        summary = queryset.values("status").annotate(total=Sum("quantity_planned"))
        summary_map = {row["status"]: row["total"] for row in summary}
        return Response({"results": serializer.data, "summary": summary_map})

    def perform_create(self, serializer):
        work_order = serializer.save()
        company = self.get_company(required=True)
        log_audit_event(
            user=self.request.user,
            company=company,
            company_group=company.company_group,
            action="WORK_ORDER_CREATED",
            entity_type="WorkOrder",
            entity_id=work_order.pk,
            description=f"Work order {work_order.number} created.",
        )

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        work_order = self.get_object()
        try:
            work_order.release()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(work_order).data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        work_order = self.get_object()
        try:
            work_order.start()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(work_order).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        work_order = self.get_object()
        quantity = request.data.get("quantity_completed", work_order.quantity_planned)
        try:
            work_order.complete(Decimal(quantity))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(work_order).data)

    @action(detail=True, methods=["post"], url_path="issue-materials")
    def issue_materials(self, request, pk=None):
        work_order = self.get_object()
        serializer = MaterialIssueCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            issue = work_order.record_material_issue(
                user=request.user,
                issue_date=data.get("issue_date"),
                notes=data.get("notes", ""),
                lines=data["lines"],
            )
        except (ValueError, Exception) as exc:  # pylint: disable=broad-except
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        company = self.get_company(required=True)
        log_audit_event(
            user=request.user,
            company=company,
            company_group=company.company_group,
            action="WORK_ORDER_ISSUE_RECORDED",
            entity_type="WorkOrder",
            entity_id=work_order.pk,
            description=f"Issue {issue.issue_number} recorded for work order {work_order.number}.",
        )
        return Response(MaterialIssueSerializer(issue).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="record-receipt")
    def record_receipt(self, request, pk=None):
        work_order = self.get_object()
        serializer = ProductionReceiptCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            receipt = work_order.record_receipt(
                user=request.user,
                receipt_date=data.get("receipt_date"),
                quantity_good=data["quantity_good"],
                quantity_scrap=data.get("quantity_scrap", Decimal("0")),
                notes=data.get("notes", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        company = self.get_company(required=True)
        log_audit_event(
            user=request.user,
            company=company,
            company_group=company.company_group,
            action="WORK_ORDER_RECEIPT_RECORDED",
            entity_type="WorkOrder",
            entity_id=work_order.pk,
            description=f"Receipt {receipt.receipt_number} recorded for work order {work_order.number}.",
        )
        return Response(ProductionReceiptSerializer(receipt).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="mrp-summary")
    def mrp_summary(self, request):
        company = self.get_company(required=True)
        from_date = parse_date(request.query_params.get("from_date")) or timezone.now().date()
        to_param = request.query_params.get("to_date")
        to_date = parse_date(to_param) if to_param else from_date + timedelta(days=30)
        include_sales = request.query_params.get("include_sales", "true").lower() in {"1", "true", "yes", "on"}

        work_orders = WorkOrder.objects.filter(
            company=company,
            status__in=[WorkOrderStatus.RELEASED, WorkOrderStatus.IN_PROGRESS],
        ).filter(
            Q(scheduled_end__isnull=True) | Q(scheduled_end__gte=from_date)
        ).filter(
            Q(scheduled_start__isnull=True) | Q(scheduled_start__lte=to_date)
        )

        components = (
            work_orders
            .values("components__component")
            .annotate(required=Sum("components__required_quantity"), issued=Sum("components__issued_quantity"))
        )
        requirements = {}
        for row in components:
            product_id = row["components__component"]
            required = row["required"] or Decimal("0")
            issued = row["issued"] or Decimal("0")
            remaining = required - issued
            if remaining <= 0:
                continue
            requirements[product_id] = requirements.get(product_id, Decimal("0")) + remaining

        stock_levels = (
            StockLevel.objects.filter(company=company, product_id__in=requirements.keys())
            .values("product_id")
            .annotate(on_hand=Sum("quantity"))
        )
        stock_map = {row["product_id"]: row["on_hand"] or Decimal("0") for row in stock_levels}

        recommendations = []
        for product_id, remaining in requirements.items():
            on_hand = stock_map.get(product_id, Decimal("0"))
            shortage = remaining - on_hand
            if shortage <= 0:
                continue
            recommendations.append(
                {
                    "product": product_id,
                    "required_quantity": str(remaining),
                    "on_hand": str(on_hand),
                    "shortage": str(shortage),
                }
            )
        demand = {"work_orders": len(work_orders)}
        if include_sales:
            sales_lines = SalesOrderLine.objects.filter(
                order__company=company,
                order__status__in=["CONFIRMED", "PARTIAL"],
            )
            sales_lines = sales_lines.filter(Q(order__delivery_date__isnull=True) | Q(order__delivery_date__gte=from_date))
            sales_lines = sales_lines.filter(Q(order__delivery_date__isnull=True) | Q(order__delivery_date__lte=to_date))
            sales_orders = []
            for line in sales_lines.select_related("order", "product"):
                outstanding = (line.quantity or Decimal("0")) - (line.delivered_qty or Decimal("0"))
                if outstanding <= 0:
                    continue
                sales_orders.append(
                    {
                        "order": line.order.order_number,
                        "product": line.product_id,
                        "due": line.order.delivery_date.isoformat() if line.order.delivery_date else None,
                        "outstanding": str(outstanding),
                    }
                )
            demand["sales_orders"] = sales_orders

        return Response({"recommendations": recommendations, "demand": demand})

    @action(detail=False, methods=["get"], url_path="capacity-summary")
    def capacity_summary(self, request):
        company = self.get_company(required=True)
        from_date = parse_date(request.query_params.get("from_date")) or timezone.now().date()
        to_param = request.query_params.get("to_date")
        to_date = parse_date(to_param) if to_param else from_date + timedelta(days=14)
        capacity_hours = Decimal(request.query_params.get("daily_capacity", 16))

        buckets = defaultdict(lambda: {"planned_hours": Decimal("0"), "available_hours": capacity_hours})
        work_orders = WorkOrder.objects.filter(
            company=company,
            status__in=[WorkOrderStatus.PLANNED, WorkOrderStatus.RELEASED, WorkOrderStatus.IN_PROGRESS],
        )
        for wo in work_orders:
            start = wo.scheduled_start or from_date
            end = wo.scheduled_end or wo.scheduled_start or from_date
            if end < from_date or start > to_date:
                continue
            total_hours = Decimal(wo.quantity_planned or 0)
            duration_days = max((end - start).days + 1, 1)
            daily_hours = total_hours / duration_days if duration_days else total_hours
            for offset in range(duration_days):
                bucket_date = start + timedelta(days=offset)
                if bucket_date < from_date or bucket_date > to_date:
                    continue
                buckets[bucket_date]["planned_hours"] += daily_hours

        ordered = []
        current = from_date
        while current <= to_date:
            data = buckets[current]
            ordered.append(
                {
                    "date": current.isoformat(),
                    "planned_hours": str(data["planned_hours"].quantize(TWOPLACES)),
                    "available_hours": str(data["available_hours"].quantize(TWOPLACES)),
                }
            )
            current += timedelta(days=1)

        return Response(
            {
                "horizon": {"from": from_date.isoformat(), "to": to_date.isoformat()},
                "default_capacity": str(capacity_hours.quantize(TWOPLACES)),
                "buckets": ordered,
            }
        )


class MaterialIssueViewSet(CompanyScopedMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = MaterialIssueSerializer
    queryset = MaterialIssue.objects.select_related("work_order").prefetch_related("lines__product")


class ProductionReceiptViewSet(CompanyScopedMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductionReceiptSerializer
    queryset = ProductionReceipt.objects.select_related("work_order", "warehouse")
