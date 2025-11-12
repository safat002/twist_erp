"""
Material Issue Service
Handles material issuance from warehouse with FEFO batch allocation and cost consumption
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError


class MaterialIssueService:
    """Service for processing material issues"""

    @staticmethod
    @transaction.atomic
    def process_issue(material_issue, issued_by):
        """
        Process a material issue - deduct stock, consume cost layers, create movement events

        Args:
            material_issue: MaterialIssue instance
            issued_by: User who is issuing the materials

        Returns:
            dict with success status and details
        """
        from ..models import (
            MaterialIssue, StockMovement, StockMovementLine,
            MovementEvent, BatchLot, SerialNumber, StockLevel
        )
        from .batch_fefo_service import BatchFEFOService
        from .valuation_service import ValuationService

        if material_issue.status != 'APPROVED':
            raise ValidationError("Only approved material issues can be processed")

        if not material_issue.lines.exists():
            raise ValidationError("Material issue has no line items")

        # Validate stock availability
        for line in material_issue.lines.all():
            stock_level = StockLevel.objects.filter(
                company=material_issue.company,
                warehouse=material_issue.warehouse,
                product=line.budget_item
            ).first()

            if not stock_level or stock_level.quantity < line.quantity_issued:
                raise ValidationError(
                    f"Insufficient stock for {line.budget_item.code}. "
                    f"Available: {stock_level.quantity if stock_level else 0}, Required: {line.quantity_issued}"
                )

        # Create stock movement (OUT type)
        stock_movement = StockMovement.objects.create(
            company=material_issue.company,
            from_warehouse=material_issue.warehouse,
            to_warehouse=None,  # Issue - no destination warehouse
            movement_type='OUT',
            movement_date=material_issue.issue_date,
            status='POSTED',
            reference_document_type='MaterialIssue',
            reference_document_id=material_issue.id,
            notes=f"Material Issue: {material_issue.issue_number} - {material_issue.purpose}"
        )

        # Process each line
        for line in material_issue.lines.all():
            budget_item = line.budget_item
            item = line.budget_item

            # Get profile for batch/serial tracking
            profile = budget_item.get_operational_profile() if hasattr(budget_item, 'get_operational_profile') else None
            is_batch_tracked = getattr(profile, 'is_batch_tracked', False) if profile else False
            is_serialized = getattr(profile, 'is_serialized', False) if profile else False

            # Allocate batch using FEFO if batch-tracked
            batch_lot = None
            if is_batch_tracked and not line.batch_lot:
                # Auto-allocate using FEFO
                batches = BatchFEFOService.allocate_batches_fefo(
                    budget_item=budget_item,
                    company=material_issue.company,
                    warehouse=material_issue.warehouse,
                    quantity_needed=line.quantity_issued
                )

                if batches:
                    # Use first batch (FEFO sorted)
                    batch_lot = batches[0]['batch']
                    line.batch_lot = batch_lot
                    line.save(update_fields=['batch_lot'])

            # Get cost from cost layers using valuation method
            cost_per_unit = ValuationService.get_current_cost(
                company=material_issue.company,
                product=item or budget_item,
                warehouse=material_issue.warehouse
            )

            line.unit_cost = cost_per_unit
            line.total_cost = line.quantity_issued * cost_per_unit
            line.save(update_fields=['unit_cost', 'total_cost'])

            # Create stock movement line
            movement_line = StockMovementLine.objects.create(
                movement=stock_movement,
                company=material_issue.company,
                item=item,
                budget_item=budget_item,
                quantity=line.quantity_issued,
                uom=line.uom,
                cost_center=line.cost_center or material_issue.cost_center,
                project=line.project or material_issue.project,
                notes=line.notes
            )

            # Create movement event (negative quantity for issue)
            movement_event = MovementEvent.objects.create(
                company=material_issue.company,
                item=item,
                budget_item=budget_item,
                warehouse=material_issue.warehouse,
                event_type='stock.issued',
                event_date=material_issue.issue_date,
                event_timestamp=timezone.now(),
                qty_change=-line.quantity_issued,  # Negative for issue
                stock_uom=line.uom,
                source_uom=line.uom,
                reference_document_type='MaterialIssue',
                reference_document_id=material_issue.id,
                reference_number=material_issue.issue_number,
                cost_center=line.cost_center or material_issue.cost_center,
                project=line.project or material_issue.project,
                notes=f"Material Issue: {material_issue.issue_number}"
            )

            line.movement_event = movement_event
            line.save(update_fields=['movement_event'])

            # Update batch quantity if batch-tracked
            if batch_lot:
                batch_lot.current_qty = (batch_lot.current_qty or 0) - line.quantity_issued
                if batch_lot.current_qty <= 0:
                    batch_lot.hold_status = 'CONSUMED'
                batch_lot.save(update_fields=['current_qty', 'hold_status'])

            # Update serial numbers status if serialized
            if is_serialized and line.serial_numbers:
                SerialNumber.objects.filter(
                    company=material_issue.company,
                    budget_item=budget_item,
                    serial_number__in=line.serial_numbers
                ).update(
                    status='ISSUED',
                    warehouse=None  # No longer in warehouse
                )

            # Consume cost layers
            try:
                ValuationService.consume_cost_layers(
                    company=material_issue.company,
                    product=item or budget_item,
                    warehouse=material_issue.warehouse,
                    quantity=line.quantity_issued,
                    transaction_date=material_issue.issue_date,
                    reference_type='MaterialIssue',
                    reference_id=material_issue.id
                )
            except Exception as e:
                # Log but don't fail - cost layer consumption is informational
                print(f"Cost layer consumption warning: {e}")

        # Update material issue status
        material_issue.status = 'ISSUED'
        material_issue.issued_by = issued_by
        material_issue.stock_movement = stock_movement
        material_issue.save(update_fields=['status', 'issued_by', 'stock_movement', 'updated_at'])

        # Create GL posting (if integrated with finance)
        try:
            MaterialIssueService._create_gl_entry(material_issue)
        except Exception as e:
            # GL posting is optional
            print(f"GL posting warning: {e}")

        return {
            'success': True,
            'material_issue_id': material_issue.id,
            'issue_number': material_issue.issue_number,
            'stock_movement_id': stock_movement.id,
            'total_cost': sum(line.total_cost for line in material_issue.lines.all())
        }

    @staticmethod
    @transaction.atomic
    def approve_issue(material_issue, approved_by):
        """Approve a material issue"""
        from ..models import MaterialIssue

        if material_issue.status != 'SUBMITTED':
            raise ValidationError("Only submitted material issues can be approved")

        material_issue.status = 'APPROVED'
        material_issue.approved_by = approved_by
        material_issue.save(update_fields=['status', 'approved_by', 'updated_at'])

        return material_issue

    @staticmethod
    @transaction.atomic
    def submit_issue(material_issue):
        """Submit a material issue for approval"""
        from ..models import MaterialIssue

        if material_issue.status != 'DRAFT':
            raise ValidationError("Only draft material issues can be submitted")

        if not material_issue.lines.exists():
            raise ValidationError("Material issue has no line items")

        material_issue.status = 'SUBMITTED'
        material_issue.save(update_fields=['status', 'updated_at'])

        return material_issue

    @staticmethod
    @transaction.atomic
    def cancel_issue(material_issue, reason=''):
        """Cancel a material issue"""
        from ..models import MaterialIssue

        if material_issue.status == 'ISSUED':
            raise ValidationError("Cannot cancel an issued material issue. Use returns instead.")

        material_issue.status = 'CANCELLED'
        material_issue.notes = f"{material_issue.notes}\n\nCancellation reason: {reason}"
        material_issue.save(update_fields=['status', 'notes', 'updated_at'])

        return material_issue

    @staticmethod
    def get_available_batches(company, warehouse, budget_item):
        """Get available batches for an item using FEFO ordering"""
        from .batch_fefo_service import BatchFEFOService
        from ..models import BatchLot

        batches = BatchLot.objects.filter(
            company=company,
            warehouse=warehouse,
            budget_item=budget_item,
            hold_status='RELEASED',
            current_qty__gt=0
        ).select_related('budget_item').order_by('fefo_sequence', 'exp_date')

        return [{
            'id': batch.id,
            'batch_code': batch.internal_batch_code,
            'expiry_date': batch.exp_date,
            'available_qty': batch.current_qty,
            'fefo_sequence': batch.fefo_sequence,
            'days_until_expiry': (batch.exp_date - timezone.now().date()).days if batch.exp_date else None
        } for batch in batches]

    @staticmethod
    def get_available_serials(company, warehouse, budget_item):
        """Get available serial numbers for an item"""
        from ..models import SerialNumber

        serials = SerialNumber.objects.filter(
            company=company,
            warehouse=warehouse,
            budget_item=budget_item,
            status='IN_STOCK'
        ).values_list('serial_number', flat=True)

        return list(serials)

    @staticmethod
    def _create_gl_entry(material_issue):
        """
        Create GL entry for material issue:
        Dr Cost Center Expense / WIP
        Cr Inventory
        """
        try:
            from apps.finance.services.journal_service import JournalEntryService
            from apps.finance.models import GLPostingRule

            # Get posting rules for material issue
            posting_rules = GLPostingRule.objects.filter(
                company=material_issue.company,
                document_type='MaterialIssue',
                is_active=True
            )

            if not posting_rules.exists():
                return None

            # Calculate total cost
            total_cost = sum(line.total_cost for line in material_issue.lines.all())

            if total_cost == 0:
                return None

            # Create journal entry
            je_data = {
                'company': material_issue.company,
                'entry_date': material_issue.issue_date,
                'reference_type': 'MaterialIssue',
                'reference_id': material_issue.id,
                'reference_number': material_issue.issue_number,
                'description': f"Material Issue: {material_issue.issue_number} - {material_issue.purpose}",
                'lines': []
            }

            # Dr: Cost Center Expense / WIP
            je_data['lines'].append({
                'account': posting_rules.first().debit_account,  # Expense/WIP account
                'debit': total_cost,
                'credit': 0,
                'cost_center': material_issue.cost_center,
                'project': material_issue.project,
                'description': f"Material Issue: {material_issue.issue_number}"
            })

            # Cr: Inventory
            je_data['lines'].append({
                'account': posting_rules.first().credit_account,  # Inventory account
                'debit': 0,
                'credit': total_cost,
                'description': f"Material Issue: {material_issue.issue_number}"
            })

            je = JournalEntryService.create_journal_entry(je_data)
            return je

        except Exception as e:
            print(f"GL entry creation failed: {e}")
            return None

    @staticmethod
    def get_issue_summary(material_issue):
        """Get summary of a material issue"""
        return {
            'issue_number': material_issue.issue_number,
            'issue_type': material_issue.get_issue_type_display(),
            'status': material_issue.get_status_display(),
            'issue_date': material_issue.issue_date.isoformat(),
            'warehouse': material_issue.warehouse.name,
            'cost_center': material_issue.cost_center.name if material_issue.cost_center else None,
            'project': material_issue.project.name if material_issue.project else None,
            'department': material_issue.department,
            'purpose': material_issue.purpose,
            'requested_by': material_issue.requested_by.get_full_name(),
            'issued_by': material_issue.issued_by.get_full_name() if material_issue.issued_by else None,
            'approved_by': material_issue.approved_by.get_full_name() if material_issue.approved_by else None,
            'total_lines': material_issue.lines.count(),
            'total_cost': float(sum(line.total_cost for line in material_issue.lines.all())),
            'lines': [{
                'item_code': line.budget_item.code,
                'item_name': line.budget_item.name,
                'quantity_issued': float(line.quantity_issued),
                'uom': line.uom.code,
                'batch': line.batch_lot.internal_batch_code if line.batch_lot else None,
                'serial_numbers': line.serial_numbers,
                'unit_cost': float(line.unit_cost),
                'total_cost': float(line.total_cost)
            } for line in material_issue.lines.all()]
        }
