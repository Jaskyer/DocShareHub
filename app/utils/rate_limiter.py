"""Simple in-memory rate limiter for brute-force protection."""

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, HTTPException


class RateLimiter:
    """Sliding window rate limiter using in-memory counters."""

    def __init__(self, max_attempts: int = 10, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        """Check if a key is rate limited. Returns True if allowed."""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old entries and append current
        timestamps = self._attempts[key]
        timestamps[:] = [t for t in timestamps if t > window_start]

        if len(timestamps) >= self.max_attempts:
            return False

        timestamps.append(now)
        return True

    def cleanup(self):
        """Remove expired entries to free memory."""
        now = time.time()
        window_start = now - self.window_seconds
        for key in list(self._attempts.keys()):
            self._attempts[key][:] = [t for t in self._attempts[key] if t > window_start]
            if not self._attempts[key]:
                del self._attempts[key]


# Global rate limiters
password_limiter = RateLimiter(max_attempts=5, window_seconds=300)  # 5 attempts per 5 min
api_limiter = RateLimiter(max_attempts=60, window_seconds=60)       # 60 requests per min
auth_limiter = RateLimiter(max_attempts=10, window_seconds=300)     # 10 login attempts per 5 min
file_scan_limiter = RateLimiter(max_attempts=30, window_seconds=60) # 30 file requests per min
