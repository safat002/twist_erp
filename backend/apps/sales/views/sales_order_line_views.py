from rest_framework import viewsets
from ..models.sales_order_line import SalesOrderLine
from ..serializers.sales_order_line_serializers import SalesOrderLineSerializer

class SalesOrderLineViewSet(viewsets.ModelViewSet):
    queryset = SalesOrderLine.objects.all()
    serializer_class = SalesOrderLineSerializer
