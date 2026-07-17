"""
Minimal in-memory TTL cache.

An MVP does not need Redis to demonstrate caching as an efficiency
practice -- it needs a cache that is actually wired into the hot path
(RAG retrieval + repeated identical queries) and actually reduces work.
This is a real cache, just not a distributed one. The interface
(get/set) is intentionally the same shape a Redis-backed cache would
expose, so swapping the backend later is a one-file change.
"""

from __future__ import annotations

import time
from threading import Lock
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 60):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# Process-wide caches, separated by purpose so a burst of chat traffic
# doesn't evict the (rarely-changing) RAG cache.
rag_cache = TTLCache(ttl_seconds=300)
live_data_cache = TTLCache(ttl_seconds=10)
