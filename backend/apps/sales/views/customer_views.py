from rest_framework import viewsets
from ..models.customer import Customer
from ..serializers.customer_serializers import CustomerSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
