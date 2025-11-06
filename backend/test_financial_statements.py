"""
Test script for financial statement endpoints.

This script tests the newly created financial statement endpoints:
- Trial Balance
- Balance Sheet
- Income Statement
- Quick Reports
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from datetime import date, timedelta
from decimal import Decimal
from apps.finance.services import TrialBalanceService, FinancialStatementService
from apps.companies.models import Company


def test_trial_balance():
    """Test trial balance generation."""
    print("\n" + "="*60)
    print("TESTING TRIAL BALANCE")
    print("="*60)

    # Get first company
    company = Company.objects.filter(is_active=True).first()
    if not company:
        print("ERROR: No active company found")
        return False

    print(f"Company: {company.name}")

    try:
        # Generate trial balance
        service = TrialBalanceService(
            company=company,
            as_of_date=date.today(),
            currency='BDT'
        )
        data = service.generate()

        print(f"As of Date: {data['as_of_date']}")
        print(f"Currency: {data['currency']}")
        print(f"Total Accounts: {len(data['accounts'])}")
        print(f"Total Debit: {data['total_debit']:,.2f}")
        print(f"Total Credit: {data['total_credit']:,.2f}")
        print(f"Difference: {data['difference']:,.2f}")
        print(f"Is Balanced: {data['is_balanced']}")

        # Show first 5 accounts
        print("\nFirst 5 Accounts:")
        for acc in data['accounts'][:5]:
            print(f"  {acc['code']} - {acc['name']}")
            print(f"    Debit: {acc['debit']:,.2f}, Credit: {acc['credit']:,.2f}, Balance: {acc['balance']:,.2f}")

        print("\n[OK] Trial Balance test passed!")
        return True

    except Exception as e:
        print(f"\n[ERROR] Trial Balance test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_balance_sheet():
    """Test balance sheet generation."""
    print("\n" + "="*60)
    print("TESTING BALANCE SHEET")
    print("="*60)

    # Get first company
    company = Company.objects.filter(is_active=True).first()
    if not company:
        print("ERROR: No active company found")
        return False

    print(f"Company: {company.name}")

    try:
        # Generate balance sheet
        today = date.today()
        start_of_year = date(today.year, 1, 1)

        service = FinancialStatementService(
            company=company,
            start_date=start_of_year,
            end_date=today,
            currency='BDT'
        )
        data = service.generate_balance_sheet()

        print(f"As of Date: {data['as_of_date']}")
        print(f"Currency: {data['currency']}")

        print("\nASSETS:")
        print(f"  Current Assets: {data['assets']['total_current']:,.2f}")
        print(f"  Non-Current Assets: {data['assets']['total_non_current']:,.2f}")
        print(f"  Total Assets: {data['total_assets']:,.2f}")

        print("\nLIABILITIES:")
        print(f"  Current Liabilities: {data['liabilities']['total_current']:,.2f}")
        print(f"  Non-Current Liabilities: {data['liabilities']['total_non_current']:,.2f}")
        print(f"  Total Liabilities: {data['liabilities']['total']:,.2f}")

        print("\nEQUITY:")
        print(f"  Total Equity: {data['equity']['total']:,.2f}")

        print(f"\nTotal Liabilities + Equity: {data['total_liabilities_and_equity']:,.2f}")
        print(f"Is Balanced: {data['is_balanced']}")

        print("\n[OK] Balance Sheet test passed!")
        return True

    except Exception as e:
        print(f"\n[ERROR] Balance Sheet test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_income_statement():
    """Test income statement generation."""
    print("\n" + "="*60)
    print("TESTING INCOME STATEMENT")
    print("="*60)

    # Get first company
    company = Company.objects.filter(is_active=True).first()
    if not company:
        print("ERROR: No active company found")
        return False

    print(f"Company: {company.name}")

    try:
        # Generate income statement for current month
        today = date.today()
        start_of_month = date(today.year, today.month, 1)

        service = FinancialStatementService(
            company=company,
            start_date=start_of_month,
            end_date=today,
            currency='BDT'
        )
        data = service.generate_income_statement()

        print(f"Period: {data['period']['start']} to {data['period']['end']}")
        print(f"Currency: {data['currency']}")

        print("\nINCOME STATEMENT:")
        print(f"  Revenue: {data['revenue']['total']:,.2f}")
        print(f"  Cost of Sales: {data['cost_of_sales']:,.2f}")
        print(f"  Gross Profit: {data['gross_profit']:,.2f} ({data['gross_profit_margin']:.2f}%)")
        print(f"  Operating Expenses: {data['operating_expenses']['total']:,.2f}")
        print(f"  Operating Profit: {data['operating_profit']:,.2f} ({data['operating_profit_margin']:.2f}%)")
        print(f"  Finance Costs: {data['finance_costs']:,.2f}")
        print(f"  Profit Before Tax: {data['profit_before_tax']:,.2f}")
        print(f"  Tax Expense: {data['tax_expense']:,.2f}")
        print(f"  Net Profit: {data['net_profit']:,.2f} ({data['net_profit_margin']:.2f}%)")

        print("\n[OK] Income Statement test passed!")
        return True

    except Exception as e:
        print(f"\n[ERROR] Income Statement test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_export_functionality():
    """Test export to dict functionality."""
    print("\n" + "="*60)
    print("TESTING EXPORT FUNCTIONALITY")
    print("="*60)

    # Get first company
    company = Company.objects.filter(is_active=True).first()
    if not company:
        print("ERROR: No active company found")
        return False

    print(f"Company: {company.name}")

    try:
        # Test trial balance export
        service = TrialBalanceService(
            company=company,
            as_of_date=date.today(),
            currency='BDT'
        )
        export_data = service.export_to_dict()

        print("Trial Balance Export:")
        print(f"  Company: {export_data['company_name']}")
        print(f"  As of Date: {export_data['as_of_date']}")
        print(f"  Currency: {export_data['currency']}")
        print(f"  Accounts: {len(export_data['accounts'])}")
        print(f"  Total Debit: {export_data['total_debit']}")
        print(f"  Total Credit: {export_data['total_credit']}")
        print(f"  Is Balanced: {export_data['is_balanced']}")

        print("\n[OK] Export functionality test passed!")
        return True

    except Exception as e:
        print(f"\n[ERROR] Export functionality test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# FINANCIAL STATEMENTS - TEST SUITE")
    print("#"*60)

    results = {
        'Trial Balance': test_trial_balance(),
        'Balance Sheet': test_balance_sheet(),
        'Income Statement': test_income_statement(),
        'Export Functionality': test_export_functionality(),
    }

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {test_name}")

    total = len(results)
    passed = sum(1 for p in results.values() if p)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
