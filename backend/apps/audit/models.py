from django.db import models
from django.conf import settings
from apps.companies.models import Company, CompanyGroup

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('READ', 'Read'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('PROVISION', 'Provision'),
        ('MIGRATE', 'Migrate'),
        ('OTHER', 'Other'),
        ('FORM_LAYOUT_CHANGED', 'Form Layout Changed'),
        ('FORM_FIELD_ADDED', 'Form Field Added'),
        ('CUSTOM_MODULE_CREATED', 'Custom Module Created'),
        ('WORKFLOW_CHANGED', 'Workflow Changed'),
        ('DASHBOARD_CHANGED', 'Dashboard Definition Changed'),
        ('AI_QUERY', 'AI Query'),
        ('AI_ACTION', 'AI Action'),
        ('AI_PREF_SET', 'AI Preference Updated'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    company_group = models.ForeignKey(CompanyGroup, on_delete=models.CASCADE, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    entity_type = models.CharField(max_length=255, help_text="Type of entity affected (e.g., 'Company', 'User', 'Invoice')")
    entity_id = models.CharField(max_length=255, help_text="ID of the entity affected")
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField(blank=True, help_text="A brief description of the action")
    before_value = models.JSONField(null=True, blank=True, help_text="JSON representation of the object before the change")
    after_value = models.JSONField(null=True, blank=True, help_text="JSON representation of the object after the change")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    correlation_id = models.CharField(max_length=255, blank=True, help_text="Identifier to link related actions (e.g., request ID)")

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        return f"{self.timestamp}: {self.user} {self.action} {self.entity_type}:{self.entity_id}"
