from base64 import b64decode
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from apps.analytics.models import CashflowSnapshot, SalesPerformanceSnapshot
from apps.analytics.services.etl import get_warehouse_alias, resolve_period, run_warehouse_etl
from apps.companies.models import Company
from apps.finance.models import Invoice
from apps.sales.models import Customer, SalesOrder
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    company = getattr(request, "company", None)
    if not company:
        company = request.user.companies.filter(is_active=True).first()
    if not company:
        return JsonResponse({'error': 'No company found for this user'}, status=404)

    period = request.GET.get('period', '30d')
    pr = resolve_period(period)

    warehouse_alias = get_warehouse_alias('default')
    sales_snapshot = (
        SalesPerformanceSnapshot.objects.using(warehouse_alias)
        .filter(company_id=company.id, period=pr.label)
        .order_by('-snapshot_date')
        .first()
    )
    cash_snapshot = (
        CashflowSnapshot.objects.using(warehouse_alias)
        .filter(company_id=company.id, period=pr.label)
        .order_by('-snapshot_date')
        .first()
    )

    if sales_snapshot is None or cash_snapshot is None:
        run_warehouse_etl(period=pr.label, companies=[company])
        warehouse_alias = get_warehouse_alias('default')
        sales_snapshot = (
            SalesPerformanceSnapshot.objects.using(warehouse_alias)
            .filter(company_id=company.id, period=pr.label)
            .order_by('-snapshot_date')
            .first()
        )
        cash_snapshot = (
            CashflowSnapshot.objects.using(warehouse_alias)
            .filter(company_id=company.id, period=pr.label)
            .order_by('-snapshot_date')
            .first()
        )

    total_revenue = float(getattr(sales_snapshot, 'total_revenue', 0) or 0)
    total_orders = getattr(sales_snapshot, 'total_orders', 0) or 0
    active_customers = Customer.objects.filter(company=company, customer_status='ACTIVE').count()
    overdue_invoices = Invoice.objects.filter(
        company=company,
        invoice_type='AR',
        status__in=['POSTED', 'PARTIAL'],
        due_date__lt=timezone.now().date(),
    ).count()

    revenue_breakdown = []
    if sales_snapshot and sales_snapshot.top_products:
        revenue_breakdown = [
            {'category': item.get('name', 'Unknown'), 'value': float(item.get('total') or 0)}
            for item in sales_snapshot.top_products[:5]
        ]

    sales_trend = getattr(sales_snapshot, 'sales_trend', [])

    payload = {
        'stats': {
            'revenue': total_revenue,
            'orders': total_orders,
            'customers': active_customers,
            'approvals': overdue_invoices,
        },
        'sales_trend': sales_trend,
        'revenue_breakdown': revenue_breakdown,
        'cash_flow': getattr(cash_snapshot, 'cash_trend', []) if cash_snapshot else [],
        'period': pr.label,
    }
    return JsonResponse(payload)



def home(_request):
    html = """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>TWIST ERP Backend</title>
      <style>
        body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; padding: 3rem; color: #222; }
        h1 { margin-bottom: .25rem; }
        .muted { color: #666; margin-top: 0; }
        ul { margin-top: 1rem; }
        a { color: #0d6efd; text-decoration: none; }
        a:hover { text-decoration: underline; }
        code { background: #f6f8fa; padding: .1rem .3rem; border-radius: 4px; }
      </style>
      <link rel="icon" href="/favicon.ico">
    </head>
    <body>
      <h1>TWIST ERP API</h1>
      <p class="muted">Django backend is running.</p>
      <ul>
        <li><a href="/api/">API Root</a></li>
        <li><a href="/api/docs/">API Docs (Swagger)</a></li>
        <li><a href="/admin/">Django Admin</a></li>
      </ul>
      <p>Dev tips: use <code>localhost</code> or <code>127.0.0.1</code> in your browser. <code>0.0.0.0</code> is a listen address.</p>
    </body>
    </html>
    """
    return HttpResponse(html)


# 16x16 transparent PNG as a tiny favicon (valid for most browsers)
_FAVICON_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAAHElEQVQoU2NkYGD4z0AEMDEwMDAwGgYGhgYAAAPQAg3w8qO1AAAAAElFTkSuQmCC"
)


def favicon(_request):
    data = b64decode(_FAVICON_BASE64)
    return HttpResponse(data, content_type="image/png")
