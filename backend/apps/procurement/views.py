from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.db.models import Sum
from django.db.models.functions import TruncWeek
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.utils import log_audit_event
from apps.budgeting.models import BudgetLine, CostCenter
from apps.inventory.models import Product, UnitOfMeasure

from .models import PurchaseOrder, PurchaseOrderLine, PurchaseRequisition, Supplier, PurchaseRequisitionDraft
from .serializers import (
    PurchaseOrderLineSerializer,
    PurchaseOrderSerializer,
    PurchaseRequisitionSerializer,
    PurchaseRequisitionDraftSerializer,
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

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        supplier = self.get_object()
        supplier.status = 'active'
        supplier.save()
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'])
    def blacklist(self, request, pk=None):
        supplier = self.get_object()
        supplier.status = 'blacklisted'
        supplier.is_blocked = True
        supplier.block_reason = request.data.get('reason', 'Blacklisted')
        supplier.save()
        return Response({'status': 'blacklisted'})


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
        # Notify procurement users
        try:
            from django.contrib.auth import get_user_model
            from apps.notifications.models import Notification, NotificationSeverity
            company = self.get_company()
            User = get_user_model()
            qs = User.objects.filter(is_staff=True)
            for u in qs:
                Notification.objects.create(
                    company=company,
                    user=u,
                    title=f"New Purchase Requisition {requisition.requisition_number}",
                    body=f"A new purchase requisition has been created and awaits processing.",
                    severity=NotificationSeverity.INFO,
                    entity_type="PurchaseRequisition",
                    entity_id=str(requisition.id),
                    group_key="procurement_pr_created",
                )
        except Exception:
            pass

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
        # Notify procurement users on submission
        try:
            from django.contrib.auth import get_user_model
            from apps.notifications.models import Notification, NotificationSeverity
            company = self.get_company()
            User = get_user_model()
            qs = User.objects.filter(is_staff=True)
            for u in qs:
                Notification.objects.create(
                    company=company,
                    user=u,
                    title=f"Purchase Requisition {requisition.requisition_number} submitted",
                    body=f"Requisition is submitted and pending review.",
                    severity=NotificationSeverity.INFO,
                    entity_type="PurchaseRequisition",
                    entity_id=str(requisition.id),
                    group_key="procurement_pr_submitted",
                )
        except Exception:
            pass
        return Response(self.get_serializer(requisition).data)

    @action(detail=True, methods=["post"], url_path="generate-po")
    def generate_po(self, request, pk=None):
        """Generate a draft Purchase Order from this requisition.

        Expects payload: {"supplier_id": int, "expected_delivery_date": "YYYY-MM-DD", "currency": "USD"}
        """
        requisition = self.get_object()
        supplier_id = request.data.get("supplier_id")
        if not supplier_id:
            return Response({"detail": "supplier_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            supplier = Supplier.objects.get(id=int(supplier_id))
        except (Supplier.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Invalid supplier_id"}, status=status.HTTP_400_BAD_REQUEST)

        # Build PO payload
        po_payload = {
            "supplier": supplier.id,
            "requisition": requisition.id,
            "cost_center": requisition.cost_center_id,
            "currency": request.data.get("currency") or "USD",
            "expected_delivery_date": request.data.get("expected_delivery_date") or requisition.required_by,
            "lines": [],
        }
        for idx, ln in enumerate(requisition.lines.all().order_by("line_number"), start=1):
            po_payload["lines"].append({
                "line_number": idx,
                "requisition_line": ln.id,
                "budget_line": ln.budget_line_id,
                "product": getattr(ln, "product_id", None),
                "description": ln.description or "",
                "quantity": ln.quantity,
                "expected_delivery_date": ln.needed_by or requisition.required_by,
                "unit_price": ln.estimated_unit_cost or 0,
                "tax_rate": 0,
            })

        serializer = PurchaseOrderSerializer(data=po_payload, context={"request": request})
        serializer.is_valid(raise_exception=True)
        po = serializer.save()
        log_audit_event(
            user=request.user,
            company=self.get_company(),
            company_group=getattr(self.get_company(), "company_group", None),
            action="PO_CREATED_FROM_PR",
            entity_type="PurchaseOrder",
            entity_id=str(po.id),
            description=f"PO {po.order_number} created from PR {requisition.requisition_number}.",
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PurchaseRequisitionDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, 'company', None)
        qs = PurchaseRequisitionDraft.objects.all().order_by('-created_at')
        if company:
            qs = qs.filter(company=company)
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        serializer = PurchaseRequisitionDraftSerializer(qs, many=True, context={'request': request})
        return Response({'results': serializer.data})

    def post(self, request):
        serializer = PurchaseRequisitionDraftSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PurchaseRequisitionDraftDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        company = getattr(request, 'company', None)
        try:
            obj = PurchaseRequisitionDraft.objects.get(pk=pk)
        except PurchaseRequisitionDraft.DoesNotExist:
            return None
        if company and obj.company_id != company.id:
            return None
        return obj

    def get(self, request, pk: int):
        obj = self.get_object(request, pk)
        if not obj:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = PurchaseRequisitionDraftSerializer(obj, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, pk: int):
        obj = self.get_object(request, pk)
        if not obj:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = PurchaseRequisitionDraftSerializer(obj, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk: int):
        obj = self.get_object(request, pk)
        if not obj:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PurchaseRequisitionDraftConvertView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        company = getattr(request, 'company', None)
        try:
            draft = PurchaseRequisitionDraft.objects.get(pk=pk)
        except PurchaseRequisitionDraft.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        if company and draft.company_id != company.id:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        cost_center_id = request.data.get('cost_center_id')
        budget_line_id = request.data.get('budget_line_id')
        if not cost_center_id or not budget_line_id:
            return Response({"detail": "cost_center_id and budget_line_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cost_center = CostCenter.objects.get(id=cost_center_id)
            budget_line = BudgetLine.objects.get(id=budget_line_id)
        except (CostCenter.DoesNotExist, BudgetLine.DoesNotExist):
            return Response({"detail": "Invalid cost_center_id or budget_line_id"}, status=status.HTTP_400_BAD_REQUEST)
        if budget_line.company_id != company.id or cost_center.company_id != company.id:
            return Response({"detail": "Budget line and cost center must belong to the active company"}, status=status.HTTP_400_BAD_REQUEST)

        # Build full PurchaseRequisition via serializer
        pr_payload = {
            'cost_center': cost_center.id,
            'request_type': budget_line.procurement_class,
            'justification': draft.purpose or '',
            'required_by': draft.needed_by,
            'lines': [],
        }
        # Build line payloads
        for idx, line in enumerate(draft.lines or [], start=1):
            product = None
            uom = None
            item_id = line.get('item_id')
            if item_id:
                try:
                    product = Product.objects.get(id=item_id)
                except Product.DoesNotExist:
                    product = None
            uom_code = line.get('uom')
            if uom_code:
                try:
                    uom = UnitOfMeasure.objects.filter(short_name__iexact=uom_code).first() or UnitOfMeasure.objects.filter(name__iexact=uom_code).first()
                except Exception:
                    uom = None
            pr_line = {
                'line_number': idx,
                'budget_line': budget_line.id,
                'cost_center': cost_center.id,
                'product': product.id if product else None,
                'description': line.get('item_name') or line.get('notes') or '',
                'quantity': line.get('quantity') or 0,
                'uom': uom.id if uom else None,
                'estimated_unit_cost': 0,
                'needed_by': draft.needed_by,
            }
            pr_payload['lines'].append(pr_line)

        serializer = PurchaseRequisitionSerializer(data=pr_payload, context={'request': request})
        serializer.is_valid(raise_exception=True)
        pr = serializer.save()
        # Mark submitted for workflow or keep as draft: here we submit if requested
        try:
            submit_now = bool(request.data.get('submit', True))
            if submit_now:
                pr.submit(request.user)
        except Exception:
            pass

        # Delete draft by default unless keep_draft=true
        keep_draft = bool(request.data.get('keep_draft'))
        if not keep_draft:
            draft.delete()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
