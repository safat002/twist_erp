from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, ROUND_UP
from typing import Optional
from django.utils import timezone
from django.db.models import Q

from apps.inventory.models import Item, ItemUOMConversion, UnitOfMeasure


class UoMConversionService:
    """Utility helpers for converting between purchase/stock/sales units."""

    @staticmethod
    def convert_quantity(
        *,
        item: Optional[Item],
        quantity: Decimal,
        from_uom: Optional[UnitOfMeasure] = None,
        to_uom: Optional[UnitOfMeasure] = None,
        context: str | None = None,
    ) -> Decimal:
        """
        Convert quantity between UoMs based on active conversion rules.
        context: 'purchase', 'sales', 'stock' to force flag matching.
        """
        if quantity is None:
            return Decimal('0')
        qty = Decimal(quantity)
        if not item:
            return qty
        budget_item = getattr(item, 'budget_item', None)
        to_uom = to_uom or getattr(budget_item, 'uom', None) or item.uom
        base_from_uom = UoMConversionService._default_from_uom(item=item, budget_item=budget_item, context=context)
        from_uom = from_uom or base_from_uom
        if not from_uom or from_uom_id_equals(from_uom, to_uom):
            return qty

        conversion = UoMConversionService._resolve_conversion(
            item=item,
            budget_item=budget_item,
            from_uom=from_uom,
            to_uom=to_uom,
            context=context,
        )
        if not conversion:
            return qty

        converted = qty * (conversion.conversion_factor or Decimal('1'))
        return UoMConversionService._apply_rounding(converted, conversion.rounding_rule)

    @staticmethod
    def _default_from_uom(*, item: Optional[Item], budget_item, context: Optional[str]):
        profile = item.get_operational_profile() if item else None
        stock_uom = getattr(profile, 'stock_uom', None) or getattr(budget_item, 'uom', None)
        if context == 'purchase':
            return getattr(profile, 'purchase_uom', None) or stock_uom
        if context == 'sales':
            return getattr(profile, 'sales_uom', None) or stock_uom
        return stock_uom

    @staticmethod
    def _resolve_conversion(*, item, budget_item, from_uom, to_uom, context):
        qs = ItemUOMConversion.objects.filter(
            Q(budget_item=budget_item) | Q(item=item, budget_item__isnull=True),
            from_uom=from_uom,
            to_uom=to_uom,
            effective_date__lte=timezone.now().date(),
        ).order_by('precedence', '-effective_date')
        if context == 'purchase':
            qs = qs.filter(is_purchase_conversion=True)
        elif context == 'sales':
            qs = qs.filter(is_sales_conversion=True)
        elif context == 'stock':
            qs = qs.filter(is_stock_conversion=True)
        return qs.first()

    @staticmethod
    def _apply_rounding(quantity: Decimal, rule: str) -> Decimal:
        quantum = Decimal('0.000')
        if rule == 'ROUND_UP':
            return quantity.quantize(quantum, rounding=ROUND_UP)
        if rule == 'ROUND_DOWN':
            return quantity.quantize(quantum, rounding=ROUND_DOWN)
        if rule == 'ROUND_NEAREST':
            return quantity.quantize(quantum, rounding=ROUND_HALF_UP)
        if rule == 'TRUNCATE':
            return quantity.quantize(quantum, rounding=ROUND_DOWN)
        return quantity


def from_uom_id_equals(a: UnitOfMeasure, b: UnitOfMeasure) -> bool:
    return getattr(a, 'id', None) == getattr(b, 'id', None)
