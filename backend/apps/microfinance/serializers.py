from __future__ import annotations

from rest_framework import serializers

from core.id_factory import IDFactory
from .models import Borrower, LoanProduct, Loan, LoanRepayment, LoanRepaymentSchedule


class BorrowerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrower
        fields = ['id', 'company', 'code', 'name', 'mobile', 'nid', 'address', 'group_name']
        read_only_fields = ['company', 'code']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['company'] = getattr(request, 'company', None)
        return super().create(validated_data)


class LoanProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanProduct
        fields = ['id', 'company', 'code', 'name', 'interest_rate_annual', 'term_months', 'repayment_frequency', 'portfolio_account', 'interest_income_account', 'cash_account']
        read_only_fields = ['company', 'code']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['company'] = getattr(request, 'company', None)
        return super().create(validated_data)


class LoanRepaymentScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRepaymentSchedule
        fields = ['id', 'loan', 'installment_number', 'due_date', 'principal_due', 'interest_due', 'total_due', 'paid_amount', 'status']
        read_only_fields = ['loan']


class LoanSerializer(serializers.ModelSerializer):
    borrower_name = serializers.ReadOnlyField(source='borrower.name')
    product_name = serializers.ReadOnlyField(source='product.name')
    schedule = LoanRepaymentScheduleSerializer(many=True, read_only=True)

    class Meta:
        model = Loan
        fields = [
            'id', 'company', 'borrower', 'borrower_name', 'product', 'product_name', 'number', 'principal',
            'interest_rate_annual', 'term_months', 'repayment_frequency', 'disburse_date', 'status',
            'outstanding_amount', 'created_by', 'created_at', 'updated_at', 'schedule'
        ]
        read_only_fields = ['company', 'number', 'status', 'outstanding_amount', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['company'] = getattr(request, 'company', None)
        if request and request.user and 'created_by' not in validated_data:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class LoanRepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRepayment
        fields = ['id', 'loan', 'schedule', 'payment_date', 'amount', 'receipt_number', 'principal_component', 'interest_component']
        read_only_fields = ['receipt_number']
