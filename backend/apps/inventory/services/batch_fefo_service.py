"""
Batch & FEFO Service
Handles batch/serial tracking, FEFO allocation, and expiry management.
"""
from decimal import Decimal
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Q, Sum
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.inventory.models import (
    BatchLot,
    SerialNumber,
    ItemFEFOConfig,
    Item,
    MovementEvent,
)


class BatchFEFOService:
    """Service for batch/lot management and FEFO enforcement"""

    @staticmethod
    @transaction.atomic
    def create_batch_lot(grn, line, batch_data, created_by):
        """
        Create a new batch/lot from goods receipt

        Args:
            grn: GoodsReceipt instance
            line: GoodsReceiptLine instance
            batch_data: dict with:
                - supplier_lot_number: str (optional)
                - internal_batch_code: str (required, unique)
                - mfg_date: date (optional)
                - exp_date: date (optional)
                - cost_per_unit: Decimal
                - certificate_of_analysis: File (optional)
                - storage_location: str (optional)
                - hazmat_classification: str (optional)
            created_by: User creating the batch

        Returns:
            BatchLot instance
        """
        budget_item = line.budget_item

        # Calculate expiry date if not provided
        exp_date = batch_data.get('exp_date')
        if not exp_date and budget_item:
            fefo_config = ItemFEFOConfig.objects.filter(
                budget_item=budget_item,
                company=grn.company
            ).first()

            if fefo_config and fefo_config.shelf_life_days > 0:
                exp_date = BatchFEFOService._calculate_expiry_date(
                    batch_data.get('mfg_date'),
                    batch_data.get('received_date', date.today()),
                    fefo_config
                )

        # Calculate FEFO sequence (lower = earlier expiry = pick first)
        fefo_sequence = 0
        if exp_date:
            # Use days until expiry as sequence (negative if expired)
            days_until_expiry = (exp_date - date.today()).days
            fefo_sequence = days_until_expiry

        batch = BatchLot.objects.create(
            company=grn.company,
            budget_item=budget_item,
            item=line.item if hasattr(line, 'item') else None,
            supplier_lot_number=batch_data.get('supplier_lot_number', ''),
            internal_batch_code=batch_data['internal_batch_code'],
            grn=grn,
            mfg_date=batch_data.get('mfg_date'),
            exp_date=exp_date,
            received_date=batch_data.get('received_date', date.today()),
            received_qty=line.quantity,
            current_qty=line.quantity,
            cost_per_unit=batch_data.get('cost_per_unit', line.unit_cost),
            certificate_of_analysis=batch_data.get('certificate_of_analysis'),
            storage_location=batch_data.get('storage_location', ''),
            hazmat_classification=batch_data.get('hazmat_classification', ''),
            hold_status='QUARANTINE',  # Always start in quarantine
            fefo_sequence=fefo_sequence,
        )

        return batch

    @staticmethod
    def _calculate_expiry_date(mfg_date, received_date, fefo_config):
        """Calculate expiry date based on FEFO configuration"""
        if fefo_config.expiry_calculation_rule == 'FIXED_DATE':
            # Expiry date should be provided explicitly
            return None

        elif fefo_config.expiry_calculation_rule == 'DAYS_FROM_MFG':
            if not mfg_date:
                return None
            return mfg_date + timedelta(days=fefo_config.shelf_life_days)

        elif fefo_config.expiry_calculation_rule == 'DAYS_FROM_RECEIPT':
            return received_date + timedelta(days=fefo_config.shelf_life_days)

        return None

    @staticmethod
    def allocate_batches_fefo(budget_item, company, warehouse, quantity_needed):
        """
        Allocate batches using FEFO (First Expiry, First Out) logic

        Args:
            budget_item: BudgetItemCode instance
            company: Company instance
            warehouse: Warehouse instance
            quantity_needed: Decimal - quantity to allocate

        Returns:
            List of dicts: [{'batch': BatchLot, 'qty': Decimal}, ...]

        Raises:
            ValidationError if insufficient released stock
        """
        # Get FEFO config
        fefo_config = ItemFEFOConfig.objects.filter(
            budget_item=budget_item,
            company=company
        ).first()

        # Get available batches
        available_batches = BatchLot.objects.filter(
            budget_item=budget_item,
            company=company,
            hold_status='RELEASED',
            current_qty__gt=0
        )

        # Filter by warehouse if specified in config
        if fefo_config and fefo_config.warehouse:
            # TODO: Add warehouse filtering when warehouse is linked to batches
            pass

        # Check expiry blocking
        if fefo_config and fefo_config.block_issue_if_expired:
            available_batches = available_batches.filter(
                Q(exp_date__isnull=True) | Q(exp_date__gte=date.today())
            )

        # Sort by FEFO sequence (earliest expiry first)
        if fefo_config and fefo_config.enforce_fefo:
            available_batches = available_batches.order_by('fefo_sequence', 'exp_date', 'received_date')
        else:
            # Default to FIFO
            available_batches = available_batches.order_by('received_date', 'id')

        # Allocate batches
        allocations = []
        remaining_needed = Decimal(str(quantity_needed))

        for batch in available_batches:
            if remaining_needed <= 0:
                break

            # Check if batch needs expiry warning
            if batch.exp_date and fefo_config:
                days_until_expiry = batch.days_until_expiry()
                if days_until_expiry and days_until_expiry <= fefo_config.warn_days_before_expiry:
                    # TODO: Create expiry warning notification
                    pass

            # Allocate from this batch
            qty_from_batch = min(batch.current_qty, remaining_needed)
            allocations.append({
                'batch': batch,
                'qty': qty_from_batch,
                'cost_per_unit': batch.cost_per_unit,
            })

            remaining_needed -= qty_from_batch

        # Check if we have enough stock
        if remaining_needed > 0:
            raise ValidationError(
                f"Insufficient released stock for {budget_item.code}. "
                f"Need {quantity_needed}, available {quantity_needed - remaining_needed}"
            )

        return allocations

    @staticmethod
    @transaction.atomic
    def consume_batches(allocations, movement_event):
        """
        Consume allocated batches and update quantities

        Args:
            allocations: List from allocate_batches_fefo()
            movement_event: MovementEvent instance for audit trail

        Returns:
            List of updated BatchLot instances
        """
        updated_batches = []

        for allocation in allocations:
            batch = allocation['batch']
            qty_to_consume = allocation['qty']

            # Update batch quantity
            batch.current_qty -= qty_to_consume
            batch.save()

            updated_batches.append(batch)

            # TODO: Create batch consumption audit record
            # This could link MovementEvent to BatchLot for full traceability

        return updated_batches

    @staticmethod
    def get_expiring_batches(company, warehouse=None, days_threshold=30):
        """
        Get batches expiring within threshold days

        Args:
            company: Company instance
            warehouse: Optional warehouse filter
            days_threshold: Days until expiry to filter by

        Returns:
            QuerySet of BatchLot instances
        """
        expiry_date = date.today() + timedelta(days=days_threshold)

        batches = BatchLot.objects.filter(
            company=company,
            hold_status='RELEASED',
            current_qty__gt=0,
            exp_date__isnull=False,
            exp_date__lte=expiry_date
        ).select_related('budget_item', 'grn')

        # TODO: Add warehouse filter when warehouse link is added to batches

        return batches.order_by('exp_date')

    @staticmethod
    def get_expired_batches(company, warehouse=None):
        """Get batches that have already expired"""
        batches = BatchLot.objects.filter(
            company=company,
            current_qty__gt=0,
            exp_date__isnull=False,
            exp_date__lt=date.today()
        ).select_related('budget_item', 'grn')

        return batches.order_by('exp_date')

    @staticmethod
    @transaction.atomic
    def dispose_expired_batch(batch, disposed_by, disposal_method='SCRAP', notes=''):
        """
        Dispose of an expired batch

        Args:
            batch: BatchLot instance
            disposed_by: User performing disposal
            disposal_method: SCRAP, DONATE, RETURN_TO_SUPPLIER, etc.
            notes: Disposal notes

        Returns:
            Updated BatchLot instance
        """
        if not batch.is_expired():
            raise ValidationError("Batch is not expired")

        # Get FEFO config for disposal method
        fefo_config = ItemFEFOConfig.objects.filter(
            budget_item=batch.budget_item,
            company=batch.company
        ).first()

        if fefo_config and not disposal_method:
            disposal_method = fefo_config.disposal_method

        # Update batch status
        batch.hold_status = 'SCRAP'
        batch.current_qty = Decimal('0')
        batch.save()

        # Create movement event for disposal
        # TODO: Create disposal movement event

        # Post GL entry for scrap
        # TODO: Post scrap journal entry

        return batch

    @staticmethod
    @transaction.atomic
    def create_serial_number(batch_lot, serial_data, created_by):
        """
        Create a serial number for tracked items

        Args:
            batch_lot: BatchLot instance (optional)
            serial_data: dict with:
                - serial_number: str (required)
                - budget_item: BudgetItemCode instance
                - warranty_start: date (optional)
                - warranty_end: date (optional)
                - asset_tag: str (optional)
            created_by: User

        Returns:
            SerialNumber instance
        """
        budget_item = serial_data.get('budget_item')
        if batch_lot:
            budget_item = batch_lot.budget_item

        serial = SerialNumber.objects.create(
            company=serial_data['company'],
            budget_item=budget_item,
            serial_number=serial_data['serial_number'],
            batch_lot=batch_lot,
            warranty_start=serial_data.get('warranty_start'),
            warranty_end=serial_data.get('warranty_end'),
            asset_tag=serial_data.get('asset_tag', ''),
            status='IN_STOCK',
        )

        return serial

    @staticmethod
    def get_batch_inventory_value(company, warehouse=None, item=None):
        """
        Calculate total inventory value across batches

        Args:
            company: Company instance
            warehouse: Optional warehouse filter
            item: Optional item filter

        Returns:
            dict with total_qty, total_value, batch_count
        """
        batches = BatchLot.objects.filter(
            company=company,
            hold_status='RELEASED',
            current_qty__gt=0
        )

        if item:
            batches = batches.filter(budget_item=item)

        # TODO: Add warehouse filter

        from django.db.models import Sum, Count
        from django.db.models.functions import Coalesce

        result = batches.aggregate(
            total_qty=Coalesce(Sum('current_qty'), Decimal('0')),
            batch_count=Count('id')
        )

        # Calculate total value (qty * cost_per_unit for each batch)
        total_value = sum(
            batch.current_qty * batch.cost_per_unit
            for batch in batches
        )

        result['total_value'] = Decimal(str(total_value))

        return result

    @staticmethod
    def get_batch_aging_report(company, warehouse=None):
        """
        Generate batch aging report

        Returns list of dicts with:
            - age_bucket: str (0-30, 31-60, 61-90, 91+)
            - batch_count: int
            - total_qty: Decimal
            - total_value: Decimal
        """
        today = date.today()

        batches = BatchLot.objects.filter(
            company=company,
            hold_status='RELEASED',
            current_qty__gt=0
        ).select_related('budget_item')

        # TODO: Add warehouse filter

        # Categorize by age
        age_buckets = {
            '0-30': [],
            '31-60': [],
            '61-90': [],
            '91+': [],
        }

        for batch in batches:
            days_old = (today - batch.received_date).days

            if days_old <= 30:
                bucket = '0-30'
            elif days_old <= 60:
                bucket = '31-60'
            elif days_old <= 90:
                bucket = '61-90'
            else:
                bucket = '91+'

            age_buckets[bucket].append(batch)

        # Aggregate by bucket
        report = []
        for bucket, batch_list in age_buckets.items():
            total_qty = sum(b.current_qty for b in batch_list)
            total_value = sum(b.current_qty * b.cost_per_unit for b in batch_list)

            report.append({
                'age_bucket': bucket,
                'batch_count': len(batch_list),
                'total_qty': total_qty,
                'total_value': Decimal(str(total_value)),
            })

        return report
