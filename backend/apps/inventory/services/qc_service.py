"""
Quality Control Service
Handles QC inspection workflows, stock holds, and quality gates.
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.inventory.models import (
    StockHold,
    QCCheckpoint,
    QCResult,
    BatchLot,
    GoodsReceipt,
    GoodsReceiptLine,
    MovementEvent,
)
from apps.finance.services.journal_service import JournalEntryService


class QCService:
    """Service for quality control operations"""

    @staticmethod
    @transaction.atomic
    def create_qc_inspection(grn, checkpoint, inspected_by, inspection_data):
        """
        Create a QC inspection result for a GRN

        Args:
            grn: GoodsReceipt instance
            checkpoint: QCCheckpoint instance
            inspected_by: User performing inspection
            inspection_data: dict with:
                - qty_inspected: Decimal
                - qty_accepted: Decimal
                - qty_rejected: Decimal
                - rejection_reason: str (optional)
                - notes: str (optional)
                - rework_instruction: str (optional)
                - attachment: File (optional)

        Returns:
            QCResult instance
        """
        qty_inspected = Decimal(str(inspection_data['qty_inspected']))
        qty_accepted = Decimal(str(inspection_data['qty_accepted']))
        qty_rejected = Decimal(str(inspection_data['qty_rejected']))

        # Validation
        if qty_inspected != (qty_accepted + qty_rejected):
            raise ValidationError(
                "Qty inspected must equal qty accepted + qty rejected"
            )

        # Determine QC status
        if qty_rejected == 0:
            qc_status = 'PASS'
        elif qty_accepted == 0:
            qc_status = 'FAIL'
        else:
            qc_status = 'CONDITIONAL_PASS'

        # Create QC result
        qc_result = QCResult.objects.create(
            company=grn.company,
            grn=grn,
            checkpoint=checkpoint,
            inspected_by=inspected_by,
            inspected_date=timezone.now().date(),
            qty_inspected=qty_inspected,
            qty_accepted=qty_accepted,
            qty_rejected=qty_rejected,
            rejection_reason=inspection_data.get('rejection_reason'),
            qc_status=qc_status,
            notes=inspection_data.get('notes', ''),
            rework_instruction=inspection_data.get('rework_instruction', ''),
            attachment=inspection_data.get('attachment'),
        )

        # Check if escalation is needed
        rejection_pct = (qty_rejected / qty_inspected * 100) if qty_inspected > 0 else 0
        if rejection_pct > float(checkpoint.escalation_threshold):
            # TODO: Create escalation notification/workflow
            pass

        # Create stock hold if inspection failed or conditional
        if qc_status in ['FAIL', 'CONDITIONAL_PASS']:
            hold = QCService._create_hold_from_inspection(
                qc_result, inspected_by, inspection_data
            )
            qc_result.hold_created = True
            qc_result.save()

        # If inspection passed, release from quarantine
        if qc_status == 'PASS':
            QCService._release_from_quarantine(grn, inspected_by)

        return qc_result

    @staticmethod
    @transaction.atomic
    def _create_hold_from_inspection(qc_result, inspected_by, inspection_data):
        """Create stock hold from failed/conditional QC inspection"""
        grn = qc_result.grn

        # Determine hold type and disposition
        if qc_result.qc_status == 'FAIL':
            hold_type = 'DEFECT'
            disposition = 'SCRAP' if 'DAMAGE' in str(qc_result.rejection_reason) else 'RETURN'
        else:
            hold_type = 'QC_INSPECTION'
            disposition = 'REWORK'

        # Get batch lot if exists
        batch_lot = None
        if hasattr(grn, 'batch_lots') and grn.batch_lots.exists():
            batch_lot = grn.batch_lots.first()

        hold = StockHold.objects.create(
            company=grn.company,
            budget_item=grn.lines.first().budget_item if grn.lines.exists() else None,
            warehouse=grn.warehouse,
            hold_type=hold_type,
            qty_held=qc_result.qty_rejected,
            hold_reason=f"QC Inspection {qc_result.qc_status}: {qc_result.rejection_reason or 'Failed inspection'}",
            hold_by=inspected_by,
            qc_pass_result='FAIL' if qc_result.qc_status == 'FAIL' else 'CONDITIONAL',
            qc_notes=qc_result.notes,
            status='ACTIVE',
            disposition=disposition,
            batch_lot=batch_lot,
        )

        # Update batch lot status if exists
        if batch_lot:
            batch_lot.hold_status = 'ON_HOLD'
            batch_lot.save()

        return hold

    @staticmethod
    @transaction.atomic
    def _release_from_quarantine(grn, released_by):
        """Release GRN items from quarantine to released state"""
        # Update batch lots to RELEASED status
        batch_lots = BatchLot.objects.filter(
            grn=grn,
            hold_status='QUARANTINE'
        )

        for batch in batch_lots:
            batch.hold_status = 'RELEASED'
            batch.save()

            # Post GL entry: Dr. Inventory-Saleable, Cr. Inventory-Quarantine
            QCService._post_qc_pass_journal(batch, grn)

        return batch_lots.count()

    @staticmethod
    @transaction.atomic
    def release_hold(hold, released_by, disposition=None, notes=''):
        """
        Release a stock hold

        Args:
            hold: StockHold instance
            released_by: User releasing the hold
            disposition: Override disposition (TO_WAREHOUSE, SCRAP, RETURN, etc.)
            notes: Additional notes

        Returns:
            Updated StockHold instance
        """
        if hold.status != 'ACTIVE':
            raise ValidationError(f"Cannot release hold in status: {hold.status}")

        # Update hold
        hold.status = 'RELEASED'
        hold.actual_release_date = timezone.now().date()
        hold.released_by = released_by
        if notes:
            hold.qc_notes += f"\nReleased: {notes}"

        # Apply disposition
        final_disposition = disposition or hold.disposition or 'TO_WAREHOUSE'
        hold.disposition = final_disposition
        hold.save()

        # Handle disposition
        if final_disposition == 'TO_WAREHOUSE':
            # Release to warehouse - update batch lot status
            if hold.batch_lot:
                hold.batch_lot.hold_status = 'RELEASED'
                hold.batch_lot.save()
                QCService._post_qc_pass_journal(hold.batch_lot, None)

        elif final_disposition == 'SCRAP':
            # Scrap the held quantity
            QCService._scrap_held_stock(hold, released_by)

        elif final_disposition == 'RETURN':
            # Will be handled by RTV process
            pass

        return hold

    @staticmethod
    @transaction.atomic
    def _scrap_held_stock(hold, scrapped_by):
        """Scrap held stock and post GL entries"""
        # Update hold status
        hold.status = 'SCRAPPED'
        hold.save()

        # Update batch lot if exists
        if hold.batch_lot:
            hold.batch_lot.hold_status = 'SCRAP'
            hold.batch_lot.current_qty = Decimal('0')
            hold.batch_lot.save()

            # Post GL entry: Dr. Scrap Loss, Cr. Inventory-On-Hold
            QCService._post_scrap_journal(hold)

    @staticmethod
    def _post_qc_pass_journal(batch_lot, grn):
        """
        Post GL entry for QC pass: Dr. Inventory-Saleable, Cr. Inventory-Quarantine
        """
        try:
            # Get inventory accounts
            # This would ideally come from posting rules
            # For now, we'll skip the actual posting and just log
            # TODO: Integrate with posting rules service
            pass
        except Exception as e:
            # Log error but don't fail the transaction
            print(f"Error posting QC pass journal: {e}")

    @staticmethod
    def _post_scrap_journal(hold):
        """
        Post GL entry for scrap: Dr. Scrap Loss, Cr. Inventory-On-Hold
        """
        try:
            # Get scrap loss account
            # This would ideally come from posting rules
            # For now, we'll skip the actual posting and just log
            # TODO: Integrate with posting rules service
            pass
        except Exception as e:
            # Log error but don't fail the transaction
            print(f"Error posting scrap journal: {e}")

    @staticmethod
    def get_pending_inspections(company, warehouse=None):
        """Get GRNs pending QC inspection"""
        from apps.inventory.models import GoodsReceipt, BatchLot

        # Get GRNs with batch lots in QUARANTINE status
        quarantine_batches = BatchLot.objects.filter(
            company=company,
            hold_status='QUARANTINE'
        )

        if warehouse:
            # Filter by warehouse through GRN
            grn_ids = quarantine_batches.values_list('grn_id', flat=True).distinct()
            pending_grns = GoodsReceipt.objects.filter(
                id__in=grn_ids,
                warehouse=warehouse
            )
        else:
            grn_ids = quarantine_batches.values_list('grn_id', flat=True).distinct()
            pending_grns = GoodsReceipt.objects.filter(id__in=grn_ids)

        return pending_grns

    @staticmethod
    def get_active_holds(company, warehouse=None, hold_type=None):
        """Get active stock holds"""
        holds = StockHold.objects.filter(
            company=company,
            status='ACTIVE'
        )

        if warehouse:
            holds = holds.filter(warehouse=warehouse)

        if hold_type:
            holds = holds.filter(hold_type=hold_type)

        return holds.select_related(
            'budget_item',
            'warehouse',
            'batch_lot',
            'hold_by'
        ).order_by('-hold_date')

    @staticmethod
    def check_and_flag_overdue_holds(company):
        """
        Check for overdue holds and flag them for escalation
        Returns count of holds flagged
        """
        from datetime import date

        today = date.today()

        overdue_holds = StockHold.objects.filter(
            company=company,
            status='ACTIVE',
            expected_release_date__lt=today,
            escalation_flag=False
        )

        count = overdue_holds.update(escalation_flag=True)

        # TODO: Create notifications for overdue holds

        return count

    @staticmethod
    def get_qc_statistics(company, warehouse=None, date_from=None, date_to=None):
        """
        Get QC performance statistics

        Returns dict with:
            - total_inspections
            - passed_count
            - failed_count
            - conditional_count
            - pass_rate
            - avg_rejection_pct
            - top_rejection_reasons
        """
        from django.db.models import Count, Sum, Avg, Q
        from datetime import date, timedelta

        if not date_from:
            date_from = date.today() - timedelta(days=30)
        if not date_to:
            date_to = date.today()

        qc_results = QCResult.objects.filter(
            company=company,
            inspected_date__gte=date_from,
            inspected_date__lte=date_to
        )

        if warehouse:
            qc_results = qc_results.filter(grn__warehouse=warehouse)

        # Aggregate statistics
        stats = qc_results.aggregate(
            total_inspections=Count('id'),
            passed_count=Count('id', filter=Q(qc_status='PASS')),
            failed_count=Count('id', filter=Q(qc_status='FAIL')),
            conditional_count=Count('id', filter=Q(qc_status='CONDITIONAL_PASS')),
            total_inspected=Sum('qty_inspected'),
            total_rejected=Sum('qty_rejected'),
        )

        # Calculate rates
        total = stats['total_inspections'] or 1
        stats['pass_rate'] = (stats['passed_count'] / total * 100) if total > 0 else 0

        total_qty = float(stats['total_inspected'] or 1)
        total_rej_qty = float(stats['total_rejected'] or 0)
        stats['avg_rejection_pct'] = (total_rej_qty / total_qty * 100) if total_qty > 0 else 0

        # Top rejection reasons
        rejection_reasons = qc_results.filter(
            rejection_reason__isnull=False
        ).values('rejection_reason').annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        stats['top_rejection_reasons'] = list(rejection_reasons)

        return stats
