from rest_framework import serializers
from ..models.customer import Customer
from core.id_factory import make_customer_code


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "company",
            "code",
            "name",
            "email",
            "phone",
            "mobile",
            "billing_address",
            "shipping_address",
            "credit_limit",
            "payment_terms",
            "customer_status",
            "customer_type",
            "is_active",
            "receivable_account",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company", "created_by", "created_at", "updated_at"]

    def validate(self, data):
        request = self.context.get("request")
        company = getattr(request, "company", None) if request else None
        name = data.get("name")
        if name and company:
            qs = Customer.objects.filter(company=company, name__iexact=name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("A customer with this name already exists.")
        return data

    def create(self, validated_data):
        request = self.context.get("request")
        if request:
            company = getattr(request, "company", None)
            user = getattr(request, "user", None)
            if company is not None:
                validated_data["company"] = company
            if user and "created_by" not in validated_data:
                validated_data["created_by"] = user
            # Auto-generate code if missing
            code = validated_data.get("code")
            if not code:
                validated_data["code"] = make_customer_code(company, Customer)
        return super().create(validated_data)
