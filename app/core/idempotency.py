import time
import threading


class IdempotencyCache:
    """In-memory TTL cache for client_run_id deduplication, keyed per tenant."""

    def __init__(self, ttl: int = 600, maxsize: int = 10000) -> None:
        self._ttl = ttl
        self._maxsize = maxsize
        self._store: dict[str, dict[str, tuple[str, float]]] = {}
        self._lock = threading.Lock()

    def check_and_set(self, tenant_id: str, client_run_id: str, run_id: str) -> str | None:
        """Return existing run_id if duplicate, else store and return None."""
        now = time.monotonic()
        with self._lock:
            tenant_cache = self._store.setdefault(tenant_id, {})
            self._evict(tenant_cache, now)
            existing = tenant_cache.get(client_run_id)
            if existing is not None:
                return existing[0]
            if len(tenant_cache) >= self._maxsize:
                self._evict_oldest(tenant_cache)
            tenant_cache[client_run_id] = (run_id, now)
            return None

    def update(self, tenant_id: str, client_run_id: str, run_id: str) -> None:
        """Update an existing entry with the real run_id."""
        now = time.monotonic()
        with self._lock:
            tenant_cache = self._store.get(tenant_id)
            if tenant_cache and client_run_id in tenant_cache:
                tenant_cache[client_run_id] = (run_id, now)

    def _evict(self, cache: dict[str, tuple[str, float]], now: float) -> None:
        expired = [k for k, (_, ts) in cache.items() if now - ts > self._ttl]
        for k in expired:
            del cache[k]

    def _evict_oldest(self, cache: dict[str, tuple[str, float]]) -> None:
        if not cache:
            return
        oldest_key = min(cache, key=lambda k: cache[k][1])
        del cache[oldest_key]


# Singleton instance
idempotency_cache = IdempotencyCache()
