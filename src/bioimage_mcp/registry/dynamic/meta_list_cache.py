from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MetaListCache:
    """Persistent, lockfile-gated cache for parsed meta.list results.

    Used by DiscoveryEngine to skip tool subprocesses when the environment
    and manifest haven't changed.
    """

    def __init__(self, cache_dir: Path):
        """Initialize cache in the specified directory.

        Args:
            cache_dir: Directory to store the cache file (e.g. ~/.bioimage-mcp/cache/dynamic/<tool_id>/).
        """
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "meta_list_cache.json"

    def get(self, lockfile_hash: str, manifest_checksum: str) -> list[dict[str, Any]] | None:
        """Retrieve cached meta.list results if they match the current state.

        Args:
            lockfile_hash: Hash of the tool's environment lockfile.
            manifest_checksum: Checksum of the tool's manifest.yaml.

        Returns:
            List of parsed function entries if found and valid, None otherwise.
        """
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return None

            key = f"{lockfile_hash}:{manifest_checksum}"
            results = data.get(key)

            if isinstance(results, list):
                return results

        except (json.JSONDecodeError, OSError) as e:
            logger.debug("Failed to read meta_list_cache at %s: %s", self.cache_file, e)

        return None

    def put(
        self, lockfile_hash: str, manifest_checksum: str, results: list[dict[str, Any]]
    ) -> None:
        """Store parsed meta.list results in the persistent cache.

        Args:
            lockfile_hash: Hash of the tool's environment lockfile.
            manifest_checksum: Checksum of the tool's manifest.yaml.
            results: Parsed list of function entries to cache.
        """
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            data: dict[str, Any] = {}
            if self.cache_file.exists():
                try:
                    with open(self.cache_file, encoding="utf-8") as f:
                        data = json.load(f)
                except (json.JSONDecodeError, OSError):
                    data = {}

            if not isinstance(data, dict):
                data = {}

            key = f"{lockfile_hash}:{manifest_checksum}"
            data[key] = results

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        except OSError as e:
            logger.debug("Failed to write meta_list_cache at %s: %s", self.cache_file, e)
