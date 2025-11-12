"""
Landed Cost Voucher Service

Handles the allocation of landed costs from vouchers to cost layers.
Manages voucher workflow, cost layer updates, and GL posting.
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, F, Q
from ..models import (
    LandedCostVoucher, LandedCostAllocation, CostLayer,
    GoodsReceipt, GoodsReceiptLine, Product
)


class LandedCostVoucherService:
    """Service for managing landed cost vouchers and allocations."""

    @staticmethod
    def create_voucher(company, voucher_date, description, total_cost,
                      currency='USD', invoice_number=None, invoice_date=None,
                      supplier_id=None, notes=None):
        """
        Create a new landed cost voucher.

        Args:
            company: Company instance
            voucher_date: Date of the voucher
            description: Description of the landed cost
            total_cost: Total cost amount
            currency: Currency code (default USD)
            invoice_number: Supplier invoice number
            invoice_date: Supplier invoice date
            supplier_id: Supplier ID
            notes: Additional notes

        Returns:
            LandedCostVoucher instance
        """
        voucher = LandedCostVoucher.objects.create(
            company=company,
            voucher_date=voucher_date,
            description=description,
            total_cost=total_cost,
            currency=currency,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            supplier_id=supplier_id,
            notes=notes,
            status='DRAFT'
        )
        return voucher

    @staticmethod
    def submit_voucher(voucher, submitted_by):
        """
        Submit voucher for approval.

        Args:
            voucher: LandedCostVoucher instance
            submitted_by: User submitting the voucher

        Returns:
            Updated voucher
        """
        if not voucher.can_submit():
            raise ValueError(f"Voucher {voucher.voucher_number} cannot be submitted in {voucher.status} status")

        voucher.status = 'SUBMITTED'
        voucher.submitted_by = submitted_by
        voucher.submitted_at = timezone.now()
        voucher.save()
        return voucher

    @staticmethod
    def approve_voucher(voucher, approved_by):
        """
        Approve voucher for allocation.

        Args:
            voucher: LandedCostVoucher instance
            approved_by: User approving the voucher

        Returns:
            Updated voucher
        """
        if not voucher.can_approve():
            raise ValueError(f"Voucher {voucher.voucher_number} cannot be approved in {voucher.status} status")

        voucher.status = 'APPROVED'
        voucher.approved_by = approved_by
        voucher.approved_at = timezone.now()
        voucher.save()
        return voucher

    @staticmethod
    @transaction.atomic
    def allocate_to_cost_layers(voucher, allocation_plan, allocated_by):
        """
        Allocate voucher amounts to specific cost layers.

        Args:
            voucher: LandedCostVoucher instance
            allocation_plan: List of dicts with allocation details:
                [
                    {
                        'goods_receipt_id': int,
                        'goods_receipt_line_id': int,
                        'product_id': int,
                        'cost_layer_id': int,
                        'allocated_amount': Decimal,
                        'allocation_percentage': Decimal,
                        'notes': str (optional)
                    },
                    ...
                ]
            allocated_by: User performing the allocation

        Returns:
            List of created LandedCostAllocation instances
        """
        if not voucher.can_allocate():
            raise ValueError(f"Voucher {voucher.voucher_number} cannot be allocated in {voucher.status} status")

        # Validate total allocation doesn't exceed voucher amount
        total_allocation = sum(Decimal(str(item['allocated_amount'])) for item in allocation_plan)
        if total_allocation > voucher.total_cost:
            raise ValueError(f"Total allocation {total_allocation} exceeds voucher amount {voucher.total_cost}")

        allocations = []

        for plan_item in allocation_plan:
            # Get related objects
            goods_receipt = GoodsReceipt.objects.get(id=plan_item['goods_receipt_id'])
            goods_receipt_line = GoodsReceiptLine.objects.get(id=plan_item['goods_receipt_line_id'])
            product = Product.objects.get(id=plan_item['product_id'])
            cost_layer = CostLayer.objects.get(id=plan_item['cost_layer_id'])

            allocated_amount = Decimal(str(plan_item['allocated_amount']))
            allocation_percentage = Decimal(str(plan_item.get('allocation_percentage', 0)))

            # Calculate inventory vs COGS split based on remaining quantity
            remaining_qty = cost_layer.remaining_quantity
            total_qty = cost_layer.quantity

            if total_qty > 0:
                inventory_ratio = remaining_qty / total_qty
                to_inventory = allocated_amount * inventory_ratio
                to_cogs = allocated_amount * (Decimal('1') - inventory_ratio)
            else:
                to_inventory = Decimal('0')
                to_cogs = allocated_amount

            # Calculate cost per unit adjustment
            if total_qty > 0:
                cost_per_unit_adjustment = allocated_amount / total_qty
            else:
                cost_per_unit_adjustment = Decimal('0')

            original_cost_per_unit = cost_layer.cost_per_unit
            new_cost_per_unit = original_cost_per_unit + cost_per_unit_adjustment

            # Create allocation record
            allocation = LandedCostAllocation.objects.create(
                company=voucher.company,
                voucher=voucher,
                goods_receipt=goods_receipt,
                goods_receipt_line=goods_receipt_line,
                budget_item=product,
                cost_layer=cost_layer,
                allocated_amount=allocated_amount,
                allocation_percentage=allocation_percentage,
                to_inventory=to_inventory,
                to_cogs=to_cogs,
                original_cost_per_unit=original_cost_per_unit,
                cost_per_unit_adjustment=cost_per_unit_adjustment,
                new_cost_per_unit=new_cost_per_unit,
                notes=plan_item.get('notes', '')
            )

            # Update the cost layer
            cost_layer.cost_per_unit = new_cost_per_unit
            cost_layer.total_cost = cost_layer.quantity * new_cost_per_unit
            cost_layer.save()

            allocations.append(allocation)

        # Update voucher status and allocated amount
        voucher.allocated_cost = total_allocation
        voucher.status = 'ALLOCATED'
        voucher.save()

        return allocations

    @staticmethod
    def generate_allocation_plan(voucher, goods_receipts, apportionment_method='BY_VALUE'):
        """
        Generate an allocation plan for distributing voucher cost across GRNs.

        Args:
            voucher: LandedCostVoucher instance
            goods_receipts: List of GoodsReceipt instances to allocate to
            apportionment_method: Method for distribution
                - BY_VALUE: Distribute by line value
                - BY_QUANTITY: Distribute by quantity
                - EQUAL: Equal distribution

        Returns:
            List of allocation plan items
        """
        allocation_plan = []

        # Collect all lines from the GRNs with their cost layers
        grn_lines = []
        for grn in goods_receipts:
            for line in grn.lines.all():
                # Get the most recent cost layer for this line
                cost_layer = CostLayer.objects.filter(
                    company=voucher.company,
                    product=line.product,
                    goods_receipt_line=line
                ).order_by('-created_at').first()

                if cost_layer:
                    grn_lines.append({
                        'grn': grn,
                        'line': line,
                        'cost_layer': cost_layer,
                        'quantity': line.quantity,
                        'value': line.quantity * line.unit_price
                    })

        if not grn_lines:
            return []

        # Calculate basis for apportionment
        if apportionment_method == 'BY_VALUE':
            total_basis = sum(item['value'] for item in grn_lines)
        elif apportionment_method == 'BY_QUANTITY':
            total_basis = sum(item['quantity'] for item in grn_lines)
        elif apportionment_method == 'EQUAL':
            total_basis = len(grn_lines)
        else:
            raise ValueError(f"Unknown apportionment method: {apportionment_method}")

        # Generate allocation plan
        for item in grn_lines:
            if apportionment_method == 'BY_VALUE':
                basis_value = item['value']
            elif apportionment_method == 'BY_QUANTITY':
                basis_value = item['quantity']
            elif apportionment_method == 'EQUAL':
                basis_value = Decimal('1')

            allocation_percentage = (basis_value / total_basis) * 100 if total_basis > 0 else Decimal('0')
            allocated_amount = (voucher.total_cost * basis_value / total_basis) if total_basis > 0 else Decimal('0')

            allocation_plan.append({
                'goods_receipt_id': item['grn'].id,
                'goods_receipt_line_id': item['line'].id,
                'product_id': item['line'].product.id,
                'cost_layer_id': item['cost_layer'].id,
                'allocated_amount': allocated_amount,
                'allocation_percentage': allocation_percentage,
                'basis_value': basis_value
            })

        return allocation_plan

    @staticmethod
    @transaction.atomic
    def post_voucher_to_gl(voucher):
        """
        Post landed cost voucher to GL.

        Creates journal entries for:
        - Inventory adjustment (debit)
        - COGS adjustment (debit)
        - Accrued landed costs / AP (credit)

        Args:
            voucher: LandedCostVoucher instance

        Returns:
            Journal entry ID
        """
        if voucher.posted_to_gl:
            raise ValueError(f"Voucher {voucher.voucher_number} is already posted to GL")

        if voucher.status != 'ALLOCATED':
            raise ValueError(f"Voucher must be ALLOCATED before posting to GL (current: {voucher.status})")

        # Calculate total inventory and COGS amounts
        allocations = voucher.allocations.all()
        total_inventory = allocations.aggregate(total=Sum('to_inventory'))['total'] or Decimal('0')
        total_cogs = allocations.aggregate(total=Sum('to_cogs'))['total'] or Decimal('0')

        # Import here to avoid circular dependency
        from apps.finance.services.journal_service import JournalService

        # Create journal entry
        je = JournalService.create_journal_entry(
            company=voucher.company,
            entry_date=voucher.voucher_date,
            description=f"Landed Cost Allocation - {voucher.voucher_number}",
            reference_type='LANDED_COST_VOUCHER',
            reference_id=voucher.id
        )

        # Debit: Inventory Asset (for remaining inventory)
        if total_inventory > 0:
            JournalService.add_line(
                journal_entry=je,
                account_code='1400',  # Inventory Asset
                debit=total_inventory,
                credit=Decimal('0'),
                description=f"Landed cost to inventory - {voucher.description}"
            )

        # Debit: COGS (for consumed inventory)
        if total_cogs > 0:
            JournalService.add_line(
                journal_entry=je,
                account_code='5000',  # COGS
                debit=total_cogs,
                credit=Decimal('0'),
                description=f"Landed cost to COGS - {voucher.description}"
            )

        # Credit: Accrued Landed Costs / AP
        JournalService.add_line(
            journal_entry=je,
            account_code='2100',  # Accounts Payable or Accrued Expenses
            debit=Decimal('0'),
            credit=voucher.allocated_cost,
            description=f"Landed cost payable - {voucher.invoice_number or 'N/A'}"
        )

        # Post the journal entry
        JournalService.post_journal_entry(je)

        # Update voucher
        voucher.je_id = je.id
        voucher.posted_to_gl = True
        voucher.gl_posted_date = timezone.now()
        voucher.status = 'POSTED'
        voucher.save()

        return je.id

    @staticmethod
    def get_voucher_summary(voucher):
        """
        Get detailed summary of voucher and its allocations.

        Args:
            voucher: LandedCostVoucher instance

        Returns:
            Dictionary with summary data
        """
        allocations = voucher.allocations.select_related(
            'goods_receipt', 'goods_receipt_line', 'product', 'cost_layer'
        ).all()

        total_inventory = allocations.aggregate(total=Sum('to_inventory'))['total'] or Decimal('0')
        total_cogs = allocations.aggregate(total=Sum('to_cogs'))['total'] or Decimal('0')

        allocation_details = []
        for alloc in allocations:
            allocation_details.append({
                'id': alloc.id,
                'grn_number': alloc.goods_receipt.grn_number,
                'product_code': alloc.product.code,
                'product_name': alloc.product.name,
                'allocated_amount': str(alloc.allocated_amount),
                'allocation_percentage': str(alloc.allocation_percentage),
                'to_inventory': str(alloc.to_inventory),
                'to_cogs': str(alloc.to_cogs),
                'original_cost': str(alloc.original_cost_per_unit),
                'cost_adjustment': str(alloc.cost_per_unit_adjustment),
                'new_cost': str(alloc.new_cost_per_unit)
            })

        return {
            'voucher_number': voucher.voucher_number,
            'voucher_date': voucher.voucher_date.isoformat(),
            'description': voucher.description,
            'total_cost': str(voucher.total_cost),
            'allocated_cost': str(voucher.allocated_cost),
            'unallocated_cost': str(voucher.unallocated_cost),
            'status': voucher.status,
            'total_to_inventory': str(total_inventory),
            'total_to_cogs': str(total_cogs),
            'posted_to_gl': voucher.posted_to_gl,
            'gl_posted_date': voucher.gl_posted_date.isoformat() if voucher.gl_posted_date else None,
            'allocations': allocation_details,
            'allocation_count': len(allocation_details)
        }

    @staticmethod
    @transaction.atomic
    def reverse_allocation(allocation, reason):
        """
        Reverse a specific allocation and restore cost layer to original value.

        Args:
            allocation: LandedCostAllocation instance
            reason: Reason for reversal

        Returns:
            Updated allocation
        """
        cost_layer = allocation.cost_layer

        # Restore original cost per unit
        cost_layer.cost_per_unit = allocation.original_cost_per_unit
        cost_layer.total_cost = cost_layer.quantity * cost_layer.cost_per_unit
        cost_layer.save()

        # Update voucher allocated cost
        voucher = allocation.voucher
        voucher.allocated_cost -= allocation.allocated_amount
        voucher.save()

        # Add reversal note to allocation
        allocation.notes = f"{allocation.notes}\n\nREVERSED: {reason} at {timezone.now()}"
        allocation.save()

        # Delete the allocation record
        allocation.delete()

        return None

    @staticmethod
    def cancel_voucher(voucher, reason):
        """
        Cancel a voucher (only if not yet allocated).

        Args:
            voucher: LandedCostVoucher instance
            reason: Reason for cancellation

        Returns:
            Updated voucher
        """
        if voucher.status not in ['DRAFT', 'SUBMITTED', 'APPROVED']:
            raise ValueError(f"Cannot cancel voucher in {voucher.status} status")

        voucher.status = 'CANCELLED'
        voucher.notes = f"{voucher.notes}\n\nCANCELLED: {reason} at {timezone.now()}"
        voucher.save()

        return voucher
