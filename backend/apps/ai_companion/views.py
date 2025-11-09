import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.utils import log_audit_event
from apps.workflows.models import WorkflowInstance

from .services import orchestrator
from .services.actions import ActionContext, ActionExecutionError, execute_action
from .services.memory import MemoryRecord
from .services.rate_limiter import RateLimiter
from .services.telemetry import TelemetryService
from .services.workflow_insights import explain_instance
from .models import (
    AIConversation,
    AIMessage,
    AIProactiveSuggestion,
    AITrainingExample,
    AITrainingExampleStatus,
    AILoRARun,
    AILoRARunStatus,
    AIActionExecution,
    AITelemetryEvent,
    UserAIPreference,
)
from .serializers import AIPreferenceSerializer
from .tasks import train_memory


logger = logging.getLogger(__name__)


def _positive_int(value, default, minimum=1):
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        coerced = default
    return max(coerced, minimum)


_ai_cfg = getattr(settings, "AI_CONFIG", {})
ACTION_RATE_LIMITER = RateLimiter(
    prefix="actions",
    limit=_positive_int(_ai_cfg.get("ACTION_RATE_LIMIT"), 20),
    window_seconds=_positive_int(_ai_cfg.get("ACTION_RATE_WINDOW"), 60),
)


class AIStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cfg = getattr(settings, "AI_CONFIG", {})
        return Response(
            {
                "llm_model": cfg.get("LLM_MODEL"),
                "embedding_model": cfg.get("EMBEDDING_MODEL"),
                "mode": cfg.get("MODE", "full"),
                "vector_db": cfg.get("VECTOR_DB_PATH"),
                "skills": list(orchestrator._skills.keys()),
            }
        )


class AIChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = request.data.get("message", "") or ""
        if not message.strip():
            return Response({"message": "Ask me something first!"}, status=status.HTTP_400_BAD_REQUEST)

        company = getattr(request, "company", None)
        conversation_id = request.data.get("conversation_id")
        context = request.data.get("context", {}) or {}

        metadata = {
            "page": context.get("page"),
            "module": context.get("module"),
            "extra": context.get("extra"),
            "preferred_skill": context.get("skill"),
        }

        try:
            result = orchestrator.chat(
                message=message,
                user=request.user,
                company=company,
                conversation_id=conversation_id,
                metadata=metadata,
            )
        except Exception as e:
            logger.exception("AI chat orchestration failed: %s", e)
            # Soft-fail with a friendly response so the UI doesn't break
            return Response(
                {
                    "message": "I'm having trouble responding right now. Please try again in a minute.",
                    "intent": "error",
                    "confidence": 0.0,
                    "skill": "system_fallback",
                },
                status=status.HTTP_200_OK,
            )
        try:
            truncated_message = message.strip()
            if len(truncated_message) > 500:
                truncated_message = f"{truncated_message[:497]}..."
            log_audit_event(
                user=request.user,
                company=company,
                company_group=getattr(company, "company_group", None),
                action="AI_QUERY",
                entity_type="AI_CONVERSATION",
                entity_id=result.get("conversation_id") or "unknown",
                description=truncated_message,
                after={
                    "intent": result.get("intent"),
                    "skill": result.get("skill"),
                    "metadata": metadata,
                },
            )
        except Exception:  # pragma: no cover - audit logging must not break chat
            logger.exception("Failed to record AI query audit log.")
        return Response(result, status=status.HTTP_200_OK)


class AIFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        conversation_id = request.data.get("conversation_id")
        rating = request.data.get("rating")
        notes = request.data.get("notes", "")
        if rating not in {"up", "down"}:
            return Response({"detail": "rating must be 'up' or 'down'"}, status=status.HTTP_400_BAD_REQUEST)
        orchestrator.record_feedback(conversation_id, request.user, rating, notes)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AITrainView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        key = request.data.get("key")
        value = request.data.get("value")
        scope = request.data.get("scope", "user")
        if not key:
            return Response({"detail": "key is required"}, status=status.HTTP_400_BAD_REQUEST)
        if value is None:
            return Response({"detail": "value cannot be null"}, status=status.HTTP_400_BAD_REQUEST)

        company = getattr(request, "company", None)
        record = MemoryRecord(
            key=key,
            value=value,
            scope=scope,
            user=request.user,
            company=company,
        )
        orchestrator.memory.save(record)
        # Also push to async task so future heavy processing is offloaded
        train_memory.delay(request.user.id, scope, key, value, getattr(company, "id", None))

        return Response({"status": "queued"})


class AISuggestionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        suggestions = orchestrator.get_pending_suggestions(request.user, getattr(request, "company", None))
        data = [
            {
                "id": suggestion.id,
                "title": suggestion.title,
                "body": suggestion.body,
                "metadata": suggestion.metadata,
                "source_skill": suggestion.source_skill,
                "alert_type": suggestion.alert_type,
                "severity": suggestion.severity,
                "created_at": suggestion.created_at.isoformat(),
            }
            for suggestion in suggestions
        ]
        return Response({"results": data})

    def post(self, request):
        suggestion_id = request.data.get("suggestion_id")
        status_value = request.data.get("status")
        if status_value not in {"accepted", "dismissed"}:
            return Response({"detail": "status must be 'accepted' or 'dismissed'"}, status=status.HTTP_400_BAD_REQUEST)
        orchestrator.mark_suggestion(suggestion_id, status_value)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AIAlertUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = orchestrator.get_pending_suggestions(request.user, getattr(request, "company", None)).count()
        return Response({"count": count})


class AIAgendaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, "company", None)
        agenda = {
            "approvals": [],
            "budgets_due": [],
            "pos_pending_grn": [],
            "ap_due": [],
            "suggestions": [],
        }
        counts = {k: 0 for k in agenda.keys()}

        # Pending approvals (workflow tasks assigned to user)
        try:
            from .services.data_query_layer import DataQueryLayer

            dql = DataQueryLayer(user=request.user, company=company)
            approvals_res = dql.get_pending_approvals()
            if approvals_res.success:
                agenda["approvals"] = approvals_res.data[:20]
                counts["approvals"] = len(approvals_res.data)
        except Exception:
            logger.exception("Failed to load pending approvals for agenda")

        # Budgets approaching entry deadline (within 7 days)
        try:
            from datetime import timedelta
            from apps.budgeting.models import Budget
            today = timezone.now().date()
            soon = today + timedelta(days=7)
            qs = Budget.objects.select_related("company", "cost_center").filter(
                company=company,
                entry_enabled=True,
                status=Budget.STATUS_ENTRY_OPEN,
                entry_end_date__isnull=False,
                entry_end_date__gte=today,
                entry_end_date__lte=soon,
            ).order_by("entry_end_date")
            rows = list(
                qs.values(
                    "id",
                    "name",
                    "budget_type",
                    "entry_end_date",
                    "period_start",
                    "period_end",
                )[:50]
            )
            agenda["budgets_due"] = rows
            counts["budgets_due"] = len(rows)
        except Exception:
            logger.exception("Failed to load budgets due for agenda")

        # Purchase Orders pending GRN (overdue vs expected delivery)
        try:
            from apps.procurement.models import PurchaseOrder
            today = timezone.now().date()
            # Heuristic: overdue POs (expected_delivery_date < today) in APPROVED/PARTIAL
            po_qs = (
                PurchaseOrder.objects.select_related("supplier")
                .filter(company=company, expected_delivery_date__lt=today)
                .filter(status__in=["APPROVED", "PARTIAL"])
                .order_by("expected_delivery_date")
            )
            pos = list(
                po_qs.values(
                    "id",
                    "po_number",
                    "supplier__name",
                    "expected_delivery_date",
                    "status",
                )[:50]
            )
            agenda["pos_pending_grn"] = pos
            counts["pos_pending_grn"] = len(pos)
        except Exception:
            logger.exception("Failed to load pending GRNs for agenda")

        # AP bills due within 7 days
        try:
            from datetime import timedelta
            from django.db.models import F
            from apps.finance.models import APBill
            today = timezone.now().date()
            soon = today + timedelta(days=7)
            bills = (
                APBill.objects.select_related("supplier")
                .filter(company=company, status__in=["POSTED", "PARTIAL"], due_date__gte=today, due_date__lte=soon)
                .annotate(outstanding=F("total_amount") - F("amount_paid"))
                .filter(outstanding__gt=0)
                .order_by("due_date")
            )
            rows = list(
                bills.values(
                    "id",
                    "bill_number",
                    "supplier__name",
                    "due_date",
                    "total_amount",
                    "amount_paid",
                )[:50]
            )
            agenda["ap_due"] = rows
            counts["ap_due"] = len(rows)
        except Exception:
            logger.exception("Failed to load AP due for agenda")

        # Proactive suggestions (pending)
        try:
            suggestions = orchestrator.get_pending_suggestions(request.user, company)
            agenda["suggestions"] = [
                {
                    "id": s.id,
                    "title": s.title,
                    "body": s.body,
                    "severity": s.severity,
                    "alert_type": s.alert_type,
                    "created_at": s.created_at.isoformat(),
                }
                for s in suggestions[:20]
            ]
            counts["suggestions"] = suggestions.count()
        except Exception:
            logger.exception("Failed to load AI suggestions for agenda")

        return Response({"agenda": agenda, "counts": counts})


class AIConversationHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversation_id = request.query_params.get("conversation_id")
        limit = request.query_params.get("limit")
        qs_limit = None
        if limit:
            try:
                qs_limit = max(1, min(int(limit), 200))
            except (TypeError, ValueError):
                qs_limit = None

        conversation = None
        if conversation_id:
            try:
                conversation = AIConversation.objects.get(conversation_id=conversation_id, user=request.user)
            except AIConversation.DoesNotExist:
                return Response(
                    {"detail": "conversation not found for user"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            conversation = (
                AIConversation.objects.filter(user=request.user)
                .order_by("-updated_at")
                .first()
            )
            if not conversation:
                return Response({"conversation": None, "messages": []})

        messages_qs = conversation.messages.order_by("created_at")
        if qs_limit:
            messages_qs = messages_qs.reverse()[:qs_limit]
            messages_qs = list(messages_qs)
            messages_qs.reverse()
        else:
            messages_qs = list(messages_qs)

        data = [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "intent": message.intent,
                "confidence": message.confidence,
                "metadata": message.metadata or {},
                "created_at": message.created_at.isoformat(),
            }
            for message in messages_qs
        ]
        return Response(
            {
                "conversation": {
                    "id": str(conversation.conversation_id),
                    "active_skill": conversation.active_skill,
                    "updated_at": conversation.updated_at.isoformat(),
                },
                "messages": data,
            }
        )


class AITrainingExampleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (getattr(request.user, "is_system_admin", False) or request.user.is_staff):
            return Response(status=status.HTTP_403_FORBIDDEN)

        status_filter = request.query_params.get("status")
        qs = AITrainingExample.objects.select_related("company", "user")
        if status_filter:
            qs = qs.filter(status=status_filter)
        else:
            qs = qs.filter(status=AITrainingExampleStatus.REVIEW)

        limit = request.query_params.get("limit")
        if limit:
            try:
                qs = qs[: max(1, min(int(limit), 500))]
            except (TypeError, ValueError):
                qs = qs[:200]
        else:
            qs = qs[:200]

        payload = [
            {
                "id": example.id,
                "prompt": example.prompt,
                "completion": example.completion,
                "status": example.status,
                "source": example.source,
                "metadata": example.metadata,
                "review_notes": example.review_notes,
                "reviewed_at": example.reviewed_at.isoformat() if example.reviewed_at else None,
                "reviewed_by": {
                    "id": getattr(example.reviewed_by, "id", None),
                    "name": (
                        example.reviewed_by.get_full_name()
                        if getattr(example.reviewed_by, "get_full_name", None)
                        else getattr(example.reviewed_by, "username", None)
                    ),
                } if example.reviewed_by else None,
                "company": {
                    "id": getattr(example.company, "id", None),
                    "code": getattr(example.company, "code", None),
                    "name": getattr(example.company, "name", None),
                },
                "user": {
                    "id": getattr(example.user, "id", None),
                    "name": getattr(example.user, "get_full_name", lambda: None)() or getattr(example.user, "username", None),
                },
                "updated_at": example.updated_at.isoformat() if example.updated_at else None,
            }
            for example in qs
        ]
        return Response({"results": payload})


class AITrainingExampleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk: int):
        if not (getattr(request.user, "is_system_admin", False) or request.user.is_staff):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            example = AITrainingExample.objects.select_related("company").get(pk=pk)
        except AITrainingExample.DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status")
        if new_status not in AITrainingExampleStatus.values:
            return Response(
                {"detail": f"status must be one of {', '.join(AITrainingExampleStatus.values)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        metadata_updates = request.data.get("metadata") or {}
        notes = request.data.get("notes")
        status_changed = example.status != new_status
        example.status = new_status
        if metadata_updates:
            merged = {**example.metadata, **metadata_updates}
            example.metadata = merged
        update_fields = ["status", "metadata", "updated_at"]
        if notes is not None:
            example.review_notes = notes
            update_fields.append("review_notes")
        if status_changed or notes is not None:
            example.reviewed_by = request.user
            example.reviewed_at = timezone.now()
            update_fields.extend(["reviewed_by", "reviewed_at"])
        example.save(update_fields=update_fields)

        orchestrator.telemetry.record_event(
            event_type=f"training_example.{new_status}",
            user=request.user,
            company=example.company,
            payload={
                "example_id": example.id,
                "source": example.source,
                "status": new_status,
                "notes": example.review_notes,
            },
        )

        return Response(
            {
                "id": example.id,
                "status": example.status,
                "metadata": example.metadata,
                "updated_at": example.updated_at.isoformat() if example.updated_at else None,
                "review_notes": example.review_notes,
                "reviewed_at": example.reviewed_at.isoformat() if example.reviewed_at else None,
                "reviewed_by": {
                    "id": getattr(example.reviewed_by, "id", None),
                    "name": (
                        example.reviewed_by.get_full_name()
                        if getattr(example.reviewed_by, "get_full_name", None)
                        else getattr(example.reviewed_by, "username", None)
                    ),
                }
                if example.reviewed_by
                else None,
            }
        )


class AITrainingExampleBulkUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not (getattr(request.user, "is_system_admin", False) or request.user.is_staff):
            return Response(status=status.HTTP_403_FORBIDDEN)

        ids = request.data.get("ids") or []
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids must be a non-empty list"}, status=status.HTTP_400_BAD_REQUEST)

        status_value = request.data.get("status")
        if status_value not in AITrainingExampleStatus.values:
            return Response(
                {"detail": f"status must be one of {', '.join(AITrainingExampleStatus.values)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        notes = request.data.get("notes")
        metadata_updates = request.data.get("metadata") or {}
        now = timezone.now()

        examples = AITrainingExample.objects.filter(id__in=ids).select_related("company")
        updated = 0
        for example in examples:
            status_changed = example.status != status_value
            example.status = status_value
            if metadata_updates:
                merged = {**example.metadata, **metadata_updates}
                example.metadata = merged
            update_fields = ["status", "metadata", "updated_at"]
            if notes is not None:
                example.review_notes = notes
                update_fields.append("review_notes")
            if status_changed or notes is not None:
                example.reviewed_by = request.user
                example.reviewed_at = now
                update_fields.extend(["reviewed_by", "reviewed_at"])
            example.save(update_fields=update_fields)
            orchestrator.telemetry.record_event(
                event_type=f"training_example.{status_value}",
                user=request.user,
                company=example.company,
                payload={
                    "example_id": example.id,
                    "source": example.source,
                    "status": status_value,
                    "notes": example.review_notes,
                },
            )
            updated += 1

        return Response({"updated": updated})


class AILoRARunView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (getattr(request.user, "is_system_admin", False) or request.user.is_staff):
            return Response(status=status.HTTP_403_FORBIDDEN)

        limit = request.query_params.get("limit")
        try:
            limit_value = max(1, min(int(limit), 100))
        except (TypeError, ValueError):
            limit_value = 25

        runs = (
            AILoRARun.objects.select_related("triggered_by")
            .order_by("-created_at")[:limit_value]
        )
        payload = []
        for run in runs:
            user = run.triggered_by
            payload.append(
                {
                    "id": run.id,
                    "run_id": str(run.run_id),
                    "status": run.status,
                    "adapter_type": run.adapter_type,
                    "dataset_size": run.dataset_size,
                    "scheduled_for": run.scheduled_for.isoformat() if run.scheduled_for else None,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                    "artifact_path": run.artifact_path,
                    "metrics": run.metrics,
                    "error": run.error,
                    "triggered_by": {
                        "id": getattr(user, "id", None),
                        "name": (
                            user.get_full_name() if user and user.get_full_name() else getattr(user, "username", None)
                        ),
                    },
                }
            )
        return Response({"results": payload})


class AILoRARunView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (getattr(request.user, "is_system_admin", False) or request.user.is_staff):
            return Response(status=status.HTTP_403_FORBIDDEN)

        limit = request.query_params.get("limit")
        try:
            limit_value = max(1, min(int(limit), 100))
        except (TypeError, ValueError):
            limit_value = 25

        runs = (
            AILoRARun.objects.select_related("triggered_by")
            .order_by('-created_at')[:limit_value]
        )
        payload = []
        for run in runs:
            user = run.triggered_by
            payload.append(
                {
                    'id': run.id,
                    'run_id': str(run.run_id),
                    'status': run.status,
                    'adapter_type': run.adapter_type,
                    'dataset_size': run.dataset_size,
                    'scheduled_for': run.scheduled_for.isoformat() if run.scheduled_for else None,
                    'started_at': run.started_at.isoformat() if run.started_at else None,
                    'finished_at': run.finished_at.isoformat() if run.finished_at else None,
                    'artifact_path': run.artifact_path,
                    'metrics': run.metrics,
                    'error': run.error,
                    'triggered_by': {
                        'id': getattr(user, 'id', None),
                        'name': (
                            user.get_full_name() if user and user.get_full_name() else getattr(user, 'username', None)
                        ),
                    },
                }
            )
        return Response({'results': payload})

    def post(self, request):
        if not (getattr(request.user, "is_system_admin", False) or request.user.is_staff):
            return Response(status=status.HTTP_403_FORBIDDEN)

        adapter_type = request.data.get("adapter_type") or "lora"
        dataset_limit = request.data.get("dataset_limit") or 200
        try:
            dataset_limit_value = max(1, min(int(dataset_limit), 1000))
        except (TypeError, ValueError):
            dataset_limit_value = 200

        run = AILoRARun.objects.create(
            adapter_type=adapter_type,
            status=AILoRARunStatus.QUEUED,
            scheduled_for=timezone.now(),
            training_args={"dataset_limit": dataset_limit_value, "adapter_type": adapter_type},
            triggered_by=request.user if request.user.is_authenticated else None,
        )

        from .tasks import execute_lora_training_run

        execute_lora_training_run.delay(run.id)
        return Response(
            {
                "run_id": str(run.run_id),
                "status": run.status,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class AIPreferenceListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request, "company", None)
        scope = (request.query_params.get("scope") or "").lower()

        queryset = (
            UserAIPreference.objects.filter(user=request.user)
            .select_related("company")
            .order_by("-updated_at")
        )

        if scope == "global":
            queryset = queryset.filter(company__isnull=True)
        elif scope == "company":
            if company:
                queryset = queryset.filter(company=company)
            else:
                queryset = queryset.none()
        elif company:
            queryset = queryset.filter(Q(company__isnull=True) | Q(company=company))

        serializer = AIPreferenceSerializer(queryset, many=True, context={"request": request})
        return Response({"results": serializer.data})

    def post(self, request):
        serializer = AIPreferenceSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        scope = (request.data.get("scope") or "").lower()
        company = serializer.validated_data.get("company")
        if scope == "global":
            company = None
        elif company is None:
            company = getattr(request, "company", None)

        if company and not request.user.has_company_access(company):
            return Response(
                {"detail": "You do not have access to that company."},
                status=status.HTTP_403_FORBIDDEN,
            )

        pref, created = UserAIPreference.objects.update_or_create(
            user=request.user,
            company=company,
            key=serializer.validated_data["key"],
            defaults={
                "value": serializer.validated_data["value"],
                "source": "manual",
            },
        )
        pref.refresh_from_db()

        log_audit_event(
            user=request.user,
            company=company,
            company_group=getattr(company, "company_group", None) if company else None,
            action="AI_PREF_SET",
            entity_type="AI_PREFERENCE",
            entity_id=pref.key,
            description="Preference created" if created else "Preference updated",
            after={"value": pref.value, "scope": pref.scope},
        )

        payload = AIPreferenceSerializer(pref, context={"request": request}).data
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(payload, status=status_code)


class AIPreferenceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        preference = get_object_or_404(UserAIPreference, id=pk, user=request.user)
        serializer = AIPreferenceSerializer(
            preference,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        updated_data = serializer.validated_data
        company = preference.company

        if "company" in updated_data:
            company = updated_data["company"]
            if company and not request.user.has_company_access(company):
                return Response(
                    {"detail": "You do not have access to that company."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            preference.company = company
            preference.company_group = getattr(company, "company_group", None) if company else None

        if "value" in updated_data:
            preference.value = updated_data["value"]

        preference.save()

        log_audit_event(
            user=request.user,
            company=company,
            company_group=getattr(company, "company_group", None) if company else None,
            action="AI_PREF_SET",
            entity_type="AI_PREFERENCE",
            entity_id=preference.key,
            description="Preference updated",
            after={"value": preference.value, "scope": preference.scope},
        )

        payload = AIPreferenceSerializer(preference, context={"request": request}).data
        return Response(payload, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        preference = get_object_or_404(UserAIPreference, id=pk, user=request.user)
        company = preference.company
        key = preference.key
        preference.delete()

        log_audit_event(
            user=request.user,
            company=company,
            company_group=getattr(company, "company_group", None) if company else None,
            action="AI_PREF_SET",
            entity_type="AI_PREFERENCE",
            entity_id=key,
            description="Preference deleted",
            after={"deleted": True},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AIActionExecuteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        action_name = request.data.get("action")
        payload = request.data.get("payload") or {}
        if not action_name:
            return Response({"detail": "action is required."}, status=status.HTTP_400_BAD_REQUEST)

        state = ACTION_RATE_LIMITER.check(identity=request.user.id)
        if not state.allowed:
            retry_after = max(int((state.reset_at - timezone.now()).total_seconds()), 1)
            headers = {"Retry-After": str(retry_after)}
            return Response(
                {"detail": "Too many AI actions. Please wait before retrying."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers=headers,
            )

        company = getattr(request, "company", None)
        company_id = request.data.get("company_id")
        if company_id:
            company = request.user.companies.filter(id=company_id, is_active=True).first()
            if not company:
                return Response(
                    {"detail": "You do not have access to that company."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        if company is None:
            company = request.user.companies.filter(is_active=True).first()

        context = ActionContext(user=request.user, company=company)
        try:
            result = execute_action(action_name, context=context, payload=payload)
        except ActionExecutionError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"status": "ok", "result": result})


class AIWorkflowExplainView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        instance_id = request.query_params.get("instance_id")
        if not instance_id:
            return Response({"detail": "instance_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        instance = get_object_or_404(
            WorkflowInstance.objects.select_related("template", "company"),
            id=instance_id,
        )
        if instance.company and not request.user.has_company_access(instance.company):
            return Response(
                {"detail": "You do not have access to this workflow instance."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = explain_instance(instance)
        return Response(data)


class AIMetadataInterestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        kind = (request.data.get("kind") or "").lower()
        entity = request.data.get("entity")
        if kind not in {"field", "dashboard"} or not entity:
            return Response(
                {"detail": "kind ('field' or 'dashboard') and entity are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        telemetry = TelemetryService()
        company = getattr(request, "company", None)
        payload = {"entity": entity}
        if kind == "field":
            payload["definition_key"] = request.data.get("definition_key") or entity
            payload["field_name"] = request.data.get("field") or request.data.get("field_name")
            payload["field_label"] = request.data.get("field_label")
            payload["field_type"] = request.data.get("field_type")
            event_type = "metadata.field_interest"
        else:
            payload["widget_id"] = request.data.get("widget_id") or entity
            payload["widget_title"] = request.data.get("widget_title")
            event_type = "metadata.dashboard_interest"

        telemetry.record_event(
            event_type=event_type,
            user=request.user,
            company=company,
            payload=payload,
        )
        return Response({"status": "queued"}, status=status.HTTP_202_ACCEPTED)


class AIOpsMetricsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (request.user.is_staff or getattr(request.user, "is_system_admin", False)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        window_hours_param = request.query_params.get("window_hours")
        window_hours = _positive_int(window_hours_param, 24)
        window_hours = min(window_hours, 168)  # clamp to 7 days
        horizon = timezone.now() - timedelta(hours=window_hours)

        conversations_active = AIConversation.objects.filter(updated_at__gte=horizon).count()
        actions_total = AIActionExecution.objects.filter(created_at__gte=horizon).count()
        actions_errors = AIActionExecution.objects.filter(
            status="error",
            created_at__gte=horizon,
        ).count()
        suggestions_pending = AIProactiveSuggestion.objects.filter(status="pending").count()
        suggestions_recent = AIProactiveSuggestion.objects.filter(updated_at__gte=horizon).count()
        telemetry_events = AITelemetryEvent.objects.filter(created_at__gte=horizon).count()

        data = {
            "window_hours": window_hours,
            "conversations_active": conversations_active,
            "actions": {
                "total": actions_total,
                "errors": actions_errors,
                "rate_limit": {
                    "limit": ACTION_RATE_LIMITER.limit,
                    "window_seconds": ACTION_RATE_LIMITER.window_seconds,
                },
            },
            "suggestions": {
                "pending": suggestions_pending,
                "recent": suggestions_recent,
            },
            "telemetry_events": telemetry_events,
        }
        return Response(data, status=status.HTTP_200_OK)
