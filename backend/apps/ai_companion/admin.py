from django.contrib import admin
from django.utils.html import format_html
from .models import (
    AIConfiguration,
    AITrainingExample,
    GeminiAPIKey,
    APIKeyUsageLog,
    AIConversation,
    AIMessage,
    AIFeedback,
    AIProactiveSuggestion,
    AISkillProfile,
    UserAIPreference,
)


# ========================================
# AI CONFIGURATION & SETTINGS
# ========================================

@admin.register(AIConfiguration)
class AIConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'ai_assistant_status',
        'document_processing_status',
        'proactive_suggestions_status',
        'gemini_model',
        'updated_at'
    )

    fieldsets = (
        ('General Settings', {
            'fields': ('name', 'ai_assistant_enabled', 'proactive_suggestions_enabled')
        }),
        ('AI Model Configuration', {
            'fields': ('gemini_model', 'temperature', 'max_tokens', 'max_retries')
        }),
        ('Document Processing', {
            'fields': ('document_processing_enabled', 'enable_caching', 'cache_ttl_minutes')
        }),
        ('Rate Limiting', {
            'fields': ('rate_limit_cooldown_minutes', 'request_timeout_seconds')
        }),
        ('Logging & Monitoring', {
            'fields': ('log_all_requests', 'enable_content_filtering', 'notify_on_key_exhaustion', 'notification_email')
        }),
    )

    def ai_assistant_status(self, obj):
        if obj.ai_assistant_enabled:
            return format_html('<span style="color: green;">✓ Enabled</span>')
        return format_html('<span style="color: red;">✗ Disabled</span>')
    ai_assistant_status.short_description = 'AI Assistant'

    def document_processing_status(self, obj):
        if obj.document_processing_enabled:
            return format_html('<span style="color: green;">✓ Enabled</span>')
        return format_html('<span style="color: red;">✗ Disabled</span>')
    document_processing_status.short_description = 'Document Processing'

    def proactive_suggestions_status(self, obj):
        if obj.proactive_suggestions_enabled:
            return format_html('<span style="color: green;">✓ Enabled</span>')
        return format_html('<span style="color: red;">✗ Disabled</span>')
    proactive_suggestions_status.short_description = 'Proactive Suggestions'


# ========================================
# API KEY MANAGEMENT
# ========================================

class APIKeyUsageLogInline(admin.TabularInline):
    model = APIKeyUsageLog
    extra = 0
    max_num = 10
    can_delete = False
    fields = ('operation', 'success', 'response_time_ms', 'created_at')
    readonly_fields = ('operation', 'success', 'response_time_ms', 'created_at')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(GeminiAPIKey)
class GeminiAPIKeyAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'status_badge',
        'priority',
        'usage_today',
        'daily_limit',
        'last_used_display',
        'created_at'
    )
    list_filter = ('status', 'priority')
    search_fields = ('name', 'api_key')
    ordering = ('priority', '-created_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'api_key', 'status', 'priority')
        }),
        ('Rate Limits', {
            'fields': ('daily_limit', 'minute_limit', 'requests_today', 'requests_this_minute')
        }),
        ('Usage Statistics', {
            'fields': ('last_used_at', 'rate_limited_until', 'last_error')
        }),
    )

    readonly_fields = ('requests_today', 'requests_this_minute', 'last_used_at', 'rate_limited_until')

    inlines = [APIKeyUsageLogInline]

    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'rate_limited': 'orange',
            'disabled': 'gray',
            'invalid': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def usage_today(self, obj):
        requests_today = obj.requests_today or 0
        daily_limit = obj.daily_limit or 0
        if daily_limit > 0:
            percentage = (requests_today / daily_limit) * 100
            percentage_label = f"{percentage:.0f}%"
        else:
            percentage = 0
            percentage_label = '—'
        color = 'green' if percentage < 70 else 'orange' if percentage < 90 else 'red'
        limit_label = daily_limit if daily_limit > 0 else '∞'
        return format_html(
            '<span style="color: {};">{} / {} ({})</span>',
            color,
            requests_today,
            limit_label,
            percentage_label
        )
    usage_today.short_description = 'Usage Today'

    def last_used_display(self, obj):
        if obj.last_used_at:
            from django.utils import timezone
            delta = timezone.now() - obj.last_used_at
            if delta.days > 0:
                return f"{delta.days} days ago"
            elif delta.seconds > 3600:
                return f"{delta.seconds // 3600} hours ago"
            elif delta.seconds > 60:
                return f"{delta.seconds // 60} minutes ago"
            else:
                return "Just now"
        return "Never"
    last_used_display.short_description = 'Last Used'


@admin.register(APIKeyUsageLog)
class APIKeyUsageLogAdmin(admin.ModelAdmin):
    list_display = (
        'api_key',
        'operation',
        'success_badge',
        'response_time_display',
        'user',
        'company',
        'created_at'
    )
    list_filter = ('success', 'operation', 'created_at')
    search_fields = ('operation', 'error_message')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    readonly_fields = ('api_key', 'operation', 'success', 'error_message', 'response_time_ms', 'user', 'company', 'metadata', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def success_badge(self, obj):
        if obj.success:
            return format_html('<span style="color: green;">✓ Success</span>')
        return format_html('<span style="color: red;">✗ Failed</span>')
    success_badge.short_description = 'Status'

    def response_time_display(self, obj):
        if obj.response_time_ms:
            if obj.response_time_ms < 1000:
                color = 'green'
            elif obj.response_time_ms < 3000:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="color: {};">{} ms</span>',
                color,
                obj.response_time_ms
            )
        return '-'
    response_time_display.short_description = 'Response Time'


# ========================================
# TRAINING & LEARNING
# ========================================

@admin.register(AITrainingExample)
class AITrainingExampleAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'prompt_preview',
        'status_badge',
        'source',
        'reviewed_by',
        'created_at'
    )
    list_filter = ('status', 'source', 'created_at')
    search_fields = ('prompt', 'completion')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Training Data', {
            'fields': ('prompt', 'completion', 'source', 'status')
        }),
        ('Review Information', {
            'fields': ('review_notes', 'reviewed_by', 'reviewed_at')
        }),
        ('Metadata', {
            'fields': ('metadata', 'user', 'company', 'feedback')
        }),
    )

    readonly_fields = ('reviewed_at', 'created_at', 'updated_at')

    def prompt_preview(self, obj):
        return obj.prompt[:100] + '...' if len(obj.prompt) > 100 else obj.prompt
    prompt_preview.short_description = 'Prompt'

    def status_badge(self, obj):
        colors = {
            'review': 'orange',
            'approved': 'green',
            'rejected': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ========================================
# CONVERSATIONS & FEEDBACK
# ========================================

@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ('conversation_id', 'user', 'company', 'active_skill', 'message_count', 'created_at', 'updated_at')
    list_filter = ('active_skill', 'created_at', 'company')
    search_fields = ('conversation_id', 'user__username', 'user__email')
    date_hierarchy = 'created_at'
    readonly_fields = ('conversation_id', 'created_at', 'updated_at')

    def message_count(self, obj):
        count = obj.messages.count()
        return format_html('<strong>{}</strong> messages', count)
    message_count.short_description = 'Messages'


@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'role', 'content_preview', 'intent', 'confidence', 'created_at')
    list_filter = ('role', 'intent', 'created_at')
    search_fields = ('content', 'intent')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)

    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'


@admin.register(AIFeedback)
class AIFeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'rating_badge', 'feedback_type', 'notes_preview', 'created_at')
    list_filter = ('rating', 'feedback_type', 'created_at')
    search_fields = ('notes',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)

    def rating_badge(self, obj):
        if obj.rating == 'up':
            return format_html('<span style="color: green;">👍 Positive</span>')
        elif obj.rating == 'down':
            return format_html('<span style="color: red;">👎 Negative</span>')
        return obj.rating
    rating_badge.short_description = 'Rating'

    def notes_preview(self, obj):
        if obj.notes:
            return obj.notes[:50] + '...' if len(obj.notes) > 50 else obj.notes
        return '-'
    notes_preview.short_description = 'Notes'


# ========================================
# PROACTIVE SUGGESTIONS
# ========================================

@admin.register(AIProactiveSuggestion)
class AIProactiveSuggestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'company', 'status_badge', 'severity', 'source_skill', 'created_at')
    list_filter = ('status', 'severity', 'source_skill', 'created_at')
    search_fields = ('title', 'body')
    date_hierarchy = 'created_at'

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'accepted': 'green',
            'dismissed': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.status.title()
        )
    status_badge.short_description = 'Status'


# ========================================
# USER PREFERENCES & SKILLS
# ========================================

@admin.register(UserAIPreference)
class UserAIPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'key', 'value_preview', 'source', 'updated_at')
    list_filter = ('source', 'created_at')
    search_fields = ('user__username', 'user__email', 'key')
    readonly_fields = ('created_at', 'updated_at')

    def value_preview(self, obj):
        value_str = str(obj.value)
        if len(value_str) > 50:
            return value_str[:50] + '...'
        return value_str
    value_preview.short_description = 'Value'


@admin.register(AISkillProfile)
class AISkillProfileAdmin(admin.ModelAdmin):
    list_display = ('skill_name', 'user', 'company', 'usage_count', 'success_rate', 'last_used_at')
    list_filter = ('skill_name', 'last_used_at')
    search_fields = ('skill_name', 'user__username')

    def success_rate(self, obj):
        if obj.usage_count > 0:
            rate = (obj.success_count / obj.usage_count) * 100
            color = 'green' if rate >= 80 else 'orange' if rate >= 60 else 'red'
            rate_str = f"{rate:.1f}%"
            return format_html('<span style="color: {};"><strong>{}</strong></span>', color, rate_str)
        return '-'
    success_rate.short_description = 'Success Rate'
