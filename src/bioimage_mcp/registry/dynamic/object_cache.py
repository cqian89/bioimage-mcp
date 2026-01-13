import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

# Configuration for Object Cache
MAX_CACHE_SIZE = 1000  # Default max objects
MAX_CACHE_MEMORY_BYTES = 1024 * 1024 * 1024  # 1GB


class LRUCache(dict):
    """
    Thread-safe LRU cache for Python objects with memory-based eviction.
    """

    def __init__(self, max_size: int = MAX_CACHE_SIZE, max_memory: int = MAX_CACHE_MEMORY_BYTES):
        super().__init__()
        self.max_size = max_size
        self.max_memory = max_memory
        self.access_order: list[str] = []
        self.current_memory: int = 0
        self.obj_memory: dict[str, int] = {}
        self._lock = threading.RLock()

    def _get_memory_usage(self, value: Any) -> int:
        """Estimate memory usage of an object."""
        try:
            # Pandas DataFrame/Series
            if hasattr(value, "memory_usage"):
                if callable(value.memory_usage):
                    usage = value.memory_usage(deep=True)
                    if hasattr(usage, "sum") and callable(usage.sum):
                        return int(usage.sum())
                    return int(usage)

            # Xarray DataArray/Dataset
            if hasattr(value, "nbytes"):
                return int(value.nbytes)

            # GroupBy object (pandas)
            if "groupby" in str(type(value)).lower():
                return 1024 * 1024  # 1MB placeholder for GroupBy

            # Default placeholder
            return 1024 * 10  # 10KB placeholder
        except Exception:
            return 1024 * 10

    def __contains__(self, key: object) -> bool:
        with self._lock:
            return super().__contains__(key)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            if key in self:
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)
                return super().__getitem__(key)
            return default

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            new_mem = self._get_memory_usage(value)

            if key in self:
                if key in self.access_order:
                    self.access_order.remove(key)
                self.current_memory -= self.obj_memory.get(key, 0)

            # Evict until we have space (by count or memory)
            while self.access_order and (
                len(self) >= self.max_size or (self.current_memory + new_mem > self.max_memory)
            ):
                evict_key = self.access_order.pop(0)
                evict_mem = self.obj_memory.get(evict_key, 0)
                logger.warning(
                    f"OBJECT_CACHE limit reached (count={len(self)}/{self.max_size}, "
                    f"mem={self.current_memory / 1e6:.1f}/{self.max_memory / 1e6:.1f}MB). "
                    f"Evicting LRU object: {evict_key}"
                )
                self.current_memory -= evict_mem
                self.obj_memory.pop(evict_key, None)
                if evict_key in self:
                    super().__delitem__(evict_key)

            super().__setitem__(key, value)
            self.access_order.append(key)
            self.obj_memory[key] = new_mem
            self.current_memory += new_mem

    def __getitem__(self, key: str) -> Any:
        val = self.get(key)
        if val is None:
            # Check if it was actually in the cache but value was None
            with self._lock:
                if key not in self:
                    raise KeyError(key)
        return val

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        with self._lock:
            if key in self:
                if key in self.access_order:
                    self.access_order.remove(key)
                self.current_memory -= self.obj_memory.get(key, 0)
                self.obj_memory.pop(key, None)
                super().__delitem__(key)

    def clear(self) -> None:
        with self._lock:
            super().clear()
            self.access_order.clear()
            self.current_memory = 0
            self.obj_memory.clear()

    def evict(self, key: str) -> bool:
        """Explicitly evict an object from cache."""
        with self._lock:
            if key in self:
                if key in self.access_order:
                    self.access_order.remove(key)
                self.current_memory -= self.obj_memory.get(key, 0)
                self.obj_memory.pop(key, None)
                super().__delitem__(key)
                return True
            return False


# Singleton instance
OBJECT_CACHE = LRUCache(MAX_CACHE_SIZE, MAX_CACHE_MEMORY_BYTES)


def get(key: str) -> Any | None:
    """Get object from cache by full URI."""
    return OBJECT_CACHE.get(key)


def register(uri: str, obj: Any) -> None:
    """Register an object in the cache with its URI."""
    OBJECT_CACHE.set(uri, obj)


def evict(uri: str) -> bool:
    """Evict an object from the cache by URI."""
    return OBJECT_CACHE.evict(uri)


def clear() -> None:
    """Clear the entire object cache."""
    OBJECT_CACHE.clear()


def get_by_artifact_id(artifact_id: str) -> Any | None:
    """
    Lookup object by just the artifact_id portion.
    Searches all URIs ending with that ID.
    """
    with OBJECT_CACHE._lock:
        # Search for URIs ending with the artifact_id
        for uri in list(OBJECT_CACHE.keys()):
            # Handle obj://session/env/id or mem://id or just id
            parts = uri.replace("://", "/").split("/")
            if parts[-1] == artifact_id:
                # Update LRU
                if uri in OBJECT_CACHE.access_order:
                    OBJECT_CACHE.access_order.remove(uri)
                OBJECT_CACHE.access_order.append(uri)
                return super(LRUCache, OBJECT_CACHE).__getitem__(uri)
    return None
