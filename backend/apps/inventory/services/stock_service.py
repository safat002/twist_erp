
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from ..models import StockMovement, StockMovementLine, StockLedger, StockLevel, MovementEvent, InTransitShipmentLine
from .valuation_service import ValuationService
from .uom_service import UoMConversionService
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
        Also creates BatchLot and SerialNumber records, and triggers QC checkpoints.

        Args:
            goods_receipt (GoodsReceipt): The goods receipt document.

        Returns:
            StockMovement: The completed stock movement.
        """
        from ..models import BatchLot, SerialNumber, QCCheckpoint
        from .qc_service import QCService

        # 1. Create the StockMovement header
        warehouse = goods_receipt.purchase_order.delivery_address
        stock_movement = StockMovement.objects.create(
            company=goods_receipt.company,
            movement_date=goods_receipt.receipt_date,
            movement_type='RECEIPT',
            to_warehouse=warehouse,
            reference=f"GRN-{goods_receipt.receipt_number}",
            notes=goods_receipt.notes,
            status='DRAFT',
            cost_center=getattr(goods_receipt.purchase_order, 'cost_center', None),
        )

        # 2. Create StockMovementLine items from GoodsReceiptLine items
        # Also create BatchLot and SerialNumber records
        for grn_line in goods_receipt.lines.select_related('item', 'purchase_order_line__requisition_line__uom'):
            item = grn_line.budget_item
            if not item:
                continue
            profile = item.get_operational_profile()
            entered_qty = grn_line.quantity_received
            entered_uom = getattr(getattr(grn_line.purchase_order_line, 'requisition_line', None), 'uom', None) or profile.purchase_uom or profile.stock_uom
            stock_qty = UoMConversionService.convert_quantity(
                item=item,
                quantity=entered_qty,
                from_uom=entered_uom,
                to_uom=profile.stock_uom,
                context='purchase',
            )

            # Create BatchLot record if batch tracking is enabled
            batch_lot = None
            if grn_line.batch_no:
                # Check if batch already exists
                batch_lot = BatchLot.objects.filter(
                    company=goods_receipt.company,
                    budget_item=item,
                    warehouse=warehouse,
                    internal_batch_code=grn_line.batch_no,
                ).first()

                if not batch_lot:
                    batch_lot = BatchLot.objects.create(
                        company=goods_receipt.company,
                        budget_item=item,
                        warehouse=warehouse,
                        internal_batch_code=grn_line.batch_no,
                        manufacturer_batch_no=getattr(grn_line, 'manufacturer_batch_no', ''),
                        mfg_date=None,  # Can be added to GRN line if needed
                        exp_date=grn_line.expiry_date,
                        quantity_received=stock_qty,
                        quantity_available=stock_qty,
                        certificate_of_analysis=getattr(grn_line, 'certificate_of_analysis', None),
                        hold_status='QUARANTINE',  # Start in quarantine pending QC
                        created_by=goods_receipt.created_by,
                    )
                else:
                    # Update existing batch quantity
                    batch_lot.quantity_received += stock_qty
                    batch_lot.quantity_available += stock_qty
                    batch_lot.save(update_fields=['quantity_received', 'quantity_available'])

            # Create SerialNumber records if serial tracking is enabled
            serial_numbers_list = getattr(grn_line, 'serial_numbers', None) or []
            if serial_numbers_list and isinstance(serial_numbers_list, list):
                for serial_no in serial_numbers_list:
                    if serial_no and serial_no.strip():
                        SerialNumber.objects.get_or_create(
                            company=goods_receipt.company,
                            budget_item=item,
                            serial_number=serial_no.strip(),
                            defaults={
                                'warehouse': warehouse,
                                'batch_lot': batch_lot,
                                'purchase_order': goods_receipt.purchase_order,
                                'status': 'IN_STOCK',
                                'warranty_start_date': goods_receipt.receipt_date,
                                'created_by': goods_receipt.created_by,
                            }
                        )

            # Create stock movement line with serial numbers joined
            serial_no_str = ', '.join(serial_numbers_list) if serial_numbers_list else ''
            StockMovementLine.objects.create(
                movement=stock_movement,
                line_number=grn_line.purchase_order_line.line_number,
                item=item,
                quantity=stock_qty,
                entered_quantity=entered_qty,
                entered_uom=entered_uom,
                rate=grn_line.purchase_order_line.unit_price,
                batch_no=getattr(grn_line, 'batch_no', ''),
                serial_no=serial_no_str[:250],  # Truncate if too long
                expiry_date=getattr(grn_line, 'expiry_date', None),
                cost_center=getattr(grn_line.purchase_order_line.purchase_order, 'cost_center', None),
            )

        # 3. Check for QC checkpoint and create pending inspection if required
        checkpoint = QCCheckpoint.objects.filter(
            company=goods_receipt.company,
            warehouse=warehouse,
            checkpoint_name='GOODS_RECEIPT',
        ).first()

        if checkpoint:
            # Mark GRN as pending QC
            goods_receipt.quality_status = 'pending'
            goods_receipt.save(update_fields=['quality_status'])

        # 4. Post the stock movement
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

        for do_line in delivery_order.lines.select_related('product__linked_item', 'sales_order_line__product'):
            item = getattr(do_line.product, 'linked_item', None) or getattr(do_line.sales_order_line, 'product', None)
            if not item:
                continue
            profile = item.get_operational_profile()
            entered_qty = do_line.quantity_shipped
            entered_uom = profile.sales_uom or profile.stock_uom
            stock_qty = UoMConversionService.convert_quantity(
                item=item,
                quantity=entered_qty,
                from_uom=entered_uom,
                to_uom=profile.stock_uom,
                context='sales',
            )
            StockMovementLine.objects.create(
                movement=stock_movement,
                line_number=do_line.sales_order_line.line_number,
                item=item,
                quantity=stock_qty,
                entered_quantity=entered_qty,
                entered_uom=entered_uom,
                rate=do_line.sales_order_line.unit_price, # This should be cost price, but using unit price for now
                cost_center=stock_movement.cost_center,
                project=stock_movement.project,
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

        reference_type = receipt_source[0] if receipt_source else 'StockMovement'
        reference_id = receipt_source[1] if receipt_source else movement.id

        for line in movement.lines.all():
            line_cost_center = getattr(line, 'cost_center', None) or getattr(movement, 'cost_center', None)
            line_project = getattr(line, 'project', None) or getattr(movement, 'project', None)

            if movement.movement_type == 'TRANSFER':
                out_qty = -line.quantity
                out_wh = movement.from_warehouse
                valuation_method_used = ''
                layer_consumed_detail = None

                try:
                    total_cost, consumed_layers, method_used = ValuationService.consume_cost_layers(
                        company=movement.company,
                        item=line.budget_item,
                        warehouse=out_wh,
                        qty=line.quantity,
                        source_document_type='StockMovement',
                        source_document_id=movement.id,
                    )
                    valuation_method_used = method_used
                    layer_consumed_detail = consumed_layers
                    line.rate = total_cost / line.quantity
                    line.save(update_fields=['rate'])
                except ValueError:
                    valuation_method_used = 'SIMPLE'

                event = InventoryService._record_movement_event(
                    movement=movement,
                    line=line,
                    warehouse=out_wh,
                    qty_change=out_qty,
                    event_type='TRANSFER_OUT',
                    valuation_method=valuation_method_used,
                    reference_type=reference_type,
                    reference_id=reference_id,
                )

                InventoryService._apply_event_effects(
                    movement=movement,
                    line=line,
                    warehouse=out_wh,
                    quantity_change=out_qty,
                    line_cost_center=line_cost_center,
                    line_project=line_project,
                    valuation_method_used=valuation_method_used,
                    layer_consumed_detail=layer_consumed_detail,
                    event=event,
                )

                InventoryService._create_in_transit_record(
                    movement=movement,
                    line=line,
                    quantity=line.quantity,
                    rate=line.rate,
                    line_cost_center=line_cost_center,
                    line_project=line_project,
                    event=event,
                )

                event_bus.publish('stock.transfer_out', stock_movement_id=movement.id)
                continue

            if movement.movement_type == 'ISSUE':
                quantity_change = -line.quantity
                warehouse = movement.from_warehouse
                is_receipt = False
            else:
                quantity_change = line.quantity
                warehouse = movement.to_warehouse
                is_receipt = True

            valuation_method_used = ''
            layer_consumed_detail = None

            if is_receipt:
                try:
                    ValuationService.create_cost_layer(
                        company=movement.company,
                        item=line.budget_item,
                        warehouse=warehouse,
                        qty=line.quantity,
                        cost_per_unit=line.rate,
                        source_document_type=(receipt_source[0] if receipt_source else 'StockMovement'),
                        source_document_id=(receipt_source[1] if receipt_source else movement.id),
                        batch_no=line.batch_no,
                        serial_no=line.serial_no,
                        receipt_date=timezone.now(),
                        stock_state=(receipt_stock_state or 'RELEASED'),
                        expiry_date=getattr(line, 'expiry_date', None),
                    )

                    val_method = ValuationService.get_valuation_method(movement.company, line.budget_item, warehouse)
                    valuation_method_used = val_method.valuation_method if val_method else 'FIFO'

                except Exception as exc:
                    print(f"Warning: ValuationService error on receipt: {exc}")
                    valuation_method_used = 'SIMPLE'
            else:
                try:
                    total_cost, consumed_layers, method_used = ValuationService.consume_cost_layers(
                        company=movement.company,
                        item=line.budget_item,
                        warehouse=warehouse,
                        qty=line.quantity,
                        source_document_type='StockMovement',
                        source_document_id=movement.id,
                    )

                    valuation_method_used = method_used
                    layer_consumed_detail = consumed_layers
                    line.rate = total_cost / line.quantity
                    line.save(update_fields=['rate'])

                except ValueError as exc:
                    print(f"Warning: ValuationService error on issue: {exc}")
                    valuation_method_used = 'SIMPLE'

            event_type = InventoryService._derive_event_type(movement.movement_type, is_receipt)
            event = InventoryService._record_movement_event(
                movement=movement,
                line=line,
                warehouse=warehouse,
                qty_change=quantity_change,
                event_type=event_type,
                valuation_method=valuation_method_used,
                reference_type=reference_type,
                reference_id=reference_id,
            )

            InventoryService._apply_event_effects(
                movement=movement,
                line=line,
                warehouse=warehouse,
                quantity_change=quantity_change,
                line_cost_center=line_cost_center,
                line_project=line_project,
                valuation_method_used=valuation_method_used,
                layer_consumed_detail=layer_consumed_detail,
                event=event,
            )

        # 3. Update movement status
        if movement.movement_type == 'TRANSFER':
            movement.status = 'IN_TRANSIT'
        else:
            movement.status = 'COMPLETED'
        movement.posted_at = timezone.now()
        movement.save(update_fields=['status', 'posted_at'])

        # 4. Publish the event
        if movement.movement_type == 'RECEIPT':
            event_bus.publish('stock.received', stock_movement_id=movement.id)
        elif movement.movement_type == 'ISSUE':
            event_bus.publish('stock.shipped', stock_movement_id=movement.id)

        return movement

    @staticmethod
    def _derive_event_type(movement_type: str, is_receipt: bool) -> str:
        if movement_type == 'ADJUSTMENT':
            return 'ADJUSTMENT'
        if movement_type == 'TRANSFER':
            return 'TRANSFER_IN' if is_receipt else 'TRANSFER_OUT'
        if movement_type in {'RECEIPT', 'ISSUE'}:
            return movement_type
        return 'RECEIPT' if is_receipt else 'ISSUE'

    @staticmethod
    def _record_movement_event(
        *,
        movement,
        line,
        warehouse,
        qty_change,
        event_type: str,
        valuation_method: str | None,
        reference_type: str,
        reference_id: int,
    ):
        try:
            return MovementEvent.objects.create(
                company=movement.company,
                movement=movement,
                movement_line=line,
                item=line.budget_item,
                warehouse=warehouse,
                event_type=event_type,
                qty_change=qty_change,
                stock_uom=line.budget_item.uom,
                source_uom=line.entered_uom or line.budget_item.uom,
                source_quantity=line.entered_quantity,
                event_date=movement.movement_date,
                reference_document_type=reference_type,
                reference_document_id=reference_id,
                reference_number=movement.movement_number or movement.reference or '',
                cost_per_unit_at_event=line.rate,
                valuation_method_used=valuation_method or '',
                event_metadata={
                    'stock_movement_id': movement.id,
                    'stock_movement_line_id': line.id,
                    'movement_type': movement.movement_type,
                },
            )
        except Exception as exc:
            print(f"Warning: failed to record movement event for movement {movement.id}: {exc}")
            return None

    @staticmethod
    def _apply_event_effects(
        *,
        movement,
        line,
        warehouse,
        quantity_change,
        line_cost_center,
        line_project,
        valuation_method_used,
        layer_consumed_detail,
        event,
    ) -> None:
        ledger_txn_type = 'TRANSFER' if movement.movement_type == 'TRANSFER' else movement.movement_type
        balance_before = StockLevel.objects.filter(
            company=movement.company,
            item=line.budget_item,
            warehouse=warehouse,
        ).first()
        current_balance_qty = balance_before.quantity if balance_before else Decimal('0')
        current_balance_value = (balance_before.quantity * line.rate) if balance_before else Decimal('0')
        new_balance_qty = current_balance_qty + quantity_change
        new_balance_value = current_balance_value + (quantity_change * line.rate)

        StockLedger.objects.create(
            company=movement.company,
            transaction_date=movement.movement_date,
            transaction_type=ledger_txn_type,
            item=line.budget_item,
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
            valuation_method_used=valuation_method_used or '',
            layer_consumed_detail=layer_consumed_detail,
            cost_center=line_cost_center,
            project=line_project,
            movement_event=event,
        )

        stock_level, _ = StockLevel.objects.get_or_create(
            company=movement.company,
            item=line.budget_item,
            warehouse=warehouse,
            defaults={'quantity': 0},
        )
        stock_level.quantity += quantity_change
        stock_level.save()

    @staticmethod
    def _create_in_transit_record(
        *,
        movement,
        line,
        quantity,
        rate,
        line_cost_center,
        line_project,
        event,
    ) -> None:
        InTransitShipmentLine.objects.update_or_create(
            movement=movement,
            movement_line=line,
            defaults={
                'company': movement.company,
                'item': line.budget_item,
                'from_warehouse': movement.from_warehouse,
                'to_warehouse': movement.to_warehouse,
                'quantity': quantity,
                'rate': rate,
                'batch_no': line.batch_no,
                'serial_no': line.serial_no,
                'cost_center': line_cost_center,
                'project': line_project,
                'movement_event': event,
            },
        )

    @staticmethod
    @transaction.atomic
    def confirm_transfer_receipt(movement: StockMovement, receipt_date=None):
        """Confirm arrival of a transfer and move stock from in-transit to destination warehouse."""
        if movement.movement_type != 'TRANSFER':
            raise ValueError('Only transfer movements can be confirmed.')
        if movement.status != 'IN_TRANSIT':
            raise ValueError('Transfer must be in IN_TRANSIT status.')

        pending_lines = list(
            InTransitShipmentLine.objects.select_related(
                'movement_line__item',
                'to_warehouse',
                'from_warehouse',
                'movement_line__entered_uom',
                'movement_line__cost_center',
                'movement_line__project',
                'cost_center',
                'project',
            ).filter(movement=movement)
        )
        if not pending_lines:
            raise ValueError('No in-transit quantities found.')

        receipt_timestamp = receipt_date or timezone.now()
        reference_type = 'StockMovement'
        reference_id = movement.id

        for pending in pending_lines:
            in_qty = pending.quantity
            in_wh = pending.to_warehouse
            line = pending.movement_line
            line_cost_center = pending.cost_center or getattr(line, 'cost_center', None) or getattr(movement, 'cost_center', None)
            line_project = pending.project or getattr(line, 'project', None) or getattr(movement, 'project', None)

            try:
                ValuationService.create_cost_layer(
                    company=movement.company,
                    item=pending.budget_item,
                    warehouse=in_wh,
                    qty=in_qty,
                    cost_per_unit=pending.rate,
                    source_document_type='StockMovement',
                    source_document_id=movement.id,
                    batch_no=pending.batch_no,
                    serial_no=pending.serial_no,
                    receipt_date=receipt_timestamp,
                    stock_state='RELEASED'
                )
            except Exception:
                pass

            event = InventoryService._record_movement_event(
                movement=movement,
                line=line,
                warehouse=in_wh,
                qty_change=in_qty,
                event_type='TRANSFER_IN',
                valuation_method='TRANSFER',
                reference_type=reference_type,
                reference_id=reference_id,
            )

            InventoryService._apply_event_effects(
                movement=movement,
                line=line,
                warehouse=in_wh,
                quantity_change=in_qty,
                line_cost_center=line_cost_center,
                line_project=line_project,
                valuation_method_used='TRANSFER',
                layer_consumed_detail=None,
                event=event,
            )

        InTransitShipmentLine.objects.filter(movement=movement).delete()
        movement.status = 'COMPLETED'
        movement.posted_at = receipt_timestamp
        movement.save(update_fields=['status', 'posted_at'])
        event_bus.publish('stock.transfer_in', stock_movement_id=movement.id)
