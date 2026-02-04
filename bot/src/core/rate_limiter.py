import time
from collections import defaultdict, deque

from config import settings


class RateLimiter:
    def __init__(self) -> None:
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        window = self._windows[key]

        # Purge expired entries (older than 60s)
        while window and window[0] <= now - 60:
            window.popleft()

        if len(window) >= settings.RATE_LIMIT_PER_MINUTE:
            return False

        window.append(now)
        return True

    def reset(self) -> None:
        self._windows.clear()


rate_limiter = RateLimiter()
