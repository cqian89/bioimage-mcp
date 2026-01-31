from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bioimage_mcp.registry.cache_version import get_cache_version_key
from bioimage_mcp.registry.dynamic.models import FunctionMetadata

"""Introspection result caching with lockfile invalidation.

Caches adapter discovery results in nested JSON structure:
{
  "program_version": {
    "adapter_name": {
      "prefix": {
        "lockfile_hash": [FunctionMetadata, ...]
      }
    }
  }
}
"""


class IntrospectionCache:
    """Cache for introspection results with lockfile-based invalidation.

    Stores discovered function metadata in a JSON file with nested structure
    keyed by program version, adapter name, prefix, and lockfile hash.
    """

    def __init__(self, cache_dir: Path):
        """Initialize cache with directory for storage.

        Args:
            cache_dir: Directory to store cache files.
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "introspection_cache.json"

    def get(
        self, adapter_name: str, prefix: str, lockfile_hash: str
    ) -> list[FunctionMetadata] | None:
        """Retrieve cached introspection results.

        Args:
            adapter_name: Name of the adapter used for introspection.
            prefix: Function prefix for the dynamic source.
            lockfile_hash: Hash of the environment lockfile.

        Returns:
            List of cached FunctionMetadata if found, None otherwise.
        """
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file) as f:
                cache_data = json.load(f)

            # Check for version key (migration support)
            vkey = get_cache_version_key()
            if vkey not in cache_data:
                return None

            v_cache = cache_data[vkey]

            # Navigate nested structure
            if adapter_name not in v_cache:
                return None
            if prefix not in v_cache[adapter_name]:
                return None
            if lockfile_hash not in v_cache[adapter_name][prefix]:
                return None

            # Deserialize FunctionMetadata objects
            cached_list = v_cache[adapter_name][prefix][lockfile_hash]
            return [FunctionMetadata.model_validate(item) for item in cached_list]

        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def put(
        self,
        adapter_name: str,
        prefix: str,
        lockfile_hash: str,
        results: list[FunctionMetadata],
    ) -> None:
        """Store introspection results in cache.

        Args:
            adapter_name: Name of the adapter used for introspection.
            prefix: Function prefix for the dynamic source.
            lockfile_hash: Hash of the environment lockfile.
            results: List of FunctionMetadata to cache.
        """
        # Load existing cache or start fresh
        cache_data: dict[str, Any] = {}
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    cache_data = json.load(f)
            except (json.JSONDecodeError, ValueError):
                cache_data = {}

        vkey = get_cache_version_key()
        if vkey not in cache_data:
            cache_data[vkey] = {}

        v_cache = cache_data[vkey]

        # Ensure nested structure exists
        if adapter_name not in v_cache:
            v_cache[adapter_name] = {}
        if prefix not in v_cache[adapter_name]:
            v_cache[adapter_name][prefix] = {}

        # Serialize FunctionMetadata objects
        v_cache[adapter_name][prefix][lockfile_hash] = [item.model_dump() for item in results]

        # Write back to file
        with open(self.cache_file, "w") as f:
            json.dump(cache_data, f, indent=2)
