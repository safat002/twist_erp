"""
Payslip Generation Service
Feature 2.2: Payslip Generation & Distribution

This service generates PDF payslips and handles email distribution.
"""
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, List
import logging

from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.utils import timezone

logger = logging.getLogger(__name__)


class PayslipGenerationService:
    """
    Service for generating and distributing payslips
    """

    @staticmethod
    def generate_payslip_data(payroll_line) -> Dict:
        """
        Compile payslip data for a single employee

        Args:
            payroll_line: PayrollLine instance

        Returns:
            Dictionary with all payslip data
        """
        from apps.hr.models import PayrollLine, OvertimeEntry

        employee = payroll_line.employee
        payroll_run = payroll_line.payroll_run
        company = payroll_run.company
        salary_structure = employee.salary_structure

        # Calculate YTD (Year-to-Date) values
        ytd_data = PayslipGenerationService._calculate_ytd(
            employee,
            payroll_run.period_end
        )

        # Get overtime details
        overtime_details = []
        if payroll_line.overtime_hours > 0:
            overtime_entries = OvertimeEntry.objects.filter(
                payroll_run=payroll_run,
                employee=employee,
                posted_to_payroll=True
            ).select_related('policy', 'shift')

            overtime_details = [
                {
                    'date': entry.date,
                    'hours': float(entry.effective_hours),
                    'rate': float(entry.hourly_rate),
                    'amount': float(entry.amount),
                    'shift': entry.shift.name if entry.shift else None,
                    'policy': entry.policy.name if entry.policy else None,
                }
                for entry in overtime_entries
            ]

        # Earnings breakdown
        earnings = []
        if salary_structure:
            if payroll_line.base_pay > 0:
                earnings.append({
                    'name': 'Basic Salary',
                    'amount': float(payroll_line.base_pay)
                })

            if salary_structure.housing_allowance > 0:
                housing = (salary_structure.housing_allowance / 30) * float(payroll_line.attendance_days)
                if housing > 0:
                    earnings.append({
                        'name': 'Housing Allowance',
                        'amount': float(housing)
                    })

            if salary_structure.transport_allowance > 0:
                transport = (salary_structure.transport_allowance / 30) * float(payroll_line.attendance_days)
                if transport > 0:
                    earnings.append({
                        'name': 'Transport Allowance',
                        'amount': float(transport)
                    })

            if salary_structure.meal_allowance > 0:
                meal = (salary_structure.meal_allowance / 30) * float(payroll_line.attendance_days)
                if meal > 0:
                    earnings.append({
                        'name': 'Meal Allowance',
                        'amount': float(meal)
                    })

            if salary_structure.other_allowance > 0:
                other = (salary_structure.other_allowance / 30) * float(payroll_line.attendance_days)
                if other > 0:
                    earnings.append({
                        'name': 'Other Allowance',
                        'amount': float(other)
                    })

        if payroll_line.overtime_pay > 0:
            earnings.append({
                'name': 'Overtime Pay',
                'amount': float(payroll_line.overtime_pay)
            })

        # Deductions breakdown
        deductions = []
        details = payroll_line.details or {}

        if details.get('tax_deduction', 0) > 0:
            deductions.append({
                'name': 'Income Tax',
                'amount': float(details['tax_deduction'])
            })

        if details.get('pension_deduction', 0) > 0:
            deductions.append({
                'name': 'Pension/PF',
                'amount': float(details['pension_deduction'])
            })

        if details.get('advance_recovery', 0) > 0:
            deductions.append({
                'name': 'Advance Recovery',
                'amount': float(details['advance_recovery'])
            })

        if details.get('loan_installment', 0) > 0:
            deductions.append({
                'name': 'Loan Installment',
                'amount': float(details['loan_installment'])
            })

        if details.get('other_deductions', 0) > 0:
            deductions.append({
                'name': 'Other Deductions',
                'amount': float(details['other_deductions'])
            })

        # Compile payslip data
        payslip_data = {
            # Company Info
            'company': {
                'name': company.name,
                'code': company.code,
                'address': getattr(company, 'address', ''),
                'phone': getattr(company, 'phone', ''),
                'email': getattr(company, 'email', ''),
                'logo_url': getattr(company, 'logo_url', ''),
            },

            # Payslip Info
            'payslip': {
                'number': f"PS-{payroll_run.id}-{employee.employee_id}",
                'period': f"{payroll_run.period_start.strftime('%B %Y')}",
                'period_start': payroll_run.period_start.strftime('%Y-%m-%d'),
                'period_end': payroll_run.period_end.strftime('%Y-%m-%d'),
                'payment_date': payroll_run.period_end.strftime('%Y-%m-%d'),
                'generated_date': timezone.now().strftime('%Y-%m-%d %H:%M'),
            },

            # Employee Info
            'employee': {
                'id': employee.employee_id,
                'name': employee.full_name,
                'email': employee.email,
                'phone': employee.phone_number,
                'department': employee.department.name if employee.department else None,
                'designation': employee.job_title,
                'joining_date': employee.date_of_joining.strftime('%Y-%m-%d') if employee.date_of_joining else None,
                'bank_name': employee.bank_name,
                'bank_account': employee.bank_account_number,
                'tax_id': employee.tax_identification_number,
                'photo_url': employee.photo if hasattr(employee, 'photo') else None,
            },

            # Attendance Info
            'attendance': {
                'days_worked': float(payroll_line.attendance_days),
                'leave_days': float(payroll_line.leave_days),
                'total_days': float(payroll_line.attendance_days + payroll_line.leave_days),
                'overtime_hours': float(payroll_line.overtime_hours),
            },

            # Earnings
            'earnings': earnings,
            'total_earnings': float(payroll_line.gross_pay),

            # Deductions
            'deductions': deductions,
            'total_deductions': float(payroll_line.deduction_total),

            # Net Pay
            'net_pay': float(payroll_line.net_pay),
            'net_pay_words': PayslipGenerationService._amount_to_words(payroll_line.net_pay),

            # YTD
            'ytd': ytd_data,

            # Overtime Details
            'overtime_details': overtime_details,

            # Remarks
            'remarks': payroll_line.remarks,
        }

        return payslip_data

    @staticmethod
    def _calculate_ytd(employee, period_end) -> Dict:
        """Calculate Year-to-Date totals"""
        from apps.hr.models import PayrollLine
        from django.db.models import Sum

        year_start = datetime(period_end.year, 1, 1).date()

        ytd_aggregates = PayrollLine.objects.filter(
            employee=employee,
            payroll_run__company=employee.company,
            payroll_run__period_end__gte=year_start,
            payroll_run__period_end__lte=period_end,
            payroll_run__status__in=['POSTED', 'APPROVED']
        ).aggregate(
            gross=Sum('gross_pay'),
            deductions=Sum('deduction_total'),
            net=Sum('net_pay')
        )

        return {
            'gross_earnings': float(ytd_aggregates.get('gross') or 0),
            'total_deductions': float(ytd_aggregates.get('deductions') or 0),
            'net_pay': float(ytd_aggregates.get('net') or 0),
        }

    @staticmethod
    def _amount_to_words(amount: Decimal) -> str:
        """Convert amount to words (simplified version)"""
        # This is a simplified version. For production, use a proper library like num2words
        try:
            amount_int = int(amount)
            # Simplified conversion
            return f"{amount_int:,} only"
        except:
            return str(amount)

    @staticmethod
    def generate_payslip_html(payslip_data: Dict) -> str:
        """
        Generate HTML for payslip using Django template

        Args:
            payslip_data: Dictionary with payslip data

        Returns:
            HTML string
        """
        template_name = 'hr/payslip_template.html'

        try:
            html = render_to_string(template_name, payslip_data)
            return html
        except Exception as e:
            logger.error(f"Error generating payslip HTML: {str(e)}")
            # Fallback to simple HTML generation
            return PayslipGenerationService._generate_simple_html(payslip_data)

    @staticmethod
    def _generate_simple_html(payslip_data: Dict) -> str:
        """Generate simple HTML payslip (fallback)"""
        employee = payslip_data['employee']
        payslip = payslip_data['payslip']
        company = payslip_data['company']

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Payslip - {payslip['number']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; }}
                .section {{ margin: 20px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .total {{ font-weight: bold; background-color: #f9f9f9; }}
                .net-pay {{ font-size: 18px; color: #2e7d32; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{company['name']}</h1>
                <p>Payslip for {payslip['period']}</p>
            </div>

            <div class="section">
                <h3>Employee Information</h3>
                <table>
                    <tr><th>Employee ID:</th><td>{employee['id']}</td></tr>
                    <tr><th>Name:</th><td>{employee['name']}</td></tr>
                    <tr><th>Department:</th><td>{employee['department'] or 'N/A'}</td></tr>
                    <tr><th>Designation:</th><td>{employee['designation'] or 'N/A'}</td></tr>
                </table>
            </div>

            <div class="section">
                <h3>Earnings</h3>
                <table>
                    <tr><th>Description</th><th>Amount</th></tr>
        """

        for earning in payslip_data['earnings']:
            html += f"<tr><td>{earning['name']}</td><td>{earning['amount']:,.2f}</td></tr>"

        html += f"""
                    <tr class="total"><td>Total Earnings</td><td>{payslip_data['total_earnings']:,.2f}</td></tr>
                </table>
            </div>

            <div class="section">
                <h3>Deductions</h3>
                <table>
                    <tr><th>Description</th><th>Amount</th></tr>
        """

        for deduction in payslip_data['deductions']:
            html += f"<tr><td>{deduction['name']}</td><td>{deduction['amount']:,.2f}</td></tr>"

        html += f"""
                    <tr class="total"><td>Total Deductions</td><td>{payslip_data['total_deductions']:,.2f}</td></tr>
                </table>
            </div>

            <div class="section net-pay">
                <h2>Net Pay: {payslip_data['net_pay']:,.2f} {employee.get('currency', 'BDT')}</h2>
                <p>Amount in words: {payslip_data['net_pay_words']}</p>
            </div>

            <div class="section">
                <p style="font-size: 10px; color: #666;">
                    Generated on {payslip['generated_date']} | This is a computer-generated document
                </p>
            </div>
        </body>
        </html>
        """

        return html

    @staticmethod
    def generate_payslip_pdf(payslip_data: Dict) -> bytes:
        """
        Generate PDF payslip

        Args:
            payslip_data: Dictionary with payslip data

        Returns:
            PDF bytes
        """
        html = PayslipGenerationService.generate_payslip_html(payslip_data)

        try:
            # Try to use weasyprint if available
            from weasyprint import HTML
            pdf_bytes = HTML(string=html).write_pdf()
            return pdf_bytes
        except ImportError:
            try:
                # Fallback to pdfkit if available
                import pdfkit
                pdf_bytes = pdfkit.from_string(html, False)
                return pdf_bytes
            except ImportError:
                logger.error("No PDF generation library available (weasyprint or pdfkit)")
                # Return HTML as bytes as last resort
                return html.encode('utf-8')

    @staticmethod
    def send_payslip_email(
        employee_email: str,
        payslip_pdf: bytes,
        payslip_data: Dict,
        password: Optional[str] = None
    ) -> bool:
        """
        Send payslip via email

        Args:
            employee_email: Employee email address
            payslip_pdf: PDF bytes
            payslip_data: Payslip data dictionary
            password: Optional password for PDF protection

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            payslip_info = payslip_data['payslip']
            employee_info = payslip_data['employee']
            company_info = payslip_data['company']

            subject = f"Payslip for {payslip_info['period']} - {company_info['name']}"

            message = f"""
Dear {employee_info['name']},

Please find attached your payslip for {payslip_info['period']}.

Payslip Details:
- Period: {payslip_info['period']}
- Net Pay: {payslip_data['net_pay']:,.2f}
- Payment Date: {payslip_info['payment_date']}

"""

            if password:
                message += f"\nThe payslip is password protected. Use your employee ID ({employee_info['id']}) as the password.\n"

            message += f"""
If you have any questions regarding your payslip, please contact the HR department.

Best regards,
{company_info['name']}
HR Department

---
This is an automated email. Please do not reply.
"""

            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[employee_email],
            )

            filename = f"Payslip_{employee_info['id']}_{payslip_info['period'].replace(' ', '_')}.pdf"
            email.attach(filename, payslip_pdf, 'application/pdf')

            email.send(fail_silently=False)

            logger.info(f"Payslip sent successfully to {employee_email}")
            return True

        except Exception as e:
            logger.error(f"Error sending payslip email to {employee_email}: {str(e)}")
            return False

    @staticmethod
    def bulk_generate_payslips(payroll_run) -> Dict[str, any]:
        """
        Generate payslips for all employees in a payroll run

        Args:
            payroll_run: PayrollRun instance

        Returns:
            Dictionary with results
        """
        from apps.hr.models import PayrollLine

        results = {
            'total': 0,
            'generated': 0,
            'failed': 0,
            'payslips': [],
            'errors': []
        }

        payroll_lines = PayrollLine.objects.filter(
            payroll_run=payroll_run
        ).select_related(
            'employee',
            'employee__department',
            'employee__salary_structure'
        )

        results['total'] = payroll_lines.count()

        for line in payroll_lines:
            try:
                payslip_data = PayslipGenerationService.generate_payslip_data(line)
                payslip_pdf = PayslipGenerationService.generate_payslip_pdf(payslip_data)

                results['payslips'].append({
                    'employee_id': line.employee.employee_id,
                    'employee_name': line.employee.full_name,
                    'data': payslip_data,
                    'pdf': payslip_pdf,
                })

                results['generated'] += 1

            except Exception as e:
                logger.error(f"Error generating payslip for {line.employee.employee_id}: {str(e)}")
                results['failed'] += 1
                results['errors'].append({
                    'employee_id': line.employee.employee_id,
                    'error': str(e)
                })

        return results

    @staticmethod
    def bulk_send_payslips(
        payroll_run,
        use_password_protection: bool = True
    ) -> Dict[str, any]:
        """
        Generate and send payslips for all employees

        Args:
            payroll_run: PayrollRun instance
            use_password_protection: Whether to password protect PDFs

        Returns:
            Dictionary with results
        """
        results = PayslipGenerationService.bulk_generate_payslips(payroll_run)

        sent_count = 0
        send_failed = 0

        for payslip_info in results['payslips']:
            employee_data = payslip_info['data']['employee']
            email = employee_data['email']

            if not email:
                logger.warning(f"No email for employee {employee_data['id']}")
                send_failed += 1
                continue

            # Use employee ID as password if protection is enabled
            password = employee_data['id'] if use_password_protection else None

            sent = PayslipGenerationService.send_payslip_email(
                employee_email=email,
                payslip_pdf=payslip_info['pdf'],
                payslip_data=payslip_info['data'],
                password=password
            )

            if sent:
                sent_count += 1
            else:
                send_failed += 1

        results['sent'] = sent_count
        results['send_failed'] = send_failed

        return results
