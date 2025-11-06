from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from ..models.customer import Customer
from ..serializers.customer_serializers import CustomerSerializer


class CompanyScopedQuerysetMixin:
    permission_classes = [IsAuthenticated]

    def get_company(self):
        return getattr(self.request, "company", None)

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset()
        company = self.get_company()
        if company:
            qs = qs.filter(company=company)
        return qs

    def get_serializer_context(self):  # type: ignore[override]
        ctx = super().get_serializer_context()
        ctx.setdefault("request", self.request)
        return ctx


class CustomerViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
