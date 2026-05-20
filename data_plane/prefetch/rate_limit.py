from __future__ import annotations

import threading
import time


class RateLimiter:
    def __init__(self, calls_per_minute: float | None = None):
        self.calls_per_minute = calls_per_minute
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        if not self.calls_per_minute or self.calls_per_minute <= 0:
            return
        interval = 60.0 / self.calls_per_minute
        with self._lock:
            now = time.monotonic()
            sleep_for = max(0.0, self._next_allowed - now)
            self._next_allowed = max(now, self._next_allowed) + interval
        if sleep_for:
            time.sleep(sleep_for)
