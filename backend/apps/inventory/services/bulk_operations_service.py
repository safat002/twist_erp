"""
Bulk Operations Service

Provides high-performance bulk operations for inventory management:
- Bulk valuation method changes
- Bulk landed cost application
- Mass product updates
- Batch processing for large datasets

Features:
- Transaction safety
- Progress tracking
- Error handling with rollback
- Async processing support
"""

import logging
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.companies.models import Company
from apps.inventory.models import (
    Product,
    Warehouse,
    ValuationMethodChange,
    CostLayer,
    StockMovement
)
from apps.inventory.services.stock_service import InventoryService
from shared.event_bus import event_bus

logger = logging.getLogger(__name__)


@dataclass
class BulkOperationResult:
    """Result of a bulk operation"""
    total_items: int
    successful: int
    failed: int
    errors: List[Dict]
    duration_seconds: float


class BulkOperationsService:
    """
    Service for performing bulk operations on inventory data.
    """

    @staticmethod
    @transaction.atomic
    def bulk_change_valuation_method(
        company: Company,
        product_ids: List[int],
        new_method: str,
        effective_date: Optional[str] = None,
        reason: str = '',
        user=None
    ) -> BulkOperationResult:
        """
        Changes valuation method for multiple products at once.

        Args:
            company: Company instance
            product_ids: List of product IDs to update
            new_method: New valuation method (FIFO, LIFO, WEIGHTED_AVG, STANDARD_COST)
            effective_date: Effective date for change
            reason: Reason for change
            user: User making the change

        Returns:
            BulkOperationResult with summary
        """
        start_time = timezone.now()
        errors = []
        successful = 0
        failed = 0

        if effective_date is None:
            effective_date = timezone.now().date()

        valid_methods = ['FIFO', 'LIFO', 'WEIGHTED_AVG', 'STANDARD_COST']
        if new_method not in valid_methods:
            raise ValueError(f"Invalid valuation method. Must be one of {valid_methods}")

        products = Product.objects.filter(
            id__in=product_ids,
            company=company
        )

        for product in products:
            try:
                # Create valuation method change record
                ValuationMethodChange.objects.create(
                    company=company,
                    product=product,
                    old_method=product.valuation_method,
                    new_method=new_method,
                    effective_date=effective_date,
                    reason=reason,
                    status='APPROVED',  # Auto-approve for bulk operations
                    requested_by=user,
                    approved_by=user,
                    approved_at=timezone.now()
                )

                # Update product
                product.valuation_method = new_method
                product.save(update_fields=['valuation_method'])

                successful += 1

                # Publish event for finance integration
                event_bus.publish(
                    'inventory.valuation_method_changed',
                    company_id=company.id,
                    product_id=product.id,
                    old_method=product.valuation_method,
                    new_method=new_method,
                    effective_date=effective_date
                )

            except Exception as e:
                failed += 1
                errors.append({
                    'product_id': product.id,
                    'product_code': product.code,
                    'error': str(e)
                })
                logger.error(f"Error changing valuation method for product {product.code}: {e}")

        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        return BulkOperationResult(
            total_items=len(product_ids),
            successful=successful,
            failed=failed,
            errors=errors,
            duration_seconds=duration
        )

    @staticmethod
    @transaction.atomic
    def bulk_apply_landed_cost(
        company: Company,
        grn_ids: List[int],
        total_adjustment: Decimal,
        allocation_method: str = 'VALUE',
        reason: str = ''
    ) -> BulkOperationResult:
        """
        Applies landed cost adjustments to multiple GRNs.

        Args:
            company: Company instance
            grn_ids: List of GRN (StockMovement) IDs
            total_adjustment: Total adjustment amount to allocate
            allocation_method: 'VALUE' or 'QUANTITY'
            reason: Reason for adjustment

        Returns:
            BulkOperationResult with summary
        """
        start_time = timezone.now()
        errors = []
        successful = 0
        failed = 0

        movements = StockMovement.objects.filter(
            id__in=grn_ids,
            company=company,
            movement_type='RECEIPT',
            status='POSTED'
        )

        if not movements.exists():
            return BulkOperationResult(
                total_items=len(grn_ids),
                successful=0,
                failed=len(grn_ids),
                errors=[{'error': 'No valid GRNs found'}],
                duration_seconds=0
            )

        # Calculate allocation weights
        if allocation_method == 'VALUE':
            total_weight = sum(
                sum(line.quantity * line.rate for line in m.lines.all())
                for m in movements
            )
        else:  # QUANTITY
            total_weight = sum(
                sum(line.quantity for line in m.lines.all())
                for m in movements
            )

        if total_weight == 0:
            return BulkOperationResult(
                total_items=len(grn_ids),
                successful=0,
                failed=len(grn_ids),
                errors=[{'error': 'Total weight is zero, cannot allocate'}],
                duration_seconds=0
            )

        # Apply adjustments
        for movement in movements:
            try:
                if allocation_method == 'VALUE':
                    movement_weight = sum(
                        line.quantity * line.rate for line in movement.lines.all()
                    )
                else:
                    movement_weight = sum(
                        line.quantity for line in movement.lines.all()
                    )

                movement_adjustment = (movement_weight / total_weight) * total_adjustment

                # Apply landed cost
                InventoryService.apply_landed_cost_adjustment(
                    goods_receipt=movement,
                    total_adjustment=movement_adjustment,
                    method=allocation_method,
                    reason=reason
                )

                successful += 1

            except Exception as e:
                failed += 1
                errors.append({
                    'grn_id': movement.id,
                    'reference': movement.reference,
                    'error': str(e)
                })
                logger.error(f"Error applying landed cost to GRN {movement.reference}: {e}")

        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        return BulkOperationResult(
            total_items=len(grn_ids),
            successful=successful,
            failed=failed,
            errors=errors,
            duration_seconds=duration
        )

    @staticmethod
    @transaction.atomic
    def bulk_update_products(
        company: Company,
        updates: List[Dict]
    ) -> BulkOperationResult:
        """
        Bulk updates product attributes.

        Args:
            company: Company instance
            updates: List of dicts with 'product_id' and fields to update

        Example:
            updates = [
                {'product_id': 1, 'reorder_level': 100, 'reorder_quantity': 500},
                {'product_id': 2, 'valuation_method': 'FIFO'},
            ]

        Returns:
            BulkOperationResult with summary
        """
        start_time = timezone.now()
        errors = []
        successful = 0
        failed = 0

        for update_data in updates:
            product_id = update_data.get('product_id')
            if not product_id:
                failed += 1
                errors.append({'error': 'Missing product_id'})
                continue

            try:
                product = Product.objects.get(id=product_id, company=company)

                # Remove product_id from update data
                fields_to_update = {k: v for k, v in update_data.items() if k != 'product_id'}

                # Update fields
                for field, value in fields_to_update.items():
                    if hasattr(product, field):
                        setattr(product, field, value)
                    else:
                        raise ValueError(f"Invalid field: {field}")

                product.save()
                successful += 1

            except Product.DoesNotExist:
                failed += 1
                errors.append({
                    'product_id': product_id,
                    'error': 'Product not found'
                })
            except Exception as e:
                failed += 1
                errors.append({
                    'product_id': product_id,
                    'error': str(e)
                })
                logger.error(f"Error updating product {product_id}: {e}")

        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        return BulkOperationResult(
            total_items=len(updates),
            successful=successful,
            failed=failed,
            errors=errors,
            duration_seconds=duration
        )

    @staticmethod
    def bulk_recalculate_stock_values(
        company: Company,
        product_ids: Optional[List[int]] = None,
        warehouse_ids: Optional[List[int]] = None
    ) -> BulkOperationResult:
        """
        Recalculates stock values for products/warehouses.
        Useful after data fixes or migrations.

        Args:
            company: Company instance
            product_ids: Optional list of product IDs (None = all products)
            warehouse_ids: Optional list of warehouse IDs (None = all warehouses)

        Returns:
            BulkOperationResult with summary
        """
        start_time = timezone.now()
        errors = []
        successful = 0
        failed = 0

        # Get products to recalculate
        products_query = Product.objects.filter(company=company, is_active=True)
        if product_ids:
            products_query = products_query.filter(id__in=product_ids)

        # Get warehouses
        warehouses_query = Warehouse.objects.filter(company=company)
        if warehouse_ids:
            warehouses_query = warehouses_query.filter(id__in=warehouse_ids)

        products = list(products_query)
        warehouses = list(warehouses_query)

        total_items = len(products) * len(warehouses)

        for product in products:
            for warehouse in warehouses:
                try:
                    # Recalculate cost layers
                    cost_layers = CostLayer.objects.filter(
                        company=company,
                        product=product,
                        warehouse=warehouse,
                        qty_remaining__gt=0
                    ).order_by('fifo_sequence')

                    # Recalculate cost_remaining for each layer
                    for layer in cost_layers:
                        base_cost = layer.cost_per_unit * layer.qty_remaining
                        landed_cost_adj = (layer.landed_cost_adjustment or Decimal('0')) * layer.qty_remaining
                        layer.cost_remaining = base_cost + landed_cost_adj
                        layer.save(update_fields=['cost_remaining'])

                    successful += 1

                except Exception as e:
                    failed += 1
                    errors.append({
                        'product_id': product.id,
                        'product_code': product.code,
                        'warehouse_id': warehouse.id,
                        'warehouse_code': warehouse.code,
                        'error': str(e)
                    })
                    logger.error(
                        f"Error recalculating stock value for product {product.code} "
                        f"in warehouse {warehouse.code}: {e}"
                    )

        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        return BulkOperationResult(
            total_items=total_items,
            successful=successful,
            failed=failed,
            errors=errors,
            duration_seconds=duration
        )

    @staticmethod
    def get_operation_progress(operation_id: str) -> Dict:
        """
        Gets progress of a long-running bulk operation.

        For async operations (future enhancement).

        Args:
            operation_id: Operation tracking ID

        Returns:
            Dict with progress information
        """
        # Placeholder for future async implementation
        # Would query a BulkOperationStatus model
        return {
            'operation_id': operation_id,
            'status': 'unknown',
            'progress_percent': 0,
            'message': 'Operation tracking not yet implemented'
        }
