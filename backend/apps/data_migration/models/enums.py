from django.db import models


class MigrationJobStatus(models.TextChoices):
    UPLOADED = "uploaded", "Uploaded"
    DETECTED = "detected", "Structure Detected"
    MAPPED = "mapped", "Field Mapping Prepared"
    VALIDATED = "validated", "Validated"
    AWAITING_APPROVAL = "awaiting_approval", "Awaiting Approval"
    APPROVED = "approved", "Approved"
    COMMITTING = "committing", "Commit In Progress"
    COMMITTED = "committed", "Committed"
    ROLLED_BACK = "rolled_back", "Rolled Back"
    ERROR = "error", "Error"


class MigrationFileStatus(models.TextChoices):
    UPLOADED = "uploaded", "Uploaded"
    PARSED = "parsed", "Parsed"
    ERROR = "error", "Error"


class TargetStorageMode(models.TextChoices):
    EXISTING_COLUMN = "column", "Existing Column"
    NEW_FIELD = "extra_data_new_field", "New Extra Data Field"
    IGNORE = "ignore", "Ignore"


class StagingRowStatus(models.TextChoices):
    PENDING_VALIDATION = "pending_validation", "Pending Validation"
    VALID = "valid", "Valid"
    INVALID = "invalid", "Invalid"
    SKIPPED = "skipped", "Skipped"


class ValidationSeverity(models.TextChoices):
    HARD = "hard", "Hard Error"
    SOFT = "soft", "Soft Warning"


class SchemaExtensionStatus(models.TextChoices):
    PENDING = "pending", "Pending Approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
