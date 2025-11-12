from rest_framework import serializers

from ..models import InventoryPostingRule


class InventoryPostingRuleSerializer(serializers.ModelSerializer):
    inventory_account_code = serializers.CharField(source='inventory_account.code', read_only=True)
    inventory_account_name = serializers.CharField(source='inventory_account.name', read_only=True)
    cogs_account_code = serializers.CharField(source='cogs_account.code', read_only=True)
    cogs_account_name = serializers.CharField(source='cogs_account.name', read_only=True)
    budget_item_code = serializers.CharField(source='budget_item.code', read_only=True)
    budget_item_name = serializers.CharField(source='budget_item.name', read_only=True)
    item_code = serializers.CharField(source='item.code', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)

    class Meta:
        model = InventoryPostingRule
        fields = '__all__'
        read_only_fields = ['company', 'created_at', 'updated_at']

    def validate(self, attrs):
        budget_item = attrs.get('budget_item') or getattr(self.instance, 'budget_item', None)
        item = attrs.get('item') or getattr(self.instance, 'item', None)
        if budget_item and item:
            raise serializers.ValidationError({'item': 'Specify either budget_item or item, not both.'})
        return super().validate(attrs)

    def create(self, validated_data):
        request = self.context.get('request')
        company = getattr(request, 'company', None)
        if not company:
            raise serializers.ValidationError({'detail': 'Active company context is required'})
        validated_data['company'] = company
        return super().create(validated_data)

