"""
Inventory Valuation Service
============================

Implements multiple valuation methods for inventory costing:
- FIFO (First In, First Out)
- LIFO (Last In, First Out)
- Weighted Average (Moving or Periodic)
- Standard Cost

This service handles:
1. Cost layer creation on receipts
2. Cost layer consumption on issues
3. Cost calculation for different valuation methods
4. Valuation method configuration per item/warehouse
"""

from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from django.db import transaction
from django.utils import timezone
from django.db.models import F, Sum, Q

from apps.inventory.models import (
    Product,
    Warehouse,
    CostLayer,
    ItemValuationMethod,
    StockLedger,
    ValuationChangeLog
)


class ValuationService:
    """Service for managing inventory valuation and cost layers."""

    @staticmethod
    def get_valuation_method(
        company,
        product: Product,
        warehouse: Warehouse,
        transaction_date=None
    ) -> Optional[ItemValuationMethod]:
        """
        Get the active valuation method for a product/warehouse combination.
        If transaction_date is provided, get method effective on that date.
        """
        if transaction_date is None:
            transaction_date = timezone.now().date()

        return ItemValuationMethod.objects.filter(
            company=company,
            budget_item=product,
            warehouse=warehouse,
            effective_date__lte=transaction_date,
            is_active=True
        ).order_by('-effective_date').first()
    @staticmethod
    def _prevent_expired(product, warehouse=None):
        try:
            config = product.get_fefo_config(warehouse=warehouse)
            if config and config.enforce_fefo:
                return config.block_issue_if_expired
            profile = product.get_operational_profile()
            return bool(getattr(profile, 'requires_expiry_tracking', False))
        except Exception:
            return getattr(product, 'prevent_expired_issuance', True)

    @staticmethod
    @transaction.atomic
    def create_cost_layer(
        company,
        product: Product,
        warehouse: Warehouse,
        qty: Decimal,
        cost_per_unit: Decimal,
        source_document_type: str,
        source_document_id: int,
        batch_no: str = "",
        serial_no: str = "",
        receipt_date=None,
        stock_state: str = 'RELEASED',
        expiry_date=None
    ) -> CostLayer:
        """
        Create a new cost layer when inventory is received.

        Args:
            company: Company instance
            product: Product instance
            warehouse: Warehouse instance
            qty: Quantity received
            cost_per_unit: Cost per unit (from PO or other source)
            source_document_type: e.g., 'GoodsReceipt', 'StockMovement'
            source_document_id: ID of source document
            batch_no: Optional batch number
            serial_no: Optional serial number
            receipt_date: When received (defaults to now)

        Returns:
            CostLayer instance
        """
        if receipt_date is None:
            receipt_date = timezone.now()

        # Get next FIFO sequence for this product/warehouse
        max_seq = CostLayer.objects.filter(
            company=company,
            budget_item=product,
            warehouse=warehouse
        ).aggregate(max_seq=Sum('fifo_sequence'))['max_seq'] or 0

        fifo_sequence = max_seq + 1

        # Create the cost layer
        layer = CostLayer.objects.create(
            company=company,
            budget_item=product,
            warehouse=warehouse,
            receipt_date=receipt_date,
            qty_received=qty,
            cost_per_unit=cost_per_unit,
            total_cost=qty * cost_per_unit,
            qty_remaining=qty,
            cost_remaining=qty * cost_per_unit,
            fifo_sequence=fifo_sequence,
            batch_no=batch_no,
            serial_no=serial_no,
            source_document_type=source_document_type,
            source_document_id=source_document_id,
            immutable_after_post=True,
            is_closed=False,
            stock_state=stock_state,
            expiry_date=expiry_date
        )

        return layer

    @staticmethod
    def calculate_fifo_cost(
        company,
        product: Product,
        warehouse: Warehouse,
        qty_needed: Decimal
    ) -> Tuple[Decimal, List[Dict]]:
        """
        Calculate cost using FIFO (First In, First Out) method.
        Consumes from oldest cost layers first.

        Returns:
            Tuple of (total_cost, consumed_layers_detail)
            consumed_layers_detail: [{layer_id, qty_consumed, cost_per_unit, cost_total}]
        """
        # Get open cost layers ordered by FIFO sequence (oldest first)
        from django.utils import timezone as _tz
        today = _tz.now().date()
        prevent_expired = ValuationService._prevent_expired(product, warehouse)
        layers = CostLayer.objects.filter(
            company=company,
            budget_item=product,
            warehouse=warehouse,
            stock_state='RELEASED',
            is_closed=False,
            qty_remaining__gt=0
        )
        if prevent_expired:
            layers = layers.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))
        layers = layers.order_by('expiry_date', 'fifo_sequence', 'receipt_date', 'id')

        total_cost = Decimal('0')
        qty_remaining = qty_needed
        consumed_layers = []

        for layer in layers:
            if qty_remaining <= 0:
                break

            # Calculate how much to consume from this layer
            qty_to_consume = min(layer.qty_remaining, qty_remaining)

            # Calculate cost including any landed cost adjustments
            effective_cost = layer.cost_per_unit + layer.landed_cost_adjustment
            layer_cost = qty_to_consume * effective_cost

            total_cost += layer_cost
            qty_remaining -= qty_to_consume

            consumed_layers.append({
                'layer_id': layer.id,
                'qty_consumed': float(qty_to_consume),
                'cost_per_unit': float(effective_cost),
                'cost_total': float(layer_cost),
                'fifo_sequence': layer.fifo_sequence
            })

        # Check if we had enough inventory
        if qty_remaining > 0:
            raise ValueError(
                f"Insufficient inventory for FIFO calculation. "
                f"Needed: {qty_needed}, Available: {qty_needed - qty_remaining}"
            )

        return total_cost, consumed_layers

    @staticmethod
    def calculate_lifo_cost(
        company,
        product: Product,
        warehouse: Warehouse,
        qty_needed: Decimal
    ) -> Tuple[Decimal, List[Dict]]:
        """
        Calculate cost using LIFO (Last In, First Out) method.
        Consumes from newest cost layers first.

        Returns:
            Tuple of (total_cost, consumed_layers_detail)
        """
        # Get open cost layers ordered by LIFO (newest first)
        from django.utils import timezone as _tz
        today = _tz.now().date()
        prevent_expired = ValuationService._prevent_expired(product, warehouse)
        layers = CostLayer.objects.filter(
            company=company,
            budget_item=product,
            warehouse=warehouse,
            stock_state='RELEASED',
            is_closed=False,
            qty_remaining__gt=0
        )
        if prevent_expired:
            layers = layers.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))
        layers = layers.order_by('expiry_date', '-fifo_sequence', '-receipt_date', '-id')

        total_cost = Decimal('0')
        qty_remaining = qty_needed
        consumed_layers = []

        for layer in layers:
            if qty_remaining <= 0:
                break

            qty_to_consume = min(layer.qty_remaining, qty_remaining)
            effective_cost = layer.cost_per_unit + layer.landed_cost_adjustment
            layer_cost = qty_to_consume * effective_cost

            total_cost += layer_cost
            qty_remaining -= qty_to_consume

            consumed_layers.append({
                'layer_id': layer.id,
                'qty_consumed': float(qty_to_consume),
                'cost_per_unit': float(effective_cost),
                'cost_total': float(layer_cost),
                'fifo_sequence': layer.fifo_sequence
            })

        if qty_remaining > 0:
            raise ValueError(
                f"Insufficient inventory for LIFO calculation. "
                f"Needed: {qty_needed}, Available: {qty_needed - qty_remaining}"
            )

        return total_cost, consumed_layers

    @staticmethod
    def calculate_weighted_average_cost(
        company,
        product: Product,
        warehouse: Warehouse,
        qty_needed: Decimal,
        avg_period: str = 'PERPETUAL'
    ) -> Tuple[Decimal, List[Dict]]:
        """
        Calculate cost using Weighted Average method.

        For PERPETUAL: Uses moving average from all open layers
        For DAILY/WEEKLY/MONTHLY: Would require period-specific calculation

        Returns:
            Tuple of (total_cost, consumed_layers_detail)
        """
        # Get all open layers
        from django.utils import timezone as _tz
        today = _tz.now().date()
        prevent_expired = ValuationService._prevent_expired(product, warehouse)
        layers = CostLayer.objects.filter(
            company=company,
            budget_item=product,
            warehouse=warehouse,
            stock_state='RELEASED',
            is_closed=False,
            qty_remaining__gt=0
        )
        if prevent_expired:
            layers = layers.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))

        # Calculate weighted average
        total_qty = Decimal('0')
        total_value = Decimal('0')

        for layer in layers:
            effective_cost = layer.cost_per_unit + layer.landed_cost_adjustment
            total_qty += layer.qty_remaining
            total_value += layer.qty_remaining * effective_cost

        if total_qty == 0:
            raise ValueError("No inventory available for weighted average calculation")

        if total_qty < qty_needed:
            raise ValueError(
                f"Insufficient inventory for weighted average calculation. "
                f"Needed: {qty_needed}, Available: {total_qty}"
            )

        # Calculate average cost per unit
        avg_cost_per_unit = total_value / total_qty
        total_cost = qty_needed * avg_cost_per_unit

        # For weighted average, we consume proportionally from all layers
        # but we'll represent it as consuming from oldest layers first for tracking
        consumed_layers = []
        qty_remaining = qty_needed

        for layer in layers.order_by('expiry_date', 'fifo_sequence', 'receipt_date'):
            if qty_remaining <= 0:
                break

            qty_to_consume = min(layer.qty_remaining, qty_remaining)
            layer_cost = qty_to_consume * avg_cost_per_unit

            qty_remaining -= qty_to_consume

            consumed_layers.append({
                'layer_id': layer.id,
                'qty_consumed': float(qty_to_consume),
                'cost_per_unit': float(avg_cost_per_unit),
                'cost_total': float(layer_cost),
                'fifo_sequence': layer.fifo_sequence
            })

        return total_cost, consumed_layers

    @staticmethod
    def calculate_standard_cost(
        company,
        product: Product,
        warehouse: Warehouse,
        qty_needed: Decimal
    ) -> Tuple[Decimal, List[Dict]]:
        """
        Calculate cost using Standard Cost method.
        Uses the product's cost_price as the standard cost.

        Variance between actual and standard is tracked separately.

        Returns:
            Tuple of (total_cost, consumed_layers_detail)
        """
        standard_cost = product.cost_price
        total_cost = qty_needed * standard_cost

        # For standard cost, we still track which layers are consumed
        # but the cost is always the standard
        layers = CostLayer.objects.filter(
            company=company,
            budget_item=product,
            warehouse=warehouse,
            stock_state='RELEASED',
            is_closed=False,
            qty_remaining__gt=0
        ).order_by('fifo_sequence', 'receipt_date')

        qty_remaining = qty_needed
        consumed_layers = []

        for layer in layers:
            if qty_remaining <= 0:
                break

            qty_to_consume = min(layer.qty_remaining, qty_remaining)
            layer_cost = qty_to_consume * standard_cost

            qty_remaining -= qty_to_consume

            consumed_layers.append({
                'layer_id': layer.id,
                'qty_consumed': float(qty_to_consume),
                'cost_per_unit': float(standard_cost),  # Always standard cost
                'cost_total': float(layer_cost),
                'actual_cost_per_unit': float(layer.cost_per_unit),  # Track actual for variance
                'fifo_sequence': layer.fifo_sequence
            })

        if qty_remaining > 0:
            raise ValueError(
                f"Insufficient inventory for standard cost calculation. "
                f"Needed: {qty_needed}, Available: {qty_needed - qty_remaining}"
            )

        return total_cost, consumed_layers

    @staticmethod
    def calculate_cost(
        company,
        product: Product,
        warehouse: Warehouse,
        qty: Decimal,
        valuation_method: Optional[ItemValuationMethod] = None
    ) -> Tuple[Decimal, List[Dict], str]:
        """
        Calculate cost based on the configured valuation method.

        Returns:
            Tuple of (total_cost, consumed_layers_detail, method_used)
        """
        if valuation_method is None:
            valuation_method = ValuationService.get_valuation_method(
                company, product, warehouse
            )

        if valuation_method is None:
            # Default to FIFO if no method configured
            method = 'FIFO'
        else:
            method = valuation_method.valuation_method

        if method == 'FIFO':
            cost, layers = ValuationService.calculate_fifo_cost(
                company, product, warehouse, qty
            )
        elif method == 'LIFO':
            cost, layers = ValuationService.calculate_lifo_cost(
                company, product, warehouse, qty
            )
        elif method == 'WEIGHTED_AVG':
            avg_period = valuation_method.avg_period if valuation_method else 'PERPETUAL'
            cost, layers = ValuationService.calculate_weighted_average_cost(
                company, product, warehouse, qty, avg_period
            )
        elif method == 'STANDARD':
            cost, layers = ValuationService.calculate_standard_cost(
                company, product, warehouse, qty
            )
        else:
            raise ValueError(f"Unknown valuation method: {method}")

        return cost, layers, method

    @staticmethod
    @transaction.atomic
    def consume_cost_layers(
        company,
        product: Product,
        warehouse: Warehouse,
        qty: Decimal,
        source_document_type: str,
        source_document_id: int,
        valuation_method: Optional[ItemValuationMethod] = None
    ) -> Tuple[Decimal, List[Dict], str]:
        """
        Consume cost layers when issuing inventory.
        Updates qty_remaining on affected layers.

        Returns:
            Tuple of (total_cost, consumed_layers_detail, method_used)
        """
        # Calculate which layers to consume
        total_cost, consumed_layers, method_used = ValuationService.calculate_cost(
            company, product, warehouse, qty, valuation_method
        )

        # Update the cost layers
        for layer_detail in consumed_layers:
            layer = CostLayer.objects.get(id=layer_detail['layer_id'])
            qty_consumed = Decimal(str(layer_detail['qty_consumed']))

            # Update remaining quantities
            layer.qty_remaining = F('qty_remaining') - qty_consumed
            layer.cost_remaining = F('cost_remaining') - Decimal(str(layer_detail['cost_total']))
            layer.save(update_fields=['qty_remaining', 'cost_remaining'])

            # Reload to check if layer is now closed
            layer.refresh_from_db()
            if layer.qty_remaining <= 0:
                layer.is_closed = True
                layer.save(update_fields=['is_closed'])

        return total_cost, consumed_layers, method_used

    @staticmethod
    def get_current_cost(
        company,
        product: Product,
        warehouse: Warehouse,
        valuation_method: Optional[ItemValuationMethod] = None
    ) -> Decimal:
        """
        Get the current cost per unit for a product/warehouse.
        Useful for estimates, quotes, and reports.

        For FIFO/LIFO: Returns cost of next layer that would be consumed
        For Weighted Avg: Returns current average cost
        For Standard: Returns standard cost from product
        """
        if valuation_method is None:
            valuation_method = ValuationService.get_valuation_method(
                company, product, warehouse
            )

        if valuation_method is None:
            method = 'FIFO'
        else:
            method = valuation_method.valuation_method

        if method == 'STANDARD':
            return product.cost_price

        elif method == 'FIFO':
            # Return cost of oldest layer
            from django.utils import timezone as _tz
            today = _tz.now().date()
            prevent_expired = ValuationService._prevent_expired(product, warehouse)
            qs = CostLayer.objects.filter(
                company=company,
                budget_item=product,
                warehouse=warehouse,
                stock_state='RELEASED',
                is_closed=False,
                qty_remaining__gt=0
            )
            if prevent_expired:
                qs = qs.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))
            layer = qs.order_by('expiry_date', 'fifo_sequence', 'receipt_date').first()

            if layer:
                return layer.cost_per_unit + layer.landed_cost_adjustment
            return product.cost_price  # Fallback

        elif method == 'LIFO':
            # Return cost of newest layer
            from django.utils import timezone as _tz
            today = _tz.now().date()
            prevent_expired = ValuationService._prevent_expired(product, warehouse)
            qs = CostLayer.objects.filter(
                company=company,
                budget_item=product,
                warehouse=warehouse,
                stock_state='RELEASED',
                is_closed=False,
                qty_remaining__gt=0
            )
            if prevent_expired:
                qs = qs.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))
            layer = qs.order_by('expiry_date', '-fifo_sequence', '-receipt_date').first()

            if layer:
                return layer.cost_per_unit + layer.landed_cost_adjustment
            return product.cost_price  # Fallback

        elif method == 'WEIGHTED_AVG':
            # Calculate current weighted average
            from django.utils import timezone as _tz
            today = _tz.now().date()
            layers = CostLayer.objects.filter(
                company=company,
                budget_item=product,
                warehouse=warehouse,
                stock_state='RELEASED',
                is_closed=False,
                qty_remaining__gt=0
            ).filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))

            total_qty = Decimal('0')
            total_value = Decimal('0')

            for layer in layers:
                effective_cost = layer.cost_per_unit + layer.landed_cost_adjustment
                total_qty += layer.qty_remaining
                total_value += layer.qty_remaining * effective_cost

            if total_qty > 0:
                return total_value / total_qty
            return product.cost_price  # Fallback

        return product.cost_price

    @staticmethod
    def get_inventory_value(
        company,
        product: Product,
        warehouse: Warehouse,
        valuation_method: Optional[ItemValuationMethod] = None
    ) -> Dict:
        """
        Get the current inventory value for a product/warehouse.

        Returns:
            Dict with qty_on_hand, current_cost_per_unit, total_value
        """
        layers = CostLayer.objects.filter(
            company=company,
            budget_item=product,
            warehouse=warehouse,
            is_closed=False,
            qty_remaining__gt=0
        )

        qty_on_hand = sum(layer.qty_remaining for layer in layers)
        total_value = sum(layer.cost_remaining for layer in layers)

        current_cost = ValuationService.get_current_cost(
            company, product, warehouse, valuation_method
        )

        return {
            'qty_on_hand': float(qty_on_hand),
            'current_cost_per_unit': float(current_cost),
            'total_value': float(total_value),
            'layer_count': layers.count()
        }
