from rest_framework import viewsets
from .models import Customer, SalesOrder, SalesOrderLine
from .serializers import CustomerSerializer, SalesOrderSerializer, SalesOrderLineSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

class SalesOrderViewSet(viewsets.ModelViewSet):
    queryset = SalesOrder.objects.all()
    serializer_class = SalesOrderSerializer

class SalesOrderLineViewSet(viewsets.ModelViewSet):
    queryset = SalesOrderLine.objects.all()
    serializer_class = SalesOrderLineSerializer