from rest_framework import serializers
from ..models.sales_order import SalesOrder


class SalesOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrder
        fields = [
            "id",
            "company",
            "created_by",
            "created_at",
            "updated_at",
            "order_number",
            "order_date",
            "delivery_date",
            "shipping_address",
            "subtotal",
            "tax_amount",
            "discount_amount",
            "total_amount",
            "status",
            "notes",
            "customer",
        ]
        read_only_fields = ["order_number", "created_at", "updated_at"]
