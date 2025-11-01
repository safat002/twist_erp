"""
API Key Manager for automatic rotation and rate limit handling.
"""
import logging
import time
from typing import Optional, Tuple

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class APIKeyManager:
    """
    Manages multiple Gemini API keys with automatic rotation.
    Handles rate limiting and failover to backup keys.
    """

    @staticmethod
    def get_available_key():
        """
        Get an available API key with automatic rotation.
        Returns (api_key, key_object) or (None, None) if no keys available.
        """
        from apps.ai_companion.models import GeminiAPIKey, AIConfiguration

        # Check if document processing is enabled
        config = AIConfiguration.get_config()
        if not config.document_processing_enabled:
            logger.warning("Document processing is disabled in AI configuration")
            return None, None

        # Get all keys ordered by priority
        keys = GeminiAPIKey.objects.filter(status="active").order_by("priority")

        for key in keys:
            if key.is_available():
                # Check rate limits
                if key.requests_today >= key.daily_limit:
                    logger.warning(f"Key {key.name} hit daily limit")
                    key.mark_rate_limited(minutes=config.rate_limit_cooldown_minutes)
                    continue

                if key.requests_this_minute >= key.minute_limit:
                    logger.warning(f"Key {key.name} hit per-minute limit")
                    key.mark_rate_limited(minutes=1)
                    continue

                return key.api_key, key

        # No available keys - try fallback to .env
        env_key = getattr(settings, 'GOOGLE_GEMINI_API_KEY', None)
        if env_key:
            logger.info("Using API key from environment variable")
            return env_key, None

        logger.error("No API keys available!")
        return None, None

    @staticmethod
    def log_usage(key_obj, operation: str, success: bool, error_message: str = "",
                  response_time_ms: Optional[int] = None, user=None, company=None,
                  metadata: dict = None):
        """Log API key usage."""
        from apps.ai_companion.models import APIKeyUsageLog, AIConfiguration

        config = AIConfiguration.get_config()

        if key_obj and config.log_all_requests:
            APIKeyUsageLog.objects.create(
                api_key=key_obj,
                operation=operation,
                success=success,
                error_message=error_message,
                response_time_ms=response_time_ms,
                user=user,
                company=company,
                metadata=metadata or {}
            )

        # Update key usage counters
        if key_obj and success:
            key_obj.increment_usage()

    @staticmethod
    def handle_rate_limit_error(key_obj, error_message: str):
        """Handle rate limit errors."""
        from apps.ai_companion.models import AIConfiguration

        if not key_obj:
            return

        config = AIConfiguration.get_config()
        key_obj.mark_rate_limited(minutes=config.rate_limit_cooldown_minutes)
        logger.warning(f"Key {key_obj.name} marked as rate limited: {error_message}")

        # Send notification if enabled
        if config.notify_on_key_exhaustion and config.notification_email:
            try:
                from django.core.mail import send_mail
                send_mail(
                    subject="AI API Key Rate Limited",
                    message=f"API Key '{key_obj.name}' has been rate limited.\n\nError: {error_message}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[config.notification_email],
                    fail_silently=True,
                )
            except Exception as e:
                logger.error(f"Failed to send rate limit notification: {e}")

    @staticmethod
    def handle_invalid_key_error(key_obj, error_message: str):
        """Handle invalid API key errors."""
        if not key_obj:
            return

        key_obj.mark_invalid(error_message)
        logger.error(f"Key {key_obj.name} marked as invalid: {error_message}")

    @staticmethod
    def process_with_retry(operation_func, operation_name: str, max_retries: int = 3,
                          user=None, company=None):
        """
        Execute an operation with automatic key rotation on rate limit.

        Args:
            operation_func: Function that takes api_key as parameter and returns result
            operation_name: Name of the operation for logging
            max_retries: Maximum number of retry attempts
            user: User making the request
            company: Company context

        Returns:
            Result from operation_func or None if all retries failed
        """
        from apps.ai_companion.models import AIConfiguration

        config = AIConfiguration.get_config()
        attempts = 0

        while attempts < max_retries:
            attempts += 1
            start_time = time.time()

            # Get available key
            api_key, key_obj = APIKeyManager.get_available_key()

            if not api_key:
                logger.error(f"No API keys available for {operation_name} (attempt {attempts}/{max_retries})")
                if attempts < max_retries:
                    time.sleep(2 ** attempts)  # Exponential backoff
                    continue
                else:
                    return None

            try:
                # Execute the operation
                result = operation_func(api_key, key_obj)

                # Log success
                response_time = int((time.time() - start_time) * 1000)
                APIKeyManager.log_usage(
                    key_obj=key_obj,
                    operation=operation_name,
                    success=True,
                    response_time_ms=response_time,
                    user=user,
                    company=company
                )

                return result

            except Exception as e:
                error_str = str(e).lower()
                response_time = int((time.time() - start_time) * 1000)

                # Handle rate limit errors
                if "rate" in error_str or "quota" in error_str or "limit" in error_str or "429" in error_str:
                    APIKeyManager.handle_rate_limit_error(key_obj, str(e))
                    APIKeyManager.log_usage(
                        key_obj=key_obj,
                        operation=operation_name,
                        success=False,
                        error_message=f"Rate limited: {e}",
                        response_time_ms=response_time,
                        user=user,
                        company=company
                    )

                    if config.auto_key_rotation and attempts < max_retries:
                        logger.info(f"Retrying with next available key (attempt {attempts + 1}/{max_retries})")
                        continue
                    else:
                        return None

                # Handle invalid key errors
                elif "invalid" in error_str or "unauthorized" in error_str or "401" in error_str:
                    APIKeyManager.handle_invalid_key_error(key_obj, str(e))
                    APIKeyManager.log_usage(
                        key_obj=key_obj,
                        operation=operation_name,
                        success=False,
                        error_message=f"Invalid key: {e}",
                        response_time_ms=response_time,
                        user=user,
                        company=company
                    )

                    if config.auto_key_rotation and attempts < max_retries:
                        continue
                    else:
                        return None

                # Other errors
                else:
                    APIKeyManager.log_usage(
                        key_obj=key_obj,
                        operation=operation_name,
                        success=False,
                        error_message=str(e),
                        response_time_ms=response_time,
                        user=user,
                        company=company
                    )
                    raise  # Re-raise other errors

        return None
