from __future__ import annotations

import copy
from datetime import date
from typing import Any, Dict, Iterable, List

from django.utils import timezone

from apps.ai_companion.services.telemetry import TelemetryService
from apps.analytics.models import CashflowSnapshot, SalesPerformanceSnapshot
from apps.analytics.serializers import (
    CashflowSnapshotSerializer,
    SalesPerformanceSnapshotSerializer,
)
from apps.analytics.services.etl import (
    decimal_or_zero,
    get_warehouse_alias,
    resolve_period,
    run_warehouse_etl,
)
from apps.finance.models import Invoice
from apps.sales.models import SalesOrder
from .models import DashboardLayout


DEFAULT_WIDGETS = [
    {'id': 'kpi-total-revenue', 'type': 'kpi', 'title': 'Revenue', 'description': 'Total revenue for the selected period', 'size': 'sm'},
    {'id': 'kpi-total-orders', 'type': 'kpi', 'title': 'Sales Orders', 'description': 'Orders confirmed in the period', 'size': 'sm'},
    {'id': 'kpi-receivables', 'type': 'kpi', 'title': 'Receivables', 'description': 'Outstanding customer balances', 'size': 'sm'},
    {'id': 'kpi-payables', 'type': 'kpi', 'title': 'Payables', 'description': 'Supplier balances due', 'size': 'sm'},
    {'id': 'chart-sales-trend', 'type': 'chart', 'chartType': 'line', 'title': 'Sales Trend', 'description': 'Daily revenue trend', 'size': 'lg'},
    {'id': 'chart-cashflow', 'type': 'chart', 'chartType': 'bar', 'title': 'Cash Flow', 'description': 'Cash in vs cash out', 'size': 'lg'},
    {'id': 'table-top-customers', 'type': 'table', 'title': 'Top Customers', 'description': 'Highest revenue customers', 'size': 'md'},
    {'id': 'table-top-products', 'type': 'table', 'title': 'Top Products', 'description': 'Best performing products', 'size': 'md'},
    {'id': 'list-recent-orders', 'type': 'list', 'title': 'Recent Orders', 'description': 'Latest confirmed orders', 'size': 'md'},
    {'id': 'list-overdue-invoices', 'type': 'list', 'title': 'Overdue Invoices', 'description': 'Invoices past due date', 'size': 'md'},
]

DEFAULT_LAYOUT = {
    'lg': [
        {'i': 'kpi-total-revenue', 'x': 0, 'y': 0, 'w': 3, 'h': 2},
        {'i': 'kpi-total-orders', 'x': 3, 'y': 0, 'w': 3, 'h': 2},
        {'i': 'kpi-receivables', 'x': 6, 'y': 0, 'w': 3, 'h': 2},
        {'i': 'kpi-payables', 'x': 9, 'y': 0, 'w': 3, 'h': 2},
        {'i': 'chart-sales-trend', 'x': 0, 'y': 2, 'w': 6, 'h': 4},
        {'i': 'chart-cashflow', 'x': 6, 'y': 2, 'w': 6, 'h': 4},
        {'i': 'table-top-customers', 'x': 0, 'y': 6, 'w': 6, 'h': 4},
        {'i': 'table-top-products', 'x': 6, 'y': 6, 'w': 6, 'h': 4},
        {'i': 'list-recent-orders', 'x': 0, 'y': 10, 'w': 6, 'h': 4},
        {'i': 'list-overdue-invoices', 'x': 6, 'y': 10, 'w': 6, 'h': 4},
    ],
    'md': [
        {'i': 'kpi-total-revenue', 'x': 0, 'y': 0, 'w': 6, 'h': 2},
        {'i': 'kpi-total-orders', 'x': 6, 'y': 0, 'w': 6, 'h': 2},
        {'i': 'kpi-receivables', 'x': 0, 'y': 2, 'w': 6, 'h': 2},
        {'i': 'kpi-payables', 'x': 6, 'y': 2, 'w': 6, 'h': 2},
        {'i': 'chart-sales-trend', 'x': 0, 'y': 4, 'w': 12, 'h': 4},
        {'i': 'chart-cashflow', 'x': 0, 'y': 8, 'w': 12, 'h': 4},
        {'i': 'table-top-customers', 'x': 0, 'y': 12, 'w': 12, 'h': 4},
        {'i': 'table-top-products', 'x': 0, 'y': 16, 'w': 12, 'h': 4},
        {'i': 'list-recent-orders', 'x': 0, 'y': 20, 'w': 12, 'h': 4},
        {'i': 'list-overdue-invoices', 'x': 0, 'y': 24, 'w': 12, 'h': 4},
    ],
    'sm': [
        {'i': 'kpi-total-revenue', 'x': 0, 'y': 0, 'w': 12, 'h': 2},
        {'i': 'kpi-total-orders', 'x': 0, 'y': 2, 'w': 12, 'h': 2},
        {'i': 'kpi-receivables', 'x': 0, 'y': 4, 'w': 12, 'h': 2},
        {'i': 'kpi-payables', 'x': 0, 'y': 6, 'w': 12, 'h': 2},
        {'i': 'chart-sales-trend', 'x': 0, 'y': 8, 'w': 12, 'h': 4},
        {'i': 'chart-cashflow', 'x': 0, 'y': 12, 'w': 12, 'h': 4},
        {'i': 'table-top-customers', 'x': 0, 'y': 16, 'w': 12, 'h': 4},
        {'i': 'table-top-products', 'x': 0, 'y': 20, 'w': 12, 'h': 4},
        {'i': 'list-recent-orders', 'x': 0, 'y': 24, 'w': 12, 'h': 4},
        {'i': 'list-overdue-invoices', 'x': 0, 'y': 28, 'w': 12, 'h': 4},
    ],
}


def _copy_layout(layout: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(layout)


def get_default_layout() -> Dict[str, Any]:
    return _copy_layout(DEFAULT_LAYOUT)


def get_default_widget_ids() -> List[str]:
    return [w['id'] for w in DEFAULT_WIDGETS]


def get_available_widgets() -> List[Dict[str, Any]]:
    return copy.deepcopy(DEFAULT_WIDGETS)


def _ensure_layout_record(layout: DashboardLayout | None, user, company) -> DashboardLayout:
    if layout:
        return layout

    return DashboardLayout.objects.create(
        user=user,
        company=company,
        layout=get_default_layout(),
        widgets=get_default_widget_ids(),
    )


def _fetch_or_build_snapshots(company, period_label: str) -> tuple[SalesPerformanceSnapshot | None, CashflowSnapshot | None]:
    alias = get_warehouse_alias("default")
    sales_snapshot = (
        SalesPerformanceSnapshot.objects.using(alias)
        .filter(company_id=company.id, period=period_label)
        .order_by('-snapshot_date')
        .first()
    )
    cash_snapshot = (
        CashflowSnapshot.objects.using(alias)
        .filter(company_id=company.id, period=period_label)
        .order_by('-snapshot_date')
        .first()
    )

    if sales_snapshot is None or cash_snapshot is None:
        run_warehouse_etl(period=period_label, companies=[company])
        alias = get_warehouse_alias("default")
        sales_snapshot = (
            SalesPerformanceSnapshot.objects.using(alias)
            .filter(company_id=company.id, period=period_label)
            .order_by('-snapshot_date')
            .first()
        )
        cash_snapshot = (
            CashflowSnapshot.objects.using(alias)
            .filter(company_id=company.id, period=period_label)
            .order_by('-snapshot_date')
            .first()
        )

    return sales_snapshot, cash_snapshot


def _as_float(value) -> float:
    return float(decimal_or_zero(value))


def _build_recent_orders(company, limit: int = 6) -> List[Dict[str, Any]]:
    orders = (
        SalesOrder.objects.filter(company=company)
        .exclude(status__in=['CANCELLED'])
        .order_by('-order_date')[:limit]
    )
    return [
        {
            'id': order.id,
            'order_number': order.order_number,
            'order_date': order.order_date.isoformat() if isinstance(order.order_date, date) else str(order.order_date),
            'customer': getattr(order.customer, 'name', ''),
            'status': order.status,
            'total': _as_float(order.total_amount),
        }
        for order in orders
    ]


def _build_overdue_invoices(company, limit: int = 6) -> List[Dict[str, Any]]:
    today = timezone.now().date()
    invoices = (
        Invoice.objects.filter(
            company=company,
            status__in=['POSTED', 'PARTIAL'],
            due_date__lt=today,
        )
        .order_by('due_date')[:limit]
    )
    return [
        {
            'id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'due_date': invoice.due_date.isoformat() if isinstance(invoice.due_date, date) else str(invoice.due_date),
            'balance': _as_float(invoice.balance_due),
        }
        for invoice in invoices
    ]


def _build_widget_payload(widget_id: str, sales_snapshot, cash_snapshot, extras: Dict[str, Any]) -> Dict[str, Any]:
    if widget_id == 'kpi-total-revenue':
        value = _as_float(getattr(sales_snapshot, 'total_revenue', 0))
        trend = (getattr(sales_snapshot, 'sales_trend', []) or [])[-7:]
        return {'value': value, 'trend': trend, 'suffix': 'BDT'}

    if widget_id == 'kpi-total-orders':
        trend = (getattr(sales_snapshot, 'sales_trend', []) or [])[-7:]
        return {'value': getattr(sales_snapshot, 'total_orders', 0) or 0, 'trend': trend}

    if widget_id == 'kpi-receivables':
        value = _as_float(getattr(cash_snapshot, 'receivables_balance', 0))
        return {'value': value, 'suffix': 'BDT'}

    if widget_id == 'kpi-payables':
        value = _as_float(getattr(cash_snapshot, 'payables_balance', 0))
        return {'value': value, 'suffix': 'BDT'}

    if widget_id == 'chart-sales-trend':
        serializer = SalesPerformanceSnapshotSerializer(sales_snapshot)
        return {'series': serializer.data.get('sales_trend', [])}

    if widget_id == 'chart-cashflow':
        serializer = CashflowSnapshotSerializer(cash_snapshot)
        return {'series': serializer.data.get('cash_trend', [])}

    if widget_id == 'table-top-customers':
        serializer = SalesPerformanceSnapshotSerializer(sales_snapshot)
        return {'rows': serializer.data.get('top_customers', [])}

    if widget_id == 'table-top-products':
        serializer = SalesPerformanceSnapshotSerializer(sales_snapshot)
        return {'rows': serializer.data.get('top_products', [])}

    if widget_id == 'list-recent-orders':
        return {'items': extras.get('recent_orders', [])}

    if widget_id == 'list-overdue-invoices':
        return {'items': extras.get('overdue_invoices', [])}

    return {}


def load_dashboard(user, company, period: str = '30d') -> Dict[str, Any]:
    """
    Returns dashboard data bundle consisting of layout, widgets, and metrics.
    """
    layout_instance = _ensure_layout_record(
        DashboardLayout.objects.filter(user=user, company=company).first(),
        user=user,
        company=company,
    )

    layout_config = layout_instance.layout or get_default_layout()
    widget_ids = layout_instance.widgets or get_default_widget_ids()

    period_range = resolve_period(period)
    sales_snapshot, cash_snapshot = _fetch_or_build_snapshots(company, period_range.label)

    # Guard against missing analytics data
    sales_snapshot = sales_snapshot or SalesPerformanceSnapshot(
        snapshot_date=period_range.end,
        period=period_range.label,
        company_id=company.id,
        company_code=company.code,
        company_name=company.name,
        timeframe_start=period_range.start,
        timeframe_end=period_range.end,
        total_orders=0,
        total_revenue=0,
        avg_order_value=0,
        sales_trend=[],
        top_customers=[],
        top_products=[],
    )
    cash_snapshot = cash_snapshot or CashflowSnapshot(
        snapshot_date=period_range.end,
        period=period_range.label,
        company_id=company.id,
        company_code=company.code,
        company_name=company.name,
        timeframe_start=period_range.start,
        timeframe_end=period_range.end,
        cash_in=0,
        cash_out=0,
        net_cash=0,
        cash_trend=[],
        receivables_balance=0,
        payables_balance=0,
        bank_balances=[],
    )

    extras = {
        'recent_orders': _build_recent_orders(company),
        'overdue_invoices': _build_overdue_invoices(company),
    }

    widgets_payload = []
    available_widgets = get_available_widgets()
    available_map = {widget['id']: widget for widget in available_widgets}

    for widget_id in widget_ids:
        widget_meta = available_map.get(widget_id)
        if not widget_meta:
            continue
        widget_data = _build_widget_payload(widget_id, sales_snapshot, cash_snapshot, extras)
        widgets_payload.append({
            **widget_meta,
            'data': widget_data,
        })

    return {
        'period': period_range.label,
        'layout': _copy_layout(layout_config),
        'widgets': widgets_payload,
        'available_widgets': available_widgets,
        'currency': getattr(company, 'currency_code', 'BDT'),
    }


def save_layout(user, company, layout: Dict[str, Any], widgets: Iterable[str]) -> DashboardLayout:
    instance = _ensure_layout_record(
        DashboardLayout.objects.filter(user=user, company=company).first(),
        user=user,
        company=company,
    )
    instance.layout = layout or get_default_layout()
    instance.widgets = list(widgets) if widgets else get_default_widget_ids()
    instance.save(update_fields=['layout', 'widgets', 'updated_at'])
    TelemetryService().record_event(
        event_type="dashboard.layout.saved",
        user=user,
        company=company,
        payload={
            "widget_ids": instance.widgets,
            "breakpoints": list((instance.layout or {}).keys()),
        },
    )
    return instance
