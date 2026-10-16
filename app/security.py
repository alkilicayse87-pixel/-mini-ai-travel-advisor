import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.config import GLOBAL_LIMIT_PER_HOUR, RATE_LIMIT_PER_MINUTE


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


def enforce_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    if not limiter.allow(f"ip:{ip}", RATE_LIMIT_PER_MINUTE, 60):
        raise HTTPException(status_code=429, detail="Too many requests. Slow down.",
                            headers={"Retry-After": "60"})
    # Global cap protects the OpenAI budget even if client IPs are spoofed.
    if not limiter.allow("global", GLOBAL_LIMIT_PER_HOUR, 3600):
        raise HTTPException(status_code=429, detail="Service is busy. Try again later.",
                            headers={"Retry-After": "600"})
