from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CACHE_VERSION = 1
# Default TTL for envs cache in seconds (e.g., 1 hour)
ENVS_CACHE_TTL = 3600


def get_cli_cache_dir() -> Path:
    """Get the CLI cache directory."""
    return Path.home() / ".bioimage-mcp" / "cache" / "cli"


class InstalledEnvsCache:
    """Cache for installed environments to avoid subprocess calls."""

    def __init__(self, cache_dir: Path):
        self.cache_file = cache_dir / "installed_envs.json"

    def get(self, manager_exe: str) -> set[str] | None:
        """Get cached env names if still valid."""
        if os.environ.get("BIOIMAGE_MCP_DISABLE_LIST_CACHE") == "1":
            return None

        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, encoding="utf-8") as f:
                data = json.load(f)

            if data.get("cache_version") != CACHE_VERSION:
                return None

            if data.get("manager_exe") != manager_exe:
                return None

            # Check expiration
            captured_at = data.get("captured_at", 0)
            if time.time() - captured_at > ENVS_CACHE_TTL:
                return None

            return set(data.get("env_names", []))
        except (json.JSONDecodeError, OSError, TypeError) as e:
            logger.debug("Failed to read envs cache: %s", e)
            return None

    def put(self, manager_exe: str, env_names: set[str]) -> str:
        """Store env names in cache and return a hash of the envs."""
        env_list = sorted(list(env_names))
        envs_hash = hashlib.sha256(json.dumps(env_list).encode()).hexdigest()

        if os.environ.get("BIOIMAGE_MCP_DISABLE_LIST_CACHE") == "1":
            return envs_hash

        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "cache_version": CACHE_VERSION,
                "manager_exe": manager_exe,
                "captured_at": time.time(),
                "env_names": env_list,
                "envs_hash": envs_hash,
            }
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.debug("Failed to write envs cache: %s", e)

        return envs_hash


class ListToolsCache:
    """Cache for computed tool summaries."""

    def __init__(self, cache_dir: Path):
        self.cache_file = cache_dir / "list_tools.json"

    def get_fingerprint(self, manifest_paths: list[Path], envs_hash: str) -> str:
        """Compute fingerprint based on manifest stats and envs state."""
        parts = [f"envs:{envs_hash}"]
        for p in sorted(manifest_paths):
            try:
                st = p.stat()
                # Include resolve() to handle symlinks, though usually not needed here
                parts.append(f"{p.resolve()}:{st.st_mtime_ns}:{st.st_size}")
            except OSError:
                continue
        return hashlib.sha256("\n".join(parts).encode()).hexdigest()

    def get(self, fingerprint: str) -> list[dict[str, Any]] | None:
        """Get cached tool details if fingerprint matches."""
        if os.environ.get("BIOIMAGE_MCP_DISABLE_LIST_CACHE") == "1":
            return None

        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, encoding="utf-8") as f:
                data = json.load(f)

            if data.get("cache_version") != CACHE_VERSION:
                return None

            if data.get("manifest_fingerprint") != fingerprint:
                return None

            return data.get("payload")
        except (json.JSONDecodeError, OSError, TypeError) as e:
            logger.debug("Failed to read list tools cache: %s", e)
            return None

    def put(self, fingerprint: str, payload: list[dict[str, Any]]) -> None:
        """Store tool details in cache."""
        if os.environ.get("BIOIMAGE_MCP_DISABLE_LIST_CACHE") == "1":
            return

        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "cache_version": CACHE_VERSION,
                "manifest_fingerprint": fingerprint,
                "payload": payload,
            }
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.debug("Failed to write list tools cache: %s", e)
