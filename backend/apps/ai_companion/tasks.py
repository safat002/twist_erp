import json
import logging
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count
from apps.data_migration.models import MigrationJob, migration_enums
from apps.metadata.models import MetadataDefinition
from apps.budgeting.models import Budget
from apps.workflows.models import WorkflowInstance
from .models import (
    AIProactiveSuggestion,
    AITelemetryEvent,
    AITrainingExampleStatus,
    AILoRARun,
    AILoRARunStatus,
)
from .services import orchestrator
from .services.alert_engine import AlertEngine
from .services.memory import MemoryRecord
from .services.telemetry import TelemetryService

logger = logging.getLogger(__name__)


@shared_task(name="apps.ai_companion.tasks.detect_anomalies")
def detect_anomalies():
    """Placeholder anomaly detection task."""
    try:
        logger.info("AI Companion: Running anomaly detection job")
        return {"status": "ok", "message": "Anomaly detection executed"}
    except Exception as exc:
        logger.exception("AI Companion anomaly detection failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def _generate_metadata_suggestions(window_start):
    created = 0
    field_events = (
        AITelemetryEvent.objects.filter(
            event_type="metadata.field_interest",
            created_at__gte=window_start,
        )
        .values(
            "user_id",
            "company_id",
            "payload__definition_key",
            "payload__field_name",
            "payload__field_label",
            "payload__field_type",
        )
        .annotate(total=Count("id"))
    )
    for event in field_events:
        if event["total"] < 3:
            continue
        definition_key = event["payload__definition_key"]
        field_name = event["payload__field_name"]
        definition = (
            MetadataDefinition.objects.filter(key=definition_key, status="active")
            .order_by("-version")
            .first()
        )
        if not definition:
            continue

        existing_fields = (definition.definition or {}).get("fields") or []
        if any(f.get("name") == field_name for f in existing_fields):
            continue

        user_id = event["user_id"]
        company_id = event["company_id"]
        exists = AIProactiveSuggestion.objects.filter(
            user_id=user_id,
            company_id=company_id,
            metadata__rule_code="metadata.promote_field",
            metadata__definition_key=definition_key,
            metadata__field_name=field_name,
            status="pending",
        ).exists()
        if exists:
            continue

        label = event["payload__field_label"] or field_name.replace("_", " ").title()
        field_type = event["payload__field_type"] or "text"
        metadata_payload = {
            "rule_code": "metadata.promote_field",
            "definition_key": definition_key,
            "field_name": field_name,
            "field_label": label,
            "actions": [
                {
                    "label": f"Promote '{label}' field",
                    "action": "ai.execute",
                    "requires_confirmation": True,
                    "confirmation_text": f"Promote field '{label}' to {definition_key}?",
                    "payload": {
                        "action_name": "metadata.promote_field",
                        "parameters": {
                            "definition_key": definition_key,
                            "field": {
                                "name": field_name,
                                "label": label,
                                "type": field_type,
                                "required": False,
                            },
                        },
                    },
                }
            ],
        }
        AIProactiveSuggestion.objects.create(
            user_id=user_id,
            company_id=company_id,
            title=f"Promote new field '{label}'",
            body=f"Field '{label}' is frequently referenced. Consider promoting it in {definition_key}.",
            metadata=metadata_payload,
            alert_type="metadata",
            severity=AIProactiveSuggestion.AlertSeverity.INFO,
            source_skill="metadata_engine",
        )
        created += 1

    dashboard_events = (
        AITelemetryEvent.objects.filter(
            event_type="metadata.dashboard_interest",
            created_at__gte=window_start,
        )
        .values(
            "user_id",
            "company_id",
            "payload__widget_id",
            "payload__widget_title",
        )
        .annotate(total=Count("id"))
    )
    for event in dashboard_events:
        if event["total"] < 3:
            continue
        user_id = event["user_id"]
        company_id = event["company_id"]
        widget_id = event["payload__widget_id"]
        title = event["payload__widget_title"] or widget_id

        exists = AIProactiveSuggestion.objects.filter(
            user_id=user_id,
            company_id=company_id,
            metadata__rule_code="metadata.dashboard_widget",
            metadata__widget_id=widget_id,
            status="pending",
        ).exists()
        if exists:
            continue

        metadata_payload = {
            "rule_code": "metadata.dashboard_widget",
            "widget_id": widget_id,
            "actions": [
                {
                    "label": f"Add widget '{title}'",
                    "action": "ai.execute",
                    "requires_confirmation": False,
                    "payload": {
                        "action_name": "metadata.create_dashboard_widget",
                        "parameters": {
                            "widget": {"id": widget_id, "title": title},
                        },
                    },
                }
            ],
        }
        AIProactiveSuggestion.objects.create(
            user_id=user_id,
            company_id=company_id,
            title=f"Add dashboard widget '{title}'",
            body=f"Users frequently request dashboard widget '{title}'.",
            metadata=metadata_payload,
            alert_type="metadata",
            severity=AIProactiveSuggestion.AlertSeverity.INFO,
            source_skill="metadata_engine",
        )
        created += 1

    return created
@shared_task(name="apps.ai_companion.tasks.generate_proactive_suggestions")
def generate_proactive_suggestions():
    """
    Periodically scans ERP signals (currently data migration) and raises proactive hints.
    """
    try:
        engine = AlertEngine()
        engine_created = engine.run()

        now = timezone.now()
        window_start = now - timedelta(hours=12)

        jobs = (
            MigrationJob.objects.filter(
                status__in=[
                    migration_enums.MigrationJobStatus.VALIDATED,
                    migration_enums.MigrationJobStatus.AWAITING_APPROVAL,
                    migration_enums.MigrationJobStatus.ERROR,
                ],
                updated_at__gte=window_start,
            )
            .select_related("company", "created_by")
            .all()
        )

        migration_created = 0
        for job in jobs:
            invalid_rows = job.staging_rows.filter(status=migration_enums.StagingRowStatus.INVALID).count()
            if invalid_rows == 0 or job.created_by is None:
                continue

            exists = AIProactiveSuggestion.objects.filter(
                user=job.created_by,
                company=job.company,
                metadata__job_id=str(job.id),
                status="pending",
            ).exists()
            if exists:
                continue

            AIProactiveSuggestion.objects.create(
                user=job.created_by,
                company=job.company,
                title="Migration rows need review",
                body=f"{invalid_rows} rows in migration job {job.migration_job_id} still require attention.",
                metadata={"job_id": str(job.id)},
                source_skill="data_migration",
                alert_type="data_migration",
                severity=AIProactiveSuggestion.AlertSeverity.WARNING,
            )
            migration_created += 1

        telemetry_events = (
            AITelemetryEvent.objects.filter(
                event_type__in=["workflow.bottleneck", "budget.threshold", "budget.breach"],
                created_at__gte=window_start,
            )
            .select_related("user", "company")
        )

        telemetry_created = 0
        for event in telemetry_events:
            if event.user is None:
                continue
            metadata = event.payload or {}
            exists = AIProactiveSuggestion.objects.filter(
                user=event.user,
                company=event.company,
                metadata__telemetry_event_id=event.id,
                status="pending",
            ).exists()
            if exists:
                continue

            title = "AI Insight"
            body = "Review recent activity for more details."
            severity = AIProactiveSuggestion.AlertSeverity.INFO
            actions = []

            if event.event_type == "workflow.bottleneck":
                workflow_name = metadata.get("workflow") or "Workflow"
                state = metadata.get("state") or "current state"
                hours = metadata.get("hours_in_state")
                transitions = metadata.get("available_transitions") or []
                hours_display = f"{hours:.1f}" if isinstance(hours, (int, float)) else hours
                title = f"{workflow_name} is stalled"
                body = (
                    f"The {workflow_name} workflow has been sitting in '{state}' for"
                    f" approximately {hours_display} hour(s)."
                )
                if transitions:
                    body += f" Next possible states: {', '.join(transitions)}."
                if isinstance(hours, (int, float)) and hours >= 24:
                    severity = AIProactiveSuggestion.AlertSeverity.CRITICAL
                else:
                    severity = AIProactiveSuggestion.AlertSeverity.WARNING
                instance_id = metadata.get("instance_id")
                if instance_id:
                    actions.append(
                        {
                            "label": "Explain workflow",
                            "action": "ai.execute",
                            "requires_confirmation": False,
                            "payload": {
                                "action_name": "workflows.explain_instance",
                                "parameters": {"workflow_instance_id": instance_id},
                            },
                        }
                    )
            elif event.event_type == "budget.threshold":
                cc_code = metadata.get("cost_center_code") or metadata.get("cost_center") or "Cost Center"
                fiscal_year = metadata.get("fiscal_year") or ""
                utilisation = metadata.get("utilization_pct")
                threshold = metadata.get("threshold_pct")
                utilisation_display = (
                    f"{utilisation:.1f}%" if isinstance(utilisation, (int, float)) else utilisation
                )
                threshold_display = (
                    f"{threshold:.0f}%" if isinstance(threshold, (int, float)) else threshold
                )
                title = f"Budget nearing threshold for {cc_code}"
                body = (
                    f"{cc_code} ({fiscal_year}) is at {utilisation_display} of its allocation."
                    f" Threshold is set at {threshold_display}. Consider reviewing planned spend."
                )
                severity = AIProactiveSuggestion.AlertSeverity.WARNING
            elif event.event_type == "budget.breach":
                cc_code = metadata.get("cost_center_code") or metadata.get("cost_center") or "Cost Center"
                fiscal_year = metadata.get("fiscal_year") or ""
                utilisation = metadata.get("utilization_pct")
                overrun = metadata.get("overrun_amount")
                utilisation_display = (
                    f"{utilisation:.1f}%" if isinstance(utilisation, (int, float)) else utilisation
                )
                overrun_display = f"{overrun}" if overrun is not None else "the remaining buffer"
                title = f"Budget overrun detected for {cc_code}"
                body = (
                    f"{cc_code} ({fiscal_year}) has exceeded its allocation at {utilisation_display}."
                    f" Overrun amount: {overrun_display}. Initiate corrective actions."
                )
                severity = AIProactiveSuggestion.AlertSeverity.CRITICAL

            metadata_payload = {**metadata, "telemetry_event_id": event.id}
            if actions:
                metadata_payload["actions"] = actions
            AIProactiveSuggestion.objects.create(
                user=event.user,
                company=event.company,
                title=title,
                body=body,
                metadata=metadata_payload,
                source_skill="telemetry",
                alert_type="insight",
                severity=severity,
            )
            telemetry_created += 1

        metadata_created = _generate_metadata_suggestions(window_start)

        logger.info(
            "AI Companion: proactive alerts generated engine=%s migration=%s telemetry=%s",
            engine_created,
            migration_created,
            telemetry_created,
        )
        return {
            "status": "ok",
            "alerts_created": engine_created,
            "migration_created": migration_created,
            "telemetry_created": telemetry_created,
            "metadata_created": metadata_created,
        }
    except Exception as exc:
        logger.exception("AI proactive suggestion generation failed: %s", exc)
        return {"status": "error", "error": str(exc)}


@shared_task(name="apps.ai_companion.tasks.monitor_workflow_bottlenecks")
def monitor_workflow_bottlenecks(stale_hours: int = 12):
    """
    Scan workflow instances for stages that have remained unchanged beyond the configured window and emit telemetry.
    """
    telemetry = TelemetryService()
    try:
        now = timezone.now()
        cutoff = now - timedelta(hours=stale_hours)
        instances = (
            WorkflowInstance.objects.select_related("template", "company")
            .filter(updated_at__lte=cutoff)
        )

        events_created = 0
        for instance in instances:
            template = instance.template
            if template is None:
                continue
            definition = template.definition or {}
            transitions = definition.get("transitions") or {}
            next_states = transitions.get(instance.state) or []
            if not next_states:
                # No onward transitions, treat as terminal state
                continue

            hours_in_state = (
                (now - instance.updated_at).total_seconds() / 3600.0 if instance.updated_at else float(stale_hours)
            )
            payload = {
                "instance_id": instance.id,
                "workflow": template.name,
                "state": instance.state,
                "hours_in_state": round(hours_in_state, 2),
                "available_transitions": next_states,
            }

            if telemetry.event_exists(
                event_type="workflow.bottleneck",
                company=instance.company,
                payload_filters={"instance_id": instance.id, "state": instance.state},
                within_hours=stale_hours,
            ):
                continue

            events = telemetry.broadcast_event(
                event_type="workflow.bottleneck",
                company=instance.company,
                payload=payload,
                preferred_roles=["Workflow Admin", "Operations Manager"],
            )
            events_created += len(events)

        logger.info("AI Companion: workflow bottleneck telemetry events created=%s", events_created)
        return {"status": "ok", "events": events_created}
    except Exception as exc:
        logger.exception("AI workflow bottleneck monitoring failed: %s", exc)
        return {"status": "error", "error": str(exc)}


@shared_task(name="apps.ai_companion.tasks.monitor_budget_health")
def monitor_budget_health(default_threshold: int = 90):
    """
    Emit telemetry when budgets approach or exceed their configured utilisation thresholds.
    """
    telemetry = TelemetryService()
    try:
        budgets = Budget.objects.select_related("cost_center", "company").filter(status=Budget.STATUS_ACTIVE)
        results = {"threshold": 0, "breach": 0}

        for budget in budgets:
            amount = Decimal(budget.amount or 0)
            consumed = Decimal(budget.consumed or 0)
            if amount <= 0:
                continue

            utilisation_pct = float((consumed / amount) * Decimal("100"))
            threshold = budget.threshold_percent or default_threshold
            event_type = None
            overrun_amount = None
            if consumed >= amount:
                event_type = "budget.breach"
                overrun_amount = str(consumed - amount)
            elif utilisation_pct >= threshold:
                event_type = "budget.threshold"
            else:
                continue

            payload_filters = {
                "budget_id": budget.id,
                "fiscal_year": budget.fiscal_year,
            }
            if telemetry.event_exists(
                event_type=event_type,
                company=budget.company,
                payload_filters=payload_filters,
                within_hours=24,
            ):
                continue

            payload = {
                "budget_id": budget.id,
                "cost_center_id": budget.cost_center_id,
                "cost_center_code": getattr(budget.cost_center, "code", None),
                "fiscal_year": budget.fiscal_year,
                "threshold_pct": threshold,
                "utilization_pct": utilisation_pct,
            }
            if overrun_amount is not None:
                payload["overrun_amount"] = overrun_amount

            events = telemetry.broadcast_event(
                event_type=event_type,
                company=budget.company,
                payload=payload,
                preferred_roles=["Finance Manager", "Finance Controller"],
            )
            if events:
                key = "breach" if event_type.endswith("breach") else "threshold"
                results[key] += len(events)

        logger.info(
            "AI Companion: budget telemetry events created threshold=%s breach=%s",
            results["threshold"],
            results["breach"],
        )
        return {"status": "ok", **results}
    except Exception as exc:
        logger.exception("AI budget health monitoring failed: %s", exc)
        return {"status": "error", "error": str(exc)}


@shared_task(name="apps.ai_companion.tasks.ingest_policy_documents")
def ingest_policy_documents(company_id: int | None = None):
    """
    Index policy documents for the requested company (or all companies) and refresh guardrail tests.
    """
    try:
        from apps.companies.models import Company

        if company_id:
            companies = Company.objects.filter(pk=company_id)
        else:
            companies = Company.objects.all()

        total_companies = 0
        total_documents = 0
        total_guardrails = 0

        from .services.policy_ingestion import ingest_policy_corpus_for_company

        for company in companies:
            documents_indexed, guardrails_synced = ingest_policy_corpus_for_company(company=company)
            total_companies += 1
            total_documents += documents_indexed
            total_guardrails += guardrails_synced

        if company_id is None:
            global_docs, global_guardrails = ingest_policy_corpus_for_company(company=None)
            total_documents += global_docs
            total_guardrails += global_guardrails

        logger.info(
            "AI Companion: policy ingestion complete companies=%s documents=%s guardrails=%s",
            total_companies,
            total_documents,
            total_guardrails,
        )
        return {
            "status": "ok",
            "companies": total_companies,
            "documents": total_documents,
            "guardrails": total_guardrails,
        }
    except Exception as exc:
        logger.exception("AI policy ingestion failed: %s", exc)
        return {"status": "error", "error": str(exc)}


@shared_task(name="apps.ai_companion.tasks.train_memory")
def train_memory(user_id: int, scope: str, key: str, value: dict, company_id: int = None):
    """
    Background helper to persist memory records without blocking the request.
    """
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("AI memory training cancelled: user %s missing", user_id)
        return

    company = None
    if company_id:
        from apps.companies.models import Company

        try:
            company = Company.objects.get(pk=company_id)
        except Company.DoesNotExist:
            logger.warning("AI memory training: company %s missing", company_id)

    orchestrator.memory.save(
        MemoryRecord(
            key=key,
            value=value,
            scope=scope,
            user=user,
            company=company,
        )
    )


@shared_task(name="apps.ai_companion.tasks.compile_training_dataset")
def compile_training_dataset(limit: int = 200):
    """
    Bundles approved training examples into a payload suitable for downstream fine-tuning.
    """
    try:
        from .services.training_export import build_training_dataset

        dataset = build_training_dataset(limit=limit)
        logger.info("AI Companion: prepared %s training examples for export", dataset["count"])
        return {"status": "ok", "examples": dataset["count"]}
    except Exception as exc:
        logger.exception("AI training dataset compilation failed: %s", exc)
        return {"status": "error", "error": str(exc)}


@shared_task(name="apps.ai_companion.tasks.schedule_lora_training_runs")
def schedule_lora_training_runs(adapter_type: str = "lora", dataset_limit: int = 200):
    """
    Schedule a LoRA/adapter fine-tuning job and enqueue the execution task.
    """
    try:
        run = AILoRARun.objects.create(
            adapter_type=adapter_type,
            status=AILoRARunStatus.QUEUED,
            scheduled_for=timezone.now(),
            training_args={"dataset_limit": dataset_limit, "adapter_type": adapter_type},
        )
        execute_lora_training_run.delay(run.id)
        logger.info("AI Companion: scheduled LoRA run %s", run.run_id)
        return {"status": "ok", "run_id": str(run.run_id)}
    except Exception as exc:
        logger.exception("AI LoRA scheduling failed: %s", exc)
        return {"status": "error", "error": str(exc)}


@shared_task(name="apps.ai_companion.tasks.execute_lora_training_run")
def execute_lora_training_run(run_pk: int):
    """
    Execute a LoRA/adapter fine-tuning run using the latest approved training dataset.
    """
    try:
        run = AILoRARun.objects.get(pk=run_pk)
    except AILoRARun.DoesNotExist:
        logger.warning("AI LoRA run %s not found", run_pk)
        return {"status": "error", "error": "run_not_found"}

    if run.status == AILoRARunStatus.RUNNING:
        return {"status": "ok", "run_id": str(run.run_id), "message": "already_running"}

    run.status = AILoRARunStatus.RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at", "updated_at"])

    try:
        from .services.training_export import build_training_dataset

        dataset = build_training_dataset(limit=run.training_args.get("dataset_limit", 200))
        run.dataset_size = dataset["count"]
        run.dataset_snapshot = dataset["records"][:20]

        if dataset["count"] == 0:
            run.status = AILoRARunStatus.FAILED
            run.error = "No approved training examples available."
            run.finished_at = timezone.now()
            run.save(
                update_fields=["status", "error", "finished_at", "dataset_size", "dataset_snapshot", "updated_at"]
            )
            return {"status": "error", "error": "empty_dataset", "run_id": str(run.run_id)}

        export_dir = Path(settings.BASE_DIR) / "chroma_db" / "training_runs"
        export_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = export_dir / f"{run.run_id}.json"
        artifact_path.write_text(json.dumps(dataset["records"], indent=2))

        run.artifact_path = str(artifact_path)
        run.metrics = {
            "adapter_type": run.adapter_type,
            "examples": dataset["count"],
        }
        run.status = AILoRARunStatus.SUCCESS
        run.finished_at = timezone.now()
        run.save(
            update_fields=[
                "status",
                "finished_at",
                "dataset_size",
                "dataset_snapshot",
                "artifact_path",
                "metrics",
                "updated_at",
            ]
        )
        logger.info("AI Companion: LoRA run %s completed", run.run_id)
        return {"status": "ok", "run_id": str(run.run_id), "examples": dataset["count"]}
    except Exception as exc:
        run.status = AILoRARunStatus.FAILED
        run.error = str(exc)
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "error", "finished_at", "updated_at"])
        logger.exception("AI LoRA run %s failed: %s", run.run_id, exc)
        return {"status": "error", "error": str(exc), "run_id": str(run.run_id)}


@shared_task(name="apps.ai_companion.tasks.reset_api_key_daily_counters")
def reset_api_key_daily_counters():
    """
    Reset daily request counters for all Gemini API keys.
    Should run once per day at midnight.
    """
    try:
        from .models import GeminiAPIKey

        keys = GeminiAPIKey.objects.all()
        reset_count = 0

        for key in keys:
            key.reset_daily_counter()
            reset_count += 1

        logger.info(f"AI Companion: Reset daily counters for {reset_count} API key(s)")
        return {"status": "ok", "keys_reset": reset_count}

    except Exception as exc:
        logger.exception("AI Companion: Failed to reset daily counters: %s", exc)
        return {"status": "error", "error": str(exc)}


@shared_task(name="apps.ai_companion.tasks.reset_api_key_minute_counters")
def reset_api_key_minute_counters():
    """
    Reset per-minute request counters for all Gemini API keys.
    Should run every minute.
    """
    try:
        from .models import GeminiAPIKey

        keys = GeminiAPIKey.objects.all()
        reset_count = 0

        for key in keys:
            key.reset_minute_counter()
            reset_count += 1

        logger.debug(f"AI Companion: Reset minute counters for {reset_count} API key(s)")
        return {"status": "ok", "keys_reset": reset_count}

    except Exception as exc:
        logger.exception("AI Companion: Failed to reset minute counters: %s", exc)
        return {"status": "error", "error": str(exc)}


@shared_task(name="apps.ai_companion.tasks.cleanup_old_api_logs")
def cleanup_old_api_logs(days_to_keep=30):
    """
    Clean up old API key usage logs to prevent database bloat.
    Keeps only the last N days of logs.
    """
    try:
        from .models import APIKeyUsageLog

        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        deleted_count, _ = APIKeyUsageLog.objects.filter(created_at__lt=cutoff_date).delete()

        logger.info(f"AI Companion: Deleted {deleted_count} old API usage log(s)")
        return {"status": "ok", "deleted": deleted_count}

    except Exception as exc:
        logger.exception("AI Companion: Failed to cleanup old API logs: %s", exc)
        return {"status": "error", "error": str(exc)}
