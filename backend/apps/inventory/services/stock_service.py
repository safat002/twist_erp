
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from ..models import StockMovement, StockMovementLine, StockLedger, StockLevel
from .valuation_service import ValuationService
from shared.event_bus import event_bus
from django.db.models import Sum

class InventoryService:
    """
    Service layer for handling all inventory transactions.
    """

    @staticmethod
    @transaction.atomic
    def receive_goods_against_po(goods_receipt):
        """
        Creates a StockMovement for a GoodsReceipt and posts it.
        
        Args:
            goods_receipt (GoodsReceipt): The goods receipt document.

        Returns:
            StockMovement: The completed stock movement.
        """
        # 1. Create the StockMovement header
        stock_movement = StockMovement.objects.create(
            company=goods_receipt.company,
            movement_date=goods_receipt.receipt_date,
            movement_type='RECEIPT',
            to_warehouse=goods_receipt.purchase_order.delivery_address, # Assuming delivery_address is a warehouse
            reference=f"GRN-{goods_receipt.receipt_number}",
            notes=goods_receipt.notes,
            status='DRAFT'
        )

        # 2. Create StockMovementLine items from GoodsReceiptLine items
        for grn_line in goods_receipt.lines.all():
            StockMovementLine.objects.create(
                movement=stock_movement,
                line_number=grn_line.purchase_order_line.line_number,
                product=grn_line.product,
                quantity=grn_line.quantity_received,
                rate=grn_line.purchase_order_line.unit_price,
                batch_no=getattr(grn_line, 'batch_no', ''),
                serial_no='',  # serial from GRN not tracked yet
                expiry_date=getattr(grn_line, 'expiry_date', None)
            )
        
        # 3. Post the stock movement
        # Determine stock state from QC
        qc_state = goods_receipt.quality_status or 'pending'
        stock_state_map = {
            'passed': 'RELEASED',
            'on_hold': 'ON_HOLD',
            'rejected': 'ON_HOLD',
            'pending': 'QUARANTINE',
        }
        stock_state = stock_state_map.get(qc_state, 'QUARANTINE')

        posted_movement = InventoryService._post_stock_movement(
            stock_movement,
            receipt_source=(
                'GoodsReceipt',
                goods_receipt.id,
            ),
            receipt_stock_state=stock_state,
        )
        
        return posted_movement

    @staticmethod
    @transaction.atomic
    def apply_landed_cost_adjustment(*, goods_receipt, total_adjustment, method: str = 'QUANTITY', reason: str = ''):
        """
        Apply landed cost adjustment to all cost layers created by a specific GRN.

        - method: 'QUANTITY' to apportion by qty_received, 'VALUE' to apportion by total_cost
        - Publishes 'stock.landed_cost_adjustment' with account-wise breakdown
        """
        from ..models import CostLayer
        from django.utils import timezone
        # Normalize inputs
        try:
            total_adj = Decimal(str(total_adjustment))
        except Exception:
            raise ValueError('total_adjustment must be a number')
        if total_adj == 0:
            return {'inventory_adjustment': 0.0, 'consumed_adjustment': 0.0}

        layers = list(CostLayer.objects.select_related('product__inventory_account', 'product__expense_account').filter(
            company=goods_receipt.company,
            source_document_type='GoodsReceipt',
            source_document_id=goods_receipt.id,
        ))
        if not layers:
            raise ValueError('No cost layers found for this Goods Receipt')

        if method == 'VALUE':
            base_total = sum((layer.total_cost or Decimal('0')) for layer in layers)
        else:
            method = 'QUANTITY'
            base_total = sum((layer.qty_received or Decimal('0')) for layer in layers)

        if base_total <= 0:
            raise ValueError('Base total for apportionment is zero')

        inv_by_account = {}
        cogs_by_account = {}
        inventory_total = Decimal('0')
        consumed_total = Decimal('0')

        for layer in layers:
            base = (layer.total_cost if method == 'VALUE' else layer.qty_received) or Decimal('0')
            share = (base / base_total) * total_adj
            per_unit_adj = (share / (layer.qty_received or Decimal('1')))

            # Update layer landed adjustment and remaining cost
            layer.landed_cost_adjustment = (layer.landed_cost_adjustment or Decimal('0')) + per_unit_adj
            layer.adjustment_date = timezone.now()
            layer.adjustment_reason = (reason or 'Landed cost adjustment')

            # Compute split between remaining and consumed
            qty_consumed = (layer.qty_received or Decimal('0')) - (layer.qty_remaining or Decimal('0'))
            adj_remaining = per_unit_adj * (layer.qty_remaining or Decimal('0'))
            adj_consumed = per_unit_adj * qty_consumed

            # Update cost_remaining to reflect new per-unit cost for remaining qty
            layer.cost_remaining = (layer.cost_remaining or Decimal('0')) + adj_remaining
            layer.save(update_fields=['landed_cost_adjustment', 'adjustment_date', 'adjustment_reason', 'cost_remaining'])

            # Aggregate by accounts
            inv_acct_id = layer.product.inventory_account_id
            cogs_acct_id = layer.product.expense_account_id
            inv_by_account[inv_acct_id] = inv_by_account.get(inv_acct_id, Decimal('0')) + adj_remaining
            cogs_by_account[cogs_acct_id] = cogs_by_account.get(cogs_acct_id, Decimal('0')) + adj_consumed
            inventory_total += adj_remaining
            consumed_total += adj_consumed

        # Publish event for finance to post JV: Dr Inventory (remaining), Dr COGS (consumed), Cr Accrued Freight
        event_bus.publish(
            'stock.landed_cost_adjustment',
            company_id=goods_receipt.company_id,
            goods_receipt_id=goods_receipt.id,
            inventory_by_account=[{'account_id': k, 'amount': float(v)} for k, v in inv_by_account.items() if v],
            cogs_by_account=[{'account_id': k, 'amount': float(v)} for k, v in cogs_by_account.items() if v],
            credit_account_code='ACCRUED_FREIGHT',
            reason=reason or 'Landed cost adjustment'
        )

        return {
            'inventory_adjustment': float(inventory_total),
            'consumed_adjustment': float(consumed_total),
        }

    @staticmethod
    @transaction.atomic
    def ship_goods_against_so(delivery_order):
        """
        Creates a StockMovement for a DeliveryOrder (shipment) and posts it.
        """
        stock_movement = StockMovement.objects.create(
            company=delivery_order.company,
            movement_date=delivery_order.delivery_date,
            movement_type='ISSUE',
            from_warehouse=delivery_order.sales_order.lines.first().warehouse, # Assumption: all lines from same warehouse
            reference=f"DO-{delivery_order.delivery_number}",
            notes=delivery_order.notes,
            status='DRAFT'
        )

        for do_line in delivery_order.lines.all():
            StockMovementLine.objects.create(
                movement=stock_movement,
                line_number=do_line.sales_order_line.line_number,
                product=do_line.product,
                quantity=do_line.quantity_shipped,
                rate=do_line.sales_order_line.unit_price # This should be cost price, but using unit price for now
            )
        
        posted_movement = InventoryService._post_stock_movement(stock_movement)
        return posted_movement

    @staticmethod
    @transaction.atomic
    def _post_stock_movement(
        movement: StockMovement,
        *,
        receipt_source: tuple | None = None,
        receipt_stock_state: str | None = None,
    ):
        """
        Posts a stock movement to the StockLedger, updates stock levels,
        creates/consumes cost layers based on valuation method, and publishes an event.

        ENHANCED: Now integrates with ValuationService for accurate costing.
        """
        if movement.status != 'DRAFT':
            raise ValueError("Stock movement must be in DRAFT status to be posted.")

        for line in movement.lines.all():

            if movement.movement_type == 'ISSUE':
                quantity_change = -line.quantity
                warehouse = movement.from_warehouse
                is_receipt = False
            elif movement.movement_type == 'TRANSFER':
                # Two-step logic within a single movement: issue from source, then receipt into destination
                # OUT leg (source)
                out_qty = -line.quantity
                out_wh = movement.from_warehouse

                valuation_method_used = ''
                layer_consumed_detail = None
                actual_cost = Decimal('0')

                try:
                    total_cost, consumed_layers, method_used = ValuationService.consume_cost_layers(
                        company=movement.company,
                        product=line.product,
                        warehouse=out_wh,
                        qty=line.quantity,
                        source_document_type='StockMovement',
                        source_document_id=movement.id
                    )
                    valuation_method_used = method_used
                    layer_consumed_detail = consumed_layers
                    actual_cost = total_cost
                    # Set line rate to per-unit cost for traceability
                    line.rate = total_cost / line.quantity
                    line.save(update_fields=['rate'])
                except ValueError as e:
                    actual_cost = line.rate * line.quantity
                    valuation_method_used = 'SIMPLE'

                # Create StockLedger for OUT leg
                balance_before = StockLevel.objects.filter(
                    company=movement.company,
                    product=line.product,
                    warehouse=out_wh
                ).first()
                current_balance_qty = balance_before.quantity if balance_before else Decimal('0')
                current_balance_value = (current_balance_qty * line.rate)
                new_balance_qty = current_balance_qty + out_qty
                new_balance_value = current_balance_value + (out_qty * line.rate)

                StockLedger.objects.create(
                    company=movement.company,
                    transaction_date=movement.movement_date,
                    transaction_type='TRANSFER',
                    product=line.product,
                    warehouse=out_wh,
                    quantity=out_qty,
                    rate=line.rate,
                    value=out_qty * line.rate,
                    balance_qty=new_balance_qty,
                    balance_value=new_balance_value,
                    source_document_type='StockMovement',
                    source_document_id=movement.id,
                    batch_no=line.batch_no,
                    serial_no=line.serial_no,
                    valuation_method_used=valuation_method_used,
                    layer_consumed_detail=layer_consumed_detail
                )

                stock_level, _ = StockLevel.objects.get_or_create(
                    company=movement.company,
                    product=line.product,
                    warehouse=out_wh,
                    defaults={'quantity': 0}
                )
                stock_level.quantity += out_qty
                stock_level.save()

                # Publish transfer out event for GL
                event_bus.publish('stock.transfer_out', stock_movement_id=movement.id)

                # IN leg (destination)
                in_qty = line.quantity
                in_wh = movement.to_warehouse

                try:
                    ValuationService.create_cost_layer(
                        company=movement.company,
                        product=line.product,
                        warehouse=in_wh,
                        qty=in_qty,
                        cost_per_unit=line.rate,
                        source_document_type='StockMovement',
                        source_document_id=movement.id,
                        batch_no=line.batch_no,
                        serial_no=line.serial_no,
                        receipt_date=timezone.now(),
                        stock_state='RELEASED'
                    )
                except Exception as e:
                    # fallback: ignore layer create failure
                    pass

                balance_before_in = StockLevel.objects.filter(
                    company=movement.company,
                    product=line.product,
                    warehouse=in_wh
                ).first()
                current_balance_qty_in = balance_before_in.quantity if balance_before_in else Decimal('0')
                current_balance_value_in = (current_balance_qty_in * line.rate)
                new_balance_qty_in = current_balance_qty_in + in_qty
                new_balance_value_in = current_balance_value_in + (in_qty * line.rate)

                StockLedger.objects.create(
                    company=movement.company,
                    transaction_date=movement.movement_date,
                    transaction_type='TRANSFER',
                    product=line.product,
                    warehouse=in_wh,
                    quantity=in_qty,
                    rate=line.rate,
                    value=in_qty * line.rate,
                    balance_qty=new_balance_qty_in,
                    balance_value=new_balance_value_in,
                    source_document_type='StockMovement',
                    source_document_id=movement.id,
                    batch_no=line.batch_no,
                    serial_no=line.serial_no,
                    valuation_method_used='TRANSFER',
                    layer_consumed_detail=None
                )

                stock_level_in, _ = StockLevel.objects.get_or_create(
                    company=movement.company,
                    product=line.product,
                    warehouse=in_wh,
                    defaults={'quantity': 0}
                )
                stock_level_in.quantity += in_qty
                stock_level_in.save()

                # Publish transfer in event for GL
                event_bus.publish('stock.transfer_in', stock_movement_id=movement.id)

                # proceed to next line (skip default flow)
                continue
            else:
                quantity_change = line.quantity
                warehouse = movement.to_warehouse
                is_receipt = True

            # ==================================================
            # VALUATION SERVICE INTEGRATION
            # ==================================================

            valuation_method_used = ''
            layer_consumed_detail = None
            actual_cost = Decimal('0')

            if is_receipt:
                # RECEIPT: Create a new cost layer
                try:
                    cost_layer = ValuationService.create_cost_layer(
                        company=movement.company,
                        product=line.product,
                        warehouse=warehouse,
                        qty=line.quantity,
                        cost_per_unit=line.rate,
                        source_document_type=(receipt_source[0] if receipt_source else 'StockMovement'),
                        source_document_id=(receipt_source[1] if receipt_source else movement.id),
                        batch_no=line.batch_no,
                        serial_no=line.serial_no,
                        receipt_date=timezone.now(),
                        stock_state=(receipt_stock_state or 'RELEASED'),
                        expiry_date=getattr(line, 'expiry_date', None)
                    )

                    # Get the valuation method for tracking
                    val_method = ValuationService.get_valuation_method(
                        movement.company, line.product, warehouse
                    )
                    valuation_method_used = val_method.valuation_method if val_method else 'FIFO'

                    # For receipts, use the provided rate
                    actual_cost = line.rate * line.quantity

                except Exception as e:
                    # If valuation service fails, fall back to simple costing
                    print(f"Warning: ValuationService error on receipt: {e}")
                    actual_cost = line.rate * line.quantity
                    valuation_method_used = 'SIMPLE'

            else:
                # ISSUE: Consume cost layers based on valuation method
                try:
                    total_cost, consumed_layers, method_used = ValuationService.consume_cost_layers(
                        company=movement.company,
                        product=line.product,
                        warehouse=warehouse,
                        qty=line.quantity,
                        source_document_type='StockMovement',
                        source_document_id=movement.id
                    )

                    valuation_method_used = method_used
                    layer_consumed_detail = consumed_layers
                    actual_cost = total_cost

                    # Override the line rate with calculated cost
                    line.rate = total_cost / line.quantity
                    line.save(update_fields=['rate'])

                except ValueError as e:
                    # Insufficient inventory or other valuation errors
                    print(f"Warning: ValuationService error on issue: {e}")
                    # Fall back to using provided rate
                    actual_cost = line.rate * line.quantity
                    valuation_method_used = 'SIMPLE'

            # 1. Create immutable StockLedger entry with valuation tracking
            balance_before = StockLevel.objects.filter(
                company=movement.company,
                product=line.product,
                warehouse=warehouse
            ).first()

            current_balance_qty = balance_before.quantity if balance_before else Decimal('0')
            current_balance_value = (balance_before.quantity * line.rate) if balance_before else Decimal('0')

            new_balance_qty = current_balance_qty + quantity_change
            new_balance_value = current_balance_value + (quantity_change * line.rate)

            StockLedger.objects.create(
                company=movement.company,
                transaction_date=movement.movement_date,
                transaction_type=movement.movement_type,
                product=line.product,
                warehouse=warehouse,
                quantity=quantity_change,
                rate=line.rate,
                value=quantity_change * line.rate,
                balance_qty=new_balance_qty,
                balance_value=new_balance_value,
                source_document_type='StockMovement',
                source_document_id=movement.id,
                batch_no=line.batch_no,
                serial_no=line.serial_no,
                # NEW: Valuation tracking fields
                valuation_method_used=valuation_method_used,
                layer_consumed_detail=layer_consumed_detail
            )

            # 2. Update the StockLevel
            stock_level, created = StockLevel.objects.get_or_create(
                company=movement.company,
                product=line.product,
                warehouse=warehouse,
                defaults={'quantity': 0}
            )
            stock_level.quantity += quantity_change
            stock_level.save()

        # 3. Mark movement as completed
        movement.status = 'COMPLETED'
        movement.posted_at = timezone.now()
        movement.save()

        # 4. Publish the event
        if movement.movement_type == 'RECEIPT':
            event_bus.publish('stock.received', stock_movement_id=movement.id)
        elif movement.movement_type == 'ISSUE':
            event_bus.publish('stock.shipped', stock_movement_id=movement.id)
        elif movement.movement_type == 'TRANSFER':
            # already published per leg
            pass

        return movement
