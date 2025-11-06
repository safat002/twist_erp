"""
Inventory Aging Analysis Service

Analyzes inventory age and identifies slow-moving, non-moving, and obsolete stock.

Features:
- Age analysis by receipt date
- Movement velocity tracking
- Slow-moving identification
- Non-moving identification
- Obsolescence risk scoring
- Aging buckets (0-30, 31-60, 61-90, 90+ days)
"""

import logging
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Q, Sum, Min, Max, Count, Avg, F
from django.utils import timezone

from apps.companies.models import Company
from apps.inventory.models import (
    Product,
    Warehouse,
    CostLayer,
    StockLevel,
    StockLedger,
    ProductCategory
)

logger = logging.getLogger(__name__)


@dataclass
class AgingBucket:
    """Represents an aging bucket"""
    bucket_name: str
    min_days: int
    max_days: Optional[int]
    quantity: Decimal
    value: Decimal
    percentage: Decimal


@dataclass
class ProductAgingAnalysis:
    """Aging analysis for a single product"""
    product_id: int
    product_code: str
    product_name: str
    category: str
    total_quantity: Decimal
    total_value: Decimal
    average_age_days: int
    oldest_stock_days: int
    newest_stock_days: int
    aging_buckets: List[AgingBucket]
    movement_velocity: str  # FAST, NORMAL, SLOW, NON_MOVING
    days_since_last_movement: int
    obsolescence_risk: str  # LOW, MEDIUM, HIGH, CRITICAL
    recommended_action: str


class AgingAnalysisService:
    """
    Service for analyzing inventory aging and movement patterns.
    """

    # Aging bucket definitions (days)
    AGING_BUCKETS = [
        ("0-30 days", 0, 30),
        ("31-60 days", 31, 60),
        ("61-90 days", 61, 90),
        ("91-180 days", 91, 180),
        ("181-365 days", 181, 365),
        ("Over 365 days", 366, None),
    ]

    # Movement velocity thresholds (days since last movement)
    FAST_MOVING_DAYS = 30
    NORMAL_MOVING_DAYS = 90
    SLOW_MOVING_DAYS = 180
    NON_MOVING_DAYS = 365

    @staticmethod
    def calculate_stock_age(receipt_date: date, as_of_date: Optional[date] = None) -> int:
        """
        Calculate age of stock in days.

        Args:
            receipt_date: Date stock was received
            as_of_date: Date to calculate age as of (default: today)

        Returns:
            Age in days
        """
        if as_of_date is None:
            as_of_date = timezone.now().date()

        return (as_of_date - receipt_date).days

    @staticmethod
    def categorize_movement_velocity(days_since_last_movement: int) -> str:
        """
        Categorize product movement velocity.

        Args:
            days_since_last_movement: Days since last stock movement

        Returns:
            Velocity category: FAST, NORMAL, SLOW, NON_MOVING
        """
        if days_since_last_movement <= AgingAnalysisService.FAST_MOVING_DAYS:
            return "FAST"
        elif days_since_last_movement <= AgingAnalysisService.NORMAL_MOVING_DAYS:
            return "NORMAL"
        elif days_since_last_movement <= AgingAnalysisService.SLOW_MOVING_DAYS:
            return "SLOW"
        else:
            return "NON_MOVING"

    @staticmethod
    def calculate_obsolescence_risk(
        average_age_days: int,
        days_since_last_movement: int,
        expiry_date: Optional[date] = None
    ) -> str:
        """
        Calculate obsolescence risk score.

        Args:
            average_age_days: Average age of stock
            days_since_last_movement: Days since last movement
            expiry_date: Optional expiry date

        Returns:
            Risk level: LOW, MEDIUM, HIGH, CRITICAL
        """
        risk_score = 0

        # Age-based risk
        if average_age_days > 365:
            risk_score += 3
        elif average_age_days > 180:
            risk_score += 2
        elif average_age_days > 90:
            risk_score += 1

        # Movement-based risk
        if days_since_last_movement > 365:
            risk_score += 3
        elif days_since_last_movement > 180:
            risk_score += 2
        elif days_since_last_movement > 90:
            risk_score += 1

        # Expiry-based risk
        if expiry_date:
            days_to_expiry = (expiry_date - timezone.now().date()).days
            if days_to_expiry < 0:
                risk_score += 4  # Already expired
            elif days_to_expiry < 30:
                risk_score += 3
            elif days_to_expiry < 90:
                risk_score += 2

        # Determine risk level
        if risk_score >= 7:
            return "CRITICAL"
        elif risk_score >= 5:
            return "HIGH"
        elif risk_score >= 3:
            return "MEDIUM"
        else:
            return "LOW"

    @staticmethod
    def get_recommended_action(
        velocity: str,
        obsolescence_risk: str,
        average_age_days: int
    ) -> str:
        """
        Get recommended action based on analysis.

        Args:
            velocity: Movement velocity
            obsolescence_risk: Obsolescence risk level
            average_age_days: Average age

        Returns:
            Recommended action string
        """
        if obsolescence_risk == "CRITICAL":
            return "URGENT: Write-off or liquidate immediately"
        elif obsolescence_risk == "HIGH":
            if velocity == "NON_MOVING":
                return "High priority: Discount pricing or return to supplier"
            else:
                return "Monitor closely: Consider promotions"
        elif obsolescence_risk == "MEDIUM":
            if velocity in ["SLOW", "NON_MOVING"]:
                return "Action needed: Sales promotion or reallocation"
            else:
                return "Watch: Monitor movement trends"
        else:
            if velocity == "SLOW":
                return "Review: Adjust reorder levels"
            elif velocity == "NON_MOVING":
                return "Investigate: Check demand forecasts"
            else:
                return "Normal: Continue monitoring"

    @staticmethod
    def analyze_product_aging(
        company: Company,
        product: Product,
        warehouse: Optional[Warehouse] = None,
        as_of_date: Optional[date] = None
    ) -> Optional[ProductAgingAnalysis]:
        """
        Analyze aging for a single product.

        Args:
            company: Company instance
            product: Product to analyze
            warehouse: Optional warehouse filter
            as_of_date: Optional date for analysis

        Returns:
            ProductAgingAnalysis or None if no stock
        """
        if as_of_date is None:
            as_of_date = timezone.now().date()

        # Get cost layers with remaining stock
        cost_layers_query = CostLayer.objects.filter(
            company=company,
            product=product,
            qty_remaining__gt=0
        ).select_related('warehouse')

        if warehouse:
            cost_layers_query = cost_layers_query.filter(warehouse=warehouse)

        cost_layers = list(cost_layers_query)

        if not cost_layers:
            return None

        # Calculate total quantity and value
        total_quantity = sum(layer.qty_remaining for layer in cost_layers)
        total_value = sum(layer.cost_remaining for layer in cost_layers)

        # Calculate age statistics
        ages = [
            AgingAnalysisService.calculate_stock_age(layer.receipt_date, as_of_date)
            for layer in cost_layers
        ]

        average_age_days = int(sum(ages) / len(ages))
        oldest_stock_days = max(ages)
        newest_stock_days = min(ages)

        # Calculate aging buckets
        aging_buckets = []
        for bucket_name, min_days, max_days in AgingAnalysisService.AGING_BUCKETS:
            bucket_quantity = Decimal('0')
            bucket_value = Decimal('0')

            for layer in cost_layers:
                age = AgingAnalysisService.calculate_stock_age(layer.receipt_date, as_of_date)

                if max_days is None:
                    # Last bucket (e.g., "Over 365 days")
                    if age >= min_days:
                        bucket_quantity += layer.qty_remaining
                        bucket_value += layer.cost_remaining
                else:
                    if min_days <= age <= max_days:
                        bucket_quantity += layer.qty_remaining
                        bucket_value += layer.cost_remaining

            percentage = (bucket_quantity / total_quantity * 100) if total_quantity > 0 else Decimal('0')

            aging_buckets.append(AgingBucket(
                bucket_name=bucket_name,
                min_days=min_days,
                max_days=max_days,
                quantity=bucket_quantity,
                value=bucket_value,
                percentage=percentage
            ))

        # Calculate days since last movement
        last_movement = StockLedger.objects.filter(
            company=company,
            product=product,
            transaction_type__in=['ISSUE', 'TRANSFER']
        ).order_by('-transaction_date').first()

        if last_movement:
            days_since_last_movement = (as_of_date - last_movement.transaction_date).days
        else:
            days_since_last_movement = 999  # No movement recorded

        # Categorize velocity
        velocity = AgingAnalysisService.categorize_movement_velocity(days_since_last_movement)

        # Get earliest expiry date from cost layers
        expiry_dates = [layer.expiry_date for layer in cost_layers if layer.expiry_date]
        earliest_expiry = min(expiry_dates) if expiry_dates else None

        # Calculate obsolescence risk
        obsolescence_risk = AgingAnalysisService.calculate_obsolescence_risk(
            average_age_days,
            days_since_last_movement,
            earliest_expiry
        )

        # Get recommended action
        recommended_action = AgingAnalysisService.get_recommended_action(
            velocity,
            obsolescence_risk,
            average_age_days
        )

        return ProductAgingAnalysis(
            product_id=product.id,
            product_code=product.code,
            product_name=product.name,
            category=product.category.name if product.category else "Uncategorized",
            total_quantity=total_quantity,
            total_value=total_value,
            average_age_days=average_age_days,
            oldest_stock_days=oldest_stock_days,
            newest_stock_days=newest_stock_days,
            aging_buckets=aging_buckets,
            movement_velocity=velocity,
            days_since_last_movement=days_since_last_movement,
            obsolescence_risk=obsolescence_risk,
            recommended_action=recommended_action
        )

    @staticmethod
    def analyze_warehouse_aging(
        company: Company,
        warehouse: Optional[Warehouse] = None,
        category: Optional[ProductCategory] = None,
        as_of_date: Optional[date] = None
    ) -> List[ProductAgingAnalysis]:
        """
        Analyze aging for all products in a warehouse.

        Args:
            company: Company instance
            warehouse: Optional warehouse filter
            category: Optional category filter
            as_of_date: Optional date for analysis

        Returns:
            List of ProductAgingAnalysis
        """
        # Get products with stock
        products_query = Product.objects.filter(
            company=company,
            is_active=True,
            stock_levels__quantity__gt=0
        ).select_related('category').distinct()

        if warehouse:
            products_query = products_query.filter(stock_levels__warehouse=warehouse)

        if category:
            products_query = products_query.filter(category=category)

        products = list(products_query)

        # Analyze each product
        analyses = []
        for product in products:
            analysis = AgingAnalysisService.analyze_product_aging(
                company=company,
                product=product,
                warehouse=warehouse,
                as_of_date=as_of_date
            )
            if analysis:
                analyses.append(analysis)

        return analyses

    @staticmethod
    def get_slow_moving_products(
        company: Company,
        warehouse: Optional[Warehouse] = None,
        min_days: int = 90
    ) -> List[ProductAgingAnalysis]:
        """
        Get list of slow-moving products.

        Args:
            company: Company instance
            warehouse: Optional warehouse filter
            min_days: Minimum days since last movement (default: 90)

        Returns:
            List of slow-moving products
        """
        analyses = AgingAnalysisService.analyze_warehouse_aging(company, warehouse)
        return [
            a for a in analyses
            if a.movement_velocity in ['SLOW', 'NON_MOVING']
            and a.days_since_last_movement >= min_days
        ]

    @staticmethod
    def get_non_moving_products(
        company: Company,
        warehouse: Optional[Warehouse] = None,
        min_days: int = 180
    ) -> List[ProductAgingAnalysis]:
        """
        Get list of non-moving products.

        Args:
            company: Company instance
            warehouse: Optional warehouse filter
            min_days: Minimum days since last movement (default: 180)

        Returns:
            List of non-moving products
        """
        analyses = AgingAnalysisService.analyze_warehouse_aging(company, warehouse)
        return [
            a for a in analyses
            if a.movement_velocity == 'NON_MOVING'
            and a.days_since_last_movement >= min_days
        ]

    @staticmethod
    def get_obsolescence_risk_report(
        company: Company,
        warehouse: Optional[Warehouse] = None,
        min_risk_level: str = 'MEDIUM'
    ) -> Dict:
        """
        Generate obsolescence risk report.

        Args:
            company: Company instance
            warehouse: Optional warehouse filter
            min_risk_level: Minimum risk level to include (MEDIUM, HIGH, CRITICAL)

        Returns:
            Dict with risk report
        """
        risk_order = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2, 'CRITICAL': 3}
        min_risk_value = risk_order.get(min_risk_level, 1)

        analyses = AgingAnalysisService.analyze_warehouse_aging(company, warehouse)

        # Filter by risk level
        at_risk_products = [
            a for a in analyses
            if risk_order.get(a.obsolescence_risk, 0) >= min_risk_value
        ]

        # Group by risk level
        by_risk = {'CRITICAL': [], 'HIGH': [], 'MEDIUM': [], 'LOW': []}
        for analysis in at_risk_products:
            by_risk[analysis.obsolescence_risk].append(analysis)

        # Calculate totals
        total_at_risk_value = sum(a.total_value for a in at_risk_products)
        total_at_risk_quantity = sum(a.total_quantity for a in at_risk_products)

        return {
            'company': company.code,
            'warehouse': warehouse.name if warehouse else 'All Warehouses',
            'total_products_at_risk': len(at_risk_products),
            'total_value_at_risk': float(total_at_risk_value),
            'total_quantity_at_risk': float(total_at_risk_quantity),
            'by_risk_level': {
                'critical': {
                    'count': len(by_risk['CRITICAL']),
                    'value': float(sum(a.total_value for a in by_risk['CRITICAL'])),
                    'products': [
                        {
                            'code': a.product_code,
                            'name': a.product_name,
                            'value': float(a.total_value),
                            'age_days': a.average_age_days,
                            'action': a.recommended_action
                        }
                        for a in by_risk['CRITICAL']
                    ]
                },
                'high': {
                    'count': len(by_risk['HIGH']),
                    'value': float(sum(a.total_value for a in by_risk['HIGH'])),
                    'products': [
                        {
                            'code': a.product_code,
                            'name': a.product_name,
                            'value': float(a.total_value),
                            'age_days': a.average_age_days,
                            'action': a.recommended_action
                        }
                        for a in by_risk['HIGH']
                    ]
                },
                'medium': {
                    'count': len(by_risk['MEDIUM']),
                    'value': float(sum(a.total_value for a in by_risk['MEDIUM'])),
                }
            }
        }

    @staticmethod
    def get_aging_summary(
        company: Company,
        warehouse: Optional[Warehouse] = None
    ) -> Dict:
        """
        Get summary of inventory aging.

        Args:
            company: Company instance
            warehouse: Optional warehouse filter

        Returns:
            Dict with aging summary
        """
        analyses = AgingAnalysisService.analyze_warehouse_aging(company, warehouse)

        if not analyses:
            return {
                'total_products': 0,
                'total_value': 0,
                'average_age_days': 0,
                'velocity_breakdown': {},
                'aging_buckets': []
            }

        total_value = sum(a.total_value for a in analyses)
        total_quantity = sum(a.total_quantity for a in analyses)
        average_age = int(sum(a.average_age_days for a in analyses) / len(analyses))

        # Velocity breakdown
        velocity_counts = {'FAST': 0, 'NORMAL': 0, 'SLOW': 0, 'NON_MOVING': 0}
        velocity_values = {'FAST': Decimal('0'), 'NORMAL': Decimal('0'), 'SLOW': Decimal('0'), 'NON_MOVING': Decimal('0')}

        for analysis in analyses:
            velocity_counts[analysis.movement_velocity] += 1
            velocity_values[analysis.movement_velocity] += analysis.total_value

        # Aggregate aging buckets
        aggregated_buckets = {}
        for analysis in analyses:
            for bucket in analysis.aging_buckets:
                if bucket.bucket_name not in aggregated_buckets:
                    aggregated_buckets[bucket.bucket_name] = {
                        'quantity': Decimal('0'),
                        'value': Decimal('0')
                    }
                aggregated_buckets[bucket.bucket_name]['quantity'] += bucket.quantity
                aggregated_buckets[bucket.bucket_name]['value'] += bucket.value

        return {
            'total_products': len(analyses),
            'total_value': float(total_value),
            'total_quantity': float(total_quantity),
            'average_age_days': average_age,
            'velocity_breakdown': {
                'fast_moving': {
                    'count': velocity_counts['FAST'],
                    'value': float(velocity_values['FAST']),
                    'percentage': round(velocity_counts['FAST'] / len(analyses) * 100, 2)
                },
                'normal_moving': {
                    'count': velocity_counts['NORMAL'],
                    'value': float(velocity_values['NORMAL']),
                    'percentage': round(velocity_counts['NORMAL'] / len(analyses) * 100, 2)
                },
                'slow_moving': {
                    'count': velocity_counts['SLOW'],
                    'value': float(velocity_values['SLOW']),
                    'percentage': round(velocity_counts['SLOW'] / len(analyses) * 100, 2)
                },
                'non_moving': {
                    'count': velocity_counts['NON_MOVING'],
                    'value': float(velocity_values['NON_MOVING']),
                    'percentage': round(velocity_counts['NON_MOVING'] / len(analyses) * 100, 2)
                }
            },
            'aging_buckets': [
                {
                    'name': name,
                    'quantity': float(data['quantity']),
                    'value': float(data['value']),
                    'percentage': round(data['value'] / total_value * 100, 2) if total_value > 0 else 0
                }
                for name, data in aggregated_buckets.items()
            ]
        }
