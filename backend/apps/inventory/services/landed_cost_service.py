"""
Enhanced Landed Cost Service
Handles multi-component landed costs with per-line apportionment and retroactive adjustments.
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import datetime

from ..models import (
    LandedCostComponent, LandedCostLineApportionment,
    GoodsReceipt, GoodsReceiptLine, CostLayer,
    Item, Warehouse
)


class LandedCostService:
    """Service for applying and managing landed costs"""

    @staticmethod
    def preview_apportionment(grn_id, components, apportionment_method):
        """
        Preview how landed costs will be apportioned before applying.

        Args:
            grn_id: GoodsReceipt ID
            components: List of dicts with component_type and total_amount
            apportionment_method: 'QUANTITY', 'VALUE', 'WEIGHT', 'VOLUME', or 'MANUAL'

        Returns:
            dict with preview data for each line
        """
        grn = GoodsReceipt.objects.prefetch_related('lines__product').get(id=grn_id)
        grn_lines = grn.lines.all()

        # Calculate total basis for apportionment
        if apportionment_method == 'QUANTITY':
            total_basis = sum(line.quantity_received for line in grn_lines)
        elif apportionment_method == 'VALUE':
            total_basis = sum(
                line.quantity_received * (line.unit_cost or Decimal('0'))
                for line in grn_lines
            )
        elif apportionment_method == 'WEIGHT':
            total_basis = sum(
                line.quantity_received * (getattr(line.product, 'weight', Decimal('1')) or Decimal('1'))
                for line in grn_lines
            )
        elif apportionment_method == 'VOLUME':
            total_basis = sum(
                line.quantity_received * (getattr(line.product, 'volume', Decimal('1')) or Decimal('1'))
                for line in grn_lines
            )
        else:
            # Manual - return structure for manual input
            total_basis = Decimal('100')  # Use percentage

        if total_basis == 0:
            raise ValueError("Cannot apportion - total basis is zero")

        # Calculate apportionment for each component and line
        preview_lines = []

        for line in grn_lines:
            # Calculate line basis
            if apportionment_method == 'QUANTITY':
                line_basis = line.quantity_received
            elif apportionment_method == 'VALUE':
                line_basis = line.quantity_received * (line.unit_cost or Decimal('0'))
            elif apportionment_method == 'WEIGHT':
                line_basis = line.quantity_received * (getattr(line.product, 'weight', Decimal('1')) or Decimal('1'))
            elif apportionment_method == 'VOLUME':
                line_basis = line.quantity_received * (getattr(line.product, 'volume', Decimal('1')) or Decimal('1'))
            else:
                line_basis = Decimal('0')  # Manual mode

            allocation_percentage = (line_basis / total_basis * 100) if total_basis > 0 else Decimal('0')

            # Calculate apportionment for each component
            component_apportionments = []
            total_line_cost_adjustment = Decimal('0')

            for component in components:
                component_amount = Decimal(str(component['total_amount']))
                apportioned_amount = (component_amount * allocation_percentage / 100)

                # Get cost layer to determine consumed vs remaining
                cost_layers = CostLayer.objects.filter(
                    product=line.product,
                    warehouse=grn.warehouse,
                    goods_receipt_line=line
                )

                total_consumed = sum(
                    layer.qty_received - layer.qty_remaining
                    for layer in cost_layers
                )
                remaining = line.quantity_received - total_consumed

                # Split between inventory and COGS
                if remaining > 0:
                    inventory_portion = (remaining / line.quantity_received) * apportioned_amount
                    cogs_portion = (total_consumed / line.quantity_received) * apportioned_amount
                else:
                    inventory_portion = Decimal('0')
                    cogs_portion = apportioned_amount

                cost_per_unit_adjustment = apportioned_amount / line.quantity_received

                component_apportionments.append({
                    'component_type': component['component_type'],
                    'component_type_display': dict(LandedCostComponent.COMPONENT_TYPE_CHOICES).get(
                        component['component_type'], component['component_type']
                    ),
                    'total_component_amount': float(component_amount),
                    'apportioned_amount': float(apportioned_amount),
                    'to_inventory': float(inventory_portion),
                    'to_cogs': float(cogs_portion),
                    'cost_per_unit_adjustment': float(cost_per_unit_adjustment)
                })

                total_line_cost_adjustment += cost_per_unit_adjustment

            preview_lines.append({
                'line_id': line.id,
                'product_code': line.product.code,
                'product_name': line.product.name,
                'quantity': float(line.quantity_received),
                'original_unit_cost': float(line.unit_cost or Decimal('0')),
                'basis_value': float(line_basis),
                'allocation_percentage': float(allocation_percentage),
                'component_apportionments': component_apportionments,
                'total_cost_adjustment': float(total_line_cost_adjustment),
                'new_unit_cost': float((line.unit_cost or Decimal('0')) + total_line_cost_adjustment)
            })

        # Calculate totals
        total_landed_cost = sum(Decimal(str(c['total_amount'])) for c in components)

        return {
            'grn_id': grn_id,
            'grn_number': grn.grn_number,
            'apportionment_method': apportionment_method,
            'total_basis': float(total_basis),
            'total_landed_cost': float(total_landed_cost),
            'lines': preview_lines
        }

    @staticmethod
    @transaction.atomic
    def apply_landed_costs(grn_id, components, apportionment_method, applied_by, notes=""):
        """
        Apply landed costs to a GRN with per-line apportionment.

        Args:
            grn_id: GoodsReceipt ID
            components: List of dicts with component details
            apportionment_method: Apportionment method
            applied_by: User applying the costs
            notes: Optional notes

        Returns:
            List of LandedCostComponent instances
        """
        grn = GoodsReceipt.objects.prefetch_related('lines__product').get(id=grn_id)
        company = grn.company

        # Get preview to use calculations
        preview = LandedCostService.preview_apportionment(grn_id, components, apportionment_method)

        created_components = []

        for component_data in components:
            # Create landed cost component
            lc_component = LandedCostComponent.objects.create(
                company=company,
                goods_receipt=grn,
                component_type=component_data['component_type'],
                description=component_data.get('description', ''),
                total_amount=Decimal(str(component_data['total_amount'])),
                currency=component_data.get('currency', 'USD'),
                apportionment_method=apportionment_method,
                invoice_number=component_data.get('invoice_number', ''),
                invoice_date=component_data.get('invoice_date'),
                supplier_id=component_data.get('supplier_id'),
                applied_by=applied_by,
                applied_date=timezone.now(),
                notes=notes
            )

            # Create line apportionments from preview
            for line_preview in preview['lines']:
                grn_line = GoodsReceiptLine.objects.get(id=line_preview['line_id'])

                # Find matching component in preview
                comp_preview = next(
                    (c for c in line_preview['component_apportionments']
                     if c['component_type'] == component_data['component_type']),
                    None
                )

                if comp_preview:
                    LandedCostLineApportionment.objects.create(
                        company=company,
                        landed_cost_component=lc_component,
                        goods_receipt_line=grn_line,
                        product=grn_line.product,
                        basis_value=Decimal(str(line_preview['basis_value'])),
                        allocation_percentage=Decimal(str(line_preview['allocation_percentage'])),
                        apportioned_amount=Decimal(str(comp_preview['apportioned_amount'])),
                        cost_per_unit_adjustment=Decimal(str(comp_preview['cost_per_unit_adjustment']))
                    )

                    # Update cost layers
                    LandedCostService._update_cost_layers(
                        grn_line=grn_line,
                        cost_adjustment=Decimal(str(comp_preview['cost_per_unit_adjustment']))
                    )

            # Update component totals
            lc_component.apportioned_to_inventory = sum(
                line['component_apportionments'][0].get('to_inventory', 0)
                for line in preview['lines']
                if line['component_apportionments']
            )
            lc_component.apportioned_to_cogs = sum(
                line['component_apportionments'][0].get('to_cogs', 0)
                for line in preview['lines']
                if line['component_apportionments']
            )
            lc_component.save()

            created_components.append(lc_component)

        # Post to GL
        LandedCostService._post_to_gl(created_components, grn)

        return created_components

    @staticmethod
    def _update_cost_layers(grn_line, cost_adjustment):
        """
        Update cost layers with landed cost adjustment.

        Args:
            grn_line: GoodsReceiptLine instance
            cost_adjustment: Per-unit cost adjustment
        """
        cost_layers = CostLayer.objects.filter(
            goods_receipt_line=grn_line
        )

        for layer in cost_layers:
            layer.landed_cost_adjustment = (layer.landed_cost_adjustment or Decimal('0')) + cost_adjustment
            layer.adjustment_date = timezone.now()
            layer.adjustment_reason = f"Landed cost applied to GRN#{grn_line.goods_receipt.grn_number}"
            layer.save()

    @staticmethod
    def _post_to_gl(components, grn):
        """
        Post landed costs to GL.

        Args:
            components: List of LandedCostComponent instances
            grn: GoodsReceipt instance
        """
        from apps.finance.services.journal_service import JournalEntryService
        from apps.finance.models import Account

        # Get accounts
        inventory_account = Account.objects.filter(
            company=grn.company,
            code__startswith='1400'  # Inventory asset
        ).first()

        cogs_account = Account.objects.filter(
            company=grn.company,
            code__startswith='5100'  # COGS
        ).first()

        accrued_freight_account = Account.objects.filter(
            company=grn.company,
            code__startswith='2100'  # Accrued expenses
        ).first()

        if not all([inventory_account, cogs_account, accrued_freight_account]):
            raise ValueError("Required GL accounts not found")

        # Build journal entry lines for all components
        lines = []
        total_to_inventory = Decimal('0')
        total_to_cogs = Decimal('0')

        for component in components:
            total_to_inventory += component.apportioned_to_inventory or Decimal('0')
            total_to_cogs += component.apportioned_to_cogs or Decimal('0')

        # Dr. Inventory (remaining)
        if total_to_inventory > 0:
            lines.append({
                'account_id': inventory_account.id,
                'debit': float(total_to_inventory),
                'credit': 0,
                'description': f"Landed cost to inventory - GRN#{grn.grn_number}"
            })

        # Dr. COGS (consumed)
        if total_to_cogs > 0:
            lines.append({
                'account_id': cogs_account.id,
                'debit': float(total_to_cogs),
                'credit': 0,
                'description': f"Landed cost to COGS - GRN#{grn.grn_number}"
            })

        # Cr. Accrued Freight
        total_landed_cost = total_to_inventory + total_to_cogs
        lines.append({
            'account_id': accrued_freight_account.id,
            'debit': 0,
            'credit': float(total_landed_cost),
            'description': f"Landed cost payable - GRN#{grn.grn_number}"
        })

        # Create JE via finance service
        je_service = JournalEntryService()
        je_data = {
            'company': grn.company,
            'entry_date': datetime.now().date(),
            'description': f"Landed cost adjustment - GRN#{grn.grn_number}",
            'reference_type': 'LANDED_COST',
            'reference_id': grn.id,
            'lines': lines
        }

        je = je_service.create_journal_entry(je_data)

        # Update components with JE reference
        for component in components:
            component.je_id = je.id
            component.posted_to_gl = True
            component.gl_posted_date = timezone.now()
            component.save()

        return je

    @staticmethod
    def get_landed_cost_summary(grn_id):
        """
        Get summary of all landed costs applied to a GRN.

        Args:
            grn_id: GoodsReceipt ID

        Returns:
            dict with summary data
        """
        components = LandedCostComponent.objects.filter(
            goods_receipt_id=grn_id
        ).prefetch_related('line_apportionments')

        summary = {
            'grn_id': grn_id,
            'total_landed_cost': float(sum(c.total_amount for c in components)),
            'total_to_inventory': float(sum(c.apportioned_to_inventory for c in components)),
            'total_to_cogs': float(sum(c.apportioned_to_cogs for c in components)),
            'components': []
        }

        for component in components:
            summary['components'].append({
                'id': component.id,
                'type': component.component_type,
                'type_display': component.get_component_type_display(),
                'amount': float(component.total_amount),
                'to_inventory': float(component.apportioned_to_inventory or 0),
                'to_cogs': float(component.apportioned_to_cogs or 0),
                'posted_to_gl': component.posted_to_gl,
                'line_count': component.line_apportionments.count()
            })

        return summary

    @staticmethod
    def reverse_landed_cost(component_id, reason, reversed_by):
        """
        Reverse a landed cost component.

        Args:
            component_id: LandedCostComponent ID
            reason: Reason for reversal
            reversed_by: User reversing

        Returns:
            Reversal journal entry
        """
        from apps.finance.services.journal_service import JournalEntryService

        component = LandedCostComponent.objects.get(id=component_id)

        if not component.posted_to_gl:
            raise ValueError("Component not yet posted to GL")

        # Create reversal JE (opposite entries)
        je_service = JournalEntryService()

        # Get original JE and reverse it
        if component.je_id:
            reversal_je = je_service.reverse_journal_entry(
                je_id=component.je_id,
                reversal_date=datetime.now().date(),
                reason=reason
            )

            # Update cost layers (reverse adjustments)
            for apportionment in component.line_apportionments.all():
                cost_layers = CostLayer.objects.filter(
                    goods_receipt_line=apportionment.goods_receipt_line
                )
                for layer in cost_layers:
                    layer.landed_cost_adjustment = (
                        (layer.landed_cost_adjustment or Decimal('0')) -
                        apportionment.cost_per_unit_adjustment
                    )
                    layer.adjustment_reason = f"Landed cost reversal: {reason}"
                    layer.adjustment_date = timezone.now()
                    layer.save()

            # Mark component as reversed
            component.posted_to_gl = False
            component.notes = f"{component.notes}\n\nREVERSED: {reason}"
            component.save()

            return reversal_je

        raise ValueError("No journal entry found to reverse")
