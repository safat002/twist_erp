"""
Return To Vendor (RTV) Service

Handles supplier returns including:
- Negative movement events for inventory reduction
- Budget usage reversal
- Financial implications (refunds, debit notes)
- GL posting for returns
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, F
from ..models import (
    ReturnToVendor, ReturnToVendorLine, GoodsReceipt, GoodsReceiptLine,
    MovementEvent, Product, Warehouse
)


class RTVService:
    """Service for managing Return To Vendor operations."""

    @staticmethod
    def create_rtv(company, goods_receipt, supplier_id, reason, rtv_date=None,
                  refund_expected=True, notes=None, created_by=None):
        """
        Create a new Return To Vendor record.

        Args:
            company: Company instance
            goods_receipt: GoodsReceipt instance being returned
            supplier_id: Supplier ID
            reason: Reason for return (DEFECTIVE, WRONG_ITEM, etc.)
            rtv_date: Date of return (default today)
            refund_expected: Whether refund is expected
            notes: Additional notes
            created_by: User creating the RTV

        Returns:
            ReturnToVendor instance
        """
        if rtv_date is None:
            rtv_date = timezone.now().date()

        rtv = ReturnToVendor.objects.create(
            company=company,
            rtv_date=rtv_date,
            goods_receipt=goods_receipt,
            supplier_id=supplier_id,
            reason=reason,
            refund_expected=refund_expected,
            status='DRAFT',
            notes=notes or '',
            created_by=created_by
        )

        return rtv

    @staticmethod
    def add_rtv_line(rtv, goods_receipt_line, product, quantity_to_return,
                    unit_cost, uom, description='', reason='',
                    batch_lot_id=None, serial_numbers=None, quality_notes=None,
                    budget_item=None):
        """
        Add a line item to the RTV.

        Args:
            rtv: ReturnToVendor instance
            goods_receipt_line: Original GoodsReceiptLine
            product: Product being returned
            quantity_to_return: Quantity to return
            unit_cost: Cost per unit
            uom: Unit of measure
            description: Line description
            reason: Reason for this line
            batch_lot_id: Batch/Lot identifier
            serial_numbers: JSON array of serial numbers
            quality_notes: Quality inspection notes
            budget_item: BudgetItem if applicable

        Returns:
            ReturnToVendorLine instance
        """
        if not rtv.can_edit():
            raise ValueError(f"Cannot add lines to RTV {rtv.rtv_number} in {rtv.status} status")

        line_total = quantity_to_return * unit_cost

        line = ReturnToVendorLine.objects.create(
            company=rtv.company,
            rtv=rtv,
            goods_receipt_line=goods_receipt_line,
            budget_item=product,
            description=description or product.name,
            quantity_to_return=quantity_to_return,
            uom=uom,
            unit_cost=unit_cost,
            line_total=line_total,
            reason=reason,
            batch_lot_id=batch_lot_id,
            serial_numbers=serial_numbers,
            quality_notes=quality_notes
        )

        # Update RTV total
        rtv.total_return_value = rtv.lines.aggregate(
            total=Sum('line_total')
        )['total'] or Decimal('0')
        rtv.save()

        return line

    @staticmethod
    def submit_rtv(rtv):
        """
        Submit RTV for approval.

        Args:
            rtv: ReturnToVendor instance

        Returns:
            Updated RTV
        """
        if not rtv.can_submit():
            raise ValueError(f"RTV {rtv.rtv_number} cannot be submitted in {rtv.status} status")

        if not rtv.lines.exists():
            raise ValueError("Cannot submit RTV without any lines")

        rtv.status = 'SUBMITTED'
        rtv.submitted_at = timezone.now()
        rtv.save()

        return rtv

    @staticmethod
    @transaction.atomic
    def approve_rtv(rtv, approved_by):
        """
        Approve RTV and create negative movement events.

        This is the critical step that:
        1. Creates negative MovementEvent records to reduce inventory
        2. Updates stock levels
        3. Does NOT yet reverse budget (that happens on completion)

        Args:
            rtv: ReturnToVendor instance
            approved_by: User approving the RTV

        Returns:
            Updated RTV with movement events created
        """
        if not rtv.can_approve():
            raise ValueError(f"RTV {rtv.rtv_number} cannot be approved in {rtv.status} status")

        # Get the warehouse from the original GRN
        warehouse = rtv.goods_receipt.warehouse

        # Create negative movement events for each line
        for line in rtv.lines.all():
            # Create negative movement event (RETURN_TO_VENDOR)
            movement_event = MovementEvent.objects.create(
                company=rtv.company,
                product=line.product,
                warehouse=warehouse,
                event_type='RETURN_TO_VENDOR',
                quantity=-line.quantity_to_return,  # NEGATIVE quantity
                uom=line.uom,
                cost_per_unit=line.unit_cost,
                total_cost=-line.line_total,  # NEGATIVE cost
                transaction_date=rtv.rtv_date,
                reference_type='RTV',
                reference_id=rtv.id,
                reference_line_id=line.id,
                batch_lot_id=line.batch_lot_id,
                serial_numbers=line.serial_numbers,
                notes=f"Return to vendor: {rtv.rtv_number} - {line.reason}"
            )

            # Link movement event to RTV line
            line.movement_event = movement_event
            line.save()

        rtv.status = 'APPROVED'
        rtv.approved_by = approved_by
        rtv.approved_at = timezone.now()
        rtv.save()

        return rtv

    @staticmethod
    @transaction.atomic
    def complete_rtv(rtv, refund_amount=None, debit_note_number=None,
                    debit_note_date=None, actual_delivery_date=None):
        """
        Complete the RTV after vendor receives goods.

        This step:
        1. Reverses budget usage (if applicable)
        2. Updates refund information
        3. Posts financial transactions to GL
        4. Marks RTV as completed

        Args:
            rtv: ReturnToVendor instance
            refund_amount: Actual refund amount received
            debit_note_number: Debit note number
            debit_note_date: Debit note date
            actual_delivery_date: Date vendor received goods

        Returns:
            Updated RTV
        """
        if not rtv.can_complete():
            raise ValueError(f"RTV {rtv.rtv_number} cannot be completed in {rtv.status} status")

        # Reverse budget usage for each line
        for line in rtv.lines.all():
            if line.budget_item:
                RTVService._reverse_budget_usage(line)

        # Update refund information
        if refund_amount is not None:
            rtv.refund_amount = refund_amount
            rtv.refund_status = 'RECEIVED' if refund_amount > 0 else 'NOT_APPLICABLE'

        if debit_note_number:
            rtv.debit_note_number = debit_note_number
            rtv.debit_note_date = debit_note_date or timezone.now().date()

        if actual_delivery_date:
            rtv.delivered_to_vendor_date = actual_delivery_date

        rtv.status = 'COMPLETED'
        rtv.completed_at = timezone.now()
        rtv.save()

        # Post to GL
        RTVService.post_rtv_to_gl(rtv)

        return rtv

    @staticmethod
    def _reverse_budget_usage(rtv_line):
        """
        Reverse budget usage for a returned item.

        Args:
            rtv_line: ReturnToVendorLine instance

        Returns:
            None
        """
        if not rtv_line.budget_item:
            return

        # Import here to avoid circular dependency
        from apps.budgeting.models import BudgetUsage

        # Find the original budget usage from the GRN
        original_usages = BudgetUsage.objects.filter(
            budget_item=rtv_line.budget_item,
            reference_type='GRN',
            reference_id=rtv_line.rtv.goods_receipt.id,
            reference_line_id=rtv_line.goods_receipt_line.id
        )

        # Calculate reversal amount
        reversal_amount = rtv_line.line_total

        # Create reversal budget usage record (negative amount)
        for original_usage in original_usages:
            # Calculate proportional reversal
            if original_usage.quantity_used > 0:
                reversal_qty = (rtv_line.quantity_to_return / original_usage.quantity_used) * original_usage.quantity_used
                reversal_amt = (rtv_line.quantity_to_return / original_usage.quantity_used) * original_usage.amount_used
            else:
                reversal_qty = rtv_line.quantity_to_return
                reversal_amt = reversal_amount

            BudgetUsage.objects.create(
                company=rtv_line.company,
                budget_item=rtv_line.budget_item,
                usage_date=rtv_line.rtv.rtv_date,
                quantity_used=-reversal_qty,  # NEGATIVE to reverse
                amount_used=-reversal_amt,    # NEGATIVE to reverse
                reference_type='RTV',
                reference_id=rtv_line.rtv.id,
                reference_line_id=rtv_line.id,
                notes=f"Budget reversal for RTV {rtv_line.rtv.rtv_number}"
            )

        # Mark line as budget reversed
        rtv_line.budget_reversed = True
        rtv_line.budget_reversal_date = timezone.now()
        rtv_line.save()

    @staticmethod
    @transaction.atomic
    def post_rtv_to_gl(rtv):
        """
        Post RTV to General Ledger.

        Journal Entry:
        - Debit: Accounts Payable (reduce liability to supplier)
        - Credit: Inventory Asset (reduce inventory value)

        If refund received:
        - Debit: Cash/Bank (when refund received)
        - Credit: Accounts Payable (clear the balance)

        Args:
            rtv: ReturnToVendor instance

        Returns:
            Journal entry ID
        """
        if rtv.posted_to_gl:
            raise ValueError(f"RTV {rtv.rtv_number} is already posted to GL")

        if rtv.status != 'COMPLETED':
            raise ValueError(f"RTV must be COMPLETED before posting to GL (current: {rtv.status})")

        # Import here to avoid circular dependency
        from apps.finance.services.journal_service import JournalService

        # Create journal entry
        je = JournalService.create_journal_entry(
            company=rtv.company,
            entry_date=rtv.rtv_date,
            description=f"Return to Vendor - {rtv.rtv_number}",
            reference_type='RTV',
            reference_id=rtv.id
        )

        # Debit: Accounts Payable (we're reducing what we owe the supplier)
        JournalService.add_line(
            journal_entry=je,
            account_code='2100',  # Accounts Payable
            debit=rtv.total_return_value,
            credit=Decimal('0'),
            description=f"RTV {rtv.rtv_number} - Reduce AP"
        )

        # Credit: Inventory Asset (reduce inventory value)
        JournalService.add_line(
            journal_entry=je,
            account_code='1400',  # Inventory Asset
            debit=Decimal('0'),
            credit=rtv.total_return_value,
            description=f"RTV {rtv.rtv_number} - Reduce Inventory"
        )

        # If refund was received, create additional entry
        if rtv.refund_amount and rtv.refund_amount > 0:
            # Debit: Cash/Bank
            JournalService.add_line(
                journal_entry=je,
                account_code='1000',  # Cash/Bank
                debit=rtv.refund_amount,
                credit=Decimal('0'),
                description=f"RTV {rtv.rtv_number} - Refund received"
            )

            # Credit: Accounts Payable (if refund equals return value) or Other Income (if variance)
            if rtv.refund_amount == rtv.total_return_value:
                # Already balanced by the AP debit above
                pass
            elif rtv.refund_amount < rtv.total_return_value:
                # Loss - debit to loss account
                loss_amount = rtv.total_return_value - rtv.refund_amount
                JournalService.add_line(
                    journal_entry=je,
                    account_code='6500',  # Loss on Returns
                    debit=loss_amount,
                    credit=Decimal('0'),
                    description=f"RTV {rtv.rtv_number} - Loss on return"
                )
            else:
                # Gain - credit to gain account
                gain_amount = rtv.refund_amount - rtv.total_return_value
                JournalService.add_line(
                    journal_entry=je,
                    account_code='4500',  # Gain on Returns
                    debit=Decimal('0'),
                    credit=gain_amount,
                    description=f"RTV {rtv.rtv_number} - Gain on return"
                )

        # Post the journal entry
        JournalService.post_journal_entry(je)

        # Update RTV
        rtv.je_id = je.id
        rtv.posted_to_gl = True
        rtv.gl_posted_date = timezone.now()
        rtv.save()

        return je.id

    @staticmethod
    def get_rtv_summary(rtv):
        """
        Get detailed summary of RTV and its lines.

        Args:
            rtv: ReturnToVendor instance

        Returns:
            Dictionary with summary data
        """
        lines = rtv.lines.select_related(
            'goods_receipt_line', 'product', 'uom', 'movement_event'
        ).all()

        line_details = []
        total_qty = Decimal('0')
        total_budget_reversed = Decimal('0')

        for line in lines:
            line_details.append({
                'id': line.id,
                'product_code': line.product.code,
                'product_name': line.product.name,
                'quantity': str(line.quantity_to_return),
                'uom': line.uom.name,
                'unit_cost': str(line.unit_cost),
                'line_total': str(line.line_total),
                'reason': line.reason,
                'budget_reversed': line.budget_reversed,
                'movement_event_id': line.movement_event.id if line.movement_event else None
            })
            total_qty += line.quantity_to_return
            if line.budget_reversed:
                total_budget_reversed += line.line_total

        return {
            'rtv_number': rtv.rtv_number,
            'rtv_date': rtv.rtv_date.isoformat(),
            'goods_receipt_number': rtv.goods_receipt.grn_number,
            'supplier_id': rtv.supplier_id,
            'reason': rtv.reason,
            'reason_display': rtv.get_reason_display(),
            'status': rtv.status,
            'status_display': rtv.get_status_display(),
            'total_return_value': str(rtv.total_return_value),
            'total_quantity': str(total_qty),
            'refund_expected': rtv.refund_expected,
            'refund_amount': str(rtv.refund_amount) if rtv.refund_amount else None,
            'refund_status': rtv.refund_status,
            'total_budget_reversed': str(total_budget_reversed),
            'posted_to_gl': rtv.posted_to_gl,
            'gl_posted_date': rtv.gl_posted_date.isoformat() if rtv.gl_posted_date else None,
            'debit_note_number': rtv.debit_note_number,
            'lines': line_details,
            'line_count': len(line_details)
        }

    @staticmethod
    def cancel_rtv(rtv, reason):
        """
        Cancel an RTV (only if not yet completed).

        Args:
            rtv: ReturnToVendor instance
            reason: Reason for cancellation

        Returns:
            Updated RTV
        """
        if rtv.status in ['COMPLETED', 'CANCELLED']:
            raise ValueError(f"Cannot cancel RTV in {rtv.status} status")

        # If approved, we need to reverse the movement events
        if rtv.status == 'APPROVED':
            for line in rtv.lines.all():
                if line.movement_event:
                    # Mark movement event as cancelled/reversed
                    line.movement_event.notes += f"\n\nCANCELLED: {reason} at {timezone.now()}"
                    line.movement_event.save()

        rtv.status = 'CANCELLED'
        rtv.notes = f"{rtv.notes}\n\nCANCELLED: {reason} at {timezone.now()}"
        rtv.save()

        return rtv

    @staticmethod
    def update_shipping_info(rtv, carrier, tracking_number, pickup_date,
                           expected_delivery_date=None):
        """
        Update shipping information for RTV.

        Args:
            rtv: ReturnToVendor instance
            carrier: Carrier name
            tracking_number: Tracking number
            pickup_date: Pickup date
            expected_delivery_date: Expected delivery date

        Returns:
            Updated RTV
        """
        rtv.carrier = carrier
        rtv.tracking_number = tracking_number
        rtv.pickup_date = pickup_date
        rtv.expected_delivery_date = expected_delivery_date
        rtv.status = 'IN_TRANSIT'
        rtv.save()

        return rtv
