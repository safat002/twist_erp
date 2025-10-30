from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone


@dataclass(frozen=True)
class RateLimitState:
    allowed: bool
    remaining: int
    reset_at: timezone.datetime


class RateLimiter:
    """
    Lightweight per-identity rate limiter backed by Django's cache.
    Designed for small bursts (e.g. conversational actions) without adding
    a new dependency.
    """

    def __init__(self, *, prefix: str, limit: int, window_seconds: int):
        if limit <= 0:
            raise ValueError("limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.prefix = prefix
        self.limit = limit
        self.window_seconds = window_seconds

    def _cache_key(self, identity: str | int) -> str:
        return f"ai:rl:{self.prefix}:{identity}"

    def check(self, *, identity: str | int) -> RateLimitState:
        """
        Atomically mark a hit for the supplied identity and return the resulting status.
        """
        now = timezone.now()
        cache_key = self._cache_key(identity)
        record = cache.get(cache_key)

        if not record or record.get("reset_at") <= now:
            reset_at = now + timedelta(seconds=self.window_seconds)
            cache.set(
                cache_key,
                {"count": 1, "reset_at": reset_at},
                timeout=self.window_seconds,
            )
            return RateLimitState(True, max(self.limit - 1, 0), reset_at)

        count = int(record.get("count", 0))
        reset_at = record["reset_at"]
        if count >= self.limit:
            return RateLimitState(False, 0, reset_at)

        count += 1
        remaining = max(self.limit - count, 0)
        cache.set(
            cache_key,
            {"count": count, "reset_at": reset_at},
            timeout=max(int((reset_at - now).total_seconds()), 1),
        )
        return RateLimitState(True, remaining, reset_at)
