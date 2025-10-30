from rest_framework import serializers
from .models import Customer, SalesOrder, SalesOrderLine

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class SalesOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrder
        fields = '__all__'

class SalesOrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrderLine
        fields = '__all__'