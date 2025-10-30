from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Dict, Iterable, List, Tuple

from django.db.models import Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.utils import log_audit_event
from apps.procurement.models import Supplier
from apps.sales.models import Customer

from .models import (
    Account,
    AccountType,
    Invoice,
    InvoiceStatus,
    Journal,
    JournalEntry,
    JournalStatus,
    JournalVoucher,
    Payment,
)
from .serializers import (
    AccountSerializer,
    InvoiceSerializer,
    JournalSerializer,
    JournalVoucherSerializer,
    PaymentSerializer,
)
from .services.invoice_service import InvoiceService
from .services.journal_service import JournalService


class CompanyScopedMixin:
    permission_classes = [IsAuthenticated]

    def get_company(self, *, required: bool = False):
        company = getattr(self.request, "company", None)
        if company is None:
            company_id = self.request.META.get("HTTP_X_COMPANY_ID")
            if company_id:
                from apps.companies.models import Company  # local import to avoid circular

                try:
                    company = Company.objects.get(pk=company_id)
                    setattr(self.request, "company", company)
                except Company.DoesNotExist:
                    company = None
        if company is None and required:
            raise ValidationError("Active company context is required for this operation.")
        return company

    def get_queryset(self):  # type: ignore[override]
        queryset = super().get_queryset()
        company = self.get_company()
        if company:
            return queryset.filter(company=company)
        return queryset.none()

    def get_serializer_context(self):  # type: ignore[override]
        context = super().get_serializer_context()
        context.setdefault("request", self.request)
        return context


class AccountViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = Account.objects.select_related("parent_account")
    serializer_class = AccountSerializer

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        company = self.get_company()
        if not company:
            return Response({"results": [], "summary": {"total": 0, "balances": {}}})
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        summary = {
            "total": queryset.count(),
            "balances": {
                choice: float(
                    queryset.filter(account_type=choice).aggregate(total=Sum("current_balance")).get("total")
                    or 0
                )
                for choice, _ in AccountType.choices
            },
        }
        return Response({"results": serializer.data, "summary": summary})

    def perform_create(self, serializer):  # type: ignore[override]
        account = serializer.save()
        company = self.get_company(required=True)
        log_audit_event(
            user=self.request.user,
            company=company,
            company_group=company.company_group,
            action="ACCOUNT_CREATED",
            entity_type="Account",
            entity_id=account.pk,
            description=f"Chart of accounts entry {account.code} created.",
        )

    def perform_update(self, serializer):  # type: ignore[override]
        account = serializer.save()
        company = self.get_company(required=True)
        log_audit_event(
            user=self.request.user,
            company=company,
            company_group=company.company_group,
            action="ACCOUNT_UPDATED",
            entity_type="Account",
            entity_id=account.pk,
            description=f"Chart of accounts entry {account.code} updated.",
        )

    def destroy(self, request, *args, **kwargs):  # type: ignore[override]
        instance = self.get_object()
        if instance.sub_accounts.exists():
            return Response({"detail": "Cannot delete an account that has child accounts."}, status=400)
        if JournalEntry.objects.filter(account=instance).exists():
            return Response({"detail": "Cannot delete an account referenced by journal entries."}, status=400)
        response = super().destroy(request, *args, **kwargs)
        company = self.get_company()
        if company:
            log_audit_event(
                user=request.user,
                company=company,
                company_group=company.company_group,
                action="ACCOUNT_DELETED",
                entity_type="Account",
                entity_id=instance.pk,
                description=f"Chart of accounts entry {instance.code} deleted.",
            )
        return response


class JournalViewSet(CompanyScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Journal.objects.all()
    serializer_class = JournalSerializer


class JournalVoucherViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = (
        JournalVoucher.objects.select_related("journal", "posted_by")
        .prefetch_related("entries__account")
        .order_by("-entry_date", "-created_at")
    )
    serializer_class = JournalVoucherSerializer

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        company = self.get_company()
        if not company:
            return Response({"results": [], "summary": {}})
        queryset = self.filter_queryset(self.get_queryset())
        status_param = request.query_params.get("status")
        if status_param and status_param.upper() != "ALL":
            queryset = queryset.filter(status=status_param.upper())
        serializer = self.get_serializer(queryset, many=True)
        summary = {status: queryset.filter(status=status).count() for status, _ in JournalStatus.choices}
        return Response({"results": serializer.data, "summary": summary})

    @action(detail=True, methods=["post"], url_path="post")
    def post_voucher(self, request, pk=None):
        voucher = self.get_object()
        try:
            JournalService.post_journal_voucher(voucher, request.user)
        except ValueError as exc:  # pragma: no cover - defensive path
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        company = self.get_company()
        if company:
            log_audit_event(
                user=request.user,
                company=company,
                company_group=company.company_group,
                action="JOURNAL_POSTED",
                entity_type="JournalVoucher",
                entity_id=voucher.pk,
                description=f"Journal voucher {voucher.voucher_number} posted.",
            )
        serializer = self.get_serializer(voucher)
        return Response(serializer.data)


class InvoiceViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("journal_voucher").prefetch_related("lines__account")
    serializer_class = InvoiceSerializer

    TYPE_MAPPING = {
        "SALES": "AR",
        "PURCHASE": "AP",
        "AR": "AR",
        "AP": "AP",
    }

    def _build_partner_map(self, invoices: Iterable[Invoice], company) -> Dict[Tuple[str, int], str]:
        customer_ids = set()
        supplier_ids = set()
        for invoice in invoices:
            if invoice.invoice_type == "AR":
                customer_ids.add(invoice.partner_id)
            else:
                supplier_ids.add(invoice.partner_id)

        partner_map: Dict[Tuple[str, int], str] = {}
        if customer_ids:
            for customer in Customer.objects.filter(pk__in=customer_ids, company=company):
                partner_map[("customer", customer.pk)] = customer.name
        if supplier_ids:
            for supplier in Supplier.objects.filter(pk__in=supplier_ids, company=company):
                partner_map[("supplier", supplier.pk)] = supplier.name
        return partner_map

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        company = self.get_company()
        if not company:
            return Response({"results": [], "summary": {}, "forecast": []})

        queryset = self.filter_queryset(self.get_queryset())
        type_param = request.query_params.get("type")
        if type_param:
            mapped = self.TYPE_MAPPING.get(type_param.upper())
            if mapped:
                queryset = queryset.filter(invoice_type=mapped)

        invoices = list(queryset)
        partner_map = self._build_partner_map(invoices, company)
        context = self.get_serializer_context()
        context["partner_map"] = partner_map
        serializer = self.get_serializer(invoices, many=True, context=context)

        total_outstanding = sum((invoice.balance_due for invoice in invoices), Decimal("0"))
        today = timezone.now().date()
        total_overdue = sum((invoice.balance_due for invoice in invoices if invoice.due_date < today), Decimal("0"))

        summary = {
            "count": len(invoices),
            "total_outstanding": float(total_outstanding),
            "total_overdue": float(total_overdue),
        }

        forecast_map: Dict[Tuple[str, str], Decimal] = defaultdict(Decimal)
        for invoice in invoices:
            outstanding = invoice.balance_due
            if outstanding <= 0:
                continue
            month_label = invoice.due_date.strftime("%b %Y")
            forecast_map[(month_label, "Due")] += outstanding
            forecast_map[(month_label, "Projected Paid")] += outstanding

        forecast = [
            {"month": month, "status": status, "amount": float(amount)}
            for (month, status), amount in sorted(forecast_map.items())
        ]

        return Response({"results": serializer.data, "summary": summary, "forecast": forecast})

    def perform_create(self, serializer):  # type: ignore[override]
        invoice = serializer.save()
        company = self.get_company(required=True)
        log_audit_event(
            user=self.request.user,
            company=company,
            company_group=company.company_group,
            action="INVOICE_CREATED",
            entity_type="Invoice",
            entity_id=invoice.pk,
            description=f"Invoice {invoice.invoice_number} created via API.",
        )

    @action(detail=True, methods=["post"], url_path="post")
    def post_invoice(self, request, pk=None):
        invoice = self.get_object()
        try:
            if invoice.invoice_type == "AP":
                InvoiceService.post_supplier_invoice(invoice, request.user)
            else:
                InvoiceService.post_sales_invoice(invoice, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        company = self.get_company()
        if company:
            log_audit_event(
                user=request.user,
                company=company,
                company_group=company.company_group,
                action="INVOICE_POSTED",
                entity_type="Invoice",
                entity_id=invoice.pk,
                description=f"Invoice {invoice.invoice_number} posted to ledger.",
            )

        context = self.get_serializer_context()
        context["partner_map"] = self._build_partner_map([invoice], company)
        serializer = self.get_serializer(invoice, context=context)
        return Response(serializer.data)


class PaymentViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("bank_account", "journal_voucher").prefetch_related("allocations__invoice")
    serializer_class = PaymentSerializer

    def _build_partner_map(self, payments: Iterable[Payment], company) -> Dict[Tuple[str, int], str]:
        customer_ids = set()
        supplier_ids = set()
        for payment in payments:
            if payment.payment_type == "RECEIPT":
                customer_ids.add(payment.partner_id)
            else:
                supplier_ids.add(payment.partner_id)

        partner_map: Dict[Tuple[str, int], str] = {}
        if customer_ids:
            for customer in Customer.objects.filter(pk__in=customer_ids, company=company):
                partner_map[("customer", customer.pk)] = customer.name
        if supplier_ids:
            for supplier in Supplier.objects.filter(pk__in=supplier_ids, company=company):
                partner_map[("supplier", supplier.pk)] = supplier.name
        return partner_map

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        company = self.get_company()
        if not company:
            return Response({"results": [], "summary": {}})

        queryset = self.filter_queryset(self.get_queryset())
        type_param = request.query_params.get("type")
        if type_param and type_param.upper() != "ALL":
            queryset = queryset.filter(payment_type=type_param.upper())

        payments = list(queryset)
        partner_map = self._build_partner_map(payments, company)
        context = self.get_serializer_context()
        context["partner_map"] = partner_map
        serializer = self.get_serializer(payments, many=True, context=context)

        receipts_total = queryset.filter(payment_type="RECEIPT").aggregate(total=Sum("amount")).get("total") or 0
        disburse_total = queryset.filter(payment_type="PAYMENT").aggregate(total=Sum("amount")).get("total") or 0
        summary = {
            "count": len(payments),
            "receipts": float(receipts_total),
            "disbursements": float(disburse_total),
        }
        return Response({"results": serializer.data, "summary": summary})

    def perform_create(self, serializer):  # type: ignore[override]
        payment = serializer.save()
        company = self.get_company(required=True)
        log_audit_event(
            user=self.request.user,
            company=company,
            company_group=company.company_group,
            action="PAYMENT_CREATED",
            entity_type="Payment",
            entity_id=payment.pk,
            description=f"Payment {payment.payment_number} recorded.",
        )

    def _post_payment(self, payment: Payment, actor) -> JournalVoucher:
        if payment.status != "DRAFT":
            raise ValueError("Only draft payments can be posted.")

        company = payment.company
        allocations = list(payment.allocations.select_related("invoice"))
        if not allocations:
            raise ValueError("Payment requires at least one invoice allocation before posting.")

        bank_account = payment.bank_account
        if bank_account is None:
            raise ValueError("A bank or cash account must be selected before posting.")
        if bank_account.company_id != company.id:
            raise ValueError("Bank account must belong to the active company.")

        total_allocated = sum((Decimal(allocation.allocated_amount) for allocation in allocations), Decimal("0"))
        if total_allocated != Decimal(payment.amount):
            raise ValueError("Allocated amount must equal the payment amount before posting.")

        journal_code = "CASH" if payment.payment_method == "CASH" else "BANK"
        try:
            journal = Journal.objects.get(company=company, code=journal_code)
        except Journal.DoesNotExist:
            journal = Journal.objects.filter(company=company).first()
            if not journal:
                raise ValueError("No journal configured for payment posting.")

        entries: List[Dict[str, Decimal]] = []
        if payment.payment_type == "RECEIPT":
            customer_cache: Dict[int, Customer] = {}
            receivable_totals: Dict[int, Decimal] = defaultdict(Decimal)
            for allocation in allocations:
                invoice = allocation.invoice
                if invoice.invoice_type != "AR":
                    raise ValueError("Customer receipts can only be matched with AR invoices.")
                if invoice.partner_id != payment.partner_id:
                    raise ValueError("Allocated invoice does not belong to the selected customer.")
                customer = customer_cache.get(invoice.partner_id)
                if not customer:
                    customer = Customer.objects.select_related("receivable_account").get(
                        pk=invoice.partner_id, company=company
                    )
                    customer_cache[invoice.partner_id] = customer
                receivable_totals[customer.receivable_account_id] += Decimal(allocation.allocated_amount)

            entries.append(
                {
                    "account": bank_account,
                    "debit": total_allocated,
                    "credit": Decimal("0"),
                    "description": f"Receipt {payment.payment_number or payment.id}",
                }
            )
            for account_id, amount in receivable_totals.items():
                account = Account.objects.get(pk=account_id, company=company)
                entries.append(
                    {
                        "account": account,
                        "debit": Decimal("0"),
                        "credit": amount,
                        "description": f"Settlement for customer invoices",
                    }
                )
        else:  # Supplier payment
            supplier_cache: Dict[int, Supplier] = {}
            payable_totals: Dict[int, Decimal] = defaultdict(Decimal)
            for allocation in allocations:
                invoice = allocation.invoice
                if invoice.invoice_type != "AP":
                    raise ValueError("Supplier payments can only be matched with AP invoices.")
                if invoice.partner_id != payment.partner_id:
                    raise ValueError("Allocated invoice does not belong to the selected supplier.")
                supplier = supplier_cache.get(invoice.partner_id)
                if not supplier:
                    supplier = Supplier.objects.select_related("payable_account").get(
                        pk=invoice.partner_id, company=company
                    )
                    supplier_cache[invoice.partner_id] = supplier
                payable_totals[supplier.payable_account_id] += Decimal(allocation.allocated_amount)

            for account_id, amount in payable_totals.items():
                account = Account.objects.get(pk=account_id, company=company)
                entries.append(
                    {
                        "account": account,
                        "debit": amount,
                        "credit": Decimal("0"),
                        "description": "Settlement of supplier liability",
                    }
                )
            entries.append(
                {
                    "account": bank_account,
                    "debit": Decimal("0"),
                    "credit": total_allocated,
                    "description": f"Payment {payment.payment_number or payment.id}",
                }
            )

        voucher = JournalService.create_journal_voucher(
            company=company,
            journal=journal,
            entry_date=payment.payment_date,
            description=f"Journal for payment {payment.payment_number or payment.id}",
            entries_data=entries,
            reference=payment.reference or "",
            source_document_type="Payment",
            source_document_id=payment.id,
            created_by=actor,
        )
        JournalService.post_journal_voucher(voucher, actor)

        for allocation in allocations:
            allocation.invoice.register_payment(allocation.allocated_amount, commit=True)

        payment.mark_posted(voucher, actor)
        return voucher

    @action(detail=True, methods=["post"], url_path="post")
    def post_payment(self, request, pk=None):
        payment = self.get_object()
        try:
            voucher = self._post_payment(payment, request.user)
        except (ValueError, Supplier.DoesNotExist, Customer.DoesNotExist, Account.DoesNotExist) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        company = self.get_company()
        if company:
            log_audit_event(
                user=request.user,
                company=company,
                company_group=company.company_group,
                action="PAYMENT_POSTED",
                entity_type="Payment",
                entity_id=payment.pk,
                description=f"Payment {payment.payment_number} posted with voucher {voucher.voucher_number}.",
            )

        context = self.get_serializer_context()
        context["partner_map"] = self._build_partner_map([payment], company)
        serializer = self.get_serializer(payment, context=context)
        return Response(serializer.data)
