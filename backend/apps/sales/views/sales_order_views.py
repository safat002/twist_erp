from rest_framework import viewsets
from ..models.sales_order import SalesOrder
from ..serializers.sales_order_serializers import SalesOrderSerializer

class SalesOrderViewSet(viewsets.ModelViewSet):
    queryset = SalesOrder.objects.all()
    serializer_class = SalesOrderSerializer
