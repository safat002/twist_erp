"""
Serializers for financial statements.
"""
from rest_framework import serializers
from datetime import date


class TrialBalanceRequestSerializer(serializers.Serializer):
    """Serializer for trial balance request parameters."""
    as_of_date = serializers.DateField(required=False, help_text="Date to generate trial balance as of")
    currency = serializers.CharField(required=False, default='BDT', max_length=3)


class BalanceSheetRequestSerializer(serializers.Serializer):
    """Serializer for balance sheet request parameters."""
    as_of_date = serializers.DateField(required=False, help_text="Date to generate balance sheet as of")
    currency = serializers.CharField(required=False, default='BDT', max_length=3)
    comparative = serializers.BooleanField(required=False, default=False)


class IncomeStatementRequestSerializer(serializers.Serializer):
    """Serializer for income statement request parameters."""
    start_date = serializers.DateField(required=True, help_text="Start date of the period")
    end_date = serializers.DateField(required=True, help_text="End date of the period")
    currency = serializers.CharField(required=False, default='BDT', max_length=3)
    comparative = serializers.BooleanField(required=False, default=False)

    def validate(self, data):
        """Validate that start_date is before end_date."""
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError({
                'start_date': 'Start date must be before end date.'
            })
        return data


class ExportFormatSerializer(serializers.Serializer):
    """Serializer for export format selection."""
    format = serializers.ChoiceField(
        choices=['excel', 'csv', 'pdf'],
        required=False,
        default='excel',
        help_text="Export format"
    )
