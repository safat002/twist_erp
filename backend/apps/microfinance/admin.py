from django.contrib import admin
from .models import Borrower, LoanProduct, Loan, LoanRepayment, LoanRepaymentSchedule


@admin.register(Borrower)
class BorrowerAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "mobile", "group_name", "company")
    search_fields = ("code", "name", "mobile", "group_name")
    list_filter = ("company",)


@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "interest_rate_annual", "term_months", "repayment_frequency", "company")
    list_filter = ("company", "repayment_frequency")
    search_fields = ("code", "name")


class LoanRepaymentInline(admin.TabularInline):
    model = LoanRepayment
    extra = 0


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("number", "borrower", "product", "principal", "status", "company")
    list_filter = ("company", "status", "product")
    search_fields = ("number", "borrower__name")
    inlines = [LoanRepaymentInline]


@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "loan", "payment_date", "amount", "principal_component", "interest_component")
    list_filter = ("payment_date",)
    search_fields = ("receipt_number",)


@admin.register(LoanRepaymentSchedule)
class LoanRepaymentScheduleAdmin(admin.ModelAdmin):
    list_display = ("loan", "installment_number", "due_date", "principal_due", "interest_due", "total_due", "paid_amount", "status")
    list_filter = ("status",)

