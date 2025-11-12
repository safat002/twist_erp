from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_UP
from math import sqrt
from typing import List, Optional

from datetime import timedelta
from django.db.models import Sum, Q
from django.utils import timezone

from apps.inventory.models import (
    ItemWarehouseConfig,
    StockLevel,
    InTransitShipmentLine,
    ItemSupplier,
)
from apps.procurement.models import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequisition,
    PurchaseRequisitionLine,
    SupplierBlackoutWindow,
)
from apps.budgeting.models import BudgetLine, CostCenter


@dataclass
class ReplenishmentSuggestion:
    config: ItemWarehouseConfig
    item_code: str
    item_name: str
    warehouse_name: str
    on_hand: Decimal
    on_order: Decimal
    in_transit: Decimal
    rop: Decimal
    recommended_qty: Decimal
    supplier: Optional[ItemSupplier]
    reason: str = ""
    budget_item_code: Optional[str] = None

    @property
    def available(self) -> Decimal:
        return self.on_hand + self.on_order + self.in_transit

    def as_dict(self):
        supplier_obj = getattr(self.supplier, 'supplier', None)
        return {
            'config_id': self.config.id,
            'item_id': self.config.item_id,
            'item_code': self.item_code,
            'item_name': self.item_name,
            'warehouse_id': self.config.warehouse_id,
            'warehouse_name': self.warehouse_name,
            'on_hand': float(self.on_hand),
            'on_order': float(self.on_order),
            'in_transit': float(self.in_transit),
            'available': float(self.available),
            'rop': float(self.rop),
            'recommended_qty': float(self.recommended_qty),
            'supplier_id': supplier_obj.id if supplier_obj else None,
            'supplier_name': supplier_obj.name if supplier_obj else None,
            'budget_item_code': self.budget_item_code,
            'reason': self.reason,
        }


class ReplenishmentService:
    """Advanced reorder planning service."""

    ACTIVE_PO_STATUSES = {
        PurchaseOrder.Status.DRAFT,
        PurchaseOrder.Status.PENDING_APPROVAL,
        PurchaseOrder.Status.APPROVED,
        PurchaseOrder.Status.ISSUED,
        PurchaseOrder.Status.PARTIALLY_RECEIVED,
    }

    @staticmethod
    def _z_score(service_level: Decimal | float | int) -> float:
        try:
            level = float(service_level or 95)
        except Exception:
            level = 95.0
        if level >= 99:
            return 2.33
        if level >= 98:
            return 2.05
        if level >= 97:
            return 1.88
        if level >= 96:
            return 1.75
        if level >= 95:
            return 1.65
        if level >= 92:
            return 1.41
        if level >= 90:
            return 1.28
        return 1.0

    @classmethod
    def _calculate_rop(cls, cfg: ItemWarehouseConfig) -> Decimal:
        avg_demand = cfg.avg_daily_demand or Decimal('0')
        lt_days = Decimal(cfg.lead_time_days or 0)
        demand_std = cfg.demand_std_dev or Decimal('0')
        lt_std = Decimal(cfg.lead_time_std_dev or 0)

        base = avg_demand * lt_days
        variance = (lt_days * (demand_std ** 2)) + ((avg_demand ** 2) * (lt_std ** 2))
        variance_float = max(float(variance), 0.0)
        safety = Decimal(str(cls._z_score(cfg.service_level_pct))) * Decimal(str(sqrt(variance_float)))
        rop = (base + safety).quantize(Decimal('0.001'))
        return max(rop, cfg.reorder_point or Decimal('0'))

    @staticmethod
    def _on_hand(company, item, warehouse) -> Decimal:
        qty = StockLevel.objects.filter(
            company=company,
            item=item,
            warehouse=warehouse
        ).aggregate(value=Sum('quantity'))['value'] or Decimal('0')
        return qty

    @classmethod
    def _on_order(cls, company, item, warehouse) -> Decimal:
        qs = PurchaseOrderLine.objects.filter(
            purchase_order__company=company,
            purchase_order__delivery_address=warehouse,
            purchase_order__status__in=cls.ACTIVE_PO_STATUSES,
            product=item,
        )
        qty = Decimal('0')
        for line in qs:
            qty += (line.quantity or Decimal('0')) - (line.received_quantity or Decimal('0'))
        return max(qty, Decimal('0'))

    @staticmethod
    def _in_transit(company, item, warehouse) -> Decimal:
        qty = InTransitShipmentLine.objects.filter(
            company=company,
            item=item,
            to_warehouse=warehouse,
        ).aggregate(value=Sum('quantity'))['value'] or Decimal('0')
        return qty

    @staticmethod
    def _supplier_blackout(supplier, target_date) -> bool:
        return SupplierBlackoutWindow.objects.filter(
            supplier=supplier,
            start_date__lte=target_date,
            end_date__gte=target_date,
        ).exists()

    @classmethod
    def _pick_supplier(cls, item) -> Optional[ItemSupplier]:
        today = timezone.now().date()
        suppliers = item.supplier_links.select_related('supplier').filter(is_active=True).order_by('preferred_rank')
        for link in suppliers:
            if cls._supplier_blackout(link.supplier, today):
                continue
            return link
        return None

    @classmethod
    def _build_suggestion(cls, cfg: ItemWarehouseConfig) -> Optional[ReplenishmentSuggestion]:
        if not cfg.warehouse or not cfg.item or not cfg.auto_replenish:
            return None

        company = cfg.company
        item = cfg.item
        warehouse = cfg.warehouse

        budget_item = getattr(cfg, 'budget_item', None) or getattr(cfg.budget_item, 'budget_item', None)
        fallback_code = budget_item.code if budget_item else item.code
        fallback_name = budget_item.name if budget_item else item.name
        rop = cls._calculate_rop(cfg)
        on_hand = cls._on_hand(company, item, warehouse)
        on_order = cls._on_order(company, item, warehouse)
        in_transit = cls._in_transit(company, item, warehouse)
        available = on_hand + on_order + in_transit

        if available > rop:
            return None

        supplier_link = cls._pick_supplier(item)
        if not supplier_link:
            return ReplenishmentSuggestion(
                config=cfg,
                item_code=fallback_code,
                item_name=fallback_name,
                warehouse_name=warehouse.name,
                on_hand=on_hand,
                on_order=on_order,
                in_transit=in_transit,
                rop=rop,
                recommended_qty=Decimal('0'),
                supplier=None,
                reason='No active supplier available',
            )

        shortfall = rop - available
        recommended = max(shortfall, cfg.economic_order_qty or Decimal('0'), Decimal('0'))
        supplier_moq = supplier_link.moq_qty or Decimal('0')
        supplier_multiple = supplier_link.multiple_qty or Decimal('0')
        if supplier_moq > 0:
            recommended = max(recommended, supplier_moq)
        if supplier_multiple > 0:
            ratio = recommended / supplier_multiple
            multiplier = ratio.to_integral_value(rounding=ROUND_UP)
            if multiplier == 0:
                multiplier = Decimal('1')
            recommended = supplier_multiple * multiplier

        if recommended <= 0:
            return None

        return ReplenishmentSuggestion(
            config=cfg,
            item_code=fallback_code,
            item_name=fallback_name,
            warehouse_name=warehouse.name,
            on_hand=on_hand,
            on_order=on_order,
            in_transit=in_transit,
            rop=rop,
            recommended_qty=recommended,
            supplier=supplier_link,
            reason='ROP breached',
            budget_item_code=budget_item.code if budget_item else None,
        )

    @classmethod
    def get_suggestions(cls, company, warehouse_id=None) -> List[dict]:
        if not company:
            return []
        configs = ItemWarehouseConfig.objects.select_related('item', 'warehouse').filter(
            company=company,
            auto_replenish=True,
            is_active=True,
            warehouse__isnull=False,
        )
        if warehouse_id:
            configs = configs.filter(warehouse_id=warehouse_id)

        results = []
        for cfg in configs:
            suggestion = cls._build_suggestion(cfg)
            if suggestion:
                results.append(suggestion.as_dict())
        return results

    @classmethod
    def _resolve_budget_line(cls, company, item):
        qs = BudgetLine.objects.filter(
            budget__company=company,
            procurement_class=BudgetLine.ProcurementClass.STOCK_ITEM,
        )
        if item.budget_item_id:
            qs = qs.filter(Q(item=item) | Q(budget_item_id=item.budget_item_id))
        else:
            qs = qs.filter(item=item)
        return qs.order_by('id').first()

    @classmethod
    def _resolve_cost_center(cls, company, budget_line):
        if budget_line and budget_line.budget and budget_line.budget.cost_center:
            return budget_line.budget.cost_center
        return CostCenter.objects.filter(company=company).first()

    @classmethod
    def create_purchase_requisitions(cls, *, company, user, config_ids: List[int]) -> dict:
        if not company or not user or not config_ids:
            return {'created': [], 'skipped': [{'reason': 'Missing company, user, or config IDs'}]}

        configs = ItemWarehouseConfig.objects.select_related('item', 'warehouse').filter(
            company=company,
            id__in=config_ids,
            auto_replenish=True,
            warehouse__isnull=False,
        )

        suggestions = []
        skips = []
        for cfg in configs:
            suggestion = cls._build_suggestion(cfg)
            if not suggestion:
                skips.append({'config_id': cfg.id, 'reason': 'No replenishment needed'})
                continue
            if suggestion.recommended_qty <= 0 or not suggestion.supplier:
                skips.append({'config_id': cfg.id, 'reason': suggestion.reason or 'Invalid quantity'})
                continue
            suggestions.append(suggestion)

        # Group suggestions by supplier for consolidated PRs
        grouped = defaultdict(list)
        for suggestion in suggestions:
            grouped[getattr(suggestion.supplier, 'supplier_id', None)].append(suggestion)

        created = []
        for supplier_id, bucket in grouped.items():
            first_cfg = bucket[0].config
            item = first_cfg.item
            budget_line = cls._resolve_budget_line(company, item)
            if not budget_line:
                skips.extend({'config_id': s.config.id, 'reason': 'No budget line for item'} for s in bucket)
                continue
            cost_center = cls._resolve_cost_center(company, budget_line)
            if not cost_center:
                skips.extend({'config_id': s.config.id, 'reason': 'No cost center configured'} for s in bucket)
                continue

            requisition = PurchaseRequisition.objects.create(
                company=company,
                cost_center=cost_center,
                requested_by=user,
                request_type=PurchaseRequisition.RequestType.STOCK_ITEM,
                justification="Auto replenishment triggered based on ROP",
                priority=PurchaseRequisition.Priority.NORMAL,
            )

            line_number = 1
            for suggestion in bucket:
                item = suggestion.config.item
                budget_master = getattr(item, 'budget_item', None)
                budget_line = cls._resolve_budget_line(company, item)
                if not budget_line:
                    skips.append({'config_id': suggestion.config.id, 'reason': 'No budget line for item'})
                    continue

                unit_cost = suggestion.supplier.last_purchase_price or getattr(budget_master, 'standard_price', None) or item.standard_cost or item.cost_price or Decimal('0')
                needed_by = timezone.now().date() + timedelta(days=suggestion.config.lead_time_days or 0)
                PurchaseRequisitionLine.objects.create(
                    requisition=requisition,
                    line_number=line_number,
                    budget_line=budget_line,
                    cost_center=cost_center,
                    product=item,
                    description=f"Auto replenish {budget_master.code if budget_master else item.code}",
                    quantity=suggestion.recommended_qty,
                    uom=(budget_master.uom if budget_master and budget_master.uom_id else item.uom),
                    estimated_unit_cost=unit_cost,
                    needed_by=needed_by,
                    metadata={
                        'supplier_code': suggestion.supplier.supplier.code if suggestion.supplier else None,
                        'reason': suggestion.reason,
                    },
                )
                line_number += 1

            requisition.refresh_totals(commit=True)
            created.append({'requisition_id': requisition.id, 'requisition_number': requisition.requisition_number})

        return {'created': created, 'skipped': skips}
