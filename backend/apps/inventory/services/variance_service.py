"""
Variance Tracking Service
Handles standard cost variance, purchase price variance, and GL posting integration.
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import datetime, date

from ..models import (
    StandardCostVariance, PurchasePriceVariance,
    Item, Warehouse, GoodsReceipt, StockLedger,
    ItemValuationMethod
)


class VarianceTrackingService:
    """Service for tracking and posting cost variances to GL"""

    @staticmethod
    def track_standard_cost_variance(
        company,
        product,
        warehouse,
        transaction_date,
        transaction_type,
        reference_id,
        standard_cost,
        actual_cost,
        quantity,
        notes=""
    ):
        """
        Track variance between standard cost and actual cost.
        Used when item is valued using STANDARD_COST method.

        Args:
            company: Company instance
            product: Item instance
            warehouse: Warehouse instance
            transaction_date: Date of transaction
            transaction_type: 'GRN', 'ISSUE', or 'ADJUSTMENT'
            reference_id: ID of related transaction (GRN, StockLedger, etc.)
            standard_cost: Standard cost per unit
            actual_cost: Actual cost per unit
            quantity: Quantity involved
            notes: Optional notes

        Returns:
            StandardCostVariance instance
        """
        variance = StandardCostVariance.objects.create(
            company=company,
            budget_item=product,
            warehouse=warehouse,
            transaction_date=transaction_date,
            transaction_type=transaction_type,
            reference_id=reference_id,
            standard_cost=Decimal(str(standard_cost)),
            actual_cost=Decimal(str(actual_cost)),
            quantity=Decimal(str(quantity)),
            notes=notes
        )

        return variance

    @staticmethod
    def track_purchase_price_variance(
        company,
        goods_receipt,
        product,
        warehouse,
        po_price,
        invoice_price,
        quantity,
        supplier_id=None,
        notes=""
    ):
        """
        Track variance between PO price and actual invoice price.

        Args:
            company: Company instance
            goods_receipt: GoodsReceipt instance
            product: Item instance
            warehouse: Warehouse instance
            po_price: Purchase Order unit price
            invoice_price: Actual invoice unit price
            quantity: Quantity received
            supplier_id: Optional supplier reference
            notes: Optional notes

        Returns:
            PurchasePriceVariance instance
        """
        variance = PurchasePriceVariance.objects.create(
            company=company,
            goods_receipt=goods_receipt,
            budget_item=product,
            warehouse=warehouse,
            po_price=Decimal(str(po_price)),
            invoice_price=Decimal(str(invoice_price)),
            quantity=Decimal(str(quantity)),
            supplier_id=supplier_id,
            notes=notes
        )

        return variance

    @staticmethod
    def post_standard_variance_to_gl(variance_id):
        """
        Post standard cost variance to GL.
        Creates journal entry with:
        - Dr. Inventory (at standard)
        - Dr/Cr. Standard Cost Variance (difference)
        - Cr. Accounts Payable (at actual)

        Args:
            variance_id: StandardCostVariance ID

        Returns:
            dict with je_id and posting details
        """
        from apps.finance.services.journal_service import JournalEntryService
        from apps.finance.models import Account

        variance = StandardCostVariance.objects.select_related(
            'product', 'warehouse', 'company'
        ).get(id=variance_id)

        if variance.posted_to_gl:
            raise ValueError("Variance already posted to GL")

        # Determine account codes based on variance type
        inventory_account = Account.objects.filter(
            company=variance.company,
            code__startswith='1400'  # Inventory asset
        ).first()

        variance_account = Account.objects.filter(
            company=variance.company,
            code__startswith='5200'  # Standard cost variance
        ).first()

        if not inventory_account or not variance_account:
            raise ValueError("Required GL accounts not found")

        # Build journal entry lines
        lines = []

        # Inventory at standard cost
        standard_amount = variance.standard_cost * variance.quantity
        lines.append({
            'account_id': inventory_account.id,
            'debit': float(standard_amount) if standard_amount > 0 else 0,
            'credit': 0,
            'description': f"Inventory at standard - {variance.product.code}"
        })

        # Variance account
        variance_amount = abs(variance.total_variance_amount)
        if variance.variance_type == 'UNFAVORABLE':
            # Unfavorable = additional cost
            lines.append({
                'account_id': variance_account.id,
                'debit': float(variance_amount),
                'credit': 0,
                'description': f"Unfavorable variance - {variance.product.code}"
            })
        else:
            # Favorable = cost savings
            lines.append({
                'account_id': variance_account.id,
                'debit': 0,
                'credit': float(variance_amount),
                'description': f"Favorable variance - {variance.product.code}"
            })

        # Create JE via finance service
        je_service = JournalEntryService()
        je_data = {
            'company': variance.company,
            'entry_date': variance.transaction_date,
            'description': f"Standard cost variance - {variance.product.code}",
            'reference_type': 'STANDARD_COST_VARIANCE',
            'reference_id': variance.id,
            'lines': lines
        }

        je = je_service.create_journal_entry(je_data)

        # Update variance record
        variance.variance_je_id = je.id
        variance.posted_to_gl = True
        variance.gl_posted_date = timezone.now()
        variance.save()

        return {
            'je_id': je.id,
            'variance_amount': float(variance.total_variance_amount),
            'variance_type': variance.variance_type
        }

    @staticmethod
    def post_ppv_to_gl(ppv_id):
        """
        Post purchase price variance to GL.
        Creates journal entry with:
        - Dr. Inventory (at PO price)
        - Dr/Cr. PPV Account (difference)
        - Cr. Accounts Payable (at invoice price)

        Args:
            ppv_id: PurchasePriceVariance ID

        Returns:
            dict with je_id and posting details
        """
        from apps.finance.services.journal_service import JournalEntryService
        from apps.finance.models import Account

        ppv = PurchasePriceVariance.objects.select_related(
            'product', 'warehouse', 'company', 'goods_receipt'
        ).get(id=ppv_id)

        if ppv.posted_to_gl:
            raise ValueError("PPV already posted to GL")

        # Determine account codes
        inventory_account = Account.objects.filter(
            company=ppv.company,
            code__startswith='1400'  # Inventory asset
        ).first()

        ppv_account = Account.objects.filter(
            company=ppv.company,
            code__startswith='5210'  # Purchase price variance
        ).first()

        if not inventory_account or not ppv_account:
            raise ValueError("Required GL accounts not found")

        # Build journal entry lines
        lines = []

        # Inventory at PO price
        po_amount = ppv.po_price * ppv.quantity
        lines.append({
            'account_id': inventory_account.id,
            'debit': float(po_amount) if po_amount > 0 else 0,
            'credit': 0,
            'description': f"Inventory at PO price - {ppv.product.code}"
        })

        # PPV account
        variance_amount = abs(ppv.total_variance_amount)
        if ppv.variance_type == 'UNFAVORABLE':
            # Unfavorable = paid more than PO
            lines.append({
                'account_id': ppv_account.id,
                'debit': float(variance_amount),
                'credit': 0,
                'description': f"Unfavorable PPV - GRN#{ppv.goods_receipt_id}"
            })
        else:
            # Favorable = paid less than PO
            lines.append({
                'account_id': ppv_account.id,
                'debit': 0,
                'credit': float(variance_amount),
                'description': f"Favorable PPV - GRN#{ppv.goods_receipt_id}"
            })

        # Create JE via finance service
        je_service = JournalEntryService()
        je_data = {
            'company': ppv.company,
            'entry_date': ppv.goods_receipt.receipt_date,
            'description': f"Purchase price variance - GRN#{ppv.goods_receipt_id}",
            'reference_type': 'PURCHASE_PRICE_VARIANCE',
            'reference_id': ppv.id,
            'lines': lines
        }

        je = je_service.create_journal_entry(je_data)

        # Update PPV record
        ppv.variance_je_id = je.id
        ppv.posted_to_gl = True
        ppv.gl_posted_date = timezone.now()
        ppv.save()

        return {
            'je_id': je.id,
            'variance_amount': float(ppv.total_variance_amount),
            'variance_type': ppv.variance_type
        }

    @staticmethod
    def get_variance_summary(company, start_date=None, end_date=None, product=None, warehouse=None):
        """
        Get summary of all variances for reporting.

        Args:
            company: Company instance
            start_date: Optional start date filter
            end_date: Optional end date filter
            product: Optional product filter
            warehouse: Optional warehouse filter

        Returns:
            dict with variance summaries
        """
        # Standard cost variances
        scv_qs = StandardCostVariance.objects.filter(company=company)
        if start_date:
            scv_qs = scv_qs.filter(transaction_date__gte=start_date)
        if end_date:
            scv_qs = scv_qs.filter(transaction_date__lte=end_date)
        if product:
            scv_qs = scv_qs.filter(budget_item=product)
        if warehouse:
            scv_qs = scv_qs.filter(warehouse=warehouse)

        scv_favorable = scv_qs.filter(variance_type='FAVORABLE').aggregate(
            total=models.Sum('total_variance_amount')
        )['total'] or Decimal('0')

        scv_unfavorable = scv_qs.filter(variance_type='UNFAVORABLE').aggregate(
            total=models.Sum('total_variance_amount')
        )['total'] or Decimal('0')

        # Purchase price variances
        ppv_qs = PurchasePriceVariance.objects.filter(company=company)
        if start_date:
            ppv_qs = ppv_qs.filter(goods_receipt__receipt_date__gte=start_date)
        if end_date:
            ppv_qs = ppv_qs.filter(goods_receipt__receipt_date__lte=end_date)
        if product:
            ppv_qs = ppv_qs.filter(budget_item=product)
        if warehouse:
            ppv_qs = ppv_qs.filter(warehouse=warehouse)

        ppv_favorable = ppv_qs.filter(variance_type='FAVORABLE').aggregate(
            total=models.Sum('total_variance_amount')
        )['total'] or Decimal('0')

        ppv_unfavorable = ppv_qs.filter(variance_type='UNFAVORABLE').aggregate(
            total=models.Sum('total_variance_amount')
        )['total'] or Decimal('0')

        return {
            'standard_cost_variance': {
                'favorable': float(abs(scv_favorable)),
                'unfavorable': float(scv_unfavorable),
                'net': float(scv_unfavorable - abs(scv_favorable)),
                'count': scv_qs.count()
            },
            'purchase_price_variance': {
                'favorable': float(abs(ppv_favorable)),
                'unfavorable': float(ppv_unfavorable),
                'net': float(ppv_unfavorable - abs(ppv_favorable)),
                'count': ppv_qs.count()
            },
            'total_variance': {
                'net': float((scv_unfavorable - abs(scv_favorable)) + (ppv_unfavorable - abs(ppv_favorable)))
            }
        }

    @staticmethod
    def auto_track_variance_on_grn(grn, grn_line, cost_per_unit):
        """
        Automatically track variance when GRN is posted.
        Determines if PPV or Standard Cost Variance applies.

        Args:
            grn: GoodsReceipt instance
            grn_line: GoodsReceiptLine instance
            cost_per_unit: Actual cost per unit from invoice

        Returns:
            Variance instance or None
        """
        product = grn_line.product
        warehouse = grn.warehouse
        company = grn.company

        # Check valuation method
        valuation_method = ItemValuationMethod.objects.filter(
            company=company,
            budget_item=product,
            warehouse=warehouse,
            is_active=True
        ).first()

        if not valuation_method:
            return None

        if valuation_method.valuation_method == 'STANDARD_COST':
            # Track standard cost variance
            standard_cost = product.standard_cost or Decimal('0')

            if abs(cost_per_unit - standard_cost) > Decimal('0.01'):  # Threshold
                return VarianceTrackingService.track_standard_cost_variance(
                    company=company,
                    budget_item=product,
                    warehouse=warehouse,
                    transaction_date=grn.receipt_date,
                    transaction_type='GRN',
                    reference_id=grn.id,
                    standard_cost=standard_cost,
                    actual_cost=cost_per_unit,
                    quantity=grn_line.quantity_received,
                    notes=f"Auto-tracked on GRN#{grn.grn_number}"
                )
        else:
            # Track PPV if PO price available
            po_price = getattr(grn_line, 'po_unit_price', None)

            if po_price and abs(cost_per_unit - po_price) > Decimal('0.01'):
                return VarianceTrackingService.track_purchase_price_variance(
                    company=company,
                    goods_receipt=grn,
                    budget_item=product,
                    warehouse=warehouse,
                    po_price=po_price,
                    invoice_price=cost_per_unit,
                    quantity=grn_line.quantity_received,
                    notes=f"Auto-tracked on GRN#{grn.grn_number}"
                )

        return None


# Import models for aggregation
from django.db import models
