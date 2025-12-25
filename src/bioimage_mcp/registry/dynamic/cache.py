"""Introspection result caching with lockfile invalidation.

Caches adapter discovery results in nested JSON structure:
{
  "adapter_name": {
    "prefix": {
      "lockfile_hash": [FunctionMetadata, ...]
    }
  }
}
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from bioimage_mcp.registry.dynamic.models import FunctionMetadata


class IntrospectionCache:
    """Cache for introspection results with lockfile-based invalidation.

    Stores discovered function metadata in a JSON file with nested structure
    keyed by adapter name, prefix, and lockfile hash.
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
    ) -> Optional[List[FunctionMetadata]]:
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
            with open(self.cache_file, "r") as f:
                cache_data = json.load(f)

            # Navigate nested structure
            if adapter_name not in cache_data:
                return None
            if prefix not in cache_data[adapter_name]:
                return None
            if lockfile_hash not in cache_data[adapter_name][prefix]:
                return None

            # Deserialize FunctionMetadata objects
            cached_list = cache_data[adapter_name][prefix][lockfile_hash]
            return [FunctionMetadata.model_validate(item) for item in cached_list]

        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def put(
        self,
        adapter_name: str,
        prefix: str,
        lockfile_hash: str,
        results: List[FunctionMetadata],
    ) -> None:
        """Store introspection results in cache.

        Args:
            adapter_name: Name of the adapter used for introspection.
            prefix: Function prefix for the dynamic source.
            lockfile_hash: Hash of the environment lockfile.
            results: List of FunctionMetadata to cache.
        """
        # Load existing cache or start fresh
        cache_data: Dict[str, Any] = {}
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    cache_data = json.load(f)
            except (json.JSONDecodeError, ValueError):
                cache_data = {}

        # Ensure nested structure exists
        if adapter_name not in cache_data:
            cache_data[adapter_name] = {}
        if prefix not in cache_data[adapter_name]:
            cache_data[adapter_name][prefix] = {}

        # Serialize FunctionMetadata objects
        cache_data[adapter_name][prefix][lockfile_hash] = [item.model_dump() for item in results]

        # Write back to file
        with open(self.cache_file, "w") as f:
            json.dump(cache_data, f, indent=2)
