from rest_framework import serializers
from ..models.sales_order import SalesOrder

class SalesOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrder
        fields = '__all__'
