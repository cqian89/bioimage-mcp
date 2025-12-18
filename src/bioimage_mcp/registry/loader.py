from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from bioimage_mcp.registry.diagnostics import ManifestDiagnostic
from bioimage_mcp.registry.manifest_schema import ToolManifest


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
    except Exception as exc:  # noqa: BLE001
        return None, ManifestDiagnostic(path=path, tool_id=tool_id, errors=[str(exc)])

    return manifest, None


def discover_manifest_paths(roots: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        paths.extend(sorted(root.rglob("*.yaml")))
        paths.extend(sorted(root.rglob("*.yml")))
    # De-dup
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def load_manifests(roots: list[Path]) -> tuple[list[ToolManifest], list[ManifestDiagnostic]]:
    manifests: list[ToolManifest] = []
    diagnostics: list[ManifestDiagnostic] = []

    for path in discover_manifest_paths(roots):
        manifest, diag = load_manifest_file(path)
        if manifest is not None:
            manifests.append(manifest)
        elif diag is not None:
            diagnostics.append(diag)

    return manifests, diagnostics
