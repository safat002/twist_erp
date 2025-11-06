"""
Advanced Reporting Service

Provides comprehensive reporting capabilities:
- Valuation variance reports
- Method comparison reports
- Stock movement analysis
- Turnover ratios
- Dead stock reports
- Custom report builder
"""

import logging
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Sum, Avg, Count, F, Q, Max, Min
from django.utils import timezone

from apps.companies.models import Company
from apps.inventory.models import (
    Product,
    Warehouse,
    ProductCategory,
    CostLayer,
    StockLedger,
    StockLevel
)
from apps.inventory.services.valuation_service import ValuationService

logger = logging.getLogger(__name__)


@dataclass
class ValuationVarianceReport:
    """Valuation variance analysis"""
    product_code: str
    product_name: str
    quantity: Decimal
    fifo_cost: Decimal
    lifo_cost: Decimal
    weighted_avg_cost: Decimal
    standard_cost: Decimal
    max_variance: Decimal
    max_variance_percent: Decimal
    variance_analysis: str


@dataclass
class TurnoverAnalysis:
    """Inventory turnover analysis"""
    product_code: str
    product_name: str
    average_inventory_value: Decimal
    cost_of_goods_sold: Decimal
    turnover_ratio: Decimal
    days_inventory_outstanding: int
    turnover_category: str  # FAST, NORMAL, SLOW


@dataclass
class DeadStockReport:
    """Dead stock identification"""
    product_code: str
    product_name: str
    category: str
    quantity: Decimal
    value: Decimal
    last_movement_date: Optional[date]
    days_without_movement: int
    risk_level: str


class AdvancedReportingService:
    """
    Service for generating advanced inventory reports and analytics.
    """

    @staticmethod
    def generate_valuation_variance_report(
        company: Company,
        warehouse: Optional[Warehouse] = None,
        category: Optional[ProductCategory] = None,
        min_variance_percent: Decimal = Decimal('5')
    ) -> List[ValuationVarianceReport]:
        """
        Generate valuation variance report comparing different methods.

        Shows how different valuation methods affect inventory value,
        helping management understand the impact of method choice.

        Args:
            company: Company instance
            warehouse: Optional warehouse filter
            category: Optional category filter
            min_variance_percent: Minimum variance to include (default: 5%)

        Returns:
            List of ValuationVarianceReport
        """
        # Get products with stock
        products_query = Product.objects.filter(
            company=company,
            is_active=True,
            stock_levels__quantity__gt=0
        ).select_related('category').distinct()

        if category:
            products_query = products_query.filter(category=category)

        if warehouse:
            products_query = products_query.filter(stock_levels__warehouse=warehouse)

        products = list(products_query)
        reports = []

        for product in products:
            # Get stock quantity
            if warehouse:
                stock_level = StockLevel.objects.filter(
                    company=company,
                    product=product,
                    warehouse=warehouse
                ).first()
            else:
                stock_levels = StockLevel.objects.filter(
                    company=company,
                    product=product
                )
                stock_level = stock_levels.aggregate(total=Sum('quantity'))
                quantity = stock_level['total'] or Decimal('0')
                # Use first warehouse for method comparison
                warehouse = stock_levels.first().warehouse if stock_levels.exists() else None

            if not warehouse or quantity == 0:
                continue

            quantity = stock_level.quantity if isinstance(stock_level, StockLevel) else quantity

            # Calculate cost under different methods
            try:
                fifo_cost, _, _ = ValuationService.calculate_fifo_cost(
                    company, product, warehouse, quantity
                )
            except:
                fifo_cost = Decimal('0')

            try:
                lifo_cost, _, _ = ValuationService.calculate_lifo_cost(
                    company, product, warehouse, quantity
                )
            except:
                lifo_cost = Decimal('0')

            try:
                wavg_cost, _, _ = ValuationService.calculate_weighted_average_cost(
                    company, product, warehouse, quantity
                )
            except:
                wavg_cost = Decimal('0')

            standard_cost = (product.standard_cost or Decimal('0')) * quantity

            # Calculate variance
            costs = [c for c in [fifo_cost, lifo_cost, wavg_cost, standard_cost] if c > 0]
            if not costs:
                continue

            max_cost = max(costs)
            min_cost = min(costs)
            max_variance = max_cost - min_cost
            max_variance_percent = (max_variance / min_cost * 100) if min_cost > 0 else Decimal('0')

            # Filter by minimum variance
            if max_variance_percent < min_variance_percent:
                continue

            # Variance analysis
            if max_variance_percent > 20:
                analysis = "CRITICAL: Large valuation difference, review method choice"
            elif max_variance_percent > 10:
                analysis = "HIGH: Significant variance, consider impact on financial statements"
            elif max_variance_percent > 5:
                analysis = "MEDIUM: Moderate variance, monitor closely"
            else:
                analysis = "LOW: Minimal variance across methods"

            reports.append(ValuationVarianceReport(
                product_code=product.code,
                product_name=product.name,
                quantity=quantity,
                fifo_cost=fifo_cost,
                lifo_cost=lifo_cost,
                weighted_avg_cost=wavg_cost,
                standard_cost=standard_cost,
                max_variance=max_variance,
                max_variance_percent=max_variance_percent,
                variance_analysis=analysis
            ))

        # Sort by variance percentage descending
        reports.sort(key=lambda x: x.max_variance_percent, reverse=True)

        return reports

    @staticmethod
    def generate_turnover_analysis(
        company: Company,
        period_months: int = 12,
        warehouse: Optional[Warehouse] = None,
        category: Optional[ProductCategory] = None
    ) -> List[TurnoverAnalysis]:
        """
        Generate inventory turnover analysis.

        Turnover Ratio = Cost of Goods Sold / Average Inventory Value
        Days Inventory Outstanding = 365 / Turnover Ratio

        Args:
            company: Company instance
            period_months: Analysis period (default: 12 months)
            warehouse: Optional warehouse filter
            category: Optional category filter

        Returns:
            List of TurnoverAnalysis
        """
        cutoff_date = timezone.now().date() - timedelta(days=period_months * 30)

        products_query = Product.objects.filter(
            company=company,
            is_active=True
        ).select_related('category')

        if category:
            products_query = products_query.filter(category=category)

        products = list(products_query)
        analyses = []

        for product in products:
            # Calculate COGS (sum of issues)
            issues_query = StockLedger.objects.filter(
                company=company,
                product=product,
                transaction_type='ISSUE',
                transaction_date__gte=cutoff_date
            )

            if warehouse:
                issues_query = issues_query.filter(warehouse=warehouse)

            cogs = issues_query.aggregate(
                total=Sum(F('quantity') * F('rate'))
            )['total'] or Decimal('0')

            cogs = abs(cogs)  # Issues are negative

            if cogs == 0:
                continue

            # Calculate average inventory value
            # Simplified: Use current value as proxy
            if warehouse:
                stock_level = StockLevel.objects.filter(
                    company=company,
                    product=product,
                    warehouse=warehouse
                ).first()
            else:
                stock_levels = StockLevel.objects.filter(
                    company=company,
                    product=product
                )
                total_qty = stock_levels.aggregate(total=Sum('quantity'))['total'] or Decimal('0')
                warehouse_temp = stock_levels.first().warehouse if stock_levels.exists() else None

            if warehouse:
                current_cost = ValuationService.get_current_cost(
                    company, product, warehouse
                )
                avg_inventory_value = current_cost * (stock_level.quantity if stock_level else Decimal('0'))
            else:
                avg_inventory_value = Decimal('0')
                for sl in stock_levels:
                    cost = ValuationService.get_current_cost(company, product, sl.warehouse)
                    avg_inventory_value += cost * sl.quantity

            if avg_inventory_value == 0:
                continue

            # Calculate turnover ratio
            turnover_ratio = cogs / avg_inventory_value

            # Calculate days inventory outstanding
            days_outstanding = int(365 / turnover_ratio) if turnover_ratio > 0 else 999

            # Categorize turnover
            if turnover_ratio >= 12:  # Monthly or faster
                turnover_category = "FAST"
            elif turnover_ratio >= 4:  # Quarterly
                turnover_category = "NORMAL"
            else:  # Less than quarterly
                turnover_category = "SLOW"

            analyses.append(TurnoverAnalysis(
                product_code=product.code,
                product_name=product.name,
                average_inventory_value=avg_inventory_value,
                cost_of_goods_sold=cogs,
                turnover_ratio=turnover_ratio,
                days_inventory_outstanding=days_outstanding,
                turnover_category=turnover_category
            ))

        # Sort by turnover ratio
        analyses.sort(key=lambda x: x.turnover_ratio)

        return analyses

    @staticmethod
    def generate_dead_stock_report(
        company: Company,
        min_days_without_movement: int = 180,
        warehouse: Optional[Warehouse] = None,
        category: Optional[ProductCategory] = None
    ) -> List[DeadStockReport]:
        """
        Generate dead stock report.

        Identifies stock with no movement for extended periods.

        Args:
            company: Company instance
            min_days_without_movement: Minimum days (default: 180)
            warehouse: Optional warehouse filter
            category: Optional category filter

        Returns:
            List of DeadStockReport
        """
        products_query = Product.objects.filter(
            company=company,
            is_active=True,
            stock_levels__quantity__gt=0
        ).select_related('category').distinct()

        if category:
            products_query = products_query.filter(category=category)

        if warehouse:
            products_query = products_query.filter(stock_levels__warehouse=warehouse)

        products = list(products_query)
        reports = []

        for product in products:
            # Get last movement
            last_movement_query = StockLedger.objects.filter(
                company=company,
                product=product,
                transaction_type__in=['ISSUE', 'TRANSFER']
            )

            if warehouse:
                last_movement_query = last_movement_query.filter(warehouse=warehouse)

            last_movement = last_movement_query.order_by('-transaction_date').first()

            if last_movement:
                last_movement_date = last_movement.transaction_date
                days_without_movement = (timezone.now().date() - last_movement_date).days
            else:
                last_movement_date = None
                days_without_movement = 999

            # Filter by minimum days
            if days_without_movement < min_days_without_movement:
                continue

            # Calculate stock value
            if warehouse:
                stock_level = StockLevel.objects.filter(
                    company=company,
                    product=product,
                    warehouse=warehouse
                ).first()

                if not stock_level or stock_level.quantity <= 0:
                    continue

                cost = ValuationService.get_current_cost(company, product, warehouse)
                value = cost * stock_level.quantity
                quantity = stock_level.quantity
            else:
                stock_levels = StockLevel.objects.filter(
                    company=company,
                    product=product,
                    quantity__gt=0
                )

                value = Decimal('0')
                quantity = Decimal('0')
                for sl in stock_levels:
                    cost = ValuationService.get_current_cost(company, product, sl.warehouse)
                    value += cost * sl.quantity
                    quantity += sl.quantity

            # Determine risk level
            if days_without_movement >= 365:
                risk_level = "CRITICAL"
            elif days_without_movement >= 270:
                risk_level = "HIGH"
            elif days_without_movement >= 180:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            reports.append(DeadStockReport(
                product_code=product.code,
                product_name=product.name,
                category=product.category.name if product.category else "Uncategorized",
                quantity=quantity,
                value=value,
                last_movement_date=last_movement_date,
                days_without_movement=days_without_movement,
                risk_level=risk_level
            ))

        # Sort by days without movement descending
        reports.sort(key=lambda x: x.days_without_movement, reverse=True)

        return reports

    @staticmethod
    def generate_stock_movement_summary(
        company: Company,
        start_date: date,
        end_date: date,
        warehouse: Optional[Warehouse] = None,
        category: Optional[ProductCategory] = None
    ) -> Dict:
        """
        Generate stock movement summary for a period.

        Args:
            company: Company instance
            start_date: Period start date
            end_date: Period end date
            warehouse: Optional warehouse filter
            category: Optional category filter

        Returns:
            Dict with movement summary
        """
        ledger_query = StockLedger.objects.filter(
            company=company,
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        )

        if warehouse:
            ledger_query = ledger_query.filter(warehouse=warehouse)

        if category:
            ledger_query = ledger_query.filter(product__category=category)

        # Aggregate by transaction type
        movements = ledger_query.values('transaction_type').annotate(
            count=Count('id'),
            total_quantity=Sum('quantity'),
            total_value=Sum(F('quantity') * F('rate'))
        )

        summary = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': (end_date - start_date).days
            },
            'receipts': {
                'count': 0,
                'quantity': 0,
                'value': 0
            },
            'issues': {
                'count': 0,
                'quantity': 0,
                'value': 0
            },
            'transfers': {
                'count': 0,
                'quantity': 0,
                'value': 0
            },
            'adjustments': {
                'count': 0,
                'quantity': 0,
                'value': 0
            }
        }

        for movement in movements:
            txn_type = movement['transaction_type'].lower()
            if txn_type == 'receipt':
                summary['receipts'] = {
                    'count': movement['count'],
                    'quantity': float(movement['total_quantity']),
                    'value': float(movement['total_value'])
                }
            elif txn_type == 'issue':
                summary['issues'] = {
                    'count': movement['count'],
                    'quantity': float(abs(movement['total_quantity'])),
                    'value': float(abs(movement['total_value']))
                }
            elif txn_type == 'transfer':
                summary['transfers'] = {
                    'count': movement['count'],
                    'quantity': float(abs(movement['total_quantity'])),
                    'value': float(abs(movement['total_value']))
                }
            elif txn_type == 'adjustment':
                summary['adjustments'] = {
                    'count': movement['count'],
                    'quantity': float(movement['total_quantity']),
                    'value': float(movement['total_value'])
                }

        return summary

    @staticmethod
    def generate_method_comparison_report(
        company: Company,
        product: Product,
        warehouse: Warehouse,
        quantity: Decimal
    ) -> Dict:
        """
        Generate detailed method comparison for a specific product.

        Args:
            company: Company instance
            product: Product to analyze
            warehouse: Warehouse
            quantity: Quantity to cost

        Returns:
            Dict with method comparison details
        """
        methods = {}

        # FIFO
        try:
            cost, layers, method = ValuationService.calculate_fifo_cost(
                company, product, warehouse, quantity
            )
            methods['FIFO'] = {
                'total_cost': float(cost),
                'unit_cost': float(cost / quantity) if quantity > 0 else 0,
                'layers_consumed': len(layers),
                'method': method
            }
        except Exception as e:
            methods['FIFO'] = {'error': str(e)}

        # LIFO
        try:
            cost, layers, method = ValuationService.calculate_lifo_cost(
                company, product, warehouse, quantity
            )
            methods['LIFO'] = {
                'total_cost': float(cost),
                'unit_cost': float(cost / quantity) if quantity > 0 else 0,
                'layers_consumed': len(layers),
                'method': method
            }
        except Exception as e:
            methods['LIFO'] = {'error': str(e)}

        # Weighted Average
        try:
            cost, layers, method = ValuationService.calculate_weighted_average_cost(
                company, product, warehouse, quantity
            )
            methods['WEIGHTED_AVG'] = {
                'total_cost': float(cost),
                'unit_cost': float(cost / quantity) if quantity > 0 else 0,
                'layers_consumed': len(layers),
                'method': method
            }
        except Exception as e:
            methods['WEIGHTED_AVG'] = {'error': str(e)}

        # Standard Cost
        if product.standard_cost:
            methods['STANDARD_COST'] = {
                'total_cost': float(product.standard_cost * quantity),
                'unit_cost': float(product.standard_cost),
                'layers_consumed': 0,
                'method': 'STANDARD_COST'
            }

        return {
            'product': {
                'code': product.code,
                'name': product.name
            },
            'warehouse': warehouse.code,
            'quantity': float(quantity),
            'methods': methods,
            'recommendation': AdvancedReportingService._recommend_method(methods)
        }

    @staticmethod
    def _recommend_method(methods: Dict) -> str:
        """Recommend best valuation method based on comparison"""
        # Simple heuristic: recommend method closest to average
        valid_costs = [
            m['total_cost'] for m in methods.values()
            if 'total_cost' in m and m['total_cost'] > 0
        ]

        if len(valid_costs) < 2:
            return "Insufficient data for recommendation"

        avg_cost = sum(valid_costs) / len(valid_costs)

        closest_method = min(
            [(name, abs(m['total_cost'] - avg_cost)) for name, m in methods.items() if 'total_cost' in m],
            key=lambda x: x[1]
        )[0]

        return f"Recommended: {closest_method} (closest to average cost)"
