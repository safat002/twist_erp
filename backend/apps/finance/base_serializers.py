from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Iterable, List

from django.db import transaction
from rest_framework import serializers

from apps.companies.models import Company
from apps.procurement.models import Supplier
from apps.sales.models import Customer

from .models import (
    Account,
    BankStatement,
    BankStatementLine,
    FiscalPeriod,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Journal,
    JournalEntry,
    JournalStatus,
    JournalVoucher,
    Payment,
    PaymentAllocation,
    Currency,
)
from .services.journal_service import JournalService

TWOPLACES = Decimal("0.01")


def _require_company(context: Dict[str, Any]) -> Company:
    request = context.get("request")
    company = getattr(request, "company", None)
    if company is None and request is not None:
        company_id = request.META.get("HTTP_X_COMPANY_ID")
        if company_id:
            try:
                company = Company.objects.get(pk=company_id)
            except Company.DoesNotExist as exc:
                raise serializers.ValidationError("Active company context is required for finance operations.") from exc
    if company is None:
        raise serializers.ValidationError("Active company context is required for finance operations.")
    return company


class AccountSerializer(serializers.ModelSerializer):
    parent_account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(),
        allow_null=True,
        required=False,
    )
    parent_account_display = serializers.SerializerMethodField()
    children_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Account
        fields = [
            "id",
            "code",
            "name",
            "account_type",
            "currency",
            "is_active",
            "is_bank_account",
            "is_control_account",
            "is_grni_account",
            "allow_direct_posting",
            "current_balance",
            "parent_account",
            "parent_account_display",
            "children_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "current_balance",
            "created_at",
            "updated_at",
            "children_count",
            "parent_account_display",
        ]

    def get_parent_account_display(self, obj: Account) -> Dict[str, Any] | None:
        if not obj.parent_account_id:
            return None
        parent = obj.parent_account
        return {"id": parent.id, "code": parent.code, "name": parent.name}

    def validate_parent_account(self, parent: Account | None) -> Account | None:
        if parent:
            company = _require_company(self.context)
            if parent.company_id != company.id:
                raise serializers.ValidationError("Parent account must belong to the active company.")
        return parent

    def create(self, validated_data: Dict[str, Any]) -> Account:
        request = self.context["request"]
        company = _require_company(self.context)
        validated_data.setdefault("created_by", request.user)
        validated_data["company"] = company
        validated_data["company_group"] = company.company_group
        return Account.objects.create(**validated_data)

    def update(self, instance: Account, validated_data: Dict[str, Any]) -> Account:
        parent = validated_data.get("parent_account")
        if parent and parent.company_id != instance.company_id:
            raise serializers.ValidationError("Parent account must belong to the same company.")
        return super().update(instance, validated_data)


class JournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Journal
        fields = ["id", "code", "name", "type", "is_active"]


class JournalEntrySerializer(serializers.ModelSerializer):
    account_detail = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = [
            "id",
            "line_number",
            "account",
            "account_detail",
            "debit_amount",
            "credit_amount",
            "description",
        ]

    def get_account_detail(self, obj: JournalEntry) -> Dict[str, Any]:
        return {
            "id": obj.account_id,
            "code": obj.account.code,
            "name": obj.account.name,
            "type": obj.account.account_type,
        }


class JournalVoucherSerializer(serializers.ModelSerializer):
    entries = JournalEntrySerializer(many=True)
    journal_name = serializers.CharField(source="journal.name", read_only=True)
    total_debit = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    total_credit = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)

    class Meta:
        model = JournalVoucher
        fields = [
            "id",
            "voucher_number",
            "journal",
            "journal_name",
            "entry_date",
            "period",
            "reference",
            "description",
            "status",
            "source_document_type",
            "source_document_id",
            "posted_at",
            "posted_by",
            "sequence_number",
            "entries",
            "total_debit",
            "total_credit",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "voucher_number",
            "period",
            "posted_at",
            "posted_by",
            "sequence_number",
            "total_debit",
            "total_credit",
            "created_at",
            "updated_at",
        ]

    def validate_entries(self, value: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
        if not value:
            raise serializers.ValidationError("At least one entry line is required.")
        return value


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = [
            "id",
            "code",
            "name",
            "symbol",
            "decimal_places",
            "is_active",
            "is_base_currency",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        company = _require_company(self.context)
        instance = Currency.objects.create(company=company, **validated_data)
        if instance.is_base_currency:
            Currency.objects.filter(company=company).exclude(pk=instance.pk).update(is_base_currency=False)
        return instance

    def update(self, instance, validated_data):
        was_base = instance.is_base_currency
        instance = super().update(instance, validated_data)
        if instance.is_base_currency and not was_base:
            Currency.objects.filter(company=instance.company).exclude(pk=instance.pk).update(is_base_currency=False)
        return instance

    def _build_entries_payload(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        payload: List[Dict[str, Any]] = []
        for idx, entry in enumerate(entries, start=1):
            account = entry["account"]
            company = _require_company(self.context)
            if account.company_id != company.id:
                raise serializers.ValidationError(f"Account {account.code} does not belong to the active company.")
            payload.append(
                {
                    "account": account,
                    "debit": entry.get("debit_amount", 0),
                    "credit": entry.get("credit_amount", 0),
                    "description": entry.get("description", ""),
                    "line_number": idx,
                }
            )
        return payload

    def create(self, validated_data: Dict[str, Any]) -> JournalVoucher:
        entries_data = validated_data.pop("entries")
        request = self.context["request"]
        company = _require_company(self.context)
        payload = self._build_entries_payload(entries_data)
        voucher = JournalService.create_journal_voucher(
            journal=validated_data["journal"],
            entry_date=validated_data["entry_date"],
            description=validated_data.get("description", ""),
            entries_data=payload,
            reference=validated_data.get("reference", ""),
            source_document_type=validated_data.get("source_document_type", ""),
            source_document_id=validated_data.get("source_document_id"),
            company=company,
            created_by=request.user,
        )
        desired_status = validated_data.get("status")
        if desired_status == JournalStatus.POSTED:
            JournalService.post_journal_voucher(voucher, request.user)
        log_audit_event(
            user=request.user,
            company=company,
            company_group=company.company_group,
            action="JOURNAL_CREATED",
            entity_type="JournalVoucher",
            entity_id=voucher.pk,
            description=f"Journal voucher {voucher.voucher_number} created.",
        )
        return voucher

    def update(self, instance: JournalVoucher, validated_data: Dict[str, Any]) -> JournalVoucher:
        if instance.status != JournalStatus.DRAFT:
            raise serializers.ValidationError("Only draft vouchers can be edited.")

        entries_data = validated_data.pop("entries", None)
        for attr in ["reference", "description", "entry_date", "source_document_type", "source_document_id", "journal"]:
            if attr in validated_data:
                setattr(instance, attr, validated_data[attr])
        instance.period = instance.entry_date.strftime("%Y-%m")
        instance.save()

        if entries_data is not None:
            instance.entries.all().delete()
            payload = self._build_entries_payload(entries_data)
            JournalEntry.objects.bulk_create(
                [
                    JournalEntry(
                        voucher=instance,
                        line_number=item["line_number"],
                        account=item["account"],
                        debit_amount=item["debit"],
                        credit_amount=item["credit"],
                        description=item["description"],
                    )
                    for item in payload
                ]
            )

        desired_status = validated_data.get("status")
        if desired_status == JournalStatus.POSTED and instance.status == JournalStatus.DRAFT:
            JournalService.post_journal_voucher(instance, self.context["request"].user)
        return instance


class InvoiceLineSerializer(serializers.ModelSerializer):
    account_detail = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceLine
        fields = [
            "id",
            "line_number",
            "description",
            "quantity",
            "unit_price",
            "tax_rate",
            "discount_percent",
            "line_total",
            "product_id",
            "account",
            "account_detail",
        ]
        read_only_fields = ["line_number", "line_total", "account_detail"]

    def validate_account(self, account: Account) -> Account:
        company = _require_company(self.context)
        if account.company_id != company.id:
            raise serializers.ValidationError("Account must belong to the active company.")
        return account

    def get_account_detail(self, obj: InvoiceLine) -> Dict[str, Any]:
        return {"id": obj.account_id, "code": obj.account.code, "name": obj.account.name}


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True)
    partner_name = serializers.SerializerMethodField()
    balance_due = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "invoice_type",
            "partner_type",
            "partner_id",
            "partner_name",
            "invoice_date",
            "due_date",
            "subtotal",
            "tax_amount",
            "discount_amount",
            "total_amount",
            "paid_amount",
            "balance_due",
            "currency",
            "exchange_rate",
            "status",
            "status_display",
            "notes",
            "journal_voucher",
            "lines",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "invoice_number",
            "subtotal",
            "tax_amount",
            "discount_amount",
            "total_amount",
            "paid_amount",
            "balance_due",
            "journal_voucher",
            "status_display",
            "is_overdue",
            "created_at",
            "updated_at",
        ]

    def get_partner_name(self, obj: Invoice) -> str:
        partner_map = self.context.get("partner_map", {})
        return partner_map.get((obj.partner_type, obj.partner_id), "")

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        invoice_date = attrs.get("invoice_date", getattr(self.instance, "invoice_date", None))
        due_date = attrs.get("due_date", getattr(self.instance, "due_date", None))
        if invoice_date and due_date and due_date < invoice_date:
            raise serializers.ValidationError("Due date cannot be earlier than invoice date.")
        return attrs

    def _write_lines(self, invoice: Invoice, lines_data: List[Dict[str, Any]]) -> None:
        if not lines_data:
            raise serializers.ValidationError("Invoice requires at least one line.")

        invoice.lines.all().delete()

        discount_total = Decimal("0.00")
        tax_total = Decimal("0.00")
        line_instances: List[InvoiceLine] = []

        for index, line in enumerate(lines_data, start=1):
            account: Account = line["account"]
            company = invoice.company
            if account.company_id != company.id:
                raise serializers.ValidationError("Line account must belong to the active company.")

            quantity = Decimal(line.get("quantity") or 0)
            unit_price = Decimal(line.get("unit_price") or 0)
            base = quantity * unit_price
            discount_percent = Decimal(line.get("discount_percent") or 0)
            discount_value = (base * discount_percent / Decimal("100")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
            net = base - discount_value

            tax_rate = Decimal(line.get("tax_rate") or 0)
            tax_value = (net * tax_rate / Decimal("100")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
            line_total = (net + tax_value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

            discount_total += discount_value
            tax_total += tax_value

            line_instances.append(
                InvoiceLine(
                    invoice=invoice,
                    line_number=index,
                    description=line.get("description", ""),
                    quantity=quantity,
                    unit_price=unit_price,
                    tax_rate=tax_rate,
                    discount_percent=discount_percent,
                    line_total=line_total,
                    product_id=line.get("product_id"),
                    account=account,
                )
            )

        InvoiceLine.objects.bulk_create(line_instances)
        invoice.discount_amount = discount_total.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        invoice.tax_amount = tax_total.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        invoice.recalculate_totals(commit=True)

    def create(self, validated_data: Dict[str, Any]) -> Invoice:
        lines_data = validated_data.pop("lines", [])
        company = _require_company(self.context)
        request = self.context["request"]

        validated_data.setdefault("subtotal", Decimal("0.00"))
        validated_data.setdefault("tax_amount", Decimal("0.00"))
        validated_data.setdefault("discount_amount", Decimal("0.00"))
        validated_data.setdefault("total_amount", Decimal("0.00"))
        validated_data.setdefault("paid_amount", Decimal("0.00"))

        validated_data["company"] = company
        validated_data["company_group"] = company.company_group
        validated_data["created_by"] = request.user

        with transaction.atomic():
            invoice = Invoice.objects.create(**validated_data)
            self._write_lines(invoice, lines_data)
        return invoice

    def update(self, instance: Invoice, validated_data: Dict[str, Any]) -> Invoice:
        if instance.status not in {InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED}:
            raise serializers.ValidationError("Only draft or cancelled invoices can be edited.")

        lines_data = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if instance.subtotal is None:
            instance.subtotal = Decimal("0.00")
        if instance.tax_amount is None:
            instance.tax_amount = Decimal("0.00")
        if instance.discount_amount is None:
            instance.discount_amount = Decimal("0.00")
        if instance.total_amount is None:
            instance.total_amount = Decimal("0.00")
        if instance.paid_amount is None:
            instance.paid_amount = Decimal("0.00")
        instance.save()

        if lines_data is not None:
            self._write_lines(instance, lines_data)

        instance.refresh_payment_status(commit=True)
        return instance


class PaymentAllocationSerializer(serializers.ModelSerializer):
    invoice_detail = serializers.SerializerMethodField()

    class Meta:
        model = PaymentAllocation
        fields = ["id", "invoice", "allocated_amount", "invoice_detail"]

    def validate_invoice(self, invoice: Invoice) -> Invoice:
        company = _require_company(self.context)
        if invoice.company_id != company.id:
            raise serializers.ValidationError("Invoice must belong to the active company.")
        return invoice

    def get_invoice_detail(self, obj: PaymentAllocation) -> Dict[str, Any]:
        return {
            "id": obj.invoice_id,
            "invoice_number": obj.invoice.invoice_number,
            "type": obj.invoice.invoice_type,
            "balance_due": str(obj.invoice.balance_due),
        }


class PaymentSerializer(serializers.ModelSerializer):
    allocations = PaymentAllocationSerializer(many=True, required=False)
    partner_name = serializers.SerializerMethodField()
    remaining_amount = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "payment_number",
            "payment_date",
            "payment_type",
            "payment_method",
            "amount",
            "currency",
            "partner_type",
            "partner_id",
            "partner_name",
            "reference",
            "notes",
            "status",
            "status_display",
            "bank_account",
            "journal_voucher",
            "allocations",
            "remaining_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "payment_number",
            "journal_voucher",
            "status_display",
            "remaining_amount",
            "created_at",
            "updated_at",
        ]

    def get_partner_name(self, obj: Payment) -> str:
        partner_map = self.context.get("partner_map", {})
        return partner_map.get((obj.partner_type, obj.partner_id), "")


class FiscalPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiscalPeriod
        fields = [
            "id",
            "period",
            "status",
            "locked_by",
            "locked_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["locked_by", "locked_at", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context["request"]
        company = _require_company(self.context)
        validated_data["company"] = company
        validated_data["company_group"] = company.company_group
        return FiscalPeriod.objects.create(**validated_data)


class BankStatementLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankStatementLine
        fields = [
            "id",
            "line_date",
            "description",
            "reference",
            "amount",
            "balance",
            "match_status",
            "matched_payment",
            "matched_voucher",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class BankStatementSerializer(serializers.ModelSerializer):
    lines = BankStatementLineSerializer(many=True, required=False)

    class Meta:
        model = BankStatement
        fields = [
            "id",
            "bank_account",
            "statement_date",
            "opening_balance",
            "closing_balance",
            "currency",
            "status",
            "imported_filename",
            "created_at",
            "updated_at",
            "lines",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        company = _require_company(self.context)
        request = self.context["request"]
        validated_data["company"] = company
        validated_data["company_group"] = company.company_group
        validated_data["created_by"] = request.user
        stmt = BankStatement.objects.create(**validated_data)
        for idx, line in enumerate(lines):
            BankStatementLine.objects.create(statement=stmt, **line)
        return stmt

    def _validate_partner(self, payment_type: str, partner_type: str) -> None:
        valid = {"RECEIPT": "customer", "PAYMENT": "supplier"}
        expected = valid.get(payment_type)
        if expected and partner_type.lower() != expected:
            raise serializers.ValidationError(f"Partner type must be '{expected}' for this payment type.")

    def _sync_allocations(self, payment: Payment, allocations_data: List[Dict[str, Any]]) -> None:
        total_allocated = Decimal("0.00")
        PaymentAllocation.objects.filter(payment=payment).delete()

        allocation_instances: List[PaymentAllocation] = []
        for allocation in allocations_data:
            invoice: Invoice = allocation["invoice"]
            amount = Decimal(allocation["allocated_amount"])
            if amount <= 0:
                raise serializers.ValidationError("Allocated amount must be positive.")

            if payment.payment_type == "RECEIPT" and invoice.invoice_type != "AR":
                raise serializers.ValidationError("Customer receipts can only allocate to AR invoices.")
            if payment.payment_type == "PAYMENT" and invoice.invoice_type != "AP":
                raise serializers.ValidationError("Supplier payments can only allocate to AP invoices.")

            total_allocated += amount
            allocation_instances.append(
                PaymentAllocation(payment=payment, invoice=invoice, allocated_amount=amount.quantize(TWOPLACES))
            )

        if total_allocated > Decimal(payment.amount):
            raise serializers.ValidationError("Allocated amount exceeds payment amount.")

        PaymentAllocation.objects.bulk_create(allocation_instances)

    def create(self, validated_data: Dict[str, Any]) -> Payment:
        allocations_data = validated_data.pop("allocations", [])
        request = self.context["request"]
        company = _require_company(self.context)

        payment_type = validated_data.get("payment_type")
        partner_type = validated_data.get("partner_type", "")
        self._validate_partner(payment_type, partner_type)

        validated_data["company"] = company
        validated_data["company_group"] = company.company_group
        validated_data["created_by"] = request.user

        with transaction.atomic():
            payment = Payment.objects.create(**validated_data)
            if allocations_data:
                self._sync_allocations(payment, allocations_data)
        return payment

    def update(self, instance: Payment, validated_data: Dict[str, Any]) -> Payment:
        if instance.status != "DRAFT":
            raise serializers.ValidationError("Only draft payments can be edited.")

        allocations_data = validated_data.pop("allocations", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if allocations_data is not None:
            self._sync_allocations(instance, allocations_data)
        return instance
