"""
Dynamic function discovery engine.

Coordinates adapter-based function discovery from dynamic_sources in tool manifests.
"""

import hashlib
from pathlib import Path
from typing import Any

from bioimage_mcp.registry.dynamic.cache import IntrospectionCache
from bioimage_mcp.registry.dynamic.models import FunctionMetadata
from bioimage_mcp.registry.manifest_schema import ToolManifest


def _calculate_lockfile_hash(manifest: ToolManifest, project_root: Path) -> str:
    """Calculate hash of environment lockfile for cache invalidation.

    Args:
        manifest: Tool manifest containing env_id.
        project_root: Project root directory (where envs/ is located).

    Returns:
        First 16 chars of SHA256 hash of lockfile contents, or empty string if not found.
    """
    lockfile_path = project_root / "envs" / f"{manifest.env_id}.lock.yml"
    if not lockfile_path.exists():
        return ""

    lockfile_content = lockfile_path.read_text()
    return hashlib.sha256(lockfile_content.encode()).hexdigest()[:16]


def discover_functions(
    manifest: ToolManifest,
    adapter_registry: dict[str, Any],
    cache: IntrospectionCache | None = None,
    project_root: Path | None = None,
) -> list[FunctionMetadata]:
    """Discover functions from dynamic sources in a tool manifest.

    Args:
        manifest: Tool manifest containing dynamic_sources configuration.
        adapter_registry: Dictionary mapping adapter names to adapter instances.
        cache: Optional introspection cache for storing/retrieving results.
        project_root: Optional project root directory for locating lockfiles.

    Returns:
        List of discovered function metadata from all dynamic sources.

    Raises:
        ValueError: If a dynamic source references an unknown adapter.
    """
    results: list[FunctionMetadata] = []

    # Calculate environment component for cache key
    env_component = "no-lockfile"
    if project_root:
        env_component = _calculate_lockfile_hash(manifest, project_root) or "no-lockfile"

    # Include manifest checksum in the composite cache key (T13.07)
    manifest_checksum_16 = manifest.manifest_checksum[:16]
    composite_key = f"{env_component}:{manifest_checksum_16}"

    for source in manifest.dynamic_sources:
        # Try cache first if available
        if cache:
            cached_results = cache.get(source.adapter, source.prefix, composite_key)
            if cached_results is not None:
                results.extend(cached_results)
                continue

        if source.adapter not in adapter_registry:
            # Try populating default adapters if registry is empty
            from bioimage_mcp.registry.dynamic.adapters import (
                KNOWN_ADAPTERS,
                populate_default_adapters,
            )

            if source.adapter in KNOWN_ADAPTERS:
                populate_default_adapters()

            if source.adapter not in adapter_registry:
                raise ValueError(f"Unknown adapter: {source.adapter}")

        # Get adapter instance
        adapter = adapter_registry[source.adapter]

        # Convert DynamicSource to dict for adapter
        source_config = source.model_dump()
        source_config["_manifest_path"] = str(manifest.manifest_path)

        # Call adapter's discover method
        discovered = adapter.discover(source_config)

        # Store in cache if available
        if cache:
            cache.put(source.adapter, source.prefix, composite_key, discovered)

        # Aggregate results
        results.extend(discovered)

    return results
