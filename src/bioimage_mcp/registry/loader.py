from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import yaml

from bioimage_mcp.registry.diagnostics import ManifestDiagnostic
from bioimage_mcp.registry.engine import DiscoveryEngine
from bioimage_mcp.registry.manifest_schema import ToolManifest

logger = logging.getLogger(__name__)

# Aliases for backward compatibility with tests
_map_io_pattern_to_ports = DiscoveryEngine.map_io_pattern_to_ports
_parameters_to_json_schema = DiscoveryEngine.parameters_to_json_schema
_deep_merge_dict = DiscoveryEngine.deep_merge_dict
merge_function_overlay = DiscoveryEngine.merge_function_overlay


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _env_prefix_from_tool_id(tool_id: str | None) -> str | None:
    if not tool_id:
        return None
    if tool_id.startswith("tools."):
        return tool_id.split(".", 1)[1]
    return tool_id


def load_manifest_file(path: Path) -> tuple[ToolManifest | None, ManifestDiagnostic | None]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, ManifestDiagnostic(path=path, tool_id=None, errors=[str(exc)])

    try:
        data = yaml.safe_load(raw)
    except Exception as exc:  # noqa: BLE001
        return None, ManifestDiagnostic(
            path=path, tool_id=None, errors=[f"YAML parse error: {exc}"]
        )

    if not isinstance(data, dict):
        return None, ManifestDiagnostic(
            path=path, tool_id=None, errors=["Manifest must be a mapping"]
        )

    checksum = _sha256_bytes(raw)
    tool_id = data.get("tool_id") if isinstance(data.get("tool_id"), str) else None

    try:
        manifest = ToolManifest.model_validate(
            {
                **data,
                "manifest_path": path,
                "manifest_checksum": checksum,
            }
        )
        # Resolve entrypoint relative to manifest file if it's a relative path
        if manifest.entrypoint and not Path(manifest.entrypoint).is_absolute():
            abs_entrypoint = (path.parent / manifest.entrypoint).resolve()
            if abs_entrypoint.exists():
                manifest.entrypoint = str(abs_entrypoint)
    except Exception as exc:  # noqa: BLE001
        return None, ManifestDiagnostic(path=path, tool_id=tool_id, errors=[str(exc)])

    warnings = []

    # Delegate function discovery and overlay application to DiscoveryEngine
    try:
        # Determine project_root (heuristic: search up for pyproject.toml or envs/ dir)
        project_root = None
        curr = path.parent
        for _ in range(5):
            if (curr / "envs").exists() or (curr / "pyproject.toml").exists():
                project_root = curr
                break
            curr = curr.parent

        engine = DiscoveryEngine(project_root=project_root)
        manifest.functions, engine_events = engine.discover(manifest)
    except Exception as e:
        engine_events = []
        warnings.append(f"Discovery engine failed for {path}: {e}")
        logger.exception("Discovery engine error")

    diag = None
    if warnings or engine_events:
        diag = ManifestDiagnostic(
            path=path,
            tool_id=manifest.tool_id,
            errors=[],
            warnings=warnings,
            engine_events=engine_events,
        )

    return manifest, diag


def discover_manifest_paths(roots: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        # Only pick up manifest files to avoid treating non-manifest YAMLs as tools
        paths.extend(sorted(root.rglob("manifest.yaml")))
        paths.extend(sorted(root.rglob("manifest.yml")))
    # De-dup
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


_MANIFEST_CACHE: dict[tuple[str, ...], tuple[list[ToolManifest], list[ManifestDiagnostic]]] = {}


def load_manifests(roots: list[Path]) -> tuple[list[ToolManifest], list[ManifestDiagnostic]]:
    cache_key = tuple(sorted(str(root.resolve()) for root in roots))
    if cache_key in _MANIFEST_CACHE:
        cached_manifests, cached_diagnostics = _MANIFEST_CACHE[cache_key]
        return list(cached_manifests), list(cached_diagnostics)

    manifests: list[ToolManifest] = []
    diagnostics: list[ManifestDiagnostic] = []

    for path in discover_manifest_paths(roots):
        manifest, diag = load_manifest_file(path)
        if manifest is not None:
            manifests.append(manifest)
        if diag is not None:
            diagnostics.append(diag)

    _MANIFEST_CACHE[cache_key] = (list(manifests), list(diagnostics))
    return manifests, diagnostics
