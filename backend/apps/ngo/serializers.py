from __future__ import annotations

from rest_framework import serializers

from core.id_factory import IDFactory
from .models import Donor, Program, ComplianceRequirement, ComplianceSubmission


class DonorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donor
        fields = ['id', 'company', 'code', 'name', 'email', 'phone', 'address', 'website']
        read_only_fields = ['company']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['company'] = getattr(request, 'company', None)
        if not validated_data.get('code'):
            validated_data['code'] = IDFactory.make_master_code('DNR', validated_data['company'], Donor, width=4)
        return super().create(validated_data)


class ProgramSerializer(serializers.ModelSerializer):
    donor_name = serializers.ReadOnlyField(source='donor.name')

    class Meta:
        model = Program
        fields = [
            'id', 'company', 'donor', 'donor_name', 'code', 'title', 'status', 'start_date', 'end_date',
            'total_budget', 'currency', 'objectives', 'tags', 'compliance_score', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['company', 'created_by', 'code', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['company'] = getattr(request, 'company', None)
        if request and request.user and 'created_by' not in validated_data:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class ComplianceRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceRequirement
        fields = ['id', 'program', 'code', 'name', 'description', 'frequency', 'next_due_date', 'status']


class ComplianceSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceSubmission
        fields = ['id', 'requirement', 'period_start', 'period_end', 'submitted_at', 'status', 'notes', 'file']
        read_only_fields = ['submitted_at']

