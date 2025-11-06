import hashlib
import math
from datetime import date as date_cls
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Optional

import pandas as pd
from django.apps import apps
from django.conf import settings
from django.db import transaction
from django.db.models import Model, NOT_PROVIDED
from django.utils import timezone
from django.utils.text import slugify

from apps.audit.models import AuditLog
from apps.permissions.models import Permission
from apps.finance.models import Account, AccountType, Journal
from apps.finance.services.journal_service import JournalService

from ..models import (
    MigrationCommitLog,
    MigrationColumnProfile,
    MigrationFieldMapping,
    MigrationFile,
    MigrationJob,
    MigrationSchemaExtension,
    MigrationStagingRow,
    MigrationValidationError,
    migration_enums,
)


SUPPORTED_EXTENSIONS = (".csv", ".xlsx", ".xls")


def normalize_header(value: str) -> str:
    return slugify(value or "", allow_unicode=False).replace("-", "_")


def compute_file_hash(file_like) -> str:
    hasher = hashlib.sha256()
    file_like.seek(0)
    while chunk := file_like.read(8192):
        hasher.update(chunk)
    file_like.seek(0)
    return hasher.hexdigest()


@dataclass
class MappingSuggestion:
    column: str
    target_field: Optional[str]
    storage_mode: str
    confidence: float
    requires_extension: bool
    proposed_definition: Optional[dict] = None


class MigrationPipeline:
    """
    High-level coordinator for the Phase 3 data migration lifecycle.
    Encapsulates upload, detection, mapping, staging, validation,
    approval, commit, and rollback responsibilities.
    """

    ENTITY_MODEL_MAP = {
        "customer": "sales.Customer",
        "supplier": "procurement.Supplier",
        "item": "inventory.Product",
        "product": "inventory.Product",
        "opening_ar": "finance.Invoice",
        "opening_ap": "finance.Invoice",
        "stock_balance": "inventory.StockLevel",
    }

    def __init__(self, job: MigrationJob):
        self.job = job

    # ------------------------------------------------------------------
    # Job lifecycle helpers
    # ------------------------------------------------------------------
    @classmethod
    def create_job(
        cls,
        *,
        company,
        created_by,
        entity_name_guess: str | None = None,
        target_model: str | None = None,
        meta: Optional[dict] = None,
    ) -> MigrationJob:
        job = MigrationJob.objects.create(
            company=company,
            company_group=company.company_group,
            created_by=created_by,
            entity_name_guess=(entity_name_guess or "").lower(),
            target_model=target_model or "",
            meta=meta or {},
        )
        cls._log_audit(
            job,
            user=created_by,
            action="IMPORT_UPLOAD",
            description=f"Migration job {job.migration_job_id} created.",
            after={"entity_guess": entity_name_guess, "target_model": target_model},
        )
        return job

    def add_file(self, *, uploaded_by, file_name: str, file_content) -> MigrationFile:
        if not file_name.lower().endswith(SUPPORTED_EXTENSIONS):
            raise ValueError(f"Unsupported file type for {file_name}.")

        # Persist to FileField if configured
        migration_file = MigrationFile.objects.create(
            migration_job=self.job,
            original_filename=file_name,
        )
        django_file = getattr(file_content, "file", file_content)
        migration_file.uploaded_file.save(f"{migration_file.pk}_{file_name}", django_file, save=True)
        migration_file.stored_path = migration_file.uploaded_file.name
        migration_file.file_hash = compute_file_hash(migration_file.uploaded_file)
        migration_file.save(update_fields=["stored_path", "file_hash"])

        self._log_audit(
            self.job,
            user=uploaded_by,
            action="IMPORT_UPLOAD",
            description=f"File {file_name} uploaded for job {self.job.migration_job_id}.",
            after={"file_id": str(migration_file.pk), "hash": migration_file.file_hash},
        )
        return migration_file

    # ------------------------------------------------------------------
    # Detection & profiling
    # ------------------------------------------------------------------
    def profile_files(self) -> pd.DataFrame:
        dataframes = []
        for migration_file in self.job.files.all():
            df = self._load_dataframe(migration_file)
            migration_file.mark_parsed(row_count=len(df), stored_path=migration_file.stored_path)
            dataframes.append((migration_file, df))

        if not dataframes:
            raise ValueError("No files attached to migration job.")

        combined_df = pd.concat([df for _, df in dataframes], ignore_index=True)
        self._store_column_profiles(combined_df, dataframes)

        guessed_target = self._guess_entity(combined_df.columns)
        if guessed_target and not self.job.target_model:
            self.job.target_model = guessed_target
            self.job.meta.setdefault("detector", {})["entity_guess"] = guessed_target
            self.job.save(update_fields=["target_model", "meta", "updated_at"])

        self.job.mark_status(migration_enums.MigrationJobStatus.DETECTED)
        return combined_df

    def _load_dataframe(self, migration_file: MigrationFile) -> pd.DataFrame:
        file_path = migration_file.uploaded_file.path if migration_file.uploaded_file else migration_file.stored_path
        if not file_path:
            raise ValueError("Migration file has no storage reference.")

        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        df.columns = [col.strip() for col in df.columns]
        return df

    def _store_column_profiles(self, combined_df: pd.DataFrame, file_pairs: Iterable[tuple[MigrationFile, pd.DataFrame]]):
        MigrationColumnProfile.objects.filter(migration_job=self.job).delete()
        for column in combined_df.columns:
            series = combined_df[column]
            sample_values = series.dropna().astype(str).head(10).tolist()
            lengths = series.dropna().astype(str).map(len)
            stats = {
                "nulls": int(series.isna().sum()),
                "unique": int(series.nunique(dropna=True)),
                "min_length": int(lengths.min()) if not lengths.empty else 0,
                "max_length": int(lengths.max()) if not lengths.empty else 0,
            }
            inferred_type = self._infer_series_type(series)
            MigrationColumnProfile.objects.create(
                migration_job=self.job,
                column_name_in_file=column,
                detected_data_type=inferred_type,
                inferred_field_name=normalize_header(column),
                sample_values=sample_values,
                stats=stats,
                confidence_score=self._type_confidence(inferred_type, stats),
            )

    @staticmethod
    def _infer_series_type(series: pd.Series) -> str:
        if pd.api.types.is_datetime64_any_dtype(series):
            return "date"
        if pd.api.types.is_numeric_dtype(series):
            return "number"
        lowered = series.dropna().astype(str).str.lower()
        if lowered.isin({"true", "false", "yes", "no"}).all():
            return "boolean"
        return "text"

    @staticmethod
    def _type_confidence(inferred_type: str, stats: dict) -> float:
        if inferred_type in {"number", "date"}:
            return 0.95
        unique = stats.get("unique", 0)
        sample_size = stats.get("sample_size", 0) or 1
        ratio = unique / sample_size if sample_size else 1
        return round(min(0.9, 0.5 + ratio), 4)

    def _guess_entity(self, columns: Iterable[str]) -> Optional[str]:
        normalized_cols = {normalize_header(col) for col in columns}
        best_score = 0
        best_model = None
        for entity, model_label in self.ENTITY_MODEL_MAP.items():
            model = self._get_model(model_label)
            candidates = {field.name for field in model._meta.fields if field.name not in {"id", "company", "company_group", "created_at", "updated_at", "created_by"}}
            overlap = len(normalized_cols & candidates)
            score = overlap / max(1, len(candidates))
            if score > best_score:
                best_score = score
                best_model = model_label
        return best_model

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------
    def generate_field_mappings(self, *, detected_df: Optional[pd.DataFrame] = None, user=None):
        if not self.job.target_model:
            raise ValueError("Target model must be resolved before mapping.")

        model = self._get_model(self.job.target_model)
        model_fields = {field.name for field in model._meta.fields}
        existing_fields = {
            field.name: field for field in model._meta.fields if field.name not in {"id", "company", "company_group", "created_at", "updated_at", "created_by"}
        }
        MigrationFieldMapping.objects.filter(migration_job=self.job).delete()

        suggestions: list[MappingSuggestion] = []
        column_profiles = MigrationColumnProfile.objects.filter(migration_job=self.job)
        for profile in column_profiles:
            normalized = profile.inferred_field_name
            target_field = None
            confidence = 0.0
            storage_mode = migration_enums.TargetStorageMode.EXISTING_COLUMN
            requires_extension = False
            proposed_definition = None

            if normalized in existing_fields:
                target_field = normalized
                confidence = float(profile.confidence_score or 0.7)
                field = existing_fields[target_field]
                is_required = not field.null and not field.blank if hasattr(field, "blank") else not field.null
            else:
                requires_extension = True
                storage_mode = migration_enums.TargetStorageMode.NEW_FIELD
                target_field = normalized
                is_required = False
                proposed_definition = {
                    "field_name": target_field,
                    "label": profile.column_name_in_file,
                    "data_type": profile.detected_data_type,
                    "layer": "COMPANY_OVERRIDE",
                }

            suggestions.append(
                MappingSuggestion(
                    column=profile.column_name_in_file,
                    target_field=target_field,
                    storage_mode=storage_mode,
                    confidence=confidence,
                    requires_extension=requires_extension,
                    proposed_definition=proposed_definition,
                )
            )

        for suggestion in suggestions:
            mapping = MigrationFieldMapping.objects.create(
                migration_job=self.job,
                column_name_in_file=suggestion.column,
                target_entity_field=suggestion.target_field or "",
                target_storage_mode=suggestion.storage_mode,
                new_field_definition_json=suggestion.proposed_definition,
                is_required_match=False,
                confidence_score=suggestion.confidence,
            )
            if suggestion.requires_extension and suggestion.proposed_definition:
                MigrationSchemaExtension.objects.update_or_create(
                    migration_job=self.job,
                    field_name=suggestion.target_field,
                    defaults={
                        "proposed_definition": suggestion.proposed_definition,
                        "metadata_layer": suggestion.proposed_definition.get("layer", "COMPANY_OVERRIDE"),
                    },
                )

        self.job.mark_status(migration_enums.MigrationJobStatus.MAPPED)
        self._log_audit(
            self.job,
            user=user,
            action="IMPORT_MAP_SAVED",
            description="Field mappings generated.",
        )

    # ------------------------------------------------------------------
    # Staging & normalization
    # ------------------------------------------------------------------
    def stage_rows(self, *, user=None, chunk_size: int | None = None):
        MigrationStagingRow.objects.filter(migration_job=self.job).delete()
        mapping_lookup = {
            mapping.column_name_in_file: mapping
            for mapping in MigrationFieldMapping.objects.filter(migration_job=self.job)
        }

        for migration_file in self.job.files.all():
            file_path = migration_file.uploaded_file.path if migration_file.uploaded_file else migration_file.stored_path
            is_csv = file_path and file_path.lower().endswith(".csv")
            # Choose iterator: chunked CSV if chunk_size is provided, else full DataFrame
            if is_csv and chunk_size and chunk_size > 0:
                chunk_iter = pd.read_csv(file_path, chunksize=chunk_size)
                chunks = ((chunk, True) for chunk in chunk_iter)
            else:
                chunks = ((self._load_dataframe(migration_file), False),)

            base_index = 0
            for df, is_chunk in chunks:
                for idx, row in df.iterrows():
                    payload = {}
                    extra_data = {}
                    for column, value in row.items():
                        mapping = mapping_lookup.get(column)
                        if not mapping or mapping.target_storage_mode == migration_enums.TargetStorageMode.IGNORE:
                            continue

                        cleaned = self._clean_value(value)
                        if mapping.requires_schema_extension:
                            extra_data[mapping.target_entity_field] = cleaned
                        else:
                            payload[mapping.target_entity_field] = cleaned

                    if extra_data:
                        payload.setdefault("extra_data", {}).update(extra_data)

                    MigrationStagingRow.objects.create(
                        migration_job=self.job,
                        source_file_name=migration_file.original_filename,
                        row_index_in_file=int(base_index + idx),
                        clean_payload_json=payload,
                        status=migration_enums.StagingRowStatus.PENDING_VALIDATION,
                    )
                if is_chunk:
                    base_index += len(df)

        self._log_audit(
            self.job,
            user=user,
            action="IMPORT_STAGE_READY",
            description="Staging rows prepared.",
        )

    @staticmethod
    def _clean_value(value):
        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                return None
            return stripped
        if isinstance(value, float) and math.isnan(value):
            return None
        return value

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self, *, user=None):
        model = self._get_model(self.job.target_model)
        required_fields = [
            field.name
            for field in model._meta.fields
            if field.name not in {"id", "company", "company_group", "created_at", "updated_at", "created_by"}
            and not getattr(field, "null", False)
            and not getattr(field, "blank", False)
            and getattr(field, "default", NOT_PROVIDED) is NOT_PROVIDED
        ]
        unique_constraints = [
            [field for field in unique_set if field not in {"company", "company_group"}]
            for unique_set in model._meta.unique_together or []
            if any(field not in {"company", "company_group"} for field in unique_set)
        ]

        MigrationValidationError.objects.filter(migration_job=self.job).delete()
        stats = Counter()
        seen_uniques = [set() for _ in unique_constraints]

        for staging_row in self.job.staging_rows.all():
            payload = staging_row.clean_payload_json or {}
            row_errors = []

            # Required field checks
            for field in required_fields:
                if payload.get(field) in (None, "") and staging_row.status != migration_enums.StagingRowStatus.SKIPPED:
                    row_errors.append(
                        self._create_validation_error(
                            staging_row,
                            field,
                            "REQUIRED_MISSING",
                            f"{field} is required",
                            severity=migration_enums.ValidationSeverity.HARD,
                        )
                    )

            # Unique combination check
            for index, fields in enumerate(unique_constraints):
                key = tuple(payload.get(field) for field in fields)
                if not fields:
                    continue
                if any(value in (None, "") for value in key):
                    continue
                if key in seen_uniques[index]:
                    row_errors.append(
                        self._create_validation_error(
                            staging_row,
                            None,
                            "DUPLICATE_ROW",
                            f"Duplicate values for unique constraint on fields: {', '.join(fields)}",
                            severity=migration_enums.ValidationSeverity.HARD,
                        )
                    )
                else:
                    seen_uniques[index].add(key)

            if row_errors:
                staging_row.mark_invalid({"errors": [error.error_code for error in row_errors]})
                stats["invalid"] += 1
            else:
                staging_row.mark_valid()
                stats["valid"] += 1

        self.job.mark_status(migration_enums.MigrationJobStatus.VALIDATED)
        self.job.meta.setdefault("validation", {})["summary"] = dict(stats)
        self.job.save(update_fields=["meta", "updated_at"])

        self._log_audit(
            self.job,
            user=user,
            action="IMPORT_VALIDATED",
            description=f"Validation complete. Summary: {dict(stats)}",
        )
        return dict(stats)

    def _create_validation_error(
        self,
        staging_row: MigrationStagingRow,
        field_name: Optional[str],
        code: str,
        message: str,
        severity: str,
    ) -> MigrationValidationError:
        mapping = None
        if field_name:
            mapping = MigrationFieldMapping.objects.filter(
                migration_job=self.job,
                target_entity_field=field_name,
            ).first()
        return MigrationValidationError.objects.create(
            migration_job=self.job,
            staging_row=staging_row,
            field_mapping=mapping,
            error_code=code,
            error_message=message,
            severity=severity,
        )

    # ------------------------------------------------------------------
    # Approval workflow
    # ------------------------------------------------------------------
    def submit_for_approval(self, *, user):
        self.job.mark_status(migration_enums.MigrationJobStatus.AWAITING_APPROVAL)
        self._log_audit(
            self.job,
            user=user,
            action="IMPORT_SUBMIT_FOR_APPROVAL",
            description="Migration job submitted for approval.",
        )

    def approve(self, *, approver, notes: str | None = None):
        self.job.mark_status(
            migration_enums.MigrationJobStatus.APPROVED,
            by_user=approver,
            notes=notes,
        )
        if notes:
            self.job.notes = (self.job.notes or "") + f"\nApproval notes: {notes}"
        self.job.save(update_fields=["notes", "updated_at"])
        self._log_audit(
            self.job,
            user=approver,
            action="IMPORT_APPROVED",
            description="Migration job approved.",
        )

    def reject(self, *, approver, notes: str | None = None):
        self.job.mark_status(
            migration_enums.MigrationJobStatus.ERROR,
            by_user=approver,
            notes=notes or "Rejected by approver",
        )
        self._log_audit(
            self.job,
            user=approver,
            action="IMPORT_REJECTED",
            description=notes or "Migration job rejected.",
        )

    # ------------------------------------------------------------------
    # Commit & rollback
    # ------------------------------------------------------------------
    def commit(self, *, user) -> MigrationCommitLog:
        if self.job.status not in {migration_enums.MigrationJobStatus.APPROVED, migration_enums.MigrationJobStatus.VALIDATED}:
            raise ValueError("Migration job must be validated and approved before committing.")

        model = self._get_model(self.job.target_model)
        model_fields = {field.name for field in model._meta.fields}
        created_records = []
        gl_entries = []

        with transaction.atomic():
            self.job.mark_status(migration_enums.MigrationJobStatus.COMMITTING, by_user=user)

            for staging_row in self.job.staging_rows.filter(status=migration_enums.StagingRowStatus.VALID):
                payload = dict(staging_row.clean_payload_json or {})
                payload.update(
                    {
                        "company": self.job.company,
                        "created_by": user,
                    }
                )
                if "company_group" in model_fields:
                    payload["company_group"] = self.job.company_group
                instance = model.objects.create(**payload)
                created_records.append({"model": self.job.target_model, "pk": instance.pk})
                gl_entry = self._post_commit_hook(instance=instance, user=user)
                if gl_entry:
                    gl_entries.append(gl_entry)

            commit_log = MigrationCommitLog.objects.create(
                migration_job=self.job,
                committed_by=user,
                summary={
                    "created": len(created_records),
                    "skipped": self.job.staging_rows.filter(status=migration_enums.StagingRowStatus.SKIPPED).count(),
                },
                created_records=created_records,
                gl_entries=gl_entries,
            )
            self.job.mark_status(migration_enums.MigrationJobStatus.COMMITTED, by_user=user)

        self._log_audit(
            self.job,
            user=user,
            action="IMPORT_COMMIT",
            description=f"Migration job committed with {len(created_records)} records.",
            after={"created_records": created_records},
        )
        return commit_log

    def rollback(self, *, user) -> int:
        if not hasattr(self.job, "commit_log"):
            raise ValueError("Cannot rollback a job without a commit log.")

        deleted = 0
        with transaction.atomic():
            for record in self.job.commit_log.created_records:
                model = self._get_model(record["model"])
                try:
                    instance = model.objects.get(pk=record["pk"], company=self.job.company)
                    instance.delete()
                    deleted += 1
                except model.DoesNotExist:
                    continue

            self.job.mark_status(migration_enums.MigrationJobStatus.ROLLED_BACK, by_user=user)
            self._log_audit(
                self.job,
                user=user,
                action="IMPORT_ROLLBACK",
                description=f"Rolled back {deleted} records.",
            )
        return deleted

    def _post_commit_hook(self, *, instance: Model, user):
        """
        Execute post-commit behaviours such as GL postings for opening balances.
        Returns metadata to store in commit log when applicable.
        """
        if self.job.target_model != "finance.Invoice":
            return None

        if not hasattr(instance, "invoice_type") or not hasattr(instance, "total_amount"):
            return None

        journal = (
            Journal.objects.filter(company=self.job.company, type="GENERAL")
            .order_by("code")
            .first()
        )
        if journal is None:
            journal, _ = Journal.objects.get_or_create(
                company=self.job.company,
                code="OPENING",
                defaults={
                    "created_by": user,
                    "name": "Opening Balances",
                    "type": "GENERAL",
                    "is_active": True,
                },
            )

        amount = instance.total_amount
        if amount in (None, 0):
            return None

        if instance.invoice_type == "AR":
            debit_account = (
                Account.objects.filter(company=self.job.company, account_type=AccountType.ASSET)
                .order_by("code")
                .first()
            )
            credit_account = (
                Account.objects.filter(company=self.job.company, account_type=AccountType.EQUITY)
                .order_by("code")
                .first()
            )
        else:
            debit_account = (
                Account.objects.filter(company=self.job.company, account_type=AccountType.EQUITY)
                .order_by("code")
                .first()
            )
            credit_account = (
                Account.objects.filter(company=self.job.company, account_type=AccountType.LIABILITY)
                .order_by("code")
                .first()
            )

        if not debit_account or not credit_account:
            return {
                "status": "warning",
                "message": "Unable to post GL entry due to missing accounts.",
                "invoice_id": instance.pk,
            }

        entry_date = getattr(instance, "invoice_date", timezone.now().date())
        if isinstance(entry_date, str):
            try:
                entry_date = date_cls.fromisoformat(entry_date)
            except ValueError:
                entry_date = timezone.now().date()

        voucher = JournalService.create_journal_voucher(
            journal=journal,
            entry_date=entry_date,
            description=f"Migration opening balance for {instance.invoice_number}",
            entries_data=[
                {"account": debit_account, "debit": amount, "credit": 0, "description": "Opening balance"},
                {"account": credit_account, "debit": 0, "credit": amount, "description": "Opening balance"},
            ],
            company=self.job.company,
            created_by=user,
            reference=f"MIG-{self.job.migration_job_id}",
            source_document_type=instance.__class__.__name__,
            source_document_id=instance.pk,
        )
        JournalService.post_journal_voucher(voucher, posted_by=user)

        instance.journal_voucher = voucher
        instance.status = "POSTED"
        instance.save(update_fields=["journal_voucher", "status"])

        return {
            "status": "posted",
            "invoice_id": instance.pk,
            "journal_voucher_id": voucher.pk,
            "debit_account": debit_account.code,
            "credit_account": credit_account.code,
            "amount": str(amount),
        }

    # ------------------------------------------------------------------
    # Metadata extension
    # ------------------------------------------------------------------
    def apply_schema_extensions(self, *, approver):
        from apps.metadata.services import MetadataScope, create_metadata_version
        for extension in self.job.schema_extensions.filter(status=migration_enums.SchemaExtensionStatus.PENDING):
            scope = MetadataScope.for_company(self.job.company)
            metadata = create_metadata_version(
                key=f"entity:{self.job.target_model}:{extension.field_name}",
                kind="ENTITY",
                layer=extension.metadata_layer or "COMPANY_OVERRIDE",
                scope=scope,
                definition=extension.proposed_definition,
                summary={"source": "data_migration", "field": extension.field_name},
                status="active",
                user=approver,
            )
            metadata.activate(user=approver)
            extension.approve(user=approver)
            self._log_audit(
                self.job,
                user=approver,
                action="METADATA_CHANGE_FROM_IMPORT",
                description=f"Schema extension applied for {extension.field_name}.",
                after={"metadata_id": str(metadata.id), "definition": extension.proposed_definition},
            )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _get_model(self, model_label: str) -> type[Model]:
        if "." not in model_label:
            raise ValueError(f"Model label must be in 'app_label.ModelName' format. Got '{model_label}'.")
        return apps.get_model(model_label)

    @staticmethod
    def _log_audit(job: MigrationJob, *, user, action: str, description: str, before=None, after=None):
        AuditLog.objects.create(
            user=user,
            company_group=job.company_group,
            company=job.company,
            entity_type="MigrationJob",
            entity_id=str(job.migration_job_id),
            action="MIGRATE",
            description=f"{action}: {description}",
            before_value=before,
            after_value=after,
        )

    # ------------------------------------------------------------------
    # Permission helpers
    # ------------------------------------------------------------------
    @staticmethod
    def ensure_permissions():
        Permission.objects.get_or_create(
            code="data_migration.importer",
            defaults={
                "name": "Data Importer",
                "module": "data_migration",
                "description": "Can upload, map, and stage migration data for their company.",
            },
        )
        Permission.objects.get_or_create(
            code="data_migration.approver",
            defaults={
                "name": "Migration Approver",
                "module": "data_migration",
                "description": "Can approve schema extensions and commit migration batches across the company group.",
            },
        )
