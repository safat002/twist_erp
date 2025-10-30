from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from django.db import connections, transaction
from django.db.models import Case, DecimalField, F, Q, Sum, When
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.companies.models import Company
from apps.finance.models import Invoice, Payment
from apps.sales.models import SalesOrder
from apps.analytics import models as warehouse_models

logger = logging.getLogger(__name__)


PERIOD_DAY_MAPPING = {
    '7d': 7,
    '14d': 14,
    '30d': 30,
    '60d': 60,
    '90d': 90,
}


def get_warehouse_alias(fallback: str = 'default') -> str:
    return 'data_warehouse' if 'data_warehouse' in connections.databases else fallback


@dataclass(frozen=True)
class PeriodRange:
    start: date
    end: date
    label: str


def resolve_period(period: str | None, reference: date | None = None) -> PeriodRange:
    today = reference or timezone.now().date()
    key = (period or '30d').lower()

    if key in PERIOD_DAY_MAPPING:
        delta = PERIOD_DAY_MAPPING[key]
        start = today - timedelta(days=delta - 1)
        return PeriodRange(start=start, end=today, label=key)

    if key in {'month', 'this_month'}:
        start = today.replace(day=1)
        return PeriodRange(start=start, end=today, label='month')

    if key in {'quarter', 'this_quarter'}:
        quarter = (today.month - 1) // 3 * 3 + 1
        start = today.replace(month=quarter, day=1)
        return PeriodRange(start=start, end=today, label='quarter')

    # Default fallback
    default_start = today - timedelta(days=29)
    return PeriodRange(start=default_start, end=today, label='30d')


def decimal_or_zero(value) -> Decimal:
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        return Decimal('0')


def _format_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _serialize_timeseries(rows: Iterable[dict], date_key: str = 'date', value_keys: Iterable[str] | None = None):
    series = []
    for row in rows:
        payload = {}
        payload['date'] = row[date_key].strftime('%Y-%m-%d') if isinstance(row[date_key], date) else row[date_key]
        keys = value_keys or [key for key in row.keys() if key != date_key]
        for key in keys:
            payload[key] = float(row.get(key, 0) or 0)
        series.append(payload)
    return series


def sync_company_snapshot(company: Company, period: str = '30d', snapshot_date: date | None = None) -> dict:
    """
    Build analytics snapshots for a single company and persist them
    into the data warehouse schema.
    """
    snapshot_at = snapshot_date or timezone.now().date()
    pr = resolve_period(period, reference=snapshot_at)

    sales_orders = SalesOrder.objects.filter(
        company=company,
        order_date__range=(pr.start, pr.end),
    )

    total_orders = sales_orders.count()
    revenue = decimal_or_zero(sales_orders.aggregate(total=Sum('total_amount'))['total'])
    avg_order_value = revenue / total_orders if total_orders else Decimal('0')

    db_alias = sales_orders.db
    vendor = connections[db_alias].vendor

    if vendor == 'sqlite':
        sales_trend_qs = (
            sales_orders
            .values('order_date')
            .annotate(total=Sum('total_amount'))
            .order_by('order_date')
        )
        sales_trend = _serialize_timeseries(sales_trend_qs, date_key='order_date', value_keys=['total'])
    else:
        sales_trend_qs = (
            sales_orders
            .annotate(day=TruncDate('order_date'))
            .values('day')
            .annotate(total=Sum('total_amount'))
            .order_by('day')
        )
        sales_trend = _serialize_timeseries(sales_trend_qs, date_key='day', value_keys=['total'])

    top_customers_qs = sales_orders.values('customer_id').annotate(
        customer_name=F('customer__name'),
        total=Sum('total_amount'),
    ).order_by('-total')[:5]
    top_customers = [
        {
            'customer_id': row['customer_id'],
            'name': row['customer_name'] or 'Unknown',
            'total': float(row['total'] or 0),
        }
        for row in top_customers_qs
    ]

    top_products_qs = sales_orders.values(
        'lines__product_id',
        'lines__product__name',
    ).annotate(
        total=Sum('lines__line_total'),
    ).order_by('-total')[:5]
    top_products = [
        {
            'product_id': row['lines__product_id'],
            'name': row['lines__product__name'] or 'Unnamed Product',
            'total': float(row['total'] or 0),
        }
        for row in top_products_qs
    ]

    payments = Payment.objects.filter(
        company=company,
        payment_date__range=(pr.start, pr.end),
        status__in=['POSTED', 'RECONCILED'],
    )

    cash_in = decimal_or_zero(
        payments.filter(payment_type='RECEIPT').aggregate(total=Sum('amount'))['total']
    )
    cash_out = decimal_or_zero(
        payments.filter(payment_type='PAYMENT').aggregate(total=Sum('amount'))['total']
    )
    net_cash = cash_in - cash_out

    cash_trend_daily = defaultdict(lambda: {'cash_in': Decimal('0'), 'cash_out': Decimal('0')})
    payments_vendor = connections[payments.db].vendor

    if payments_vendor == 'sqlite':
        payments_annotated = (
            payments
            .values('payment_date', 'payment_type')
            .annotate(total=Sum('amount'))
            .order_by('payment_date')
        )
    else:
        payments_annotated = (
            payments
            .annotate(day=TruncDate('payment_date'))
            .values('day', 'payment_type')
            .annotate(total=Sum('amount'))
            .order_by('day')
        )
    for row in payments_annotated:
        day_key = row.get('day') or row.get('payment_date')
        bucket = cash_trend_daily[day_key]
        amount = decimal_or_zero(row['total'])
        if row['payment_type'] == 'RECEIPT':
            bucket['cash_in'] += amount
        else:
            bucket['cash_out'] += amount
    cash_trend = [
        {
            'date': day.strftime('%Y-%m-%d'),
            'cash_in': float(data['cash_in']),
            'cash_out': float(data['cash_out']),
            'net': float(data['cash_in'] - data['cash_out']),
        }
        for day, data in sorted(cash_trend_daily.items())
    ]

    balance_fields = ['POSTED', 'PARTIAL']
    receivables = Invoice.objects.filter(
        company=company,
        invoice_type='AR',
        status__in=balance_fields,
    ).aggregate(
        due=Sum('total_amount'),
        paid=Sum('paid_amount'),
    )
    payables = Invoice.objects.filter(
        company=company,
        invoice_type='AP',
        status__in=balance_fields,
    ).aggregate(
        due=Sum('total_amount'),
        paid=Sum('paid_amount'),
    )

    receivables_balance = decimal_or_zero(receivables['due']) - decimal_or_zero(receivables['paid'])
    payables_balance = decimal_or_zero(payables['due']) - decimal_or_zero(payables['paid'])

    payment_method_summary = payments.values('payment_method').annotate(
        inbound=Sum(
            Case(
                When(payment_type='RECEIPT', then=F('amount')),
                default=Decimal('0'),
                output_field=DecimalField(max_digits=20, decimal_places=2),
            )
        ),
        outbound=Sum(
            Case(
                When(payment_type='PAYMENT', then=F('amount')),
                default=Decimal('0'),
                output_field=DecimalField(max_digits=20, decimal_places=2),
            )
        ),
    )
    bank_balances = [
        {
            'method': row['payment_method'],
            'cash_in': float(row['inbound'] or 0),
            'cash_out': float(row['outbound'] or 0),
            'net': float(decimal_or_zero(row['inbound']) - decimal_or_zero(row['outbound'])),
        }
        for row in payment_method_summary
    ]

    warehouse_db = get_warehouse_alias(company._state.db or 'default')
    defaults_sales = {
        'timeframe_start': pr.start,
        'timeframe_end': pr.end,
        'total_orders': total_orders,
        'total_revenue': _format_money(revenue),
        'avg_order_value': _format_money(avg_order_value),
        'sales_trend': sales_trend,
        'top_customers': top_customers,
        'top_products': top_products,
        'metadata': {
            'period_label': pr.label,
            'generated_at': timezone.now().isoformat(),
        },
    }

    defaults_cash = {
        'timeframe_start': pr.start,
        'timeframe_end': pr.end,
        'cash_in': _format_money(cash_in),
        'cash_out': _format_money(cash_out),
        'net_cash': _format_money(net_cash),
        'cash_trend': cash_trend,
        'receivables_balance': _format_money(receivables_balance),
        'payables_balance': _format_money(payables_balance),
        'bank_balances': bank_balances,
        'metadata': {
            'period_label': pr.label,
            'generated_at': timezone.now().isoformat(),
        },
    }

    processed = 0
    with transaction.atomic(using=warehouse_db):
        warehouse_models.SalesPerformanceSnapshot.objects.using(warehouse_db).update_or_create(
            snapshot_date=snapshot_at,
            period=pr.label,
            company_id=company.id,
            defaults={
                **defaults_sales,
                'company_code': company.code,
                'company_name': company.name,
            },
        )
        processed += 1

        warehouse_models.CashflowSnapshot.objects.using(warehouse_db).update_or_create(
            snapshot_date=snapshot_at,
            period=pr.label,
            company_id=company.id,
            defaults={
                **defaults_cash,
                'company_code': company.code,
                'company_name': company.name,
            },
        )
        processed += 1

        warehouse_models.WarehouseRunLog.objects.using(warehouse_db).create(
            company_id=company.id,
            company_code=company.code,
            company_name=company.name,
            run_type='adhoc' if snapshot_date else 'nightly',
            status='SUCCESS',
            processed_records=processed,
            message=f'ETL complete for period {pr.label}',
        )

    return {
        'company_id': company.id,
        'company_code': company.code,
        'period': pr.label,
        'processed_records': processed,
        'snapshot_date': snapshot_at,
    }


def run_warehouse_etl(period: str = '30d', companies: Iterable[Company] | None = None) -> dict:
    """
    Run the nightly ETL sync across all active companies.
    """
    companies_qs = companies or Company.objects.filter(is_active=True)
    results = []
    errors = []

    for company in companies_qs:
        try:
            result = sync_company_snapshot(company=company, period=period)
            results.append(result)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Warehouse ETL failed for company %s", company.id)
            warehouse_db = get_warehouse_alias(company._state.db or 'default')
            warehouse_models.WarehouseRunLog.objects.using(warehouse_db).create(
                company_id=company.id,
                company_code=company.code,
                company_name=company.name,
                run_type='nightly',
                status='FAILED',
                processed_records=0,
                message=str(exc),
            )
            errors.append({'company_id': company.id, 'error': str(exc)})

    return {
        'success': len(errors) == 0,
        'processed_companies': len(results),
        'results': results,
        'errors': errors,
    }
