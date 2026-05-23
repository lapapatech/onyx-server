"""Rate limiting per API key — sliding window counter."""

import logging
import time
from collections import defaultdict
from typing import Optional

from .config import settings

log = logging.getLogger("onyx.ratelimit")

# Default: 60 requests per minute
DEFAULT_LIMIT = 60
WINDOW_SECONDS = 60


class RateLimiter:
    """Sliding-window rate limiter per API key."""

    def __init__(self, limit: int = DEFAULT_LIMIT, window: int = WINDOW_SECONDS):
        self.limit = limit
        self.window = window
        # key -> list of timestamps (sorted oldest first)
        self._buckets: dict[str, list[float]] = defaultdict(list)

    @property
    def _configured_limit(self) -> int:
        """Resolve limit from env or use default."""
        try:
            return int(getattr(settings, "rate_limit", 0) or 
                      __import__("os").environ.get("ONYX_RATE_LIMIT", str(self.limit)))
        except (ValueError, TypeError):
            return self.limit

    def _prune(self, key: str, now: float) -> None:
        """Remove timestamps outside the sliding window."""
        cutoff = now - self.window
        bucket = self._buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)

    def check(self, key: str) -> tuple[bool, int, int]:
        """Check if request is allowed.

        Returns (allowed, remaining, reset_seconds).
        """
        limit = self._configured_limit
        now = time.time()
        self._prune(key, now)
        bucket = self._buckets[key]
        count = len(bucket)

        if count >= limit:
            # Calculate retry-after based on oldest request in window
            oldest = bucket[0] if bucket else now
            retry_after = int(self.window - (now - oldest)) + 1
            return False, 0, max(0, retry_after)

        bucket.append(now)
        remaining = limit - len(bucket)
        return True, remaining, self.window

    def cleanup(self, max_age: float = 300) -> int:
        """Remove stale entries older than max_age seconds. Returns count removed."""
        now = time.time()
        stale_keys = []
        for key in list(self._buckets):
            self._prune(key, now)
            if not self._buckets[key]:
                stale_keys.append(key)
        for key in stale_keys:
            del self._buckets[key]
        if stale_keys:
            log.debug("Rate limiter cleanup: removed %d stale keys", len(stale_keys))
        return len(stale_keys)


# Global singleton
limiter = RateLimiter()


def extract_api_key(auth_header: Optional[str]) -> str:
    """Extract API key from Authorization header. Returns key string or 'anonymous'."""
    if not auth_header:
        return "anonymous"
    auth = auth_header.strip()
    if auth.startswith("Bearer "):
        return auth[7:]
    return auth[:48]  # Truncate long garbage
