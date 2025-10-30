from __future__ import annotations

import math
from typing import List

from django.utils import timezone

from apps.data_migration.models import MigrationJob, migration_enums
from .base import (
    BaseSkill,
    ProactiveSuggestionPayload,
    SkillAction,
    SkillContext,
    SkillResponse,
)
from ..memory import MemoryRecord

KEYWORDS = {"import", "migration", "data load", "opening balance", "csv", "excel"}


class DataMigrationSkill(BaseSkill):
    name = "data_migration"
    description = "Assists with legacy data onboarding, mapping, and validation."
    priority = 10

    def _has_access(self, context: SkillContext) -> bool:
        if getattr(context.user, "is_system_admin", False):
            return True
        roles = {role.lower() for role in context.short_term.get("user_roles", [])}
        if not roles:
            return False
        keywords = ("migration", "data", "admin")
        return any(any(keyword in role for keyword in keywords) for role in roles)

    def is_authorised(self, context: SkillContext) -> bool:
        return self._has_access(context)

    def can_handle(self, message: str, context: SkillContext) -> bool:
        if context.module == "data_migration":
            return True
        lowered = message.lower()
        return any(keyword in lowered for keyword in KEYWORDS)

    def _summarise_jobs(self, jobs: List[MigrationJob]) -> str:
        if not jobs:
            return "I couldn't find any migration jobs for this company. You can start one from the Data Migration workspace."

        latest = jobs[0]
        summary_parts = [
            f"The latest migration job **{latest.migration_job_id}** targets *{latest.target_model or latest.entity_name_guess or 'unknown entity'}* and is currently **{latest.status}**.",
        ]
        invalid_rows = latest.staging_rows.filter(status=migration_enums.StagingRowStatus.INVALID).count()
        valid_rows = latest.staging_rows.filter(status=migration_enums.StagingRowStatus.VALID).count()
        if valid_rows or invalid_rows:
            summary_parts.append(f"I see {valid_rows} rows ready to import and {invalid_rows} rows with issues.")

        pending_schema = latest.schema_extensions.filter(status="pending").count()
        if pending_schema:
            summary_parts.append(f"{pending_schema} new fields require approval before committing.")

        if len(jobs) > 1:
            summary_parts.append(f"There are {len(jobs)} total jobs in the queue. The most recent three are {', '.join(j.migration_job_id for j in jobs[:3])}.")

        return " ".join(summary_parts)

    def handle(self, message: str, context: SkillContext) -> SkillResponse:
        if not self._has_access(context):
            return SkillResponse(
                message="I do not have migration workspace access for your role. Please ask a migration lead or admin to share the status.",
                intent="data_migration.permission_denied",
                confidence=0.05,
            )
        if context.company is None:
            return SkillResponse(
                message="Please select a company first so I can review its migration pipeline.",
                intent="data_migration.no_company",
            )

        jobs = list(
            MigrationJob.objects.filter(company=context.company)
            .order_by("-updated_at")[:5]
            .select_related("company")
        )

        summary = self._summarise_jobs(jobs)
        actions = []
        memory_updates = []
        proactive: List[ProactiveSuggestionPayload] = []

        if jobs:
            latest = jobs[0]
            actions.append(
                SkillAction(
                    label="Open migration dashboard",
                    action="navigate",
                    payload={"path": "/migration", "jobId": str(latest.id)},
                )
            )

            if latest.status in {
                migration_enums.MigrationJobStatus.VALIDATED,
                migration_enums.MigrationJobStatus.APPROVED,
            }:
                actions.append(
                    SkillAction(
                        label="Commit this batch",
                        action="api",
                        payload={"endpoint": f"/api/v1/data-migration/jobs/{latest.id}/commit/"},
                    )
                )

            invalid_rows = latest.staging_rows.filter(status=migration_enums.StagingRowStatus.INVALID).count()
            duplicate_errors = latest.validation_errors.filter(error_code__icontains="duplicate").count()
            if latest.status in {
                migration_enums.MigrationJobStatus.UPLOADED,
                migration_enums.MigrationJobStatus.DETECTED,
                migration_enums.MigrationJobStatus.MAPPED,
            }:
                actions.append(
                    SkillAction(
                        label="Run validation",
                        action="api",
                        payload={
                            "endpoint": f"/api/v1/data-migration/jobs/{latest.id}/validate/",
                            "method": "post",
                        },
                    )
                )

            if invalid_rows:
                proactive.append(
                    ProactiveSuggestionPayload(
                        title="Migration rows need attention",
                        body=f"{invalid_rows} rows in job {latest.migration_job_id} still have validation errors. Shall I re-run validation after your fixes?",
                        metadata={
                            "job_id": latest.id,
                            "migration_job_id": str(latest.migration_job_id),
                        },
                    )
                )
            if duplicate_errors:
                proactive.append(
                    ProactiveSuggestionPayload(
                        title="Possible duplicates detected",
                        body=f"I spotted {duplicate_errors} potential duplicate rows in job {latest.migration_job_id}. Consider reviewing the duplicate report before committing.",
                        metadata={
                            "job_id": latest.id,
                            "migration_job_id": str(latest.migration_job_id),
                            "issue": "duplicates",
                        },
                    )
                )

            memory_updates.append(
                MemoryRecord(
                    key="last_migration_job",
                    value={
                        "job_id": latest.id,
                        "migration_job_id": str(latest.migration_job_id),
                        "status": latest.status,
                        "updated_at": timezone.now().isoformat(),
                    },
                    scope="user",
                    user=context.user,
                    company=context.company,
                )
            )

        confidence = 0.65 if jobs else 0.3

        return SkillResponse(
            message=summary,
            intent="data_migration.summary",
            confidence=confidence,
            sources=[str(job.migration_job_id) for job in jobs],
            actions=actions,
            memory_updates=memory_updates,
            proactive_suggestions=proactive,
        )
