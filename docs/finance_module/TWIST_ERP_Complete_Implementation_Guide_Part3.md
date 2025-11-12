# TWIST ERP FINANCE MODULE - IMPLEMENTATION GUIDE PART 3
## API Implementation & One-Click Financial Statement Generator

---

## 3. BACKEND API IMPLEMENTATION

### 3.1 API Views - Journal Vouchers

**File: `backend/apps/finance/api/views/journal_voucher.py`**

```python
"""
Journal Voucher API endpoints
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from apps.finance.models import JournalVoucher, JournalLine
from apps.finance.services.posting import PostingService
from ..serializers.journal_voucher import (
    JournalVoucherSerializer,
    JournalVoucherCreateSerializer,
    JournalLineSerializer
)
from apps.core.permissions import HasFinancePermission


class JournalVoucherViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Journal Vouchers
    
    list: Get all journal vouchers
    create: Create new journal voucher
    retrieve: Get specific journal voucher
    update: Update journal voucher (if draft)
    partial_update: Partial update
    destroy: Delete journal voucher (if draft)
    
    Custom actions:
    - submit: Submit for approval
    - approve: Approve voucher
    - reject: Reject voucher
    - post: Post to GL
    - reverse: Create reversal entry
    """
    permission_classes = [IsAuthenticated, HasFinancePermission]
    serializer_class = JournalVoucherSerializer
    
    def get_queryset(self):
        """Filter by company context"""
        company = self.request.user.get_current_company()
        queryset = JournalVoucher.objects.filter(company=company)
        
        # Filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        period_id = self.request.query_params.get('period')
        if period_id:
            queryset = queryset.filter(period_id=period_id)
        
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(voucher_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(voucher_date__lte=date_to)
        
        return queryset.select_related('period', 'created_by').prefetch_related('lines')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return JournalVoucherCreateSerializer
        return JournalVoucherSerializer
    
    @transaction.atomic
    def perform_create(self, serializer):
        """Create journal voucher with lines"""
        company = self.request.user.get_current_company()
        
        # Get next voucher number
        voucher_number = self._get_next_voucher_number(company)
        
        # Create voucher
        jv = serializer.save(
            company=company,
            voucher_number=voucher_number,
            created_by=self.request.user,
            status='DRAFT'
        )
        
        return jv
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit voucher for approval"""
        jv = self.get_object()
        
        # Validation
        if not jv.can_submit():
            return Response(
                {'error': 'Cannot submit this voucher'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status
        jv.status = 'IN_REVIEW'
        jv.submitted_by = request.user
        jv.submitted_at = timezone.now()
        jv.save()
        
        # Send notification to approvers
        self._notify_approvers(jv)
        
        return Response({'message': 'Voucher submitted for approval'})
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve voucher"""
        jv = self.get_object()
        
        # SoD check
        if not jv.can_approve(request.user):
            return Response(
                {'error': 'You cannot approve this voucher'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update status
        jv.status = 'APPROVED'
        jv.approved_by = request.user
        jv.approved_at = timezone.now()
        jv.save()
        
        return Response({'message': 'Voucher approved'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject voucher"""
        jv = self.get_object()
        reason = request.data.get('reason', '')
        
        if not reason:
            return Response(
                {'error': 'Rejection reason required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        jv.status = 'REJECTED'
        jv.rejected_by = request.user
        jv.rejected_at = timezone.now()
        jv.rejection_reason = reason
        jv.save()
        
        # Notify creator
        self._notify_rejection(jv)
        
        return Response({'message': 'Voucher rejected'})
    
    @action(detail=True, methods=['post'])
    def post_to_gl(self, request, pk=None):
        """Post voucher to GL"""
        jv = self.get_object()
        
        try:
            posting_service = PostingService(request.user)
            gl_entries = posting_service.post_journal_voucher(jv)
            
            return Response({
                'message': 'Voucher posted successfully',
                'gl_entries_created': len(gl_entries)
            })
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """Create reversal entry"""
        jv = self.get_object()
        reversal_date = request.data.get('reversal_date')
        reason = request.data.get('reason', '')
        
        if jv.status != 'POSTED':
            return Response(
                {'error': 'Can only reverse posted vouchers'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            posting_service = PostingService(request.user)
            reversal_jv = posting_service.reverse_journal_voucher(
                jv, reversal_date, reason
            )
            
            serializer = self.get_serializer(reversal_jv)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
```

---

## 4. ONE-CLICK FINANCIAL STATEMENT GENERATOR

### 4.1 Report Generation Service

**File: `backend/apps/finance/services/financial_statements.py`**

```python
"""
Financial Statement Generator
One-click generation of P&L, Balance Sheet, Cash Flow
"""
from django.db.models import Sum, Q
from apps.finance.models import GLEntry, GLAccount, FiscalPeriod, ReportTemplate
from decimal import Decimal
from datetime import date
import logging

logger = logging.getLogger(__name__)


class FinancialStatementGenerator:
    """Generate financial statements with one click"""
    
    def __init__(self, company, period, comparison_period=None):
        self.company = company
        self.period = period
        self.comparison_period = comparison_period
    
    def generate_all_statements(self):
        """
        Generate all financial statements at once
        Returns: dict with all statements
        """
        return {
            'profit_loss': self.generate_profit_loss(),
            'balance_sheet': self.generate_balance_sheet(),
            'cash_flow': self.generate_cash_flow(),
            'trial_balance': self.generate_trial_balance(),
            'metadata': {
                'company': self.company.name,
                'period': self.period.name,
                'generated_at': timezone.now(),
                'currency': self.company.currency
            }
        }
    
    def generate_profit_loss(self):
        """
        Generate Profit & Loss Statement
        """
        # Get or use default template
        template = self._get_template('PROFIT_LOSS')
        
        # Revenue section
        revenue = self._get_section_total('REVENUE', template)
        
        # Cost of Sales
        cos = self._get_section_total('COST_OF_SALES', template)
        
        # Gross Profit
        gross_profit = revenue['total'] - cos['total']
        
        # Operating Expenses
        expenses = self._get_section_total('EXPENSES', template)
        
        # Operating Profit
        operating_profit = gross_profit - expenses['total']
        
        # Other Income
        other_income = self._get_section_total('OTHER_INCOME', template)
        
        # Other Expenses
        other_expenses = self._get_section_total('OTHER_EXPENSES', template)
        
        # Net Profit
        net_profit = operating_profit + other_income['total'] - other_expenses['total']
        
        statement = {
            'type': 'PROFIT_LOSS',
            'title': f"Profit & Loss Statement - {self.period.name}",
            'sections': {
                'revenue': {
                    'title': 'Revenue',
                    'items': revenue['items'],
                    'total': revenue['total']
                },
                'cost_of_sales': {
                    'title': 'Cost of Sales',
                    'items': cos['items'],
                    'total': cos['total']
                },
                'gross_profit': {
                    'title': 'Gross Profit',
                    'amount': gross_profit,
                    'percentage': (gross_profit / revenue['total'] * 100) if revenue['total'] else 0
                },
                'expenses': {
                    'title': 'Operating Expenses',
                    'items': expenses['items'],
                    'total': expenses['total']
                },
                'operating_profit': {
                    'title': 'Operating Profit',
                    'amount': operating_profit
                },
                'other_income': {
                    'title': 'Other Income',
                    'items': other_income['items'],
                    'total': other_income['total']
                },
                'other_expenses': {
                    'title': 'Other Expenses',
                    'items': other_expenses['items'],
                    'total': other_expenses['total']
                },
                'net_profit': {
                    'title': 'Net Profit',
                    'amount': net_profit,
                    'percentage': (net_profit / revenue['total'] * 100) if revenue['total'] else 0
                }
            }
        }
        
        # Add comparison if requested
        if self.comparison_period:
            statement['comparison'] = self._add_comparison(statement, 'PROFIT_LOSS')
        
        return statement
    
    def generate_balance_sheet(self):
        """
        Generate Balance Sheet
        """
        template = self._get_template('BALANCE_SHEET')
        
        # Assets
        current_assets = self._get_section_total('CURRENT_ASSETS', template)
        fixed_assets = self._get_section_total('FIXED_ASSETS', template)
        total_assets = current_assets['total'] + fixed_assets['total']
        
        # Liabilities
        current_liabilities = self._get_section_total('CURRENT_LIABILITIES', template)
        long_term_liabilities = self._get_section_total('LONG_TERM_LIABILITIES', template)
        total_liabilities = current_liabilities['total'] + long_term_liabilities['total']
        
        # Equity
        equity = self._get_section_total('EQUITY', template)
        
        # Get retained earnings (accumulated P&L)
        retained_earnings = self._calculate_retained_earnings()
        
        total_equity = equity['total'] + retained_earnings
        
        statement = {
            'type': 'BALANCE_SHEET',
            'title': f"Balance Sheet - {self.period.end_date}",
            'sections': {
                'assets': {
                    'current_assets': {
                        'title': 'Current Assets',
                        'items': current_assets['items'],
                        'total': current_assets['total']
                    },
                    'fixed_assets': {
                        'title': 'Fixed Assets',
                        'items': fixed_assets['items'],
                        'total': fixed_assets['total']
                    },
                    'total': total_assets
                },
                'liabilities': {
                    'current_liabilities': {
                        'title': 'Current Liabilities',
                        'items': current_liabilities['items'],
                        'total': current_liabilities['total']
                    },
                    'long_term_liabilities': {
                        'title': 'Long Term Liabilities',
                        'items': long_term_liabilities['items'],
                        'total': long_term_liabilities['total']
                    },
                    'total': total_liabilities
                },
                'equity': {
                    'equity': {
                        'title': 'Equity',
                        'items': equity['items'],
                        'total': equity['total']
                    },
                    'retained_earnings': {
                        'title': 'Retained Earnings',
                        'amount': retained_earnings
                    },
                    'total': total_equity
                },
                'total_liabilities_equity': total_liabilities + total_equity
            },
            'is_balanced': abs(total_assets - (total_liabilities + total_equity)) < 0.01
        }
        
        if self.comparison_period:
            statement['comparison'] = self._add_comparison(statement, 'BALANCE_SHEET')
        
        return statement
    
    def generate_cash_flow(self):
        """
        Generate Cash Flow Statement (Indirect Method)
        """
        # Operating Activities
        net_profit = self._get_net_profit()
        
        # Adjustments for non-cash items
        depreciation = self._get_account_balance('6200-6299')  # Depreciation expense
        
        # Changes in working capital
        ar_change = self._get_balance_change('1200-1299')  # Accounts Receivable
        inventory_change = self._get_balance_change('1300-1399')  # Inventory
        ap_change = self._get_balance_change('2100-2199')  # Accounts Payable
        
        operating_cf = net_profit + depreciation - ar_change - inventory_change + ap_change
        
        # Investing Activities
        capex = self._get_account_activity('1500-1599', type='debit')  # Fixed assets
        
        investing_cf = -capex
        
        # Financing Activities
        borrowings = self._get_account_activity('2300-2399', type='credit')  # Loans
        repayments = self._get_account_activity('2300-2399', type='debit')
        
        financing_cf = borrowings - repayments
        
        # Net change in cash
        net_change = operating_cf + investing_cf + financing_cf
        
        # Cash beginning and ending
        cash_beginning = self._get_cash_beginning_balance()
        cash_ending = cash_beginning + net_change
        
        statement = {
            'type': 'CASH_FLOW',
            'title': f"Cash Flow Statement - {self.period.name}",
            'sections': {
                'operating': {
                    'title': 'Cash Flow from Operating Activities',
                    'net_profit': net_profit,
                    'adjustments': {
                        'depreciation': depreciation,
                        'ar_change': -ar_change,
                        'inventory_change': -inventory_change,
                        'ap_change': ap_change
                    },
                    'total': operating_cf
                },
                'investing': {
                    'title': 'Cash Flow from Investing Activities',
                    'capex': -capex,
                    'total': investing_cf
                },
                'financing': {
                    'title': 'Cash Flow from Financing Activities',
                    'borrowings': borrowings,
                    'repayments': -repayments,
                    'total': financing_cf
                },
                'net_change': net_change,
                'cash_beginning': cash_beginning,
                'cash_ending': cash_ending
            }
        }
        
        return statement
    
    def generate_trial_balance(self):
        """
        Generate Trial Balance
        """
        accounts = GLAccount.objects.filter(
            company=self.company,
            is_active=True,
            is_header=False
        ).order_by('code')
        
        trial_balance = []
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')
        
        for account in accounts:
            balance = self._get_account_balance_detail(account)
            
            if balance['debit'] != 0 or balance['credit'] != 0:
                trial_balance.append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'debit': balance['debit'],
                    'credit': balance['credit']
                })
                
                total_debit += balance['debit']
                total_credit += balance['credit']
        
        return {
            'type': 'TRIAL_BALANCE',
            'title': f"Trial Balance - {self.period.end_date}",
            'accounts': trial_balance,
            'totals': {
                'debit': total_debit,
                'credit': total_credit
            },
            'is_balanced': total_debit == total_credit
        }
    
    # Helper methods
    
    def _get_template(self, report_type):
        """Get report template or use default"""
        try:
            return ReportTemplate.objects.get(
                company=self.company,
                report_type=report_type,
                is_default=True
            )
        except ReportTemplate.DoesNotExist:
            return self._get_default_template(report_type)
    
    def _get_default_template(self, report_type):
        """Return default template structure"""
        defaults = {
            'PROFIT_LOSS': {
                'REVENUE': {'accounts': '4000-4999'},
                'COST_OF_SALES': {'accounts': '5000-5999'},
                'EXPENSES': {'accounts': '6000-6999'},
                'OTHER_INCOME': {'accounts': '7000-7499'},
                'OTHER_EXPENSES': {'accounts': '7500-7999'}
            },
            'BALANCE_SHEET': {
                'CURRENT_ASSETS': {'accounts': '1000-1499'},
                'FIXED_ASSETS': {'accounts': '1500-1999'},
                'CURRENT_LIABILITIES': {'accounts': '2000-2299'},
                'LONG_TERM_LIABILITIES': {'accounts': '2300-2999'},
                'EQUITY': {'accounts': '3000-3999'}
            }
        }
        return defaults.get(report_type, {})
    
    def _get_section_total(self, section_name, template):
        """Calculate total for a section with account details"""
        section_def = template.get(section_name, {})
        account_range = section_def.get('accounts', '')
        
        if '-' in account_range:
            start, end = account_range.split('-')
            accounts = GLAccount.objects.filter(
                company=self.company,
                code__gte=start,
                code__lte=end,
                is_header=False
            )
        else:
            accounts = GLAccount.objects.filter(
                company=self.company,
                code=account_range
            )
        
        items = []
        total = Decimal('0.00')
        
        for account in accounts:
            balance = self._get_account_balance(account.code)
            if balance != 0:
                items.append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'amount': abs(balance)
                })
                total += abs(balance)
        
        return {
            'items': items,
            'total': total
        }
    
    def _get_account_balance(self, account_code_or_range):
        """Get account balance for period"""
        if '-' in str(account_code_or_range):
            start, end = account_code_or_range.split('-')
            entries = GLEntry.objects.filter(
                company=self.company,
                period=self.period,
                account__code__gte=start,
                account__code__lte=end
            )
        else:
            entries = GLEntry.objects.filter(
                company=self.company,
                period=self.period,
                account__code=account_code_or_range
            )
        
        totals = entries.aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )
        
        debit = totals['total_debit'] or Decimal('0.00')
        credit = totals['total_credit'] or Decimal('0.00')
        
        return debit - credit
    
    def _get_account_balance_detail(self, account):
        """Get debit/credit balances separately"""
        entries = GLEntry.objects.filter(
            company=self.company,
            period=self.period,
            account=account
        ).aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )
        
        debit = entries['total_debit'] or Decimal('0.00')
        credit = entries['total_credit'] or Decimal('0.00')
        
        # Return net balance in appropriate column
        net = debit - credit
        if net > 0:
            return {'debit': net, 'credit': Decimal('0.00')}
        else:
            return {'debit': Decimal('0.00'), 'credit': abs(net)}
    
    def _calculate_retained_earnings(self):
        """Calculate retained earnings up to this period"""
        # Sum of all revenue and expense accounts from inception
        revenue = self._get_account_balance('4000-4999')
        expenses = self._get_account_balance('5000-7999')
        
        return revenue - expenses
    
    def _get_net_profit(self):
        """Get net profit for the period"""
        revenue = self._get_account_balance('4000-4999')
        expenses = self._get_account_balance('5000-7999')
        return revenue - expenses
```

---

### 4.2 Report API Endpoint

**File: `backend/apps/finance/api/views/reports.py`**

```python
"""
Financial Reports API
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from apps.finance.services.financial_statements import FinancialStatementGenerator
from apps.finance.services.report_export import ReportExporter
from apps.finance.models import FiscalPeriod


class FinancialStatementView(APIView):
    """
    One-click financial statement generation
    
    GET /api/finance/reports/financial-statements/
        ?period=<period_id>
        &comparison_period=<period_id>
        &format=json|pdf|excel
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        company = request.user.get_current_company()
        
        # Get periods
        period_id = request.query_params.get('period')
        if not period_id:
            return Response(
                {'error': 'Period is required'},
                status=400
            )
        
        try:
            period = FiscalPeriod.objects.get(id=period_id, company=company)
        except FiscalPeriod.DoesNotExist:
            return Response({'error': 'Period not found'}, status=404)
        
        comparison_period_id = request.query_params.get('comparison_period')
        comparison_period = None
        if comparison_period_id:
            try:
                comparison_period = FiscalPeriod.objects.get(
                    id=comparison_period_id,
                    company=company
                )
            except FiscalPeriod.DoesNotExist:
                pass
        
        # Generate statements
        generator = FinancialStatementGenerator(
            company,
            period,
            comparison_period
        )
        statements = generator.generate_all_statements()
        
        # Export format
        export_format = request.query_params.get('format', 'json')
        
        if export_format == 'json':
            return Response(statements)
        
        elif export_format == 'pdf':
            exporter = ReportExporter()
            pdf_bytes = exporter.export_to_pdf(statements)
            
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="financial_statements_{period.name}.pdf"'
            return response
        
        elif export_format == 'excel':
            exporter = ReportExporter()
            excel_bytes = exporter.export_to_excel(statements)
            
            response = HttpResponse(
                excel_bytes,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="financial_statements_{period.name}.xlsx"'
            return response
        
        else:
            return Response({'error': 'Invalid format'}, status=400)


class ProfitLossView(APIView):
    """Individual P&L statement"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        company = request.user.get_current_company()
        period_id = request.query_params.get('period')
        
        period = FiscalPeriod.objects.get(id=period_id, company=company)
        generator = FinancialStatementGenerator(company, period)
        
        statement = generator.generate_profit_loss()
        return Response(statement)


class BalanceSheetView(APIView):
    """Individual Balance Sheet"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        company = request.user.get_current_company()
        period_id = request.query_params.get('period')
        
        period = FiscalPeriod.objects.get(id=period_id, company=company)
        generator = FinancialStatementGenerator(company, period)
        
        statement = generator.generate_balance_sheet()
        return Response(statement)
```

---

### 4.3 PDF Export Service

**File: `backend/apps/finance/services/report_export.py`**

```python
"""
Export reports to PDF and Excel
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side


class ReportExporter:
    """Export financial statements to various formats"""
    
    def export_to_pdf(self, statements):
        """
        Export all statements to PDF
        Returns: BytesIO object with PDF
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Title page
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1976d2'),
            spaceAfter=30,
            alignment=1  # Center
        )
        
        story.append(Paragraph(
            f"{statements['metadata']['company']}<br/>Financial Statements",
            title_style
        ))
        story.append(Paragraph(
            f"Period: {statements['metadata']['period']}",
            styles['Normal']
        ))
        story.append(Spacer(1, 0.5*inch))
        
        # Profit & Loss
        if 'profit_loss' in statements:
            story.extend(self._render_profit_loss_pdf(statements['profit_loss'], styles))
            story.append(PageBreak())
        
        # Balance Sheet
        if 'balance_sheet' in statements:
            story.extend(self._render_balance_sheet_pdf(statements['balance_sheet'], styles))
            story.append(PageBreak())
        
        # Cash Flow
        if 'cash_flow' in statements:
            story.extend(self._render_cash_flow_pdf(statements['cash_flow'], styles))
            story.append(PageBreak())
        
        # Trial Balance
        if 'trial_balance' in statements:
            story.extend(self._render_trial_balance_pdf(statements['trial_balance'], styles))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _render_profit_loss_pdf(self, pl, styles):
        """Render P&L as PDF elements"""
        elements = []
        
        # Title
        elements.append(Paragraph(pl['title'], styles['Heading2']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Data table
        data = [['Description', 'Amount']]
        
        # Revenue
        data.append(['REVENUE', ''])
        for item in pl['sections']['revenue']['items']:
            data.append([
                f"  {item['account_name']}",
                f"{item['amount']:,.2f}"
            ])
        data.append(['Total Revenue', f"{pl['sections']['revenue']['total']:,.2f}"])
        
        # Cost of Sales
        data.append(['', ''])
        data.append(['COST OF SALES', ''])
        for item in pl['sections']['cost_of_sales']['items']:
            data.append([
                f"  {item['account_name']}",
                f"{item['amount']:,.2f}"
            ])
        data.append(['Total Cost of Sales', f"{pl['sections']['cost_of_sales']['total']:,.2f}"])
        
        # Gross Profit
        data.append(['', ''])
        data.append(['GROSS PROFIT', f"{pl['sections']['gross_profit']['amount']:,.2f}"])
        
        # Operating Expenses
        data.append(['', ''])
        data.append(['OPERATING EXPENSES', ''])
        for item in pl['sections']['expenses']['items']:
            data.append([
                f"  {item['account_name']}",
                f"{item['amount']:,.2f}"
            ])
        data.append(['Total Expenses', f"{pl['sections']['expenses']['total']:,.2f}"])
        
        # Net Profit
        data.append(['', ''])
        data.append(['NET PROFIT', f"{pl['sections']['net_profit']['amount']:,.2f}"])
        
        # Create table
        table = Table(data, colWidths=[4*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e3f2fd')),
        ]))
        
        elements.append(table)
        return elements
    
    def export_to_excel(self, statements):
        """
        Export all statements to Excel
        Returns: BytesIO object with Excel file
        """
        buffer = BytesIO()
        wb = openpyxl.Workbook()
        
        # Remove default sheet
        wb.remove(wb.active)
        
        # Create sheets for each statement
        if 'profit_loss' in statements:
            self._create_pl_sheet(wb, statements['profit_loss'])
        
        if 'balance_sheet' in statements:
            self._create_bs_sheet(wb, statements['balance_sheet'])
        
        if 'trial_balance' in statements:
            self._create_tb_sheet(wb, statements['trial_balance'])
        
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _create_pl_sheet(self, wb, pl):
        """Create P&L worksheet"""
        ws = wb.create_sheet("Profit & Loss")
        
        # Styling
        header_font = Font(bold=True, size=14, color="FFFFFF")
        header_fill = PatternFill(start_color="1976D2", end_color="1976D2", fill_type="solid")
        section_font = Font(bold=True, size=12)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Title
        ws['A1'] = pl['title']
        ws['A1'].font = Font(bold=True, size=16)
        ws.merge_cells('A1:B1')
        
        row = 3
        
        # Headers
        ws[f'A{row}'] = 'Description'
        ws[f'B{row}'] = 'Amount'
        for col in ['A', 'B']:
            ws[f'{col}{row}'].font = header_font
            ws[f'{col}{row}'].fill = header_fill
            ws[f'{col}{row}'].alignment = Alignment(horizontal='center')
        
        row += 1
        
        # Revenue
        ws[f'A{row}'] = 'REVENUE'
        ws[f'A{row}'].font = section_font
        row += 1
        
        for item in pl['sections']['revenue']['items']:
            ws[f'A{row}'] = f"  {item['account_name']}"
            ws[f'B{row}'] = item['amount']
            ws[f'B{row}'].number_format = '#,##0.00'
            row += 1
        
        ws[f'A{row}'] = 'Total Revenue'
        ws[f'A{row}'].font = section_font
        ws[f'B{row}'] = pl['sections']['revenue']['total']
        ws[f'B{row}'].number_format = '#,##0.00'
        ws[f'B{row}'].font = section_font
        row += 2
        
        # Continue for other sections...
        
        # Auto-size columns
        ws.column_dimensions['A'].width = 50
        ws.column_dimensions['B'].width = 20
        
        return ws
```

This is Part 3. Should I continue with Part 4 covering the Frontend React components and UI implementation?

