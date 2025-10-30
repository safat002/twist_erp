from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction

from ..models import MigrationJob, migration_enums
from ..services import MigrationPipeline


def _get_job(job_id: int) -> MigrationJob:
    return MigrationJob.objects.select_related("company", "company_group").get(pk=job_id)


def _handle_task_error(job: MigrationJob, exc: Exception):
    job.mark_status(migration_enums.MigrationJobStatus.ERROR, notes=str(exc))


@shared_task(bind=True)
def profile_migration_job(self, job_id: int):
    """
    Run detection + column profiling + auto field mapping.
    """
    job = _get_job(job_id)
    pipeline = MigrationPipeline(job)
    try:
        df = pipeline.profile_files()
        pipeline.generate_field_mappings(detected_df=df)
        return {
            "status": "success",
            "rows": len(df),
            "columns": len(df.columns),
        }
    except Exception as exc:
        _handle_task_error(job, exc)
        raise


@shared_task(bind=True)
def stage_migration_job(self, job_id: int):
    """
    Transform raw rows into normalized staging payloads.
    """
    job = _get_job(job_id)
    pipeline = MigrationPipeline(job)
    try:
        pipeline.stage_rows()
        job.meta.setdefault("stage", {})["staged_rows"] = job.staging_rows.count()
        job.save(update_fields=["meta", "updated_at"])
        return {"status": "success", "staged_rows": job.staging_rows.count()}
    except Exception as exc:
        _handle_task_error(job, exc)
        raise


@shared_task(bind=True)
def validate_migration_job(self, job_id: int):
    """
    Execute validation rules over staged rows.
    """
    job = _get_job(job_id)
    pipeline = MigrationPipeline(job)
    try:
        summary = pipeline.validate()
        return {"status": "success", "summary": summary}
    except Exception as exc:
        _handle_task_error(job, exc)
        raise


@shared_task(bind=True)
def commit_migration_job(self, job_id: int, approver_id: int):
    """
    Commit a validated & approved migration into live tables.
    """
    job = _get_job(job_id)
    pipeline = MigrationPipeline(job)
    approver = get_user_model().objects.get(pk=approver_id)

    try:
        with transaction.atomic():
            pipeline.apply_schema_extensions(approver=approver)
            commit_log = pipeline.commit(user=approver)
        return {
            "status": "success",
            "created": commit_log.summary.get("created", 0),
        }
    except Exception as exc:
        _handle_task_error(job, exc)
        raise


@shared_task(bind=True)
def rollback_migration_job(self, job_id: int, user_id: int):
    """
    Roll back a previously committed migration.
    """
    job = _get_job(job_id)
    pipeline = MigrationPipeline(job)
    actor = get_user_model().objects.get(pk=user_id)

    try:
        deleted = pipeline.rollback(user=actor)
        return {"status": "success", "deleted": deleted}
    except Exception as exc:
        _handle_task_error(job, exc)
        raise
