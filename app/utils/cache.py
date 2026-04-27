import time
from typing import Any


class TTLCache:
    """In-memory cache with per-entry TTL (seconds)."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: float) -> None:
        self._store[key] = (value, time.monotonic() + ttl)
