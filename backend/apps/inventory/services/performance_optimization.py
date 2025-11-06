"""
Performance Optimization Utilities

Provides caching, query optimization, and performance monitoring for inventory operations.

Features:
- Query result caching
- Computed value caching (stock values, costs)
- Cache invalidation strategies
- Query optimization helpers
- Performance monitoring
"""

import logging
import time
from decimal import Decimal
from typing import Optional, Dict, Any, Callable
from functools import wraps

from django.core.cache import cache
from django.db.models import Prefetch, Sum, Q, F
from django.utils import timezone

from apps.companies.models import Company
from apps.inventory.models import Product, Warehouse, StockLevel, CostLayer

logger = logging.getLogger(__name__)


class InventoryCache:
    """
    Centralized caching for inventory values.
    Uses Django cache backend with intelligent key generation and TTL.
    """

    DEFAULT_TTL = 300  # 5 minutes
    STOCK_LEVEL_TTL = 60  # 1 minute (changes frequently)
    COST_VALUE_TTL = 300  # 5 minutes
    PRODUCT_INFO_TTL = 3600  # 1 hour (changes rarely)

    @staticmethod
    def _generate_key(prefix: str, company_id: int, **kwargs) -> str:
        """Generate cache key from components"""
        parts = [f"inv:{prefix}", f"c:{company_id}"]
        for k, v in sorted(kwargs.items()):
            if v is not None:
                parts.append(f"{k}:{v}")
        return ":".join(parts)

    @classmethod
    def get_stock_level(
        cls,
        company: Company,
        product: Product,
        warehouse: Warehouse
    ) -> Optional[Decimal]:
        """
        Get cached stock level.

        Returns:
            Quantity or None if not cached
        """
        key = cls._generate_key(
            "stock_level",
            company.id,
            product=product.id,
            warehouse=warehouse.id
        )
        return cache.get(key)

    @classmethod
    def set_stock_level(
        cls,
        company: Company,
        product: Product,
        warehouse: Warehouse,
        quantity: Decimal,
        ttl: Optional[int] = None
    ):
        """Cache stock level"""
        key = cls._generate_key(
            "stock_level",
            company.id,
            product=product.id,
            warehouse=warehouse.id
        )
        cache.set(key, quantity, ttl or cls.STOCK_LEVEL_TTL)

    @classmethod
    def invalidate_stock_level(
        cls,
        company: Company,
        product: Product,
        warehouse: Warehouse
    ):
        """Invalidate cached stock level"""
        key = cls._generate_key(
            "stock_level",
            company.id,
            product=product.id,
            warehouse=warehouse.id
        )
        cache.delete(key)

    @classmethod
    def get_product_cost(
        cls,
        company: Company,
        product: Product,
        warehouse: Warehouse
    ) -> Optional[Decimal]:
        """Get cached product cost"""
        key = cls._generate_key(
            "product_cost",
            company.id,
            product=product.id,
            warehouse=warehouse.id
        )
        return cache.get(key)

    @classmethod
    def set_product_cost(
        cls,
        company: Company,
        product: Product,
        warehouse: Warehouse,
        cost: Decimal,
        ttl: Optional[int] = None
    ):
        """Cache product cost"""
        key = cls._generate_key(
            "product_cost",
            company.id,
            product=product.id,
            warehouse=warehouse.id
        )
        cache.set(key, cost, ttl or cls.COST_VALUE_TTL)

    @classmethod
    def invalidate_product_cost(
        cls,
        company: Company,
        product: Product,
        warehouse: Optional[Warehouse] = None
    ):
        """Invalidate cached product costs"""
        if warehouse:
            key = cls._generate_key(
                "product_cost",
                company.id,
                product=product.id,
                warehouse=warehouse.id
            )
            cache.delete(key)
        else:
            # Invalidate all warehouses for this product
            # Note: Requires pattern deletion (Redis-specific)
            pattern = cls._generate_key(
                "product_cost",
                company.id,
                product=product.id
            )
            cache.delete_pattern(f"{pattern}:*")

    @classmethod
    def get_inventory_value(
        cls,
        company: Company,
        warehouse: Optional[Warehouse] = None
    ) -> Optional[Decimal]:
        """Get cached total inventory value"""
        key = cls._generate_key(
            "inventory_value",
            company.id,
            warehouse=warehouse.id if warehouse else "all"
        )
        return cache.get(key)

    @classmethod
    def set_inventory_value(
        cls,
        company: Company,
        value: Decimal,
        warehouse: Optional[Warehouse] = None,
        ttl: Optional[int] = None
    ):
        """Cache total inventory value"""
        key = cls._generate_key(
            "inventory_value",
            company.id,
            warehouse=warehouse.id if warehouse else "all"
        )
        cache.set(key, value, ttl or cls.COST_VALUE_TTL)


def cached_query(ttl: int = 300, key_prefix: str = "query"):
    """
    Decorator for caching query results.

    Usage:
        @cached_query(ttl=600, key_prefix="products")
        def get_active_products(company_id):
            return Product.objects.filter(company_id=company_id, is_active=True)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key_parts = [key_prefix, func.__name__]
            for arg in args:
                cache_key_parts.append(str(arg))
            for k, v in sorted(kwargs.items()):
                cache_key_parts.append(f"{k}:{v}")

            cache_key = ":".join(cache_key_parts)

            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return result

            # Execute function and cache result
            logger.debug(f"Cache miss for {cache_key}, executing query")
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


def timed_operation(operation_name: str):
    """
    Decorator for timing operations and logging slow queries.

    Usage:
        @timed_operation("calculate_stock_value")
        def calculate_value(company, product):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time

                if duration > 1.0:  # Log slow operations (> 1 second)
                    logger.warning(
                        f"Slow operation detected: {operation_name} "
                        f"took {duration:.2f}s"
                    )
                else:
                    logger.debug(f"{operation_name} completed in {duration:.3f}s")

        return wrapper
    return decorator


class QueryOptimizer:
    """
    Helper class for optimizing common inventory queries.
    """

    @staticmethod
    def get_products_with_stock(company: Company, warehouse: Optional[Warehouse] = None):
        """
        Optimized query for products with stock levels.

        Uses select_related and prefetch_related to minimize queries.
        """
        query = Product.objects.filter(
            company=company,
            is_active=True
        ).select_related(
            'category',
            'uom',
            'inventory_account',
            'expense_account'
        )

        # Add stock level filter
        stock_filter = Q(stock_levels__quantity__gt=0)
        if warehouse:
            stock_filter &= Q(stock_levels__warehouse=warehouse)

        query = query.filter(stock_filter).distinct()

        # Prefetch stock levels
        stock_prefetch = Prefetch(
            'stock_levels',
            queryset=StockLevel.objects.filter(
                warehouse=warehouse if warehouse else None
            ).select_related('warehouse')
        )
        query = query.prefetch_related(stock_prefetch)

        return query

    @staticmethod
    def get_cost_layers_optimized(
        company: Company,
        product: Optional[Product] = None,
        warehouse: Optional[Warehouse] = None
    ):
        """
        Optimized query for cost layers.

        Returns queryset with related objects pre-loaded.
        """
        query = CostLayer.objects.filter(
            company=company,
            qty_remaining__gt=0
        ).select_related(
            'product',
            'warehouse',
            'product__category',
            'product__uom'
        ).order_by('fifo_sequence', 'receipt_date')

        if product:
            query = query.filter(product=product)

        if warehouse:
            query = query.filter(warehouse=warehouse)

        return query

    @staticmethod
    def get_inventory_value_aggregated(
        company: Company,
        warehouse: Optional[Warehouse] = None
    ) -> Decimal:
        """
        Efficiently calculates total inventory value using aggregation.

        Much faster than iterating through cost layers.
        """
        cost_layers = CostLayer.objects.filter(
            company=company,
            qty_remaining__gt=0
        )

        if warehouse:
            cost_layers = cost_layers.filter(warehouse=warehouse)

        result = cost_layers.aggregate(
            total=Sum('cost_remaining')
        )

        return result['total'] or Decimal('0')


class PerformanceMonitor:
    """
    Monitor and track performance metrics for inventory operations.
    """

    @staticmethod
    def log_query_count(operation_name: str):
        """
        Context manager for logging query count.

        Usage:
            with PerformanceMonitor.log_query_count("get_products"):
                products = Product.objects.filter(...)
        """
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        class QueryLogger:
            def __enter__(self):
                self.context = CaptureQueriesContext(connection)
                self.context.__enter__()
                return self

            def __exit__(self, *args):
                self.context.__exit__(*args)
                query_count = len(self.context.captured_queries)

                if query_count > 10:
                    logger.warning(
                        f"Operation '{operation_name}' executed {query_count} queries. "
                        "Consider optimization."
                    )
                else:
                    logger.debug(f"Operation '{operation_name}' executed {query_count} queries")

        return QueryLogger()

    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """
        Get cache statistics (if supported by cache backend).

        Returns:
            Dict with cache stats
        """
        try:
            # This works with memcached/redis backends
            stats = cache.get_stats()
            return stats
        except AttributeError:
            return {
                'message': 'Cache statistics not available for this backend'
            }


# Pre-defined optimized queries for common operations

@cached_query(ttl=600, key_prefix="products")
def get_active_products_cached(company_id: int):
    """Cached query for active products"""
    return list(
        Product.objects.filter(
            company_id=company_id,
            is_active=True
        ).select_related('category', 'uom').values(
            'id', 'code', 'name', 'valuation_method'
        )
    )


@cached_query(ttl=300, key_prefix="stock_summary")
def get_stock_summary_cached(company_id: int, warehouse_id: Optional[int] = None):
    """Cached stock summary"""
    filters = {'company_id': company_id, 'quantity__gt': 0}
    if warehouse_id:
        filters['warehouse_id'] = warehouse_id

    return list(
        StockLevel.objects.filter(**filters).values(
            'product_id', 'product__code', 'product__name',
            'warehouse_id', 'warehouse__code', 'quantity'
        )
    )
