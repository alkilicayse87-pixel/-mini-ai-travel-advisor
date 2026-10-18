import threading
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import HTTPException, Request

from app import usage
from app.config import (
    ALLOWED_ORIGINS,
    DAILY_BUDGET_USD,
    GLOBAL_LIMIT_PER_HOUR,
    MAX_CONVERSATION_USD,
    RATE_LIMIT_PER_MINUTE,
)


class SlidingWindowLimiter:
    """In-memory limiter. Per-process: fine for one instance; use Redis if scaled out."""

    def __init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_s: int) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_s:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


def enforce_origin(request: Request) -> None:
    """Only the configured frontend may call the API from a browser.

    This blocks other websites and casual abuse; a script can still fake the header, which is why
    the rate limits and spend caps below exist.
    """
    if "*" in ALLOWED_ORIGINS:
        return
    if request.headers.get("origin") not in ALLOWED_ORIGINS:
        raise HTTPException(status_code=403, detail="Origin not allowed.")


def enforce_budget(previous_response_id: Optional[str] = None) -> None:
    if usage.spent_today() >= DAILY_BUDGET_USD:
        raise HTTPException(status_code=503, detail="Daily capacity reached. Please try again tomorrow.")
    if usage.conversation_cost(previous_response_id) >= MAX_CONVERSATION_USD:
        raise HTTPException(status_code=429, detail="This conversation is too long. Please start a new chat.")


def enforce_rate_limit(request: Request) -> None:
    enforce_origin(request)
    ip =  request.client.host if request.client else "unknown"
    if not limiter.allow(f"ip:{ip}", RATE_LIMIT_PER_MINUTE, 60):
        raise HTTPException(status_code=429, detail="Too many requests. Slow down.",
                            headers={"Retry-After": "60"})
    # Global cap protects the OpenAI budget even if client IPs are spoofed.
    if not limiter.allow("global", GLOBAL_LIMIT_PER_HOUR, 3600):
        raise HTTPException(status_code=429, detail="Service is busy. Try again later.",
                            headers={"Retry-After": "600"})
