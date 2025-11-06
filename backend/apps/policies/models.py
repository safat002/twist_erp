from __future__ import annotations

from django.conf import settings
from django.db import models


class PolicyCategory(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class PolicyDocument(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    class Category(models.TextChoices):
        HR = "hr", "HR"
        FINANCE = "finance", "Finance"
        OPERATIONS = "operations", "Operations"
        QUALITY = "quality", "Quality"
        COMPLIANCE = "compliance", "Compliance"
        SAFETY = "safety", "Safety"
        IT = "it", "IT"

    company = models.ForeignKey("companies.Company", on_delete=models.PROTECT, related_name="policies")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_policies")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_policies")
    owner_department = models.ForeignKey(
        'hr.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='policies',
        help_text="Owning department for this policy",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    code = models.CharField(max_length=30)
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OPERATIONS)
    category_ref = models.ForeignKey(PolicyCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="policies")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    version = models.PositiveIntegerField(default=1)
    effective_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    content = models.TextField(blank=True)
    file = models.FileField(upload_to="policies/", null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)
    requires_acknowledgement = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    previous_version = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="next_versions")
    compliance_links = models.JSONField(default=list, blank=True, help_text="List of {label, url} links")
    # Audience targeting & meta
    audience_roles = models.ManyToManyField('permissions.Role', blank=True, related_name='policy_documents')
    audience_departments = models.ManyToManyField('hr.Department', blank=True, related_name='policy_documents')
    reading_time_minutes = models.PositiveIntegerField(default=0, help_text="Estimated reading time in minutes")
    review_cycle_months = models.PositiveSmallIntegerField(default=12, help_text="Recommended review cycle in months")
    last_reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("company", "code", "version")
        indexes = [
            models.Index(fields=["company", "code", "version"]),
            models.Index(fields=["company", "status", "category"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} v{self.version} - {self.title}"


class PolicyAcknowledgement(models.Model):
    company = models.ForeignKey("companies.Company", on_delete=models.PROTECT, related_name="policy_acks")
    policy = models.ForeignKey(PolicyDocument, on_delete=models.CASCADE, related_name="acknowledgements")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="policy_acks")
    version = models.PositiveIntegerField()
    acknowledged_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        unique_together = ("policy", "user", "version")
        indexes = [
            models.Index(fields=["company", "user"]),
        ]


class PolicyAttachment(models.Model):
    policy = models.ForeignKey(PolicyDocument, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='policies/attachments/')
    name = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    size = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['policy', 'uploaded_at']),
        ]

    def __str__(self) -> str:
        return self.name or (self.file.name.split('/')[-1] if self.file else 'Attachment')


class PolicyChangeLog(models.Model):
    policy = models.ForeignKey(PolicyDocument, on_delete=models.CASCADE, related_name='change_logs')
    version = models.PositiveIntegerField()
    change_type = models.CharField(max_length=40, blank=True, help_text="e.g., created, updated, published, archived")
    notes = models.TextField(blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['policy', 'version']),
        ]

    def __str__(self) -> str:
        return f"{self.policy.code} v{self.version}: {self.change_type or 'change'}"
