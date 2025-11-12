from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.db import models
from .models import (
    Product, Item, StockMovement, Warehouse, UnitOfMeasure, StockMovementLine,
    ProductCategory, StockLedger, DeliveryOrder, GoodsReceipt, StockLevel,
    GoodsReceiptLine, DeliveryOrderLine, InternalRequisition,
    ItemValuationMethod, CostLayer, ValuationChangeLog,
    ItemOperationalExtension, ItemWarehouseConfig, ItemUOMConversion,
    MovementEvent, WarehouseBin, ItemSupplier, ItemFEFOConfig,
    StandardCostVariance, PurchasePriceVariance,
    LandedCostComponent, LandedCostLineApportionment, InTransitShipmentLine,
    LandedCostVoucher, LandedCostAllocation, ReturnToVendor, ReturnToVendorLine,
    # Phase 3: QC & Compliance
    StockHold, QCCheckpoint, QCResult, BatchLot, SerialNumber,
    # Material Issue Management
    MaterialIssue, MaterialIssueLine,
    # Warehouse Category Mapping
    WarehouseCategoryMapping, WarehouseOverrideLog
)
from apps.budgeting.models import BudgetItemCode
from .serializers import (
    ProductSerializer, StockMovementSerializer, WarehouseSerializer,
    UnitOfMeasureSerializer, StockMovementLineSerializer, ProductCategorySerializer,
    StockLedgerSerializer, DeliveryOrderSerializer, GoodsReceiptSerializer,
    StockLevelSerializer, GoodsReceiptLineSerializer, DeliveryOrderLineSerializer,
    InternalRequisitionSerializer, ItemValuationMethodSerializer,
    CostLayerSerializer, CostLayerDetailSerializer, ValuationChangeLogSerializer,
    ItemSerializer, ItemOperationalExtensionSerializer, ItemWarehouseConfigSerializer,
    ItemUOMConversionSerializer, MovementEventSerializer, WarehouseBinSerializer,
    ItemSupplierSerializer, ItemFEFOConfigSerializer, InTransitShipmentLineSerializer,
    StandardCostVarianceSerializer, PurchasePriceVarianceSerializer,
    LandedCostComponentSerializer, LandedCostPreviewSerializer, InTransitShipmentLineSerializer,
    LandedCostVoucherSerializer, LandedCostAllocationSerializer,
    ReturnToVendorSerializer, ReturnToVendorLineSerializer,
    # Phase 3: QC & Compliance
    StockHoldSerializer, QCCheckpointSerializer, QCResultSerializer,
    BatchLotSerializer, SerialNumberSerializer,
    # Material Issue Management
    MaterialIssueSerializer, MaterialIssueLineSerializer,
    # Warehouse Category Mapping
    WarehouseCategoryMappingSerializer, WarehouseOverrideLogSerializer,
    WarehouseValidationRequestSerializer, WarehouseOverrideCreateSerializer
)
from .services.valuation_service import ValuationService
from .services.stock_service import InventoryService
from .services.replenishment_service import ReplenishmentService
from .services.landed_cost_voucher_service import LandedCostVoucherService
from .services.rtv_service import RTVService
from .services.gl_preview_service import StockGLPreviewService
from .services.material_issue_service import MaterialIssueService

class CompanyScopedQuerysetMixin:
    permission_classes = [IsAuthenticated]

    def get_company(self):
        return getattr(self.request, "company", None)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

class ProductViewSet(viewsets.ModelViewSet):
    # Legacy viewset - Product model is deprecated
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class ItemViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = ItemSerializer

    def get_queryset(self):
        qs = Item.objects.select_related('company', 'category', 'uom', 'budget_item', 'budget_item__uom').prefetch_related(
            'warehouse_configs',
            'warehouse_configs__warehouse',
            'budget_item__operational_extension',
            'uom_conversions',
            'uom_conversions__from_uom',
            'uom_conversions__to_uom',
        )
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)
        budget_item_id = self.request.query_params.get('budget_item')
        if budget_item_id:
            qs = qs.filter(models.Q(budget_item_id=budget_item_id) | models.Q(item__budget_item_id=budget_item_id))
        category_id = self.request.query_params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)
        code = self.request.query_params.get('code')
        if code:
            qs = qs.filter(code__icontains=code)
        active = self.request.query_params.get('active')
        if active and active.lower() in {'true', '1', 'yes'}:
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        company = self.get_company()
        if not company:
            raise serializers.ValidationError({'detail': 'Active company context is required'})
        serializer.save(company=company)

class WarehouseBinViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = WarehouseBinSerializer

    def get_queryset(self):
        qs = WarehouseBin.objects.select_related('warehouse', 'company')
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)
        warehouse_id = self.request.query_params.get('warehouse')
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        return qs

class ItemOperationalExtensionViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = ItemOperationalExtensionSerializer

    def get_queryset(self):
        qs = ItemOperationalExtension.objects.select_related('budget_item', 'company', 'purchase_uom', 'sales_uom', 'stock_uom')
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)
        budget_item_id = self.request.query_params.get('budget_item')
        if budget_item_id:
            qs = qs.filter(models.Q(budget_item_id=budget_item_id) | models.Q(item__budget_item_id=budget_item_id))
        return qs

class ItemWarehouseConfigViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = ItemWarehouseConfigSerializer

    def get_queryset(self):
        qs = ItemWarehouseConfig.objects.select_related('budget_item', 'warehouse', 'company', 'pack_size_uom')
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)
        warehouse_id = self.request.query_params.get('warehouse')
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        budget_item_id = self.request.query_params.get('budget_item')
        if budget_item_id:
            qs = qs.filter(models.Q(budget_item_id=budget_item_id) | models.Q(item__budget_item_id=budget_item_id))
        item_id = self.request.query_params.get('item')
        if item_id:
            qs = qs.filter(item_id=item_id)
        return qs

class ItemUOMConversionViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = ItemUOMConversionSerializer

    def get_queryset(self):
        qs = ItemUOMConversion.objects.select_related('budget_item', 'from_uom', 'to_uom', 'company')
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)
        item_id = self.request.query_params.get('item')
        if item_id:
            qs = qs.filter(item_id=item_id)
        budget_item_id = self.request.query_params.get('budget_item')
        if budget_item_id:
            qs = qs.filter(models.Q(budget_item_id=budget_item_id) | models.Q(item__budget_item_id=budget_item_id))
        context_flag = self.request.query_params.get('context')
        if context_flag:
            flag = context_flag.lower()
            if flag == 'purchase':
                qs = qs.filter(is_purchase_conversion=True)
            elif flag == 'sales':
                qs = qs.filter(is_sales_conversion=True)
            elif flag == 'stock':
                qs = qs.filter(is_stock_conversion=True)
        return qs

class MovementEventViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = MovementEventSerializer

    def get_queryset(self):
        qs = MovementEvent.objects.select_related('budget_item', 'warehouse', 'stock_uom', 'source_uom')
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)
        item_id = self.request.query_params.get('item')
        if item_id:
            qs = qs.filter(item_id=item_id)
        warehouse_id = self.request.query_params.get('warehouse')
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        event_type = self.request.query_params.get('event_type')
        if event_type:
            qs = qs.filter(event_type__iexact=event_type)
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(event_date__gte=date_from)
        if date_to:
            qs = qs.filter(event_date__lte=date_to)
        return qs.order_by('-event_date', '-id')

class InTransitShipmentLineViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = InTransitShipmentLineSerializer

    def get_queryset(self):
        qs = InTransitShipmentLine.objects.select_related(
            'item', 'from_warehouse', 'to_warehouse', 'movement', 'movement_line'
        )
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)
        item_id = self.request.query_params.get('item')
        if item_id:
            qs = qs.filter(item_id=item_id)
        warehouse_id = self.request.query_params.get('warehouse')
        if warehouse_id:
            qs = qs.filter(models.Q(from_warehouse_id=warehouse_id) | models.Q(to_warehouse_id=warehouse_id))
        return qs.order_by('-created_at')

class ItemSupplierViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = ItemSupplierSerializer

    def get_queryset(self):
        qs = ItemSupplier.objects.select_related('budget_item', 'supplier', 'supplier_pack_uom')
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)
        item_id = self.request.query_params.get('item')
        if item_id:
            qs = qs.filter(item_id=item_id)
        budget_item_id = self.request.query_params.get('budget_item')
        if budget_item_id:
            qs = qs.filter(budget_item_id=budget_item_id)
        supplier_id = self.request.query_params.get('supplier')
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        return qs

class ItemFEFOConfigViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = ItemFEFOConfigSerializer

    def get_queryset(self):
        qs = ItemFEFOConfig.objects.select_related('budget_item', 'warehouse')
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)
        item_id = self.request.query_params.get('item')
        if item_id:
            qs = qs.filter(item_id=item_id)
        budget_item_id = self.request.query_params.get('budget_item')
        if budget_item_id:
            qs = qs.filter(budget_item_id=budget_item_id)
        warehouse_id = self.request.query_params.get('warehouse')
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        return qs
class StockMovementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = StockMovementSerializer

    def get_queryset(self):
        qs = (
            StockMovement.objects.select_related('company', 'from_warehouse', 'to_warehouse')
            .prefetch_related('lines__budget_item', 'lines__cost_center', 'lines__project')
            .order_by('-movement_date')
        )
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
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status__iexact=status_filter)
        return qs

    @action(detail=True, methods=['post'])
    def confirm_receipt(self, request, pk=None):
        movement = self.get_object()
        receipt_date = request.data.get('receipt_date')
        InventoryService.confirm_transfer_receipt(movement, receipt_date=receipt_date)
        serializer = self.get_serializer(movement)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='gl-preview')
    def gl_preview(self, request, pk=None):
        movement = self.get_object()
        preview = StockGLPreviewService.preview_stock_movement(movement)
        return Response(preview)

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
        qs_items = BudgetItemCode.objects.all()
        qs_wh = Warehouse.objects.all()
        qs_mv = StockMovement.objects.all()
        if company:
            qs_items = qs_items.filter(company=company)
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

        master_summary = {
            'items': qs_items.count(),
            'operational_profiles': ItemOperationalExtension.objects.filter(company=company).count() if company else ItemOperationalExtension.objects.count(),
            'warehouse_configs': ItemWarehouseConfig.objects.filter(company=company).exclude(warehouse__isnull=True).count() if company else ItemWarehouseConfig.objects.exclude(warehouse__isnull=True).count(),
            'global_configs': ItemWarehouseConfig.objects.filter(company=company, warehouse__isnull=True).count() if company else ItemWarehouseConfig.objects.filter(warehouse__isnull=True).count(),
            'uom_conversions': ItemUOMConversion.objects.filter(company=company).count() if company else ItemUOMConversion.objects.count(),
            'gaps': {
                'missing_operational_profile': qs_items.filter(operational_extension__isnull=True).count(),
                'missing_conversion_definition': qs_items.filter(uom_conversions__isnull=True).distinct().count(),
            }
        }

        data = {
            'items': qs_items.count(),
            'warehouses': qs_wh.count(),
            'movements': movements_count,
            'master_summary': master_summary,
            'movement_events': MovementEvent.objects.filter(company=company).count() if company else MovementEvent.objects.count(),
        }
        return Response(data)


class StockLedgerSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, 'company', None)
        qs = StockLedger.objects.all()
        if company:
            qs = qs.filter(company=company)

        total_skus_tracked = qs.values('budget_item').distinct().count()
        last = qs.order_by('-transaction_date', '-id').values_list('transaction_date', flat=True).first()

        # Rough approximation for ledger value: sum of balance_value of the latest entry per (budget_item, warehouse)
        ledger_value = 0
        try:
            latest_map = {}
            for row in qs.values('budget_item', 'warehouse', 'transaction_date', 'id', 'balance_value'):
                key = (row['budget_item'], row['warehouse'])
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

        qs = MovementEvent.objects.select_related('budget_item', 'warehouse', 'stock_uom', 'source_uom')
        if company:
            qs = qs.filter(company=company)
        qs = qs.order_by('-event_timestamp', '-id')[:limit]

        events = []
        for ev in qs:
            reference = ev.reference_number or f"{ev.reference_document_type or ''}#{ev.reference_document_id or ''}".strip('#')
            journal_impact = f"{ev.event_type}: {ev.qty_change} {ev.stock_uom.code}"
            events.append({
                'id': ev.id,
                'event': ev.event_type,
                'reference': reference,
                'journal_impact': journal_impact,
                'status': 'synced',
                'timestamp': ev.event_timestamp.isoformat() if ev.event_timestamp else None,
                'item_code': ev.budget_item.code,
                'warehouse_code': ev.warehouse.code,
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
        qs = ItemValuationMethod.objects.select_related('budget_item', 'warehouse').order_by('-effective_date')
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)

        # Filter by budget item
        budget_item_id = self.request.query_params.get('budget_item')
        if budget_item_id:
            qs = qs.filter(budget_item_id=budget_item_id)

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
            product=BudgetItemCode.objects.get(id=product_id, company=company),
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
        qs = CostLayer.objects.select_related('budget_item', 'warehouse').order_by('-receipt_date')
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)

        # Filter by budget item
        budget_item_id = self.request.query_params.get('budget_item')
        if budget_item_id:
            qs = qs.filter(budget_item_id=budget_item_id)

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
        product = BudgetItemCode.objects.get(id=product_id, company=company)
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
            'budget_item', 'warehouse', 'requested_by', 'approved_by'
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
        products = BudgetItemCode.objects.filter(company=company, track_inventory=True)
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
            product = BudgetItemCode.objects.get(id=product_id, company=company)
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


class ReplenishmentSuggestionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, 'company', None)
        warehouse_id = request.query_params.get('warehouse')
        suggestions = ReplenishmentService.get_suggestions(company=company, warehouse_id=warehouse_id)
        return Response({'results': suggestions})


class AutoReplenishmentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        company = getattr(request, 'company', None)
        config_ids = request.data.get('config_ids') or []
        if not isinstance(config_ids, list) or not config_ids:
            return Response({'error': 'config_ids list is required'}, status=status.HTTP_400_BAD_REQUEST)
        clean_ids = [int(cid) for cid in config_ids if str(cid).isdigit()]
        if not clean_ids:
            return Response({'error': 'No valid config IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        result = ReplenishmentService.create_purchase_requisitions(
            company=company,
            user=request.user,
            config_ids=clean_ids,
        )
        return Response(result)


# ========================================
# PHASE 2: VARIANCE TRACKING VIEWS
# ========================================

class StandardCostVarianceViewSet(viewsets.ModelViewSet):
    """ViewSet for Standard Cost Variance tracking"""
    permission_classes = [IsAuthenticated]
    serializer_class = StandardCostVarianceSerializer
    filterset_fields = ['product', 'warehouse', 'transaction_type', 'variance_type', 'posted_to_gl']
    search_fields = ['product__code', 'product__name', 'notes']
    ordering_fields = ['transaction_date', 'total_variance_amount', 'created_at']
    ordering = ['-transaction_date']

    def get_queryset(self):
        company = getattr(self.request, 'company', None)
        qs = StandardCostVariance.objects.filter(company=company).select_related(
            'product', 'warehouse'
        )

        # Date range filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(transaction_date__gte=start_date)
        if end_date:
            qs = qs.filter(transaction_date__lte=end_date)

        return qs

    @action(detail=True, methods=['post'])
    def post_to_gl(self, request, pk=None):
        """Post variance to GL"""
        from .services.variance_service import VarianceTrackingService

        try:
            result = VarianceTrackingService.post_standard_variance_to_gl(pk)
            return Response({
                'status': 'posted',
                'je_id': result['je_id'],
                'message': f"Variance posted to GL (JE#{result['je_id']})"
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PurchasePriceVarianceViewSet(viewsets.ModelViewSet):
    """ViewSet for Purchase Price Variance tracking"""
    permission_classes = [IsAuthenticated]
    serializer_class = PurchasePriceVarianceSerializer
    filterset_fields = ['product', 'warehouse', 'goods_receipt', 'variance_type', 'posted_to_gl']
    search_fields = ['product__code', 'product__name', 'goods_receipt__grn_number', 'notes']
    ordering_fields = ['created_at', 'total_variance_amount']
    ordering = ['-created_at']

    def get_queryset(self):
        company = getattr(self.request, 'company', None)
        qs = PurchasePriceVariance.objects.filter(company=company).select_related(
            'product', 'warehouse', 'goods_receipt'
        )

        # Date range filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(goods_receipt__receipt_date__gte=start_date)
        if end_date:
            qs = qs.filter(goods_receipt__receipt_date__lte=end_date)

        return qs

    @action(detail=True, methods=['post'])
    def post_to_gl(self, request, pk=None):
        """Post PPV to GL"""
        from .services.variance_service import VarianceTrackingService

        try:
            result = VarianceTrackingService.post_ppv_to_gl(pk)
            return Response({
                'status': 'posted',
                'je_id': result['je_id'],
                'message': f"PPV posted to GL (JE#{result['je_id']})"
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VarianceSummaryView(APIView):
    """Get variance summary for reporting"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .services.variance_service import VarianceTrackingService

        company = getattr(request, 'company', None)
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        product_id = request.query_params.get('product')
        warehouse_id = request.query_params.get('warehouse')

        product = None
        warehouse = None

        if product_id:
            product = BudgetItemCode.objects.filter(id=product_id, company=company).first()
        if warehouse_id:
            warehouse = Warehouse.objects.filter(id=warehouse_id, company=company).first()

        summary = VarianceTrackingService.get_variance_summary(
            company=company,
            start_date=start_date,
            end_date=end_date,
            product=product,
            warehouse=warehouse
        )

        return Response(summary)


# ========================================
# PHASE 2: ENHANCED LANDED COST VIEWS
# ========================================

class LandedCostComponentViewSet(viewsets.ModelViewSet):
    """ViewSet for Landed Cost Components"""
    permission_classes = [IsAuthenticated]
    serializer_class = LandedCostComponentSerializer
    filterset_fields = ['goods_receipt', 'component_type', 'posted_to_gl']
    search_fields = ['description', 'invoice_number', 'goods_receipt__grn_number']
    ordering_fields = ['created_at', 'total_amount']
    ordering = ['-created_at']

    def get_queryset(self):
        company = getattr(self.request, 'company', None)
        return LandedCostComponent.objects.filter(company=company).select_related(
            'goods_receipt', 'applied_by'
        ).prefetch_related('line_apportionments')

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get summary for a specific landed cost component"""
        component = self.get_object()

        line_details = []
        for apportionment in component.line_apportionments.all():
            line_details.append({
                'product_code': apportionment.budget_item.code,
                'product_name': apportionment.budget_item.name,
                'basis_value': float(apportionment.basis_value),
                'allocation_percentage': float(apportionment.allocation_percentage),
                'apportioned_amount': float(apportionment.apportioned_amount),
                'cost_per_unit_adjustment': float(apportionment.cost_per_unit_adjustment)
            })

        return Response({
            'component_id': component.id,
            'type': component.get_component_type_display(),
            'total_amount': float(component.total_amount),
            'to_inventory': float(component.apportioned_to_inventory or 0),
            'to_cogs': float(component.apportioned_to_cogs or 0),
            'posted_to_gl': component.posted_to_gl,
            'line_details': line_details
        })

    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """Reverse a landed cost component"""
        from .services.landed_cost_service import LandedCostService

        component = self.get_object()
        reason = request.data.get('reason', '')

        if not reason:
            return Response({'error': 'Reason is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reversal_je = LandedCostService.reverse_landed_cost(
                component_id=component.id,
                reason=reason,
                reversed_by=request.user
            )
            return Response({
                'status': 'reversed',
                'reversal_je_id': reversal_je.id,
                'message': 'Landed cost successfully reversed'
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LandedCostPreviewView(APIView):
    """Preview landed cost apportionment before applying"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .services.landed_cost_service import LandedCostService

        serializer = LandedCostPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            preview = LandedCostService.preview_apportionment(
                grn_id=serializer.validated_data['goods_receipt'],
                components=serializer.validated_data['components'],
                apportionment_method=serializer.validated_data['apportionment_method']
            )
            return Response(preview)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LandedCostApplyView(APIView):
    """Apply landed costs to a GRN"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .services.landed_cost_service import LandedCostService

        company = getattr(request, 'company', None)
        grn_id = request.data.get('goods_receipt')
        components = request.data.get('components', [])
        apportionment_method = request.data.get('apportionment_method', 'QUANTITY')
        notes = request.data.get('notes', '')

        if not grn_id or not components:
            return Response({
                'error': 'goods_receipt and components are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            created_components = LandedCostService.apply_landed_costs(
                grn_id=grn_id,
                components=components,
                apportionment_method=apportionment_method,
                applied_by=request.user,
                notes=notes
            )

            return Response({
                'status': 'applied',
                'component_ids': [c.id for c in created_components],
                'total_components': len(created_components),
                'message': f'Successfully applied {len(created_components)} landed cost components'
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LandedCostSummaryView(APIView):
    """Get summary of landed costs for a GRN"""
    permission_classes = [IsAuthenticated]

    def get(self, request, grn_id):
        from .services.landed_cost_service import LandedCostService

        try:
            summary = LandedCostService.get_landed_cost_summary(grn_id)
            return Response(summary)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ========================================
# PHASE 2: VALUATION CHANGE APPROVAL WORKFLOW
# ========================================

class ValuationChangeLogViewSet(viewsets.ModelViewSet):
    """ViewSet for valuation method change requests and approvals"""
    permission_classes = [IsAuthenticated]
    serializer_class = ValuationChangeLogSerializer
    filterset_fields = ['product', 'warehouse', 'status', 'old_method', 'new_method']
    search_fields = ['product__code', 'product__name', 'reason']
    ordering_fields = ['requested_date', 'effective_date', 'revaluation_amount']
    ordering = ['-requested_date']

    def get_queryset(self):
        company = getattr(self.request, 'company', None)
        return ValuationChangeLog.objects.filter(company=company).select_related(
            'product', 'warehouse', 'requested_by', 'approved_by'
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a valuation change request"""
        change_log = self.get_object()

        if change_log.status != 'PENDING':
            return Response({
                'error': 'Only pending requests can be approved'
            }, status=status.HTTP_400_BAD_REQUEST)

        change_log.status = 'APPROVED'
        change_log.approved_by = request.user
        change_log.approval_date = timezone.now()
        change_log.save()

        # TODO: Trigger revaluation workflow on effective date

        return Response({
            'status': 'approved',
            'message': 'Valuation change request approved'
        })

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a valuation change request"""
        change_log = self.get_object()
        rejection_reason = request.data.get('rejection_reason', '')

        if change_log.status != 'PENDING':
            return Response({
                'error': 'Only pending requests can be rejected'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not rejection_reason:
            return Response({
                'error': 'Rejection reason is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        change_log.status = 'REJECTED'
        change_log.rejection_reason = rejection_reason
        change_log.approved_by = request.user
        change_log.approval_date = timezone.now()
        change_log.save()

        return Response({
            'status': 'rejected',
            'message': 'Valuation change request rejected'
        })

    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Get all pending approval requests"""
        company = getattr(request, 'company', None)
        pending = ValuationChangeLog.objects.filter(
            company=company,
            status='PENDING'
        ).select_related('budget_item', 'warehouse', 'requested_by')

        serializer = self.get_serializer(pending, many=True)
        return Response({
            'count': pending.count(),
            'results': serializer.data
        })


# ============================================================================
# LANDED COST VOUCHER VIEWS
# ============================================================================

class LandedCostVoucherViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for Landed Cost Vouchers."""

    serializer_class = LandedCostVoucherSerializer

    def get_queryset(self):
        company = self.get_company()
        queryset = LandedCostVoucher.objects.filter(company=company)

        # Filter by status
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Filter by date range
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        if date_from:
            queryset = queryset.filter(voucher_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(voucher_date__lte=date_to)

        return queryset.select_related(
            'submitted_by', 'approved_by'
        ).prefetch_related('allocations').order_by('-created_at')

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit voucher for approval."""
        voucher = self.get_object()

        try:
            LandedCostVoucherService.submit_voucher(
                voucher=voucher,
                submitted_by=request.user
            )
            return Response({
                'status': 'success',
                'message': f'Voucher {voucher.voucher_number} submitted for approval'
            })
        except ValueError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve voucher."""
        voucher = self.get_object()

        try:
            LandedCostVoucherService.approve_voucher(
                voucher=voucher,
                approved_by=request.user
            )
            return Response({
                'status': 'success',
                'message': f'Voucher {voucher.voucher_number} approved'
            })
        except ValueError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def allocate(self, request, pk=None):
        """Allocate voucher to cost layers."""
        voucher = self.get_object()
        allocation_plan = request.data.get('allocation_plan', [])

        try:
            allocations = LandedCostVoucherService.allocate_to_cost_layers(
                voucher=voucher,
                allocation_plan=allocation_plan,
                allocated_by=request.user
            )
            return Response({
                'status': 'success',
                'message': f'Voucher allocated to {len(allocations)} cost layers',
                'allocations': LandedCostAllocationSerializer(allocations, many=True).data
            })
        except (ValueError, Exception) as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def generate_allocation_plan(self, request, pk=None):
        """Generate allocation plan for voucher."""
        voucher = self.get_object()
        grn_ids = request.data.get('goods_receipt_ids', [])
        method = request.data.get('apportionment_method', 'BY_VALUE')

        try:
            goods_receipts = GoodsReceipt.objects.filter(
                id__in=grn_ids,
                company=voucher.company
            )

            allocation_plan = LandedCostVoucherService.generate_allocation_plan(
                voucher=voucher,
                goods_receipts=goods_receipts,
                apportionment_method=method
            )

            return Response({
                'status': 'success',
                'allocation_plan': allocation_plan
            })
        except (ValueError, Exception) as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def post_to_gl(self, request, pk=None):
        """Post voucher to GL."""
        voucher = self.get_object()

        try:
            je_id = LandedCostVoucherService.post_voucher_to_gl(voucher)
            return Response({
                'status': 'success',
                'message': f'Voucher posted to GL (JE #{je_id})',
                'je_id': je_id
            })
        except ValueError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get voucher summary."""
        voucher = self.get_object()
        summary = LandedCostVoucherService.get_voucher_summary(voucher)
        return Response(summary)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel voucher."""
        voucher = self.get_object()
        reason = request.data.get('reason', 'No reason provided')

        try:
            LandedCostVoucherService.cancel_voucher(voucher, reason)
            return Response({
                'status': 'success',
                'message': f'Voucher {voucher.voucher_number} cancelled'
            })
        except ValueError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class LandedCostAllocationViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for Landed Cost Allocations."""

    serializer_class = LandedCostAllocationSerializer

    def get_queryset(self):
        company = self.get_company()
        queryset = LandedCostAllocation.objects.filter(company=company)

        # Filter by voucher
        voucher_id = self.request.query_params.get('voucher', None)
        if voucher_id:
            queryset = queryset.filter(voucher_id=voucher_id)

        # Filter by budget item
        budget_item_id = self.request.query_params.get('budget_item', None)
        if budget_item_id:
            queryset = queryset.filter(budget_item_id=budget_item_id)

        return queryset.select_related(
            'voucher', 'goods_receipt', 'budget_item', 'cost_layer'
        ).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """Reverse an allocation."""
        allocation = self.get_object()
        reason = request.data.get('reason', 'No reason provided')

        try:
            LandedCostVoucherService.reverse_allocation(allocation, reason)
            return Response({
                'status': 'success',
                'message': 'Allocation reversed successfully'
            })
        except (ValueError, Exception) as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# RETURN TO VENDOR (RTV) VIEWS
# ============================================================================

class ReturnToVendorViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for Return To Vendor (RTV)."""

    serializer_class = ReturnToVendorSerializer

    def get_queryset(self):
        company = self.get_company()
        queryset = ReturnToVendor.objects.filter(company=company)

        # Filter by status
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Filter by supplier
        supplier_id = self.request.query_params.get('supplier_id', None)
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)

        # Filter by date range
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        if date_from:
            queryset = queryset.filter(rtv_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(rtv_date__lte=date_to)

        return queryset.select_related(
            'goods_receipt', 'warehouse', 'requested_by', 'approved_by'
        ).prefetch_related('lines').order_by('-created_at')

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit RTV for approval."""
        rtv = self.get_object()

        try:
            RTVService.submit_rtv(rtv)
            return Response({
                'status': 'success',
                'message': f'RTV {rtv.rtv_number} submitted for approval'
            })
        except ValueError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve RTV and create negative movement events."""
        rtv = self.get_object()

        try:
            RTVService.approve_rtv(rtv, approved_by=request.user)
            return Response({
                'status': 'success',
                'message': f'RTV {rtv.rtv_number} approved and movement events created'
            })
        except ValueError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete RTV and reverse budget."""
        rtv = self.get_object()

        refund_amount = request.data.get('refund_amount', None)
        debit_note_number = request.data.get('debit_note_number', None)
        debit_note_date = request.data.get('debit_note_date', None)
        actual_delivery_date = request.data.get('actual_delivery_date', None)

        try:
            RTVService.complete_rtv(
                rtv=rtv,
                refund_amount=refund_amount,
                debit_note_number=debit_note_number,
                debit_note_date=debit_note_date,
                actual_delivery_date=actual_delivery_date
            )
            return Response({
                'status': 'success',
                'message': f'RTV {rtv.rtv_number} completed and posted to GL'
            })
        except ValueError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def update_shipping(self, request, pk=None):
        """Update shipping information."""
        rtv = self.get_object()

        carrier = request.data.get('carrier')
        tracking_number = request.data.get('tracking_number')
        pickup_date = request.data.get('pickup_date')
        expected_delivery_date = request.data.get('expected_delivery_date', None)

        try:
            RTVService.update_shipping_info(
                rtv=rtv,
                carrier=carrier,
                tracking_number=tracking_number,
                pickup_date=pickup_date,
                expected_delivery_date=expected_delivery_date
            )
            return Response({
                'status': 'success',
                'message': 'Shipping information updated'
            })
        except (ValueError, Exception) as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get RTV summary."""
        rtv = self.get_object()
        summary = RTVService.get_rtv_summary(rtv)
        return Response(summary)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel RTV."""
        rtv = self.get_object()
        reason = request.data.get('reason', 'No reason provided')

        try:
            RTVService.cancel_rtv(rtv, reason)
            return Response({
                'status': 'success',
                'message': f'RTV {rtv.rtv_number} cancelled'
            })
        except ValueError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class ReturnToVendorLineViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for Return To Vendor Line items."""

    serializer_class = ReturnToVendorLineSerializer

    def get_queryset(self):
        company = self.get_company()
        queryset = ReturnToVendorLine.objects.filter(company=company)

        # Filter by RTV
        rtv_id = self.request.query_params.get('rtv', None)
        if rtv_id:
            queryset = queryset.filter(rtv_id=rtv_id)

        # Filter by budget item
        budget_item_id = self.request.query_params.get('budget_item', None)
        if budget_item_id:
            queryset = queryset.filter(budget_item_id=budget_item_id)

        return queryset.select_related(
            'rtv', 'budget_item', 'uom', 'movement_event'
        ).order_by('-created_at')


# ============================================================================
# PHASE 3: QUALITY CONTROL & COMPLIANCE VIEWS
# ============================================================================

class StockHoldViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for managing stock holds"""
    serializer_class = StockHoldSerializer

    def get_queryset(self):
        company = self.get_company()
        queryset = StockHold.objects.filter(company=company)

        # Filters
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        warehouse_id = self.request.query_params.get('warehouse')
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        hold_type = self.request.query_params.get('hold_type')
        if hold_type:
            queryset = queryset.filter(hold_type=hold_type)

        # Show only overdue if requested
        if self.request.query_params.get('overdue') == 'true':
            from datetime import date
            queryset = queryset.filter(
                status='ACTIVE',
                expected_release_date__lt=date.today()
            )

        return queryset.select_related(
            'budget_item', 'warehouse', 'batch_lot', 'hold_by', 'released_by'
        ).order_by('-hold_date')

    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Release a stock hold"""
        from apps.inventory.services.qc_service import QCService

        hold = self.get_object()
        disposition = request.data.get('disposition')
        notes = request.data.get('notes', '')

        try:
            updated_hold = QCService.release_hold(
                hold, request.user, disposition, notes
            )
            serializer = self.get_serializer(updated_hold)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class QCCheckpointViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for QC checkpoint configuration"""
    serializer_class = QCCheckpointSerializer

    def get_queryset(self):
        company = self.get_company()
        queryset = QCCheckpoint.objects.filter(company=company)

        warehouse_id = self.request.query_params.get('warehouse')
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        if self.request.query_params.get('active_only') == 'true':
            queryset = queryset.filter(is_active=True)

        return queryset.select_related('warehouse', 'assigned_to')


class QCResultViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for QC inspection results"""
    serializer_class = QCResultSerializer

    def get_queryset(self):
        company = self.get_company()
        queryset = QCResult.objects.filter(company=company)

        # Filter by GRN
        grn_id = self.request.query_params.get('grn')
        if grn_id:
            queryset = queryset.filter(grn_id=grn_id)

        # Filter by checkpoint
        checkpoint_id = self.request.query_params.get('checkpoint')
        if checkpoint_id:
            queryset = queryset.filter(checkpoint_id=checkpoint_id)

        # Filter by status
        qc_status = self.request.query_params.get('qc_status')
        if qc_status:
            queryset = queryset.filter(qc_status=qc_status)

        # Date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(inspected_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(inspected_date__lte=date_to)

        return queryset.select_related(
            'grn', 'checkpoint', 'inspected_by'
        ).order_by('-inspected_date')

    @action(detail=False, methods=['get'])
    def pending_inspections(self, request):
        """Get GRNs pending QC inspection"""
        from apps.inventory.services.qc_service import QCService

        company = self.get_company()
        warehouse_id = request.query_params.get('warehouse')
        warehouse = None
        if warehouse_id:
            warehouse = Warehouse.objects.get(id=warehouse_id, company=company)

        pending_grns = QCService.get_pending_inspections(company, warehouse)

        # Simplified GRN data
        data = [{
            'id': grn.id,
            'grn_number': grn.grn_number,
            'receipt_date': grn.receipt_date,
            'warehouse_id': grn.warehouse_id,
            'warehouse_name': grn.warehouse.name
        } for grn in pending_grns]

        return Response(data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get QC performance statistics"""
        from apps.inventory.services.qc_service import QCService

        company = self.get_company()
        warehouse_id = request.query_params.get('warehouse')
        warehouse = None
        if warehouse_id:
            warehouse = Warehouse.objects.get(id=warehouse_id, company=company)

        stats = QCService.get_qc_statistics(company, warehouse)
        return Response(stats)


class BatchLotViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for batch/lot management"""
    serializer_class = BatchLotSerializer

    def get_queryset(self):
        company = self.get_company()
        queryset = BatchLot.objects.filter(company=company)

        # Filter by item
        budget_item_id = self.request.query_params.get('budget_item')
        if budget_item_id:
            queryset = queryset.filter(budget_item_id=budget_item_id)

        # Filter by status
        hold_status = self.request.query_params.get('hold_status')
        if hold_status:
            queryset = queryset.filter(hold_status=hold_status)

        # Filter by GRN
        grn_id = self.request.query_params.get('grn')
        if grn_id:
            queryset = queryset.filter(grn_id=grn_id)

        # Show only batches with stock
        if self.request.query_params.get('with_stock') == 'true':
            queryset = queryset.filter(current_qty__gt=0)

        # Show only expired
        if self.request.query_params.get('expired') == 'true':
            from datetime import date
            queryset = queryset.filter(exp_date__lt=date.today(), current_qty__gt=0)

        # Show expiring soon
        days_threshold = self.request.query_params.get('expiring_within_days')
        if days_threshold:
            from datetime import date, timedelta
            expiry_date = date.today() + timedelta(days=int(days_threshold))
            queryset = queryset.filter(
                exp_date__lte=expiry_date,
                exp_date__gte=date.today(),
                current_qty__gt=0
            )

        return queryset.select_related('budget_item', 'grn').order_by('fefo_sequence', 'exp_date')

    @action(detail=True, methods=['post'])
    def dispose(self, request, pk=None):
        """Dispose an expired batch"""
        from apps.inventory.services.batch_fefo_service import BatchFEFOService

        batch = self.get_object()
        disposal_method = request.data.get('disposal_method', 'SCRAP')
        notes = request.data.get('notes', '')

        try:
            updated_batch = BatchFEFOService.dispose_expired_batch(
                batch, request.user, disposal_method, notes
            )
            serializer = self.get_serializer(updated_batch)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class SerialNumberViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for serial number tracking"""
    serializer_class = SerialNumberSerializer

    def get_queryset(self):
        company = self.get_company()
        queryset = SerialNumber.objects.filter(company=company)

        # Filter by item
        budget_item_id = self.request.query_params.get('budget_item')
        if budget_item_id:
            queryset = queryset.filter(budget_item_id=budget_item_id)

        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Filter by batch
        batch_lot_id = self.request.query_params.get('batch_lot')
        if batch_lot_id:
            queryset = queryset.filter(batch_lot_id=batch_lot_id)

        # Search by serial number
        serial_search = self.request.query_params.get('serial_number')
        if serial_search:
            queryset = queryset.filter(serial_number__icontains=serial_search)

        return queryset.select_related('budget_item', 'batch_lot').order_by('-created_at')


# ============================================================================
# MATERIAL ISSUE MANAGEMENT VIEWS
# ============================================================================

class MaterialIssueViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for Material Issue Management"""
    serializer_class = MaterialIssueSerializer

    def get_queryset(self):
        company = self.get_company()
        queryset = MaterialIssue.objects.filter(company=company)

        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Filter by warehouse
        warehouse_id = self.request.query_params.get('warehouse')
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        # Filter by issue type
        issue_type = self.request.query_params.get('issue_type')
        if issue_type:
            queryset = queryset.filter(issue_type=issue_type)

        # Filter by cost center
        cost_center_id = self.request.query_params.get('cost_center')
        if cost_center_id:
            queryset = queryset.filter(cost_center_id=cost_center_id)

        # Filter by project
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        # Date range filter
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(issue_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(issue_date__lte=date_to)

        return queryset.select_related(
            'warehouse', 'cost_center', 'project', 'requested_by', 'issued_by', 'approved_by'
        ).prefetch_related('lines').order_by('-issue_date', '-created_at')

    def perform_create(self, serializer):
        company = self.get_company()
        if not company:
            raise serializers.ValidationError({'detail': 'Active company context is required'})
        serializer.save(company=company, requested_by=self.request.user)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit material issue for approval"""
        material_issue = self.get_object()

        try:
            MaterialIssueService.submit_issue(material_issue)
            serializer = self.get_serializer(material_issue)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve material issue"""
        material_issue = self.get_object()

        try:
            MaterialIssueService.approve_issue(material_issue, approved_by=request.user)
            serializer = self.get_serializer(material_issue)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def issue(self, request, pk=None):
        """Process material issue - deduct stock and create movements"""
        material_issue = self.get_object()

        try:
            result = MaterialIssueService.process_issue(material_issue, issued_by=request.user)
            return Response({
                'status': 'success',
                'message': f'Material issue {result["issue_number"]} processed successfully',
                **result
            })
        except ValidationError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel material issue"""
        material_issue = self.get_object()
        reason = request.data.get('reason', '')

        try:
            MaterialIssueService.cancel_issue(material_issue, reason=reason)
            return Response({
                'status': 'success',
                'message': f'Material issue {material_issue.issue_number} cancelled'
            })
        except ValidationError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get summary of material issue"""
        material_issue = self.get_object()
        summary = MaterialIssueService.get_issue_summary(material_issue)
        return Response(summary)

    @action(detail=False, methods=['get'])
    def available_batches(self, request):
        """Get available batches for item using FEFO"""
        company = self.get_company()
        warehouse_id = request.query_params.get('warehouse')
        budget_item_id = request.query_params.get('budget_item')

        if not warehouse_id or not budget_item_id:
            return Response({
                'error': 'warehouse and budget_item parameters are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.budgeting.models import BudgetItem
            budget_item = BudgetItem.objects.get(id=budget_item_id, company=company)
            warehouse = Warehouse.objects.get(id=warehouse_id, company=company)

            batches = MaterialIssueService.get_available_batches(company, warehouse, budget_item)
            return Response({'batches': batches})
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def available_serials(self, request):
        """Get available serial numbers for item"""
        company = self.get_company()
        warehouse_id = request.query_params.get('warehouse')
        budget_item_id = request.query_params.get('budget_item')

        if not warehouse_id or not budget_item_id:
            return Response({
                'error': 'warehouse and budget_item parameters are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.budgeting.models import BudgetItem
            budget_item = BudgetItem.objects.get(id=budget_item_id, company=company)
            warehouse = Warehouse.objects.get(id=warehouse_id, company=company)

            serials = MaterialIssueService.get_available_serials(company, warehouse, budget_item)
            return Response({'serial_numbers': serials})
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class MaterialIssueLineViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for Material Issue Line items"""
    serializer_class = MaterialIssueLineSerializer

    def get_queryset(self):
        company = self.get_company()
        queryset = MaterialIssueLine.objects.filter(company=company)

        # Filter by material issue
        material_issue_id = self.request.query_params.get('material_issue')
        if material_issue_id:
            queryset = queryset.filter(material_issue_id=material_issue_id)

        # Filter by budget item
        budget_item_id = self.request.query_params.get('budget_item')
        if budget_item_id:
            queryset = queryset.filter(budget_item_id=budget_item_id)

        return queryset.select_related(
            'material_issue', 'budget_item', 'item', 'uom', 'batch_lot', 'cost_center', 'project'
        ).order_by('-created_at')


# ============================================================================
# WAREHOUSE CATEGORY MAPPING VIEWSETS
# ============================================================================

class WarehouseCategoryMappingViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for Warehouse-Category Mapping configuration"""
    serializer_class = WarehouseCategoryMappingSerializer

    def get_queryset(self):
        company = self.get_company()
        queryset = WarehouseCategoryMapping.objects.filter(company=company)

        # Filter by warehouse
        warehouse_id = self.request.query_params.get('warehouse')
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        # Filter by category
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Filter by subcategory
        subcategory_id = self.request.query_params.get('subcategory')
        if subcategory_id:
            queryset = queryset.filter(subcategory_id=subcategory_id)

        # Filter by default flag
        is_default = self.request.query_params.get('is_default')
        if is_default and is_default.lower() in {'true', '1', 'yes'}:
            queryset = queryset.filter(is_default=True)

        return queryset.select_related(
            'warehouse', 'category', 'subcategory', 'created_by'
        ).order_by('priority', 'warehouse__code')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'])
    def validate_warehouse(self, request):
        """
        Validate warehouse selection for a given item

        POST /api/v1/inventory/warehouse-mappings/validate_warehouse/
        Body: {
            "budget_item_id": 123,
            "selected_warehouse_id": 456
        }

        Returns: {
            "is_valid": true/false,
            "warning_level": "INFO/WARNING/CRITICAL",
            "message": "...",
            "suggested_warehouse": {...},
            "requires_reason": true/false,
            "requires_approval": true/false,
            "allowed_warehouses": [...]
        }
        """
        validation_serializer = WarehouseValidationRequestSerializer(data=request.data)
        validation_serializer.is_valid(raise_exception=True)

        budget_item_id = validation_serializer.validated_data['budget_item_id']
        selected_warehouse_id = validation_serializer.validated_data['selected_warehouse_id']

        try:
            budget_item = BudgetItemCode.objects.get(id=budget_item_id)
            selected_warehouse = Warehouse.objects.get(id=selected_warehouse_id)

            # Use the model's validation method
            validation_result = WarehouseCategoryMapping.validate_warehouse_selection(
                item=budget_item,
                selected_warehouse=selected_warehouse,
                user=request.user
            )

            # Get allowed warehouses
            allowed_warehouses = WarehouseCategoryMapping.get_allowed_warehouses_for_item(budget_item)

            # Get suggested default warehouse
            suggested_warehouse = WarehouseCategoryMapping.get_default_warehouse_for_item(budget_item)

            # Format response
            response_data = {
                'is_valid': validation_result['is_valid'],
                'warning_level': validation_result['warning_level'],
                'message': validation_result['message'],
                'requires_reason': validation_result['requires_reason'],
                'requires_approval': validation_result['requires_approval'],
                'allowed_warehouses': [
                    {
                        'id': wh.id,
                        'code': wh.code,
                        'name': wh.name
                    } for wh in allowed_warehouses
                ],
                'suggested_warehouse': {
                    'id': suggested_warehouse.id,
                    'code': suggested_warehouse.code,
                    'name': suggested_warehouse.name
                } if suggested_warehouse else None
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except BudgetItemCode.DoesNotExist:
            return Response({
                'error': 'Budget item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Warehouse.DoesNotExist:
            return Response({
                'error': 'Warehouse not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def allowed_warehouses(self, request):
        """
        Get allowed warehouses for a given item

        GET /api/v1/inventory/warehouse-mappings/allowed_warehouses/?budget_item=123

        Returns: {
            "allowed_warehouses": [...],
            "suggested_warehouse": {...}
        }
        """
        budget_item_id = request.query_params.get('budget_item')
        if not budget_item_id:
            return Response({
                'error': 'budget_item parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            budget_item = BudgetItemCode.objects.get(id=budget_item_id)

            # Get allowed warehouses
            allowed_warehouses = WarehouseCategoryMapping.get_allowed_warehouses_for_item(budget_item)

            # Get suggested default warehouse
            suggested_warehouse = WarehouseCategoryMapping.get_default_warehouse_for_item(budget_item)

            response_data = {
                'allowed_warehouses': [
                    {
                        'id': wh.id,
                        'code': wh.code,
                        'name': wh.name,
                        'warehouse_type': wh.warehouse_type
                    } for wh in allowed_warehouses
                ],
                'suggested_warehouse': {
                    'id': suggested_warehouse.id,
                    'code': suggested_warehouse.code,
                    'name': suggested_warehouse.name,
                    'warehouse_type': suggested_warehouse.warehouse_type
                } if suggested_warehouse else None
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except BudgetItemCode.DoesNotExist:
            return Response({
                'error': 'Budget item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class WarehouseOverrideLogViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet for Warehouse Override Audit Log - Read-only with create action"""
    serializer_class = WarehouseOverrideLogSerializer

    def get_queryset(self):
        company = self.get_company()
        queryset = WarehouseOverrideLog.objects.filter(company=company)

        # Filter by transaction type
        transaction_type = self.request.query_params.get('transaction_type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        # Filter by budget item
        budget_item_id = self.request.query_params.get('budget_item')
        if budget_item_id:
            queryset = queryset.filter(budget_item_id=budget_item_id)

        # Filter by warehouse
        warehouse_id = self.request.query_params.get('warehouse')
        if warehouse_id:
            queryset = queryset.filter(
                models.Q(suggested_warehouse_id=warehouse_id) |
                models.Q(actual_warehouse_id=warehouse_id)
            )

        # Filter by warning level
        warning_level = self.request.query_params.get('warning_level')
        if warning_level:
            queryset = queryset.filter(warning_level=warning_level)

        # Filter by user
        overridden_by = self.request.query_params.get('overridden_by')
        if overridden_by:
            queryset = queryset.filter(overridden_by_id=overridden_by)

        return queryset.select_related(
            'budget_item', 'suggested_warehouse', 'actual_warehouse',
            'overridden_by', 'approved_by', 'reviewed_by'
        ).order_by('-overridden_at')

    @action(detail=False, methods=['post'])
    def log_override(self, request):
        """
        Create a new warehouse override log entry

        POST /api/v1/inventory/warehouse-overrides/log_override/
        Body: {
            "transaction_type": "GRN",
            "transaction_id": 123,
            "transaction_number": "GRN-001",
            "budget_item_id": 456,
            "suggested_warehouse_id": 789,
            "actual_warehouse_id": 101,
            "warning_level": "WARNING",
            "override_reason": "Urgent requirement",
            "was_approved": false
        }

        Returns: {
            "id": 1,
            "message": "Override logged successfully"
        }
        """
        override_serializer = WarehouseOverrideCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        override_serializer.is_valid(raise_exception=True)

        log_entry = override_serializer.save()

        return Response({
            'id': log_entry.id,
            'message': 'Override logged successfully',
            'log_entry': WarehouseOverrideLogSerializer(log_entry).data
        }, status=status.HTTP_201_CREATED)
