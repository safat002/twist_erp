from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
from .models import (
    Product, StockMovement, Warehouse, UnitOfMeasure, StockMovementLine,
    ProductCategory, StockLedger, DeliveryOrder, GoodsReceipt, StockLevel,
    GoodsReceiptLine, DeliveryOrderLine, InternalRequisition,
    ItemValuationMethod, CostLayer, ValuationChangeLog
)
from .serializers import (
    ProductSerializer, StockMovementSerializer, WarehouseSerializer,
    UnitOfMeasureSerializer, StockMovementLineSerializer, ProductCategorySerializer,
    StockLedgerSerializer, DeliveryOrderSerializer, GoodsReceiptSerializer,
    StockLevelSerializer, GoodsReceiptLineSerializer, DeliveryOrderLineSerializer,
    InternalRequisitionSerializer, ItemValuationMethodSerializer,
    CostLayerSerializer, CostLayerDetailSerializer, ValuationChangeLogSerializer
)
from .services.valuation_service import ValuationService
from .services.stock_service import InventoryService

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class StockMovementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = StockMovementSerializer

    def get_queryset(self):
        qs = StockMovement.objects.all().order_by('-movement_date')
        company = getattr(self.request, 'company', None)
        if company:
            qs = qs.filter(company=company)
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from and date_to:
            try:
                qs = qs.filter(movement_date__range=[date_from, date_to])
            except Exception:
                pass
        mtype = self.request.query_params.get('type')
        if mtype:
            qs = qs.filter(movement_type__iexact=mtype)
        return qs

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer

class UnitOfMeasureViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UnitOfMeasureSerializer
    queryset = UnitOfMeasure.objects.all()

    def get_queryset(self):
        qs = UnitOfMeasure.objects.all().order_by('code', 'id')
        company = getattr(self.request, 'company', None)
        if company and getattr(company, 'company_group_id', None):
            # Group-scoped: share UOMs across companies in the same group
            qs = qs.filter(company__company_group_id=company.company_group_id)
        elif company:
            qs = qs.filter(company=company)
        return qs

    def list(self, request, *args, **kwargs):
        # Deduplicate by code within the company group so each UOM shows once
        queryset = self.get_queryset()
        by_code = {}
        for u in queryset:
            if u.code not in by_code:
                by_code[u.code] = u
        serializer = self.get_serializer(list(by_code.values()), many=True)
        return Response(serializer.data)

class StockMovementLineViewSet(viewsets.ModelViewSet):
    queryset = StockMovementLine.objects.all()
    serializer_class = StockMovementLineSerializer

class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer

class StockLedgerViewSet(viewsets.ModelViewSet):
    queryset = StockLedger.objects.all()
    serializer_class = StockLedgerSerializer

class DeliveryOrderViewSet(viewsets.ModelViewSet):
    queryset = DeliveryOrder.objects.all()
    serializer_class = DeliveryOrderSerializer

class GoodsReceiptViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceipt.objects.all()
    serializer_class = GoodsReceiptSerializer

class StockLevelViewSet(viewsets.ModelViewSet):
    queryset = StockLevel.objects.all()
    serializer_class = StockLevelSerializer

class GoodsReceiptLineViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceiptLine.objects.all()
    serializer_class = GoodsReceiptLineSerializer

class DeliveryOrderLineViewSet(viewsets.ModelViewSet):
    queryset = DeliveryOrderLine.objects.all()
    serializer_class = DeliveryOrderLineSerializer


class CompanyScopedQuerysetMixin:
    permission_classes = [IsAuthenticated]

    def get_company(self):
        return getattr(self.request, "company", None)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class InternalRequisitionViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = InternalRequisitionSerializer

    def get_queryset(self):
        qs = InternalRequisition.objects.order_by('-created_at')
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        instance = self.get_object()
        instance.status = instance.Status.SUBMITTED
        instance.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        instance = self.get_object()
        instance.status = instance.Status.APPROVED
        instance.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        instance = self.get_object()
        instance.status = instance.Status.CANCELLED
        instance.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(instance).data)


class InventoryOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, 'company', None)
        qs_products = Product.objects.all()
        qs_wh = Warehouse.objects.all()
        qs_mv = StockMovement.objects.all()
        if company:
            qs_products = qs_products.filter(company=company)
            qs_wh = qs_wh.filter(company=company)
            qs_mv = qs_mv.filter(company=company)

        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        movements_count = qs_mv.count()
        if date_from and date_to:
            try:
                movements_count = qs_mv.filter(movement_date__range=[date_from, date_to]).count()
            except Exception:
                pass

        data = {
            'products': qs_products.count(),
            'warehouses': qs_wh.count(),
            'movements': movements_count,
        }
        return Response(data)


class StockLedgerSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, 'company', None)
        qs = StockLedger.objects.all()
        if company:
            qs = qs.filter(company=company)

        total_skus_tracked = qs.values('product').distinct().count()
        last = qs.order_by('-transaction_date', '-id').values_list('transaction_date', flat=True).first()

        # Rough approximation for ledger value: sum of balance_value of the latest entry per (product, warehouse)
        ledger_value = 0
        try:
            latest_map = {}
            for row in qs.values('product', 'warehouse', 'transaction_date', 'id', 'balance_value'):
                key = (row['product'], row['warehouse'])
                prev = latest_map.get(key)
                curr_key = (row['transaction_date'], row['id'])
                if not prev or curr_key > prev[0]:
                    latest_map[key] = (curr_key, row['balance_value'])
            ledger_value = float(sum(v[1] or 0 for v in latest_map.values()))
        except Exception:
            ledger_value = 0

        # Open discrepancies placeholder (requires reconciliation features); return 0
        open_discrepancies = 0

        data = {
            'total_skus_tracked': total_skus_tracked,
            'last_movement_at': last.isoformat() if last else None,
            'ledger_value': ledger_value,
            'open_discrepancies': open_discrepancies,
        }
        return Response(data)


class StockLedgerEventsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, 'company', None)
        limit = request.query_params.get('limit')
        try:
            limit = max(1, min(int(limit or 10), 100))
        except Exception:
            limit = 10

        qs = StockLedger.objects.select_related('product', 'warehouse')
        if company:
            qs = qs.filter(company=company)
        qs = qs.order_by('-transaction_date', '-id')[:limit]

        events = []
        for led in qs:
            # Human-readable event text
            ev_map = {
                'RECEIPT': 'Stock Receipt posted',
                'ISSUE': 'Stock Issue posted',
                'TRANSFER': 'Stock Transfer posted',
                'ADJUSTMENT': 'Stock Adjustment posted',
            }
            ev = ev_map.get(getattr(led, 'transaction_type', ''), 'Stock event')
            ref = f"{getattr(led, 'source_document_type', '')} #{getattr(led, 'source_document_id', '')}".strip()
            j_impact = f"Qty {led.quantity} × Rate {led.rate} = {led.value}"
            events.append({
                'id': led.id,
                'event': ev,
                'reference': ref,
                'journal_impact': j_impact,
                'status': 'synced',
                'timestamp': led.transaction_date.isoformat() if led.transaction_date else None,
            })

        return Response({'results': events})


# ========================================
# VALUATION API ENDPOINTS
# ========================================

class ItemValuationMethodViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing item valuation methods.
    Allows configuring FIFO/LIFO/Average/Standard costing per item/warehouse.
    """
    serializer_class = ItemValuationMethodSerializer

    def get_queryset(self):
        qs = ItemValuationMethod.objects.select_related('product', 'warehouse').order_by('-effective_date')
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)

        # Filter by product
        product_id = self.request.query_params.get('product')
        if product_id:
            qs = qs.filter(product_id=product_id)

        # Filter by warehouse
        warehouse_id = self.request.query_params.get('warehouse')
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)

        # Filter by method
        method = self.request.query_params.get('method')
        if method:
            qs = qs.filter(valuation_method=method)

        # Filter active only
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() in ['true', '1', 'yes']:
            qs = qs.filter(is_active=True)

        return qs

    @action(detail=False, methods=['get'])
    def by_product_warehouse(self, request):
        """
        Get valuation method for a specific product/warehouse combination.
        Query params: product_id, warehouse_id
        """
        product_id = request.query_params.get('product_id')
        warehouse_id = request.query_params.get('warehouse_id')

        if not product_id or not warehouse_id:
            return Response(
                {'error': 'Both product_id and warehouse_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        company = self.get_company()
        method = ValuationService.get_valuation_method(
            company=company,
            product=Product.objects.get(id=product_id, company=company),
            warehouse=Warehouse.objects.get(id=warehouse_id, company=company)
        )

        if method:
            serializer = self.get_serializer(method)
            return Response(serializer.data)
        else:
            return Response(
                {'message': 'No valuation method configured, using default FIFO'},
                status=status.HTTP_404_NOT_FOUND
            )


class CostLayerViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet for viewing cost layers.
    Cost layers are created automatically on receipts and consumed on issues.
    """
    serializer_class = CostLayerSerializer

    def get_queryset(self):
        qs = CostLayer.objects.select_related('product', 'warehouse').order_by('-receipt_date')
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)

        # Filter by product
        product_id = self.request.query_params.get('product')
        if product_id:
            qs = qs.filter(product_id=product_id)

        # Filter by warehouse
        warehouse_id = self.request.query_params.get('warehouse')
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)

        # Filter open layers only
        open_only = self.request.query_params.get('open_only')
        if open_only and open_only.lower() in ['true', '1', 'yes']:
            qs = qs.filter(is_closed=False, qty_remaining__gt=0)

        # Filter by batch
        batch_no = self.request.query_params.get('batch_no')
        if batch_no:
            qs = qs.filter(batch_no=batch_no)

        return qs

    def get_serializer_class(self):
        """Use detailed serializer for retrieve action"""
        if self.action == 'retrieve':
            return CostLayerDetailSerializer
        return CostLayerSerializer

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get summary of cost layers for a product/warehouse.
        Query params: product_id, warehouse_id
        """
        product_id = request.query_params.get('product_id')
        warehouse_id = request.query_params.get('warehouse_id')

        if not product_id or not warehouse_id:
            return Response(
                {'error': 'Both product_id and warehouse_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        company = self.get_company()
        product = Product.objects.get(id=product_id, company=company)
        warehouse = Warehouse.objects.get(id=warehouse_id, company=company)

        # Get inventory value
        value_data = ValuationService.get_inventory_value(
            company=company,
            product=product,
            warehouse=warehouse
        )

        # Get open layers
        open_layers = CostLayer.objects.filter(
            company=company,
            product=product,
            warehouse=warehouse,
            is_closed=False,
            qty_remaining__gt=0
        ).order_by('fifo_sequence')

        layers_data = CostLayerSerializer(open_layers, many=True).data

        return Response({
            'summary': value_data,
            'open_layers': layers_data
        })


class ValuationChangeLogViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing valuation method change requests.
    Includes approval workflow.
    """
    serializer_class = ValuationChangeLogSerializer

    def get_queryset(self):
        qs = ValuationChangeLog.objects.select_related(
            'product', 'warehouse', 'requested_by', 'approved_by'
        ).order_by('-requested_date')
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        # Filter by product
        product_id = self.request.query_params.get('product')
        if product_id:
            qs = qs.filter(product_id=product_id)

        return qs

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a valuation method change request.
        Creates the new valuation method and marks change as effective.
        """
        change_log = self.get_object()

        if change_log.status != 'PENDING':
            return Response(
                {'error': 'Only pending change requests can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update change log
        change_log.status = 'APPROVED'
        change_log.approved_by = request.user
        change_log.approval_date = timezone.now()
        change_log.save()

        # Create the new valuation method
        ItemValuationMethod.objects.create(
            company=change_log.company,
            product=change_log.product,
            warehouse=change_log.warehouse,
            valuation_method=change_log.new_method,
            effective_date=change_log.effective_date,
            created_by=request.user,
            is_active=True
        )

        # Mark as effective
        change_log.status = 'EFFECTIVE'
        change_log.save()

        serializer = self.get_serializer(change_log)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a valuation method change request.
        """
        change_log = self.get_object()

        if change_log.status != 'PENDING':
            return Response(
                {'error': 'Only pending change requests can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rejection_reason = request.data.get('rejection_reason', '')

        change_log.status = 'REJECTED'
        change_log.approved_by = request.user
        change_log.approval_date = timezone.now()
        change_log.rejection_reason = rejection_reason
        change_log.save()

        serializer = self.get_serializer(change_log)
        return Response(serializer.data)


class ValuationReportView(APIView):
    """
    Generate valuation reports for inventory.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get inventory valuation report.
        Query params: product_id (optional), warehouse_id (optional), method (optional)
        """
        company = getattr(request, 'company', None)

        # Get filters
        product_id = request.query_params.get('product_id')
        warehouse_id = request.query_params.get('warehouse_id')
        method_filter = request.query_params.get('method')

        # Build queryset
        products = Product.objects.filter(company=company, track_inventory=True)
        if product_id:
            products = products.filter(id=product_id)

        warehouses = Warehouse.objects.filter(company=company)
        if warehouse_id:
            warehouses = warehouses.filter(id=warehouse_id)

        # Generate report data
        report_data = []
        total_value = 0

        for product in products:
            for warehouse in warehouses:
                # Get valuation method
                val_method = ValuationService.get_valuation_method(
                    company, product, warehouse
                )

                method_code = val_method.valuation_method if val_method else 'FIFO'

                # Skip if method filter doesn't match
                if method_filter and method_code != method_filter:
                    continue

                # Get inventory value
                try:
                    value_data = ValuationService.get_inventory_value(
                        company, product, warehouse, val_method
                    )

                    if value_data['qty_on_hand'] > 0:
                        # Near-expiry and expired warnings
                        today = timezone.now().date()
                        warn_days = getattr(product, 'expiry_warning_days', 0) or 0
                        near_expiry_count = 0
                        near_expiry_qty = 0.0
                        expired_count = 0
                        expired_qty = 0.0

                        try:
                            qs_layers = CostLayer.objects.filter(
                                company=company,
                                product=product,
                                warehouse=warehouse,
                                is_closed=False,
                                qty_remaining__gt=0,
                                expiry_date__isnull=False
                            )
                            if warn_days > 0:
                                near_qs = qs_layers.filter(expiry_date__gte=today, expiry_date__lte=today + timedelta(days=warn_days))
                                near_expiry_count = near_qs.count()
                                near_expiry_qty = float(sum(l.qty_remaining for l in near_qs))
                            exp_qs = qs_layers.filter(expiry_date__lt=today)
                            expired_count = exp_qs.count()
                            expired_qty = float(sum(l.qty_remaining for l in exp_qs))
                        except Exception:
                            pass

                        item_data = {
                            'product_id': product.id,
                            'product_code': product.code,
                            'product_name': product.name,
                            'warehouse_id': warehouse.id,
                            'warehouse_code': warehouse.code,
                            'warehouse_name': warehouse.name,
                            'valuation_method': method_code,
                            'qty_on_hand': value_data['qty_on_hand'],
                            'cost_per_unit': value_data['current_cost_per_unit'],
                            'total_value': value_data['total_value'],
                            'layer_count': value_data['layer_count'],
                            'near_expiry_layers': near_expiry_count,
                            'near_expiry_qty': near_expiry_qty,
                            'expired_layers': expired_count,
                            'expired_qty': expired_qty
                        }
                        report_data.append(item_data)
                        total_value += value_data['total_value']

                except Exception as e:
                    # Skip items with errors
                    continue

        return Response({
            'report_date': timezone.now().isoformat(),
            'total_items': len(report_data),
            'total_inventory_value': total_value,
            'items': report_data
        })


class CurrentCostView(APIView):
    """
    Get current cost for a product/warehouse for quotes and estimates.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get current cost per unit.
        Query params: product_id, warehouse_id
        """
        company = getattr(request, 'company', None)
        product_id = request.query_params.get('product_id')
        warehouse_id = request.query_params.get('warehouse_id')

        if not product_id or not warehouse_id:
            return Response(
                {'error': 'Both product_id and warehouse_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            product = Product.objects.get(id=product_id, company=company)
            warehouse = Warehouse.objects.get(id=warehouse_id, company=company)

            # Get valuation method
            val_method = ValuationService.get_valuation_method(
                company, product, warehouse
            )

            # Get current cost
            current_cost = ValuationService.get_current_cost(
                company, product, warehouse, val_method
            )

            method_code = val_method.valuation_method if val_method else 'FIFO'

            return Response({
                'product_id': product.id,
                'product_code': product.code,
                'product_name': product.name,
                'warehouse_id': warehouse.id,
                'warehouse_code': warehouse.code,
                'valuation_method': method_code,
                'current_cost_per_unit': float(current_cost),
                'as_of': timezone.now().isoformat()
            })

        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Warehouse.DoesNotExist:
            return Response(
                {'error': 'Warehouse not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LandedCostAdjustmentView(APIView):
    """
    Apply landed cost adjustment to a Goods Receipt (late freight invoice).
    Body: { goods_receipt_id, total_adjustment, method: 'QUANTITY'|'VALUE', reason }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        company = getattr(request, 'company', None)
        data = request.data or {}
        grn_id = data.get('goods_receipt_id')
        total_adjustment = data.get('total_adjustment')
        method = (data.get('method') or 'QUANTITY').upper()
        reason = data.get('reason') or ''

        if not grn_id or total_adjustment is None:
            return Response({'error': 'goods_receipt_id and total_adjustment are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            grn = GoodsReceipt.objects.get(id=grn_id, company=company)
        except GoodsReceipt.DoesNotExist:
            return Response({'error': 'GoodsReceipt not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            result = InventoryService.apply_landed_cost_adjustment(
                goods_receipt=grn,
                total_adjustment=total_adjustment,
                method=method,
                reason=reason
            )
            return Response({'status': 'ok', **result})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
