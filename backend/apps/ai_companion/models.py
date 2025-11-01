import uuid

from django.conf import settings
from django.db import models


class AIConversation(models.Model):
    """
    Tracks an interactive session between a user and the AI assistant.
    """

    conversation_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_conversations",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_conversations",
    )
    active_skill = models.CharField(max_length=120, blank=True, default="")
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=["conversation_id"]),
            models.Index(fields=["user", "updated_at"]),
        ]


class AIMessage(models.Model):
    """
    Stores messages exchanged within a conversation.
    """

    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]

    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    intent = models.CharField(max_length=120, blank=True, null=True)
    confidence = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["intent"]),
        ]


class AIFeedback(models.Model):
    """
    Explicit thumbs-up/thumbs-down or structured feedback from the user.
    """

    FEEDBACK_CHOICES = [
        ("up", "Positive"),
        ("down", "Negative"),
    ]
    FEEDBACK_TYPE_CHOICES = [
        ("thumbs", "Thumbs"),
        ("review", "Structured Review"),
        ("task", "Review Task"),
    ]

    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name="feedback_items",
    )
    message = models.ForeignKey(
        AIMessage,
        on_delete=models.CASCADE,
        related_name="feedback_items",
        null=True,
        blank=True,
    )
    rating = models.CharField(max_length=10, choices=FEEDBACK_CHOICES)
    notes = models.TextField(blank=True)
    feedback_type = models.CharField(
        max_length=20,
        choices=FEEDBACK_TYPE_CHOICES,
        default="thumbs",
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class AIUserMemory(models.Model):
    """
    Stores personalised memory that the assistant can recall within scope.
    """

    SCOPE_CHOICES = [
        ("user", "User"),
        ("company", "Company"),
        ("global", "Global"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_memories",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="ai_memories",
        null=True,
        blank=True,
    )
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default="user")
    key = models.CharField(max_length=255)
    value = models.JSONField(default=dict, blank=True)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "company", "scope", "key")
        indexes = [
            models.Index(fields=["scope", "key"]),
        ]


class AIProactiveSuggestion(models.Model):
    """
    Suggestions generated automatically based on telemetry or scheduled insights.
    """

    class AlertSeverity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("dismissed", "Dismissed"),
        ("accepted", "Accepted"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_suggestions",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="ai_suggestions",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    alert_type = models.CharField(max_length=120, blank=True, default="")
    severity = models.CharField(
        max_length=20,
        choices=AlertSeverity.choices,
        default=AlertSeverity.INFO,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    source_skill = models.CharField(max_length=120, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "status"]),
        ]


class AITelemetryEvent(models.Model):
    """
    Lightweight activity log capturing user actions that AI can learn from.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_telemetry_events",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ai_telemetry_events",
    )
    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="telemetry_events",
    )
    event_type = models.CharField(max_length=120)
    source = models.CharField(max_length=80, default="ai_companion")
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["company", "created_at"]),
            models.Index(fields=["event_type"]),
        ]


class AITrainingExampleStatus(models.TextChoices):
    REVIEW = "review", "Pending Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class AITrainingExample(models.Model):
    """
    Stores curated prompt/response pairs sourced from feedback and reviews.
    """

    SOURCE_CHOICES = [
        ("feedback", "Feedback"),
        ("curated", "Curated"),
        ("telemetry", "Telemetry"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_training_examples",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ai_training_examples",
    )
    feedback = models.ForeignKey(
        AIFeedback,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="training_examples",
    )
    prompt = models.TextField()
    completion = models.TextField()
    source = models.CharField(max_length=32, choices=SOURCE_CHOICES, default="feedback")
    status = models.CharField(
        max_length=20,
        choices=AITrainingExampleStatus.choices,
        default=AITrainingExampleStatus.REVIEW,
    )
    metadata = models.JSONField(default=dict, blank=True)
    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_training_reviews",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["source"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["reviewed_by", "reviewed_at"]),
        ]


class AIGuardrailTestStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    DISABLED = "disabled", "Disabled"


class AIGuardrailTestResult(models.TextChoices):
    NOT_RUN = "not_run", "Not Run"
    PASS = "pass", "Pass"
    FAIL = "fail", "Fail"


class AIGuardrailTestCase(models.Model):
    """
    Regression test prompts tied to policy content to validate assistant guardrails.
    """

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ai_guardrail_tests",
    )
    policy_name = models.CharField(max_length=255)
    prompt = models.TextField()
    expected_phrases = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=20,
        choices=AIGuardrailTestStatus.choices,
        default=AIGuardrailTestStatus.ACTIVE,
    )
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_result = models.CharField(
        max_length=20,
        choices=AIGuardrailTestResult.choices,
        default=AIGuardrailTestResult.NOT_RUN,
    )
    last_output = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("policy_name", "company")
        unique_together = ("company", "policy_name")
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["policy_name"]),
        ]

    def __str__(self):
        scope = getattr(self.company, "code", "Global")
        return f"{self.policy_name} ({scope})"


class AILoRARunStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class AILoRARun(models.Model):
    """
    Tracks LoRA/adapter fine-tuning runs initiated from the AI Ops workspace.
    """

    run_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    adapter_type = models.CharField(max_length=32, default="lora")
    status = models.CharField(
        max_length=20,
        choices=AILoRARunStatus.choices,
        default=AILoRARunStatus.QUEUED,
    )
    dataset_size = models.PositiveIntegerField(default=0)
    dataset_snapshot = models.JSONField(default=list, blank=True)
    training_args = models.JSONField(default=dict, blank=True)
    metrics = models.JSONField(default=dict, blank=True)
    artifact_path = models.CharField(max_length=512, blank=True)
    error = models.TextField(blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_lora_runs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["adapter_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.adapter_type} run {self.run_id} ({self.status})"


class AISkillProfile(models.Model):
    """
    Tracks skill usage statistics and preferences per user/company.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_skill_profiles",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="ai_skill_profiles",
        null=True,
        blank=True,
    )
    skill_name = models.CharField(max_length=120)
    usage_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    preferences = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("user", "company", "skill_name")
        indexes = [
            models.Index(fields=["skill_name"]),
        ]


class UserAIPreference(models.Model):
    """
    Stores user-specific AI preferences, optionally scoped to a company.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_preferences",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ai_preferences",
    )
    company_group = models.ForeignKey(
        "companies.CompanyGroup",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ai_preferences",
    )
    key = models.CharField(max_length=120)
    value = models.JSONField(default=dict, blank=True)
    source = models.CharField(max_length=32, default="manual", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "company", "key")
        indexes = [
            models.Index(fields=["user", "company", "key"]),
            models.Index(fields=["user", "key"]),
        ]
        ordering = ("-updated_at",)

    def save(self, *args, **kwargs):
        if self.company and not self.company_group:
            self.company_group = self.company.company_group
        super().save(*args, **kwargs)

    @property
    def scope(self) -> str:
        return "company" if self.company_id else "global"

    def __str__(self) -> str:
        scope = f"{self.company.code}" if self.company else "global"
        return f"{self.user}::{self.key} ({scope})"


class AIActionExecution(models.Model):
    """
    Audit-friendly log of conversational actions executed through the AI assistant.
    """

    STATUS_CHOICES = [
        ("success", "Success"),
        ("error", "Error"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action_name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="success")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_action_executions",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ai_action_executions",
    )
    payload = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["action_name", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action_name} ({self.status})"


class AIConfiguration(models.Model):
    """
    Global AI assistant configuration settings.
    Allows admins to enable/disable AI features system-wide.
    """

    name = models.CharField(max_length=100, unique=True, default="default")

    # Feature Toggles
    ai_assistant_enabled = models.BooleanField(
        default=True,
        help_text="Enable or disable AI assistant globally"
    )
    document_processing_enabled = models.BooleanField(
        default=True,
        help_text="Enable or disable AI document processing (PDF/image extraction)"
    )
    proactive_suggestions_enabled = models.BooleanField(
        default=True,
        help_text="Enable or disable proactive AI suggestions"
    )

    # API Key Management
    auto_key_rotation = models.BooleanField(
        default=True,
        help_text="Automatically switch to next API key when rate limit is reached"
    )
    max_retries = models.PositiveIntegerField(
        default=3,
        help_text="Maximum retries when all API keys are rate limited"
    )
    rate_limit_cooldown_minutes = models.PositiveIntegerField(
        default=60,
        help_text="Minutes to wait before retrying a rate-limited key"
    )

    # Model Settings
    gemini_model = models.CharField(
        max_length=100,
        default="gemini-2.0-flash-exp",
        help_text="Gemini model to use (e.g., gemini-2.0-flash-exp, gemini-pro-vision)"
    )
    max_tokens = models.PositiveIntegerField(
        default=2048,
        help_text="Maximum tokens in AI response"
    )
    temperature = models.FloatField(
        default=0.7,
        help_text="Temperature for AI responses (0.0-1.0). Higher = more creative"
    )

    # Performance Settings
    request_timeout_seconds = models.PositiveIntegerField(
        default=30,
        help_text="Timeout for AI API requests in seconds"
    )
    enable_caching = models.BooleanField(
        default=True,
        help_text="Cache AI responses for identical requests"
    )
    cache_ttl_minutes = models.PositiveIntegerField(
        default=60,
        help_text="How long to cache responses in minutes"
    )

    # Safety Settings
    enable_content_filtering = models.BooleanField(
        default=True,
        help_text="Enable content filtering for AI responses"
    )
    log_all_requests = models.BooleanField(
        default=True,
        help_text="Log all AI requests for audit purposes"
    )

    # Notifications
    notify_on_key_exhaustion = models.BooleanField(
        default=True,
        help_text="Send notification when all API keys are rate limited"
    )
    notification_email = models.EmailField(
        blank=True,
        help_text="Email to notify about AI system issues"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI Configuration"
        verbose_name_plural = "AI Configuration"

    def __str__(self):
        status = "Enabled" if self.ai_assistant_enabled else "Disabled"
        return f"AI Configuration ({status})"

    @classmethod
    def get_config(cls):
        """Get or create the default configuration."""
        config, created = cls.objects.get_or_create(name="default")
        return config


class GeminiAPIKey(models.Model):
    """
    Stores multiple Gemini API keys for automatic rotation.
    When one key hits rate limit, system automatically switches to another.
    """

    STATUS_CHOICES = [
        ("active", "Active"),
        ("rate_limited", "Rate Limited"),
        ("disabled", "Disabled"),
        ("invalid", "Invalid"),
    ]

    name = models.CharField(
        max_length=100,
        help_text="Friendly name for this API key (e.g., 'Production Key 1')"
    )
    api_key = models.CharField(
        max_length=200,
        unique=True,
        help_text="Google Gemini API key"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active"
    )
    priority = models.PositiveIntegerField(
        default=0,
        help_text="Lower number = higher priority. Keys are used in priority order."
    )
    daily_limit = models.PositiveIntegerField(
        default=1500,
        help_text="Daily request limit for free tier (default: 1500)"
    )
    minute_limit = models.PositiveIntegerField(
        default=15,
        help_text="Per-minute request limit for free tier (default: 15)"
    )
    requests_today = models.PositiveIntegerField(default=0)
    requests_this_minute = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    rate_limited_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Temporarily disabled until this time"
    )
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "-created_at"]
        verbose_name = "Gemini API Key"
        verbose_name_plural = "Gemini API Keys"

    def __str__(self):
        masked_key = f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else "***"
        return f"{self.name} ({masked_key}) - {self.get_status_display()}"

    def is_available(self):
        """Check if this key is available for use."""
        from django.utils import timezone

        if self.status == "disabled" or self.status == "invalid":
            return False

        # Check if rate limit cooldown has expired
        if self.rate_limited_until and self.rate_limited_until > timezone.now():
            return False

        # If was rate limited but cooldown expired, reset status
        if self.status == "rate_limited" and (
            not self.rate_limited_until or self.rate_limited_until <= timezone.now()
        ):
            self.status = "active"
            self.save(update_fields=["status"])

        return self.status == "active"

    def mark_rate_limited(self, minutes=60):
        """Mark this key as rate limited for the specified duration."""
        from django.utils import timezone

        self.status = "rate_limited"
        self.rate_limited_until = timezone.now() + timezone.timedelta(minutes=minutes)
        self.save(update_fields=["status", "rate_limited_until", "updated_at"])

    def mark_invalid(self, error_message=""):
        """Mark this key as invalid (bad credentials, etc.)."""
        self.status = "invalid"
        self.last_error = error_message
        self.save(update_fields=["status", "last_error", "updated_at"])

    def increment_usage(self):
        """Increment usage counters."""
        from django.utils import timezone

        self.requests_today += 1
        self.requests_this_minute += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=["requests_today", "requests_this_minute", "last_used_at", "updated_at"])

    def reset_daily_counter(self):
        """Reset daily request counter (called by scheduled task)."""
        self.requests_today = 0
        self.save(update_fields=["requests_today", "updated_at"])

    def reset_minute_counter(self):
        """Reset per-minute request counter."""
        self.requests_this_minute = 0
        self.save(update_fields=["requests_this_minute", "updated_at"])


class APIKeyUsageLog(models.Model):
    """
    Logs API key usage for monitoring and debugging.
    Helps track which keys are being used and why they fail.
    """

    api_key = models.ForeignKey(
        GeminiAPIKey,
        on_delete=models.CASCADE,
        related_name="usage_logs"
    )
    operation = models.CharField(
        max_length=100,
        help_text="Operation type (e.g., 'document_processing', 'chat')"
    )
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    response_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Response time in milliseconds"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="api_usage_logs"
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="api_usage_logs"
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "API Key Usage Log"
        verbose_name_plural = "API Key Usage Logs"
        indexes = [
            models.Index(fields=["api_key", "created_at"]),
            models.Index(fields=["success", "created_at"]),
            models.Index(fields=["operation", "created_at"]),
        ]

    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.operation} - {status} ({self.created_at})"
