"""
ABC/VED Classification Service

Automatically classifies inventory using multiple analysis methods:
- ABC Analysis (value-based)
- VED Analysis (criticality-based)
- FSN Analysis (movement frequency)
- HML Analysis (unit price)
- SDE Analysis (lead time/availability)

Features:
- Automatic classification
- Periodic reclassification
- Multi-criteria analysis
- Actionable recommendations
"""

import logging
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Sum, Count, Avg, F, Q
from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company
from apps.inventory.models import (
    Product,
    ProductCategory,
    Warehouse,
    StockLedger,
    StockLevel
)

logger = logging.getLogger(__name__)


@dataclass
class ABCClassification:
    """ABC classification result"""
    product_id: int
    product_code: str
    product_name: str
    annual_consumption_value: Decimal
    percentage_of_total: Decimal
    cumulative_percentage: Decimal
    abc_class: str  # A, B, or C
    recommendation: str


@dataclass
class VEDClassification:
    """VED classification result"""
    product_id: int
    product_code: str
    product_name: str
    criticality_score: int
    ved_class: str  # V (Vital), E (Essential), D (Desirable)
    rationale: str


@dataclass
class MultiDimensionalClassification:
    """Combined classification result"""
    product_id: int
    product_code: str
    product_name: str
    abc_class: str
    ved_class: str
    fsn_class: str  # F (Fast), S (Slow), N (Non-moving)
    hml_class: str  # H (High), M (Medium), L (Low) - unit price
    combined_priority: str  # CRITICAL, HIGH, MEDIUM, LOW
    management_strategy: str


class ABCVEDClassificationService:
    """
    Service for ABC/VED and multi-dimensional inventory classification.
    """

    # ABC thresholds (cumulative percentage of value)
    ABC_A_THRESHOLD = 70  # Top 70% of value
    ABC_B_THRESHOLD = 90  # Next 20% of value (70-90%)
    # C class = remaining 10% (90-100%)

    # FSN thresholds (days since last movement)
    FSN_FAST_DAYS = 30
    FSN_SLOW_DAYS = 180

    # HML thresholds (percentiles of unit price)
    HML_HIGH_PERCENTILE = 80
    HML_LOW_PERCENTILE = 20

    @staticmethod
    @transaction.atomic
    def perform_abc_analysis(
        company: Company,
        period_months: int = 12,
        warehouse: Optional[Warehouse] = None,
        category: Optional[ProductCategory] = None
    ) -> List[ABCClassification]:
        """
        Perform ABC analysis based on annual consumption value.

        ABC Analysis classifies inventory based on consumption value:
        - A items: Top 70% of consumption value (typically 10-20% of items)
        - B items: Next 20% of consumption value (typically 30% of items)
        - C items: Bottom 10% of consumption value (typically 50-60% of items)

        Args:
            company: Company instance
            period_months: Analysis period in months (default: 12)
            warehouse: Optional warehouse filter
            category: Optional category filter

        Returns:
            List of ABCClassification sorted by value
        """
        cutoff_date = timezone.now().date() - timedelta(days=period_months * 30)

        # Get products with stock
        products_query = Product.objects.filter(
            company=company,
            is_active=True
        ).select_related('category')

        if category:
            products_query = products_query.filter(category=category)

        products = list(products_query)

        # Calculate consumption value for each product
        product_values = []

        for product in products:
            # Get issue transactions in the period
            issues_query = StockLedger.objects.filter(
                company=company,
                product=product,
                transaction_type='ISSUE',
                transaction_date__gte=cutoff_date
            )

            if warehouse:
                issues_query = issues_query.filter(warehouse=warehouse)

            # Sum absolute value of issues
            consumption_value = issues_query.aggregate(
                total=Sum(F('quantity') * F('rate'))
            )['total'] or Decimal('0')

            consumption_value = abs(consumption_value)  # Issues are negative

            if consumption_value > 0:
                product_values.append({
                    'product': product,
                    'value': consumption_value
                })

        if not product_values:
            return []

        # Sort by value descending
        product_values.sort(key=lambda x: x['value'], reverse=True)

        # Calculate total value
        total_value = sum(pv['value'] for pv in product_values)

        # Classify products
        classifications = []
        cumulative_value = Decimal('0')

        for pv in product_values:
            product = pv['product']
            value = pv['value']

            cumulative_value += value
            percentage = (value / total_value * 100) if total_value > 0 else Decimal('0')
            cumulative_percentage = (cumulative_value / total_value * 100) if total_value > 0 else Decimal('0')

            # Determine ABC class
            if cumulative_percentage <= ABCVEDClassificationService.ABC_A_THRESHOLD:
                abc_class = 'A'
                recommendation = (
                    "Tight control: Daily monitoring, accurate records, "
                    "frequent review of demand forecasts, close supplier relationships"
                )
            elif cumulative_percentage <= ABCVEDClassificationService.ABC_B_THRESHOLD:
                abc_class = 'B'
                recommendation = (
                    "Moderate control: Regular monitoring, good records, "
                    "periodic demand review, standard supplier management"
                )
            else:
                abc_class = 'C'
                recommendation = (
                    "Simple control: Periodic review, basic records, "
                    "bulk ordering to reduce costs, standard procedures"
                )

            classifications.append(ABCClassification(
                product_id=product.id,
                product_code=product.code,
                product_name=product.name,
                annual_consumption_value=value,
                percentage_of_total=percentage,
                cumulative_percentage=cumulative_percentage,
                abc_class=abc_class,
                recommendation=recommendation
            ))

            # Update product record
            product.abc_classification = abc_class
            product.abc_classification_date = timezone.now().date()

        # Bulk update products
        Product.objects.bulk_update(
            [c.product_code for c in classifications],
            ['abc_classification', 'abc_classification_date'],
            batch_size=100
        )

        return classifications

    @staticmethod
    @transaction.atomic
    def perform_ved_analysis(
        company: Company,
        category: Optional[ProductCategory] = None
    ) -> List[VEDClassification]:
        """
        Perform VED analysis based on criticality.

        VED Analysis classifies inventory based on criticality:
        - V (Vital): Critical items, shortage leads to production stoppage
        - E (Essential): Important items, shortage causes problems but not immediate stoppage
        - D (Desirable): Nice to have, shortage causes minor inconvenience

        Since criticality is subjective, this method uses heuristics:
        - Products with high consumption frequency = V
        - Products used in production/sales = E
        - Rarely used products = D

        Args:
            company: Company instance
            category: Optional category filter

        Returns:
            List of VEDClassification
        """
        products_query = Product.objects.filter(
            company=company,
            is_active=True
        )

        if category:
            products_query = products_query.filter(category=category)

        products = list(products_query)

        classifications = []

        for product in products:
            criticality_score = 0
            rationale_parts = []

            # Check consumption frequency (last 90 days)
            cutoff_date = timezone.now().date() - timedelta(days=90)
            issue_count = StockLedger.objects.filter(
                company=company,
                product=product,
                transaction_type='ISSUE',
                transaction_date__gte=cutoff_date
            ).count()

            if issue_count >= 20:  # Issued 20+ times in 90 days
                criticality_score += 3
                rationale_parts.append("High consumption frequency")
            elif issue_count >= 10:
                criticality_score += 2
                rationale_parts.append("Moderate consumption frequency")
            elif issue_count >= 5:
                criticality_score += 1
                rationale_parts.append("Regular consumption")

            # Check if product has low stock levels (indicates importance)
            stock_levels = StockLevel.objects.filter(
                company=company,
                product=product
            )

            for stock_level in stock_levels:
                if product.reorder_level and stock_level.quantity <= product.reorder_level:
                    criticality_score += 2
                    rationale_parts.append("Frequently at reorder level")
                    break

            # Check if product is expensive (high value items are often critical)
            if product.standard_cost and product.standard_cost > Decimal('1000'):
                criticality_score += 1
                rationale_parts.append("High value item")

            # Check expiry tracking (perishable items often critical)
            if product.prevent_expired_issuance:
                criticality_score += 1
                rationale_parts.append("Expiry-controlled item")

            # Determine VED class based on score
            if criticality_score >= 5:
                ved_class = 'V'  # Vital
                rationale = "Vital: " + ", ".join(rationale_parts) if rationale_parts else "High criticality indicators"
            elif criticality_score >= 3:
                ved_class = 'E'  # Essential
                rationale = "Essential: " + ", ".join(rationale_parts) if rationale_parts else "Moderate criticality"
            else:
                ved_class = 'D'  # Desirable
                rationale = "Desirable: " + ", ".join(rationale_parts) if rationale_parts else "Low criticality"

            classifications.append(VEDClassification(
                product_id=product.id,
                product_code=product.code,
                product_name=product.name,
                criticality_score=criticality_score,
                ved_class=ved_class,
                rationale=rationale
            ))

            # Update product record
            product.ved_classification = ved_class
            product.ved_classification_date = timezone.now().date()

        # Bulk update products
        Product.objects.bulk_update(
            [c.product_code for c in classifications],
            ['ved_classification', 'ved_classification_date'],
            batch_size=100
        )

        return classifications

    @staticmethod
    def classify_fsn(days_since_last_movement: int) -> str:
        """
        Classify product as Fast/Slow/Non-moving.

        Args:
            days_since_last_movement: Days since last issue

        Returns:
            F, S, or N
        """
        if days_since_last_movement <= ABCVEDClassificationService.FSN_FAST_DAYS:
            return 'F'  # Fast moving
        elif days_since_last_movement <= ABCVEDClassificationService.FSN_SLOW_DAYS:
            return 'S'  # Slow moving
        else:
            return 'N'  # Non-moving

    @staticmethod
    def classify_hml(unit_price: Decimal, price_percentiles: Dict[str, Decimal]) -> str:
        """
        Classify product as High/Medium/Low value based on unit price.

        Args:
            unit_price: Product unit price
            price_percentiles: Dict with 'high' and 'low' thresholds

        Returns:
            H, M, or L
        """
        if unit_price >= price_percentiles['high']:
            return 'H'  # High value
        elif unit_price <= price_percentiles['low']:
            return 'L'  # Low value
        else:
            return 'M'  # Medium value

    @staticmethod
    def perform_multi_dimensional_classification(
        company: Company,
        period_months: int = 12,
        warehouse: Optional[Warehouse] = None,
        category: Optional[ProductCategory] = None
    ) -> List[MultiDimensionalClassification]:
        """
        Perform comprehensive multi-dimensional classification.

        Combines ABC, VED, FSN, and HML analyses for holistic view.

        Args:
            company: Company instance
            period_months: Analysis period
            warehouse: Optional warehouse filter
            category: Optional category filter

        Returns:
            List of MultiDimensionalClassification
        """
        # Run ABC analysis
        abc_results = ABCVEDClassificationService.perform_abc_analysis(
            company, period_months, warehouse, category
        )
        abc_dict = {r.product_id: r.abc_class for r in abc_results}

        # Run VED analysis
        ved_results = ABCVEDClassificationService.perform_ved_analysis(company, category)
        ved_dict = {r.product_id: r.ved_class for r in ved_results}

        # Get all products
        products_query = Product.objects.filter(
            company=company,
            is_active=True
        )

        if category:
            products_query = products_query.filter(category=category)

        products = list(products_query)

        # Calculate price percentiles for HML
        prices = [
            p.standard_cost for p in products
            if p.standard_cost and p.standard_cost > 0
        ]
        prices.sort()

        if prices:
            high_idx = int(len(prices) * ABCVEDClassificationService.HML_HIGH_PERCENTILE / 100)
            low_idx = int(len(prices) * ABCVEDClassificationService.HML_LOW_PERCENTILE / 100)
            price_percentiles = {
                'high': prices[high_idx] if high_idx < len(prices) else prices[-1],
                'low': prices[low_idx] if low_idx >= 0 else prices[0]
            }
        else:
            price_percentiles = {'high': Decimal('1000'), 'low': Decimal('10')}

        # Classify each product
        classifications = []
        cutoff_date = timezone.now().date() - timedelta(days=90)

        for product in products:
            abc_class = abc_dict.get(product.id, 'C')
            ved_class = ved_dict.get(product.id, 'D')

            # FSN classification
            last_movement = StockLedger.objects.filter(
                company=company,
                product=product,
                transaction_type='ISSUE'
            ).order_by('-transaction_date').first()

            if last_movement:
                days_since_movement = (timezone.now().date() - last_movement.transaction_date).days
            else:
                days_since_movement = 999

            fsn_class = ABCVEDClassificationService.classify_fsn(days_since_movement)

            # HML classification
            unit_price = product.standard_cost or Decimal('0')
            hml_class = ABCVEDClassificationService.classify_hml(unit_price, price_percentiles)

            # Determine combined priority
            combined_priority = ABCVEDClassificationService._determine_combined_priority(
                abc_class, ved_class, fsn_class
            )

            # Get management strategy
            management_strategy = ABCVEDClassificationService._get_management_strategy(
                abc_class, ved_class, fsn_class, hml_class
            )

            classifications.append(MultiDimensionalClassification(
                product_id=product.id,
                product_code=product.code,
                product_name=product.name,
                abc_class=abc_class,
                ved_class=ved_class,
                fsn_class=fsn_class,
                hml_class=hml_class,
                combined_priority=combined_priority,
                management_strategy=management_strategy
            ))

        return classifications

    @staticmethod
    def _determine_combined_priority(abc_class: str, ved_class: str, fsn_class: str) -> str:
        """
        Determine combined priority based on multiple classifications.

        Priority matrix:
        - AV or BV = CRITICAL
        - AE or BE or CV = HIGH
        - CE or AD or BD = MEDIUM
        - CD or Rest = LOW

        Args:
            abc_class: A, B, or C
            ved_class: V, E, or D
            fsn_class: F, S, or N

        Returns:
            CRITICAL, HIGH, MEDIUM, or LOW
        """
        # Vital items with high value = CRITICAL
        if ved_class == 'V' and abc_class in ['A', 'B']:
            return 'CRITICAL'

        # Essential items with high value OR Vital items with lower value = HIGH
        if (ved_class == 'E' and abc_class in ['A', 'B']) or (ved_class == 'V' and abc_class == 'C'):
            return 'HIGH'

        # Essential items with low value OR Desirable items with high value = MEDIUM
        if (ved_class == 'E' and abc_class == 'C') or (ved_class == 'D' and abc_class in ['A', 'B']):
            return 'MEDIUM'

        # Desirable items with low value = LOW
        return 'LOW'

    @staticmethod
    def _get_management_strategy(
        abc_class: str,
        ved_class: str,
        fsn_class: str,
        hml_class: str
    ) -> str:
        """
        Get recommended management strategy.

        Args:
            abc_class: A, B, or C
            ved_class: V, E, or D
            fsn_class: F, S, or N
            hml_class: H, M, or L

        Returns:
            Management strategy recommendation
        """
        strategies = []

        # ABC-based strategy
        if abc_class == 'A':
            strategies.append("Tight inventory control")
            strategies.append("Frequent cycle counts")
        elif abc_class == 'B':
            strategies.append("Regular monitoring")
        else:
            strategies.append("Periodic review only")

        # VED-based strategy
        if ved_class == 'V':
            strategies.append("Safety stock mandatory")
            strategies.append("Backup suppliers required")
        elif ved_class == 'E':
            strategies.append("Maintain adequate buffer")

        # FSN-based strategy
        if fsn_class == 'N':
            strategies.append("Review for obsolescence")
            strategies.append("Consider liquidation")
        elif fsn_class == 'S':
            strategies.append("Reduce order quantities")

        # HML-based strategy
        if hml_class == 'H':
            strategies.append("Bulk purchase negotiations")
            strategies.append("Consignment arrangements")

        return " | ".join(strategies) if strategies else "Standard procedures"

    @staticmethod
    def get_classification_summary(company: Company) -> Dict:
        """
        Get summary of product classifications.

        Args:
            company: Company instance

        Returns:
            Dict with classification summary
        """
        products = Product.objects.filter(company=company, is_active=True)

        abc_counts = products.values('abc_classification').annotate(count=Count('id'))
        ved_counts = products.values('ved_classification').annotate(count=Count('id'))

        total_products = products.count()

        return {
            'total_products': total_products,
            'abc_analysis': {
                class_name: next((c['count'] for c in abc_counts if c['abc_classification'] == class_name), 0)
                for class_name in ['A', 'B', 'C']
            },
            'ved_analysis': {
                class_name: next((c['count'] for c in ved_counts if c['ved_classification'] == class_name), 0)
                for class_name in ['V', 'E', 'D']
            },
            'last_classification_date': products.aggregate(
                last_abc=Max('abc_classification_date'),
                last_ved=Max('ved_classification_date')
            )
        }
