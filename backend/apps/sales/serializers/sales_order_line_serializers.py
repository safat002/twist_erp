from rest_framework import serializers
from ..models.sales_order_line import SalesOrderLine

class SalesOrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrderLine
        fields = '__all__'
