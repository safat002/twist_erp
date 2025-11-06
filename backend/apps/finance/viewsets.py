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
from apps.permissions.permissions import has_permission

from .models import (
    Account,
    AccountType,
    BankStatement,
    BankStatementLine,
    FiscalPeriod,
    Invoice,
    InvoiceStatus,
    Journal,
    JournalEntry,
    JournalStatus,
    JournalVoucher,
    Payment,
    Currency,
)
from .serializers import (
    AccountSerializer,
    BankStatementSerializer,
    FiscalPeriodSerializer,
    InvoiceSerializer,
    JournalSerializer,
    JournalVoucherSerializer,
    PaymentSerializer,
    CurrencySerializer,
)
from .services.invoice_service import InvoiceService
from .services.journal_service import JournalService
from .services.document_processor import DocumentProcessor
from .services.config import (
    require_journal_review,
    require_invoice_approval,
    require_payment_approval,
    enforce_segregation_of_duties,
)


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

    def ensure_perm(self, perm_code: str):
        company = self.get_company(required=True)
        if not has_permission(self.request.user, perm_code, company):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(detail=f"Missing permission: {perm_code}")


class AccountViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = Account.objects.select_related("parent_account")
    serializer_class = AccountSerializer

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        self.ensure_perm("finance_view_coa")
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
        self.ensure_perm("finance_manage_coa")
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
        self.ensure_perm("finance_manage_coa")
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
        self.ensure_perm("finance_manage_coa")
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

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        self.ensure_perm("finance_view_journal")
        return super().list(request, *args, **kwargs)


class FiscalPeriodViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = FiscalPeriod.objects.all()
    serializer_class = FiscalPeriodSerializer

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        self.ensure_perm("finance_close_period")
        # Autogenerate current/next periods based on company settings
        try:
            from apps.finance.services.period_service import ensure_upcoming_periods
            company = self.get_company(required=True)
            ensure_upcoming_periods(company, days_threshold=15)
        except Exception:
            # Soft-fail; listing should still work
            pass
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):  # type: ignore[override]
        self.ensure_perm("finance_close_period")
        serializer.save()

    def perform_update(self, serializer):  # type: ignore[override]
        self.ensure_perm("finance_close_period")
        serializer.save()

    def destroy(self, request, *args, **kwargs):  # type: ignore[override]
        self.ensure_perm("finance_close_period")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="close")
    def close_period(self, request, pk=None):
        self.ensure_perm("finance_close_period")
        period = self.get_object()
        period.status = "CLOSED"
        period.save(update_fields=["status"]) 
        return Response(self.get_serializer(period).data)

    @action(detail=True, methods=["post"], url_path="open")
    def open_period(self, request, pk=None):
        self.ensure_perm("finance_close_period")
        period = self.get_object()
        period.status = "OPEN"
        period.save(update_fields=["status"]) 
        return Response(self.get_serializer(period).data)

    @action(detail=True, methods=["post"], url_path="lock")
    def lock_period(self, request, pk=None):
        self.ensure_perm("finance_close_period")
        from django.utils import timezone
        period = self.get_object()
        period.status = "LOCKED"
        period.locked_by = request.user
        period.locked_at = timezone.now()
        period.save(update_fields=["status", "locked_by", "locked_at"]) 
        return Response(self.get_serializer(period).data)

    @action(detail=True, methods=["post"], url_path="unlock")
    def unlock_period(self, request, pk=None):
        self.ensure_perm("finance_close_period")
        period = self.get_object()
        period.status = "OPEN"
        period.locked_by = None
        period.locked_at = None
        period.save(update_fields=["status", "locked_by", "locked_at"]) 
        return Response(self.get_serializer(period).data)


class BankStatementViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = BankStatement.objects.prefetch_related("lines")
    serializer_class = BankStatementSerializer

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        self.ensure_perm("finance_reconcile_bank")
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):  # type: ignore[override]
        self.ensure_perm("finance_reconcile_bank")
        serializer.save()

    def perform_update(self, serializer):  # type: ignore[override]
        self.ensure_perm("finance_reconcile_bank")
        serializer.save()

    def destroy(self, request, *args, **kwargs):  # type: ignore[override]
        self.ensure_perm("finance_reconcile_bank")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="match-line")
    def match_line(self, request, pk=None):
        self.ensure_perm("finance_reconcile_bank")
        stmt = self.get_object()
        line_id = request.data.get("line_id")
        payment_id = request.data.get("payment_id")
        voucher_id = request.data.get("voucher_id")
        try:
            line = stmt.lines.get(pk=line_id)
        except BankStatementLine.DoesNotExist:
            return Response({"detail": "Statement line not found."}, status=404)
        if payment_id:
            try:
                payment = Payment.objects.get(pk=payment_id, company=stmt.company)
            except Payment.DoesNotExist:
                return Response({"detail": "Payment not found in company."}, status=404)
            line.matched_payment = payment
            line.matched_voucher = payment.journal_voucher
            line.match_status = "MATCHED"
            line.save(update_fields=["matched_payment", "matched_voucher", "match_status"]) 
        elif voucher_id:
            try:
                voucher = JournalVoucher.objects.get(pk=voucher_id, company=stmt.company)
            except JournalVoucher.DoesNotExist:
                return Response({"detail": "Voucher not found in company."}, status=404)
            line.matched_voucher = voucher
            line.match_status = "MATCHED"
            line.save(update_fields=["matched_voucher", "match_status"]) 
        else:
            return Response({"detail": "Provide payment_id or voucher_id"}, status=400)
        return Response(self.get_serializer(stmt).data)


class FinanceReportsViewSet(CompanyScopedMixin, viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _parse_dates(self, request):
        from datetime import datetime
        fmt = "%Y-%m-%d"
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        start_date = datetime.strptime(start, fmt).date() if start else None
        end_date = datetime.strptime(end, fmt).date() if end else None
        return start_date, end_date

    @action(detail=False, methods=["get"], url_path="trial-balance")
    def trial_balance(self, request):
        self.ensure_perm("finance_view_reports")
        company = self.get_company(required=True)
        start_date, end_date = self._parse_dates(request)

        # Posted vouchers in range
        vouchers = JournalVoucher.objects.filter(company=company, status=JournalStatus.POSTED)
        if end_date:
            vouchers = vouchers.filter(entry_date__lte=end_date)

        # Entries up to end_date (for closing) and up to start-1 (for opening)
        entries = JournalEntry.objects.filter(voucher__in=vouchers).select_related("account", "voucher")
        if start_date:
            opening_entries = entries.filter(voucher__entry_date__lt=start_date)
            period_entries = entries.filter(voucher__entry_date__gte=start_date)
        else:
            opening_entries = entries.none()
            period_entries = entries

        from collections import defaultdict
        from decimal import Decimal

        def sums(queryset):
            data = defaultdict(lambda: {"debit": Decimal("0"), "credit": Decimal("0")})
            for e in queryset:
                data[e.account_id]["debit"] += e.debit_amount
                data[e.account_id]["credit"] += e.credit_amount
            return data

        open_map = sums(opening_entries)
        period_map = sums(period_entries)

        account_ids = set(list(open_map.keys()) + list(period_map.keys()))
        accounts = {a.pk: a for a in Account.objects.filter(pk__in=account_ids)}

        rows = []
        for aid in sorted(account_ids, key=lambda x: accounts[x].code if x in accounts else ""):
            acc = accounts.get(aid)
            o = open_map.get(aid, {"debit": 0, "credit": 0})
            p = period_map.get(aid, {"debit": 0, "credit": 0})
            opening = (o["debit"] - o["credit"]) if acc and acc.account_type in [AccountType.ASSET, AccountType.EXPENSE] else (o["credit"] - o["debit"])
            movement = p["debit"] - p["credit"] if acc and acc.account_type in [AccountType.ASSET, AccountType.EXPENSE] else (p["credit"] - p["debit"])
            closing = opening + movement
            rows.append({
                "account_id": aid,
                "code": getattr(acc, "code", ""),
                "name": getattr(acc, "name", ""),
                "type": getattr(acc, "account_type", ""),
                "opening": float(opening),
                "debits": float(p["debit"]),
                "credits": float(p["credit"]),
                "closing": float(closing),
            })

        totals = {
            "debits": float(sum(e["debits"] for e in rows)),
            "credits": float(sum(e["credits"] for e in rows)),
        }
        return Response({"results": rows, "totals": totals})

    @action(detail=False, methods=["get"], url_path="general-ledger")
    def general_ledger(self, request):
        self.ensure_perm("finance_view_reports")
        from decimal import Decimal
        company = self.get_company(required=True)
        start_date, end_date = self._parse_dates(request)
        try:
            account_id = int(request.query_params.get("account"))
        except Exception:
            raise ValidationError("Query param 'account' is required and must be an integer.")
        account = Account.objects.get(pk=account_id, company=company)
        vouchers = JournalVoucher.objects.filter(company=company, status=JournalStatus.POSTED)
        if end_date:
            vouchers = vouchers.filter(entry_date__lte=end_date)
        entries = JournalEntry.objects.filter(voucher__in=vouchers, account=account).select_related("voucher")
        if start_date:
            opening_qs = entries.filter(voucher__entry_date__lt=start_date)
            period_qs = entries.filter(voucher__entry_date__gte=start_date)
        else:
            opening_qs = entries.none()
            period_qs = entries
        opening = sum((e.debit_amount - e.credit_amount for e in opening_qs), Decimal("0"))
        if account.account_type not in [AccountType.ASSET, AccountType.EXPENSE]:
            opening = -opening
        lines = []
        running = opening
        for e in period_qs.order_by("voucher__entry_date", "line_number"):
            delta = e.debit_amount - e.credit_amount
            if account.account_type not in [AccountType.ASSET, AccountType.EXPENSE]:
                delta = -delta
            running += delta
            lines.append({
                "date": e.voucher.entry_date,
                "voucher": e.voucher.voucher_number,
                "ref": e.voucher.reference,
                "desc": e.description,
                "debit": float(e.debit_amount),
                "credit": float(e.credit_amount),
                "balance": float(running),
            })
        return Response({
            "account": {"id": account.id, "code": account.code, "name": account.name},
            "opening": float(opening),
            "lines": lines,
        })

    @action(detail=False, methods=["get"], url_path="ar-aging")
    def ar_aging(self, request):
        self.ensure_perm("finance_view_reports")
        from datetime import datetime
        from collections import defaultdict
        as_of = request.query_params.get("as_of")
        as_of_date = datetime.strptime(as_of, "%Y-%m-%d").date() if as_of else timezone.now().date()
        company = self.get_company(required=True)
        invoices = Invoice.objects.filter(company=company, invoice_type="AR", status__in=[InvoiceStatus.POSTED, InvoiceStatus.PARTIAL])
        buckets = defaultdict(list)
        def bucket_for(days):
            if days <= 0: return "CURRENT"
            if days <= 30: return "DUE_1_30"
            if days <= 60: return "DUE_31_60"
            if days <= 90: return "DUE_61_90"
            return ">90"
        for inv in invoices:
            due_in = (as_of_date - inv.due_date).days
            bucket = bucket_for(due_in)
            amt = float(inv.balance_due)
            if amt <= 0: continue
            buckets[bucket].append({"id": inv.id, "number": inv.invoice_number, "partner_id": inv.partner_id, "due_date": inv.due_date, "amount": amt})
        summary = {k: float(sum(i["amount"] for i in v)) for k, v in buckets.items()}
        return Response({"summary": summary, "buckets": buckets})

    @action(detail=False, methods=["get"], url_path="ap-aging")
    def ap_aging(self, request):
        self.ensure_perm("finance_view_reports")
        from datetime import datetime
        from collections import defaultdict
        as_of = request.query_params.get("as_of")
        as_of_date = datetime.strptime(as_of, "%Y-%m-%d").date() if as_of else timezone.now().date()
        company = self.get_company(required=True)
        invoices = Invoice.objects.filter(company=company, invoice_type="AP", status__in=[InvoiceStatus.POSTED, InvoiceStatus.PARTIAL])
        buckets = defaultdict(list)
        def bucket_for(days):
            if days <= 0: return "CURRENT"
            if days <= 30: return "DUE_1_30"
            if days <= 60: return "DUE_31_60"
            if days <= 90: return "DUE_61_90"
            return ">90"
        for inv in invoices:
            due_in = (as_of_date - inv.due_date).days
            bucket = bucket_for(due_in)
            amt = float(inv.balance_due)
            if amt <= 0: continue
            buckets[bucket].append({"id": inv.id, "number": inv.invoice_number, "partner_id": inv.partner_id, "due_date": inv.due_date, "amount": amt})
        summary = {k: float(sum(i["amount"] for i in v)) for k, v in buckets.items()}
        return Response({"summary": summary, "buckets": buckets})

    @action(detail=False, methods=["get"], url_path="vat-return")
    def vat_return(self, request):
        self.ensure_perm("finance_view_reports")
        from datetime import datetime
        company = self.get_company(required=True)
        start, end = self._parse_dates(request)
        qs = Invoice.objects.filter(company=company, status__in=[InvoiceStatus.POSTED, InvoiceStatus.PAID, InvoiceStatus.PARTIAL])
        if start:
            qs = qs.filter(invoice_date__gte=start)
        if end:
            qs = qs.filter(invoice_date__lte=end)
        sales = qs.filter(invoice_type="AR").aggregate(total=models.Sum("tax_amount"))['total'] or 0
        purchases = qs.filter(invoice_type="AP").aggregate(total=models.Sum("tax_amount"))['total'] or 0
        net = float(sales) - float(purchases)
        return Response({"period": {"start": start, "end": end}, "output_vat": float(sales), "input_vat": float(purchases), "net_vat": net})

    @action(detail=False, methods=["post"], url_path="fx-revaluation")
    def fx_revaluation(self, request):
        """
        Accepts a payload:
        {
          "date": "YYYY-MM-DD",
          "rates": {"USD": 110.40, "EUR": 120.50},
          "gain_account": 123,   # Account ID for FX Gain (REVENUE)
          "loss_account": 456,   # Account ID for FX Loss (EXPENSE)
          "lines": [
            {"account": 10, "currency": "USD", "foreign_amount": 10000.00},
            ...
          ],
          "post": false          # if true, creates and posts a JV
        }
        Returns a preview of entries and optionally posts a journal voucher.
        """
        self.ensure_perm("finance_view_reports")
        from decimal import Decimal
        from datetime import datetime

        company = self.get_company(required=True)
        data = request.data or {}
        date_str = data.get("date")
        try:
            entry_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else timezone.now().date()
        except Exception:
            return Response({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=400)
        rates = data.get("rates") or {}
        lines = data.get("lines") or []
        gain_account_id = data.get("gain_account")
        loss_account_id = data.get("loss_account")
        do_post = bool(data.get("post"))

        if do_post and (not gain_account_id or not loss_account_id):
            return Response({"detail": "gain_account and loss_account must be provided when posting."}, status=400)

        # Build revaluation entries
        jv_entries = []
        total_gain = Decimal("0")
        total_loss = Decimal("0")

        for row in lines:
            try:
                acc = Account.objects.get(pk=row.get("account"), company=company)
            except Account.DoesNotExist:
                return Response({"detail": f"Account {row.get('account')} not found in company."}, status=400)
            ccy = (row.get("currency") or acc.currency or company.base_currency).upper()
            foreign_amount = Decimal(str(row.get("foreign_amount", 0)))
            rate = Decimal(str(rates.get(ccy, 0)))
            if rate <= 0:
                return Response({"detail": f"Missing FX rate for currency {ccy}."}, status=400)
            revalued = (foreign_amount * rate).quantize(Decimal("0.01"))
            carrying = Decimal(acc.current_balance or 0)
            delta = revalued - carrying
            if delta == 0:
                continue
            # For assets/expenses positive delta = debit to account; for liabilities/equity/revenue inverse
            if acc.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
                if delta > 0:
                    jv_entries.append({"account": acc, "debit": delta, "credit": Decimal("0"), "description": f"FX revaluation {ccy}"})
                    total_gain += delta
                else:
                    jv_entries.append({"account": acc, "debit": Decimal("0"), "credit": -delta, "description": f"FX revaluation {ccy}"})
                    total_loss += (-delta)
            else:
                if delta > 0:
                    jv_entries.append({"account": acc, "debit": Decimal("0"), "credit": delta, "description": f"FX revaluation {ccy}"})
                    total_loss += delta
                else:
                    jv_entries.append({"account": acc, "debit": -delta, "credit": Decimal("0"), "description": f"FX revaluation {ccy}"})
                    total_gain += (-delta)

        # Counter-entries to balance with gain/loss accounts
        preview = []
        for e in jv_entries:
            preview.append({
                "account": getattr(e["account"], "code", ""),
                "debit": float(e["debit"]),
                "credit": float(e["credit"]),
                "desc": e["description"],
            })
        preview.append({"account": f"GAIN({gain_account_id})", "debit": 0.0, "credit": float(total_gain)})
        preview.append({"account": f"LOSS({loss_account_id})", "debit": float(total_loss), "credit": 0.0})

        if not do_post:
            return Response({"entries": preview, "totals": {"gain": float(total_gain), "loss": float(total_loss)}})

        # Post journal
        self.ensure_perm("finance_post_journal")
        try:
            gain_acc = Account.objects.get(pk=gain_account_id, company=company)
            loss_acc = Account.objects.get(pk=loss_account_id, company=company)
        except Account.DoesNotExist:
            return Response({"detail": "Gain or Loss account not found."}, status=400)

        # Find General journal or fallback
        journal = Journal.objects.filter(company=company, code="GENERAL").first() or Journal.objects.filter(company=company).first()
        if not journal:
            return Response({"detail": "No journal configured."}, status=400)

        entries_data = list(jv_entries)
        if total_gain:
            entries_data.append({"account": gain_acc, "debit": Decimal("0"), "credit": total_gain, "description": "FX gain"})
        if total_loss:
            entries_data.append({"account": loss_acc, "debit": total_loss, "credit": Decimal("0"), "description": "FX loss"})

        voucher = JournalService.create_journal_voucher(
            company=company,
            journal=journal,
            entry_date=entry_date,
            description=f"FX Revaluation {entry_date}",
            entries_data=entries_data,
            reference="FXREV",
            source_document_type="FX_REVALUATION",
            source_document_id=None,
            created_by=request.user,
        )
        JournalService.post_journal_voucher(voucher, request.user)
        return Response({"voucher": voucher.voucher_number, "entries": preview})

class JournalVoucherViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = (
        JournalVoucher.objects.select_related("journal", "posted_by")
        .prefetch_related("entries__account")
        .order_by("-entry_date", "-created_at")
    )
    serializer_class = JournalVoucherSerializer

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        self.ensure_perm("finance_view_journal")
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
        self.ensure_perm("finance_post_journal")
        voucher = self.get_object()
        company = self.get_company(required=True)
        if require_journal_review(company) and voucher.status != JournalStatus.REVIEW:
            return Response({"detail": "Voucher must be in review state before posting."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            JournalService.post_journal_voucher(voucher, request.user)
        except ValueError as exc:  # pragma: no cover - defensive path
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
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

    @action(detail=True, methods=["post"], url_path="submit")
    def submit_for_review(self, request, pk=None):
        self.ensure_perm("finance_manage_journal")
        voucher = self.get_object()
        try:
            JournalService.submit_for_review(voucher, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(voucher).data)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        self.ensure_perm("finance_post_journal")
        voucher = self.get_object()
        company = self.get_company(required=True)
        try:
            JournalService.approve_voucher(voucher, request.user)
            JournalService.post_journal_voucher(voucher, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        log_audit_event(
            user=request.user,
            company=company,
            company_group=company.company_group,
            action="JOURNAL_APPROVED",
            entity_type="JournalVoucher",
            entity_id=voucher.pk,
            description=f"Journal voucher {voucher.voucher_number} approved and posted.",
        )
        return Response(self.get_serializer(voucher).data)

    @action(detail=False, methods=["post"], url_path="process-document")
    def process_document(self, request):
        """Process uploaded PDF/image to extract journal voucher data using AI."""
        company = self.get_company(required=True)

        # Get uploaded file
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {"detail": "No file uploaded. Please attach a PDF or image file."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if uploaded_file.size > max_size:
            return Response(
                {"detail": "File size exceeds 10MB limit."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get available accounts and journals for matching
        accounts = Account.objects.filter(company=company).values('id', 'code', 'name')
        journals = Journal.objects.filter(company=company).values('id', 'code', 'name')

        accounts_list = list(accounts)
        journals_list = list(journals)

        try:
            # Read file content
            file_content = uploaded_file.read()

            # Process document with AI (pass user and company for logging)
            processor = DocumentProcessor(user=request.user, company=company)
            extracted_data = processor.process_journal_voucher_document(
                file_content=file_content,
                file_name=uploaded_file.name,
                company=company,
                accounts_list=accounts_list,
                journals_list=journals_list,
            )

            # Log the processing
            log_audit_event(
                user=request.user,
                company=company,
                company_group=company.company_group,
                action="DOCUMENT_PROCESSED",
                entity_type="JournalVoucher",
                entity_id=None,
                description=f"Processed document {uploaded_file.name} for journal voucher creation.",
            )

            return Response(extracted_data)

        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Failed to process document: %s", exc)
            return Response(
                {"detail": "An error occurred while processing the document. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
        self.ensure_perm("finance_view_invoice")
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
        self.ensure_perm("finance_manage_invoice")
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

    @action(detail=True, methods=["post"], url_path="approve")
    def approve_invoice(self, request, pk=None):
        self.ensure_perm("finance_manage_invoice")
        invoice = self.get_object()
        try:
            InvoiceService.approve_invoice(invoice, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=["post"], url_path="post")
    def post_invoice(self, request, pk=None):
        self.ensure_perm("finance_manage_invoice")
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
        self.ensure_perm("finance_view_payment")
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
        self.ensure_perm("finance_manage_payment")
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
        company = payment.company
        # Approval and SoD checks
        if require_payment_approval(company) and payment.status != "APPROVED":
            raise ValueError("Payment must be approved before posting.")
        if not require_payment_approval(company) and payment.status not in {"DRAFT", "APPROVED"}:
            raise ValueError("Payment is not in a postable state.")
        if enforce_segregation_of_duties(company) and payment.created_by_id == getattr(actor, 'id', None):
            raise ValueError("Segregation of duties: creator cannot post their own payment.")
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
        self.ensure_perm("finance_manage_payment")
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

    @action(detail=True, methods=["post"], url_path="approve")
    def approve_payment(self, request, pk=None):
        self.ensure_perm("finance_manage_payment")
        payment = self.get_object()
        company = self.get_company(required=True)
        # SoD: prevent creator from approving
        if enforce_segregation_of_duties(company) and payment.created_by_id == request.user.id:
            return Response({"detail": "Segregation of duties: creator cannot approve their own payment."}, status=400)
        from django.utils import timezone
        payment.status = "APPROVED"
        payment.approved_by = request.user
        payment.approved_at = timezone.now()
        payment.save(update_fields=["status", "approved_by", "approved_at"])
        return Response(self.get_serializer(payment).data)


class CurrencyViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        company = self.get_company(required=True)
        qs = self.get_queryset().filter(company=company).order_by('-is_base_currency', 'code')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):  # type: ignore[override]
        serializer.save()

    def perform_update(self, serializer):  # type: ignore[override]
        serializer.save()

    @action(detail=False, methods=["get"], url_path="choices")
    def choices(self, request):
        """Return system-supported currency choices (ISO 4217 codes).

        Useful for UI dropdowns when creating groups/companies.
        """
        try:
            from apps.companies.models import CompanyGroup  # local import to avoid cycles
            data = [{"code": code, "name": name} for code, name in CompanyGroup.CURRENCY_CHOICES]
        except Exception:
            data = []
        return Response(data)

    @action(detail=False, methods=["post"], url_path="set-base")
    def set_base(self, request):
        company = self.get_company(required=True)
        code = request.data.get('code')
        if not code:
            return Response({"detail": "code is required"}, status=400)
        try:
            cur = Currency.objects.get(company=company, code=code)
        except Currency.DoesNotExist:
            return Response({"detail": "Currency not found for this company."}, status=404)
        Currency.objects.filter(company=company).update(is_base_currency=False)
        cur.is_base_currency = True
        cur.save(update_fields=["is_base_currency", "updated_at"])
        return Response({"detail": f"Base currency set to {code}"})

    @action(detail=False, methods=["get", "post"], url_path="config")
    def config(self, request):
        """Get or set multi-currency configuration for the active company.

        GET: returns { enabled, base_currency, count }
        POST: body { enabled: bool } updates company.feature_flags.multi_currency_enabled
        """
        company = self.get_company(required=True)
        # Ensure feature_flags exists
        flags = dict(company.feature_flags or {})
        if request.method.lower() == "post":
            enabled = bool(request.data.get("enabled", True))
            flags["multi_currency_enabled"] = enabled
            company.feature_flags = flags
            company.save(update_fields=["feature_flags", "updated_at"])
            return Response({"enabled": enabled})

        enabled = bool(flags.get("multi_currency_enabled", True))
        base = (
            Currency.objects.filter(company=company, is_base_currency=True)
            .values_list("code", flat=True)
            .first()
        ) or getattr(company, "base_currency", None)
        count = Currency.objects.filter(company=company).count()
        return Response({"enabled": enabled, "base_currency": base, "count": count})
