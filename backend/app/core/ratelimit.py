"""In-process sliding-window rate limiting (tech_doc.md §5.1).

Adequate for a single API task. A multi-task deployment needs a shared store
(Redis) — see ``progress/phase_seven.md``.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from app.core.errors import RateLimitError


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._failures: dict[str, int] = defaultdict(int)

    def _prune(self, key: str, window: float, now: float) -> None:
        bucket = self._hits[key]
        while bucket and bucket[0] <= now - window:
            bucket.popleft()

    def check(self, key: str, *, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        self._prune(key, window_seconds, now)
        bucket = self._hits[key]
        if len(bucket) >= limit:
            retry_after = max(1, int(window_seconds - (now - bucket[0])))
            raise RateLimitError(
                "Too many attempts — please wait before trying again.",
                retry_after=retry_after,
            )
        bucket.append(now)

    def record_failure(self, key: str) -> int:
        self._failures[key] += 1
        return self._failures[key]

    def clear_failures(self, key: str) -> None:
        self._failures.pop(key, None)

    def failures(self, key: str) -> int:
        return self._failures[key]

    def reset(self) -> None:
        self._hits.clear()
        self._failures.clear()


login_limiter = SlidingWindowLimiter()
