from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from apps.companies.models import Company, CompanyGroup
from apps.metadata.models import MetadataDefinition
from apps.permissions.models import Role
from apps.users.models import User


class WorkflowTemplate(models.Model):
    """
    Simple, JSON-driven workflow template used by API.
    Example definition:
    {
      "states": ["draft", "submitted", "approved"],
      "transitions": { "draft": ["submitted"], "submitted": ["approved", "draft"] }
    }
    """
    SCOPE_CHOICES = [
        ("COMPANY", "Company"),
        ("GROUP", "Company Group"),
        ("GLOBAL", "Global"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("archived", "Archived"),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True)
    definition = models.JSONField(default=dict, blank=True)
    layer = models.CharField(max_length=20, choices=MetadataDefinition.LAYER_CHOICES, default="COMPANY_OVERRIDE")
    scope_type = models.CharField(max_length=15, choices=SCOPE_CHOICES, default="COMPANY")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="draft")
    version = models.PositiveIntegerField(default=1)
    company_group = models.ForeignKey(
        CompanyGroup,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="workflow_templates",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="workflow_templates",
    )
    approver_role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Role responsible for approving instances of this workflow",
        related_name="workflow_templates_as_approver",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["company", "status"])]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "company"],
                condition=Q(scope_type="COMPANY"),
                name="uniq_workflow_company_slug",
            ),
            models.UniqueConstraint(
                fields=["slug", "company_group"],
                condition=Q(scope_type="GROUP"),
                name="uniq_workflow_group_slug",
            ),
            models.UniqueConstraint(
                fields=["slug"],
                condition=Q(scope_type="GLOBAL"),
                name="uniq_workflow_global_slug",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or f"workflow-{self.pk or 'new'}"
            slug_candidate = base_slug
            counter = 1
            qs = WorkflowTemplate.objects.exclude(pk=self.pk)
            while qs.filter(slug=slug_candidate).exists():
                counter += 1
                slug_candidate = f"{base_slug}-{counter}"
            self.slug = slug_candidate
        super().save(*args, **kwargs)


class WorkflowInstance(models.Model):
    """
    Instance of a workflow template tracked by string state and optional context.
    """
    template = models.ForeignKey(WorkflowTemplate, on_delete=models.PROTECT, related_name="instances")
    state = models.CharField(max_length=100)
    context = models.JSONField(default=dict, blank=True)
    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, null=True, blank=True, related_name="workflow_instances"
    )
    approver_role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_instances",
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_workflow_instances",
        help_text="If set, only this user may act on the instance",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["company", "state"])]

    def __str__(self) -> str:
        return f"{self.template.name} - {self.state}"
