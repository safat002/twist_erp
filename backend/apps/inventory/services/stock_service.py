
from django.db import transaction
from django.utils import timezone

from ..models import StockMovement, StockMovementLine, StockLedger, StockLevel
from shared.event_bus import event_bus

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
                product=grn_line.item,
                quantity=grn_line.quantity_received,
                rate=grn_line.purchase_order_line.unit_price
            )
        
        # 3. Post the stock movement
        posted_movement = InventoryService._post_stock_movement(stock_movement)
        
        return posted_movement

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
                product=do_line.item,
                quantity=do_line.quantity_shipped,
                rate=do_line.sales_order_line.unit_price # This should be cost price, but using unit price for now
            )
        
        posted_movement = InventoryService._post_stock_movement(stock_movement)
        return posted_movement

    @staticmethod
    @transaction.atomic
    def _post_stock_movement(movement: StockMovement):
        """
        Posts a stock movement to the StockLedger, updates stock levels,
        and publishes an event.
        """
        if movement.status != 'DRAFT':
            raise ValueError("Stock movement must be in DRAFT status to be posted.")

        for line in movement.lines.all():
            
            if movement.movement_type == 'ISSUE':
                quantity_change = -line.quantity
                warehouse = movement.from_warehouse
            else:
                quantity_change = line.quantity
                warehouse = movement.to_warehouse

            # 1. Create immutable StockLedger entry
            StockLedger.objects.create(
                company=movement.company,
                transaction_date=movement.movement_date,
                transaction_type=movement.movement_type,
                product=line.product,
                warehouse=warehouse,
                quantity=quantity_change,
                rate=line.rate,
                value=quantity_change * line.rate,
                source_document_type='StockMovement',
                source_document_id=movement.id
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
            
        return movement
