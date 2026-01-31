from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import os
from functools import lru_cache
from pathlib import Path

CACHE_SCHEMA_VERSION = "3"

CRITICAL_MODULES = [
    "bioimage_mcp.registry.engine",
    "bioimage_mcp.registry.dynamic.discovery",
    "bioimage_mcp.registry.dynamic.cache",
    "bioimage_mcp.registry.manifest_schema",
    "bioimage_mcp.registry.static.inspector",
]


def _compute_critical_source_hash() -> str:
    """
    Computes a hash of the source code for critical registry modules.
    This is used for cache invalidation during development.
    """
    hasher = hashlib.sha256()
    for module_name in sorted(CRITICAL_MODULES):
        spec = importlib.util.find_spec(module_name)
        if spec and spec.origin:
            source_path = Path(spec.origin)
            if source_path.exists():
                # Add filename and size to hash to ensure path changes or size changes are caught
                hasher.update(module_name.encode())
                hasher.update(source_path.read_bytes())
    return hasher.hexdigest()[:12]


@lru_cache(maxsize=1)
def get_cache_version_key() -> str:
    """
    Returns a unique key for cache invalidation.
    Combines schema version, package version, and optionally source hash.
    """
    try:
        pkg_version = importlib.metadata.version("bioimage-mcp")
    except importlib.metadata.PackageNotFoundError:
        pkg_version = "editable"

    key_parts = [CACHE_SCHEMA_VERSION, pkg_version]

    if os.environ.get("BIOIMAGE_MCP_DEV_CACHE_CHECK") == "1":
        source_hash = _compute_critical_source_hash()
        key_parts.append(source_hash)

    return "-".join(key_parts)
