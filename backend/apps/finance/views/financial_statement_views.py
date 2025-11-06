"""
Views for financial statements.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from apps.finance.services import FinancialStatementService, TrialBalanceService
from apps.finance.services.statement_export_service import StatementExportService
from apps.finance.serializers.financial_statement_serializers import (
    TrialBalanceRequestSerializer,
    BalanceSheetRequestSerializer,
    IncomeStatementRequestSerializer,
    ExportFormatSerializer,
)
from shared.middleware.company_context import get_current_company


class FinancialStatementViewSet(viewsets.ViewSet):
    """
    ViewSet for financial statements.

    Provides endpoints for:
    - Trial Balance
    - Balance Sheet (Statement of Financial Position)
    - Income Statement (Statement of Comprehensive Income)
    - Export to Excel/CSV
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='trial-balance')
    def trial_balance(self, request):
        """
        Generate trial balance.

        Query Parameters:
            - as_of_date: Date (YYYY-MM-DD) - defaults to today
            - currency: Currency code - defaults to BDT
            - format: excel|csv|json - defaults to json

        Returns:
            Trial balance data or file download
        """
        serializer = TrialBalanceRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        company = get_current_company(request)
        as_of_date = serializer.validated_data.get('as_of_date') or date.today()
        currency = serializer.validated_data.get('currency', 'BDT')
        export_format = request.query_params.get('format', 'json')

        # Generate trial balance
        service = TrialBalanceService(
            company=company,
            as_of_date=as_of_date,
            currency=currency
        )
        data = service.generate()

        # Handle export formats
        if export_format == 'excel':
            return self._export_to_excel(data, 'trial_balance', f'trial_balance_{as_of_date}.xlsx')
        elif export_format == 'csv':
            return self._export_to_csv(data, 'trial_balance', f'trial_balance_{as_of_date}.csv')

        # Return JSON
        return Response({
            'success': True,
            'data': service.export_to_dict()
        })

    @action(detail=False, methods=['get'], url_path='balance-sheet')
    def balance_sheet(self, request):
        """
        Generate balance sheet (Statement of Financial Position).

        Query Parameters:
            - as_of_date: Date (YYYY-MM-DD) - defaults to today
            - currency: Currency code - defaults to BDT
            - format: excel|csv|json - defaults to json

        Returns:
            Balance sheet data or file download
        """
        serializer = BalanceSheetRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        company = get_current_company(request)
        as_of_date = serializer.validated_data.get('as_of_date') or date.today()
        currency = serializer.validated_data.get('currency', 'BDT')
        export_format = request.query_params.get('format', 'json')

        # Generate balance sheet
        service = FinancialStatementService(
            company=company,
            start_date=date(as_of_date.year, 1, 1),  # Start of year
            end_date=as_of_date,
            currency=currency
        )
        data = service.generate_balance_sheet()

        # Handle export formats
        if export_format == 'excel':
            return self._export_to_excel(data, 'balance_sheet', f'balance_sheet_{as_of_date}.xlsx')
        elif export_format == 'csv':
            return self._export_to_csv(data, 'balance_sheet', f'balance_sheet_{as_of_date}.csv')

        # Return JSON
        return Response({
            'success': True,
            'data': self._serialize_balance_sheet(data)
        })

    @action(detail=False, methods=['get'], url_path='income-statement')
    def income_statement(self, request):
        """
        Generate income statement (Statement of Comprehensive Income).

        Query Parameters:
            - start_date: Date (YYYY-MM-DD) - required
            - end_date: Date (YYYY-MM-DD) - required
            - currency: Currency code - defaults to BDT
            - format: excel|csv|json - defaults to json

        Returns:
            Income statement data or file download
        """
        serializer = IncomeStatementRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        company = get_current_company(request)
        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']
        currency = serializer.validated_data.get('currency', 'BDT')
        export_format = request.query_params.get('format', 'json')

        # Generate income statement
        service = FinancialStatementService(
            company=company,
            start_date=start_date,
            end_date=end_date,
            currency=currency
        )
        data = service.generate_income_statement()

        # Handle export formats
        if export_format == 'excel':
            return self._export_to_excel(data, 'income_statement', f'income_statement_{start_date}_to_{end_date}.xlsx')
        elif export_format == 'csv':
            return self._export_to_csv(data, 'income_statement', f'income_statement_{start_date}_to_{end_date}.csv')

        # Return JSON
        return Response({
            'success': True,
            'data': self._serialize_income_statement(data)
        })

    @action(detail=False, methods=['get'], url_path='quick-reports')
    def quick_reports(self, request):
        """
        Get quick financial reports (current month, quarter, year).

        Returns:
            Summary of key financial metrics
        """
        company = get_current_company(request)
        today = date.today()

        # Current month
        month_start = date(today.year, today.month, 1)
        month_end = today

        # Current quarter
        quarter = (today.month - 1) // 3
        quarter_start = date(today.year, quarter * 3 + 1, 1)

        # Current year
        year_start = date(today.year, 1, 1)

        # Generate reports
        month_service = FinancialStatementService(company, month_start, month_end)
        quarter_service = FinancialStatementService(company, quarter_start, month_end)
        year_service = FinancialStatementService(company, year_start, month_end)

        month_income = month_service.generate_income_statement()
        quarter_income = quarter_service.generate_income_statement()
        year_income = year_service.generate_income_statement()

        return Response({
            'success': True,
            'data': {
                'current_month': {
                    'period': {'start': month_start.isoformat(), 'end': month_end.isoformat()},
                    'revenue': str(month_income['revenue']['total']),
                    'gross_profit': str(month_income['gross_profit']),
                    'net_profit': str(month_income['net_profit']),
                },
                'current_quarter': {
                    'period': {'start': quarter_start.isoformat(), 'end': month_end.isoformat()},
                    'revenue': str(quarter_income['revenue']['total']),
                    'gross_profit': str(quarter_income['gross_profit']),
                    'net_profit': str(quarter_income['net_profit']),
                },
                'current_year': {
                    'period': {'start': year_start.isoformat(), 'end': month_end.isoformat()},
                    'revenue': str(year_income['revenue']['total']),
                    'gross_profit': str(year_income['gross_profit']),
                    'net_profit': str(year_income['net_profit']),
                }
            }
        })

    def _export_to_excel(self, data, statement_type, filename):
        """Export statement to Excel and return as download."""
        export_service = StatementExportService(data, statement_type)
        excel_buffer = export_service.export_to_excel()

        response = HttpResponse(
            excel_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def _export_to_csv(self, data, statement_type, filename):
        """Export statement to CSV and return as download."""
        export_service = StatementExportService(data, statement_type)
        csv_buffer = export_service.export_to_csv()

        response = HttpResponse(csv_buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def _serialize_balance_sheet(self, data):
        """Serialize balance sheet data for JSON response."""
        return {
            'company_name': data['company'].name,
            'as_of_date': data['as_of_date'].isoformat(),
            'currency': data['currency'],
            'assets': {
                'current': [
                    {'name': item['name'], 'amount': str(item['amount'])}
                    for item in data['assets']['current']
                ],
                'non_current': [
                    {'name': item['name'], 'amount': str(item['amount'])}
                    for item in data['assets']['non_current']
                ],
                'total_current': str(data['assets']['total_current']),
                'total_non_current': str(data['assets']['total_non_current']),
                'total': str(data['assets']['total'])
            },
            'liabilities': {
                'current': [
                    {'name': item['name'], 'amount': str(item['amount'])}
                    for item in data['liabilities']['current']
                ],
                'non_current': [
                    {'name': item['name'], 'amount': str(item['amount'])}
                    for item in data['liabilities']['non_current']
                ],
                'total_current': str(data['liabilities']['total_current']),
                'total_non_current': str(data['liabilities']['total_non_current']),
                'total': str(data['liabilities']['total'])
            },
            'equity': {
                'items': [
                    {'name': item['name'], 'amount': str(item['amount'])}
                    for item in data['equity']['items']
                ],
                'total': str(data['equity']['total'])
            },
            'total_assets': str(data['total_assets']),
            'total_liabilities_and_equity': str(data['total_liabilities_and_equity']),
            'is_balanced': data['is_balanced']
        }

    def _serialize_income_statement(self, data):
        """Serialize income statement data for JSON response."""
        return {
            'company_name': data['company'].name,
            'period': {
                'start': data['period']['start'].isoformat(),
                'end': data['period']['end'].isoformat()
            },
            'currency': data['currency'],
            'revenue': {
                'items': [
                    {'name': item['name'], 'amount': str(item['amount'])}
                    for item in data['revenue']['items']
                ],
                'total': str(data['revenue']['total'])
            },
            'cost_of_sales': str(data['cost_of_sales']),
            'gross_profit': str(data['gross_profit']),
            'gross_profit_margin': str(round(data['gross_profit_margin'], 2)),
            'operating_expenses': {
                'items': [
                    {'name': item['name'], 'amount': str(item['amount'])}
                    for item in data['operating_expenses']['items']
                ],
                'total': str(data['operating_expenses']['total'])
            },
            'operating_profit': str(data['operating_profit']),
            'operating_profit_margin': str(round(data['operating_profit_margin'], 2)),
            'finance_costs': str(data['finance_costs']),
            'profit_before_tax': str(data['profit_before_tax']),
            'tax_expense': str(data['tax_expense']),
            'net_profit': str(data['net_profit']),
            'net_profit_margin': str(round(data['net_profit_margin'], 2)),
        }
