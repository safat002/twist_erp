from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.finance.models import Invoice, Payment
from apps.sales.models import SalesOrder

logger = logging.getLogger(__name__)


def chat(
    message: str,
    *,
    user=None,
    company=None,
    conversation_id: str | None = None,
    metadata: Dict | None = None,
) -> Dict:
    """
    Rule-based question answering against transactional data.
    """
    if not message:
        return _fallback_response(
            "I didn't catch that. Could you rephrase your question?",
            conversation_id=conversation_id,
        )

    if not company:
        return _fallback_response(
            "I need a company context to answer that. Please select a company.",
            conversation_id=conversation_id,
        )

    text = message.strip()
    normalized = text.lower()
    timeframe = _resolve_timeframe(normalized)
    intent = _detect_intent(normalized)

    if intent is None:
        return _fallback_response(
            "I'm still learning. Try asking about sales orders, revenue, cash flow, receivables, or payables.",
            conversation_id=conversation_id,
        )

    handler = INTENT_HANDLERS.get(intent)
    if handler is None:
        return _fallback_response(
            "That topic isn't supported yet. Please try a finance or sales related question.",
            conversation_id=conversation_id,
        )

    try:
        result = handler(
            text=text,
            company=company,
            timeframe=timeframe,
            user=user,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("AI companion failed to answer intent %s: %s", intent, exc)
        return _fallback_response(
            "Sorry, I ran into a problem while looking that up. Please try again in a moment.",
            conversation_id=conversation_id,
        )

    response_id = conversation_id or str(uuid.uuid4())
    result.setdefault('intent', intent)
    result.setdefault('confidence', 0.72)
    result.setdefault('sources', [])
    result.setdefault('conversation_id', response_id)
    result.setdefault('timeframe', timeframe.label)
    if metadata:
        result.setdefault('metadata', {}).update(metadata)
    return result


# ---------------------------------------------------------------------------
# Intent detection and timeframe parsing
# ---------------------------------------------------------------------------

class Timeframe:
    def __init__(self, start: date, end: date, label: str):
        self.start = start
        self.end = end
        self.label = label

    def to_dict(self) -> Dict[str, str]:
        return {
            'start': self.start.isoformat(),
            'end': self.end.isoformat(),
            'label': self.label,
        }


def _resolve_timeframe(text: str) -> Timeframe:
    today = timezone.now().date()

    if 'today' in text:
        return Timeframe(today, today, 'today')
    if 'yesterday' in text:
        yesterday = today - timedelta(days=1)
        return Timeframe(yesterday, yesterday, 'yesterday')
    if 'last week' in text:
        end = today - timedelta(days=today.weekday() + 1)
        start = end - timedelta(days=6)
        return Timeframe(start, end, 'last_week')
    if 'this week' in text:
        start = today - timedelta(days=today.weekday())
        return Timeframe(start, today, 'this_week')
    if 'last month' in text:
        first_of_this_month = today.replace(day=1)
        end = first_of_this_month - timedelta(days=1)
        start = end.replace(day=1)
        return Timeframe(start, end, 'last_month')
    if 'this month' in text or 'current month' in text:
        start = today.replace(day=1)
        return Timeframe(start, today, 'this_month')
    if 'last quarter' in text:
        quarter = (today.month - 1) // 3
        last_quarter_end_month = quarter * 3
        if last_quarter_end_month == 0:
            year = today.year - 1
            last_quarter_end_month = 12
        else:
            year = today.year
        end = date(year, last_quarter_end_month, 1).replace(day=1) + timedelta(days=-1)
        start_month = last_quarter_end_month - 2
        start = date(end.year, start_month, 1)
        return Timeframe(start, end, 'last_quarter')
    if '90 day' in text or 'last 90 days' in text:
        start = today - timedelta(days=89)
        return Timeframe(start, today, '90d')
    if '7 day' in text or 'last 7 days' in text or 'past week' in text:
        start = today - timedelta(days=6)
        return Timeframe(start, today, '7d')

    # Default window: 30 days
    start = today - timedelta(days=29)
    return Timeframe(start, today, '30d')


INTENT_KEYWORDS = {
    'sales.orders.count': ['sales order', 'sales orders', 'order count', 'orders'],
    'finance.revenue.total': ['revenue', 'sales revenue', 'turnover', 'total sales', 'income'],
    'finance.cashflow.net': ['cashflow', 'cash flow', 'net cash'],
    'finance.receivables.balance': ['receivable', 'owed', 'customer due', 'accounts receivable', 'outstanding customer'],
    'finance.payables.balance': ['payable', 'supplier due', 'accounts payable', 'vendor due'],
    'sales.customers.top': ['top customer', 'best customer', 'top customers', 'best customers'],
    'sales.products.top': ['top product', 'best selling product', 'top products', 'best products'],
}


def _detect_intent(text: str) -> str | None:
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return intent
    return None


def _format_currency(value: Decimal, currency_code: str | None) -> str:
    code = currency_code or 'BDT'
    return f"{code} {value:,.2f}"


def _fallback_response(message: str, conversation_id: str | None = None) -> Dict:
    return {
        'message': message,
        'intent': 'fallback',
        'confidence': 0.2,
        'sources': [],
        'conversation_id': conversation_id or str(uuid.uuid4()),
    }


# ---------------------------------------------------------------------------
# Intent handlers
# ---------------------------------------------------------------------------

def _handle_sales_order_count(text: str, company, timeframe: Timeframe, **_: Dict) -> Dict:
    orders = SalesOrder.objects.filter(
        company=company,
        order_date__range=(timeframe.start, timeframe.end),
    )
    total = orders.count()
    total_amount = orders.aggregate(value=Coalesce(Sum('total_amount'), Decimal('0')))['value']
    message = (
        f"You booked {total} sales order{'s' if total != 1 else ''} between "
        f"{timeframe.start:%b %d} and {timeframe.end:%b %d}. "
        f"The combined order value was {_format_currency(total_amount, company.currency_code)}."
    )
    return {
        'message': message,
        'data': {
            'order_count': total,
            'total_amount': float(total_amount),
            'timeframe': timeframe.to_dict(),
        },
        'sources': ['sales_order'],
        'confidence': 0.78,
    }


def _handle_revenue_total(text: str, company, timeframe: Timeframe, **_: Dict) -> Dict:
    invoices = Invoice.objects.filter(
        company=company,
        invoice_type='AR',
        status__in=['POSTED', 'PAID', 'PARTIAL'],
        invoice_date__range=(timeframe.start, timeframe.end),
    )
    total_revenue = invoices.aggregate(value=Coalesce(Sum('total_amount'), Decimal('0')))['value']
    paid_amount = invoices.aggregate(value=Coalesce(Sum('paid_amount'), Decimal('0')))['value']
    message = (
        f"Revenue recognised from {timeframe.start:%b %d} to {timeframe.end:%b %d} "
        f"is {_format_currency(total_revenue, company.currency_code)}. "
        f"Customers have already paid {_format_currency(paid_amount, company.currency_code)}."
    )
    return {
        'message': message,
        'data': {
            'total_revenue': float(total_revenue),
            'paid_amount': float(paid_amount),
            'outstanding': float(total_revenue - paid_amount),
            'timeframe': timeframe.to_dict(),
        },
        'sources': ['invoice'],
        'confidence': 0.76,
    }


def _handle_cashflow(text: str, company, timeframe: Timeframe, **_: Dict) -> Dict:
    payments = Payment.objects.filter(
        company=company,
        payment_date__range=(timeframe.start, timeframe.end),
        status__in=['POSTED', 'RECONCILED'],
    )
    cash_in = payments.filter(payment_type='RECEIPT').aggregate(value=Coalesce(Sum('amount'), Decimal('0')))['value']
    cash_out = payments.filter(payment_type='PAYMENT').aggregate(value=Coalesce(Sum('amount'), Decimal('0')))['value']
    net_cash = cash_in - cash_out
    message = (
        f"Net cash flow between {timeframe.start:%b %d} and {timeframe.end:%b %d} "
        f"is {_format_currency(net_cash, company.currency_code)} "
        f"({ _format_currency(cash_in, company.currency_code)} in vs "
        f"{_format_currency(cash_out, company.currency_code)} out)."
    )
    return {
        'message': message,
        'data': {
            'cash_in': float(cash_in),
            'cash_out': float(cash_out),
            'net_cash': float(net_cash),
            'timeframe': timeframe.to_dict(),
        },
        'sources': ['payment'],
        'confidence': 0.74,
    }


def _handle_receivables(text: str, company, timeframe: Timeframe, **_: Dict) -> Dict:
    invoices = Invoice.objects.filter(
        company=company,
        invoice_type='AR',
        status__in=['POSTED', 'PARTIAL'],
        invoice_date__lte=timeframe.end,
    )
    total = invoices.aggregate(value=Coalesce(Sum('total_amount'), Decimal('0')))['value']
    paid = invoices.aggregate(value=Coalesce(Sum('paid_amount'), Decimal('0')))['value']
    outstanding = total - paid
    message = (
        f"Customers currently owe {_format_currency(outstanding, company.currency_code)}. "
        f"Invoices raised so far total {_format_currency(total, company.currency_code)}, "
        f"with {_format_currency(paid, company.currency_code)} already collected."
    )
    return {
        'message': message,
        'data': {
            'total': float(total),
            'paid': float(paid),
            'outstanding': float(outstanding),
            'timeframe': timeframe.to_dict(),
        },
        'sources': ['invoice'],
        'confidence': 0.79,
    }


def _handle_payables(text: str, company, timeframe: Timeframe, **_: Dict) -> Dict:
    invoices = Invoice.objects.filter(
        company=company,
        invoice_type='AP',
        status__in=['POSTED', 'PARTIAL'],
        invoice_date__lte=timeframe.end,
    )
    total = invoices.aggregate(value=Coalesce(Sum('total_amount'), Decimal('0')))['value']
    paid = invoices.aggregate(value=Coalesce(Sum('paid_amount'), Decimal('0')))['value']
    outstanding = total - paid
    message = (
        f"You owe suppliers {_format_currency(outstanding, company.currency_code)} as of {timeframe.end:%b %d}. "
        f"In total {_format_currency(total, company.currency_code)} is payable, and "
        f"{_format_currency(paid, company.currency_code)} has been settled."
    )
    return {
        'message': message,
        'data': {
            'total': float(total),
            'paid': float(paid),
            'outstanding': float(outstanding),
            'timeframe': timeframe.to_dict(),
        },
        'sources': ['invoice'],
        'confidence': 0.75,
    }


def _handle_top_customers(text: str, company, timeframe: Timeframe, **_: Dict) -> Dict:
    orders = SalesOrder.objects.filter(
        company=company,
        order_date__range=(timeframe.start, timeframe.end),
    )
    ranking = (
        orders.values('customer__name')
        .annotate(total=Coalesce(Sum('total_amount'), Decimal('0')))
        .order_by('-total')[:5]
    )
    items = [
        {
            'name': row['customer__name'] or 'Unknown',
            'total': float(row['total'] or 0),
        }
        for row in ranking
    ]
    if not items:
        message = "I could not find any customer sales in that period."
    else:
        first = items[0]
        message = (
            f"{first['name']} is your top customer in this period "
            f"with {_format_currency(Decimal(str(first['total'])), company.currency_code)} in orders."
        )
    return {
        'message': message,
        'data': {
            'top_customers': items,
            'timeframe': timeframe.to_dict(),
        },
        'sources': ['sales_order'],
        'confidence': 0.73,
    }


def _handle_top_products(text: str, company, timeframe: Timeframe, **_: Dict) -> Dict:
    orders = SalesOrder.objects.filter(
        company=company,
        order_date__range=(timeframe.start, timeframe.end),
    )
    ranking = (
        orders.values('lines__product__name')
        .annotate(total=Coalesce(Sum('lines__line_total'), Decimal('0')))
        .order_by('-total')[:5]
    )
    items = [
        {
            'name': row['lines__product__name'] or 'Unnamed product',
            'total': float(row['total'] or 0),
        }
        for row in ranking
    ]
    if not items:
        message = "No product sales were found for that timeframe."
    else:
        best = items[0]
        message = (
            f"The best-selling product was {best['name']} with "
            f"{_format_currency(Decimal(str(best['total'])), company.currency_code)} in revenue."
        )
    return {
        'message': message,
        'data': {
            'top_products': items,
            'timeframe': timeframe.to_dict(),
        },
        'sources': ['sales_order'],
        'confidence': 0.72,
    }


INTENT_HANDLERS = {
    'sales.orders.count': _handle_sales_order_count,
    'finance.revenue.total': _handle_revenue_total,
    'finance.cashflow.net': _handle_cashflow,
    'finance.receivables.balance': _handle_receivables,
    'finance.payables.balance': _handle_payables,
    'sales.customers.top': _handle_top_customers,
    'sales.products.top': _handle_top_products,
}
