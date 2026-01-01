from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from bioimage_mcp.config.schema import Config

if TYPE_CHECKING:
    from bioimage_mcp.registry.manifest_schema import ToolManifest


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text())
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a YAML mapping: {path}")
    return data


def _find_repo_root() -> Path | None:
    """Try to find the repository root by looking for common markers."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent
    return None


def find_repo_root() -> Path | None:
    """Public wrapper for repo root discovery."""
    return _find_repo_root()


def _discover_tool_manifest_roots() -> list[str]:
    """Discover default tool manifest roots.

    Priority:
    1. Repository tools/ directory (if in a repo with tools/)
    2. User-level ~/.bioimage-mcp/tools
    """
    roots: list[str] = []

    # Check for repository-local tools directory
    repo_root = _find_repo_root()
    if repo_root:
        tools_dir = repo_root / "tools"
        if tools_dir.exists():
            # Add specific tool directories (builtin, cellpose, etc.)
            for tool_dir in tools_dir.iterdir():
                if tool_dir.is_dir() and (tool_dir / "manifest.yaml").exists():
                    roots.append(str(tool_dir))

    # Always include user-level tools directory
    user_tools = Path.home() / ".bioimage-mcp" / "tools"
    if user_tools.exists():
        roots.append(str(user_tools))
    elif not roots:
        # Fallback: create default even if doesn't exist yet
        roots.append(str(user_tools))

    return roots


def _merge_manifest_roots(configured: list[str]) -> list[str]:
    roots = list(configured)
    repo_root = _find_repo_root()
    if not repo_root:
        return roots

    tools_dir = repo_root / "tools"
    if not tools_dir.exists():
        return roots

    for tool_dir in tools_dir.iterdir():
        if tool_dir.is_dir() and (tool_dir / "manifest.yaml").exists():
            path = str(tool_dir)
            if path not in roots:
                roots.append(path)

    return roots


_CANONICAL_FN_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2,}$")


def is_canonical_fn_id(fn_id: str, *, allow_meta: bool = True) -> bool:
    """Return True if fn_id matches canonical env.package.module.function."""
    if allow_meta and fn_id == "meta.describe":
        return True
    return bool(_CANONICAL_FN_ID_PATTERN.match(fn_id))


def validate_manifest_fn_ids(
    manifests: Iterable[ToolManifest],
    *,
    allow_meta: bool = True,
) -> None:
    """Validate that all manifest fn_ids are canonical."""
    invalid = sorted(
        {
            fn.fn_id
            for manifest in manifests
            for fn in manifest.functions
            if not is_canonical_fn_id(fn.fn_id, allow_meta=allow_meta)
        }
    )
    if invalid:
        raise ValueError(f"Non-canonical fn_id(s): {', '.join(invalid)}")


def validate_manifest_fn_ids_for_config(config: Config, *, allow_meta: bool = True) -> None:
    """Validate manifest fn_ids for configured tool roots."""
    from bioimage_mcp.registry.loader import load_manifests

    manifests, _diagnostics = load_manifests(list(config.tool_manifest_roots))
    validate_manifest_fn_ids(manifests, allow_meta=allow_meta)


def load_config(*, global_path: Path | None = None, local_path: Path | None = None) -> Config:
    global_path = global_path or (Path.home() / ".bioimage-mcp" / "config.yaml")
    local_path = local_path or (Path.cwd() / ".bioimage-mcp" / "config.yaml")

    merged: dict = {}
    merged.update(_read_yaml(global_path))
    merged.update(_read_yaml(local_path))

    # Provide minimal defaults to keep early phases runnable.
    merged.setdefault("artifact_store_root", str(Path.home() / ".bioimage-mcp" / "artifacts"))
    merged.setdefault(
        "schema_cache_path",
        str(Path(merged["artifact_store_root"]) / "state" / "schema_cache.json"),
    )
    # Use discovered tool manifest roots if not explicitly configured
    merged.setdefault("tool_manifest_roots", _discover_tool_manifest_roots())
    if "tool_manifest_roots" in merged:
        merged["tool_manifest_roots"] = _merge_manifest_roots(list(merged["tool_manifest_roots"]))
    merged.setdefault("fs_allowlist_read", [merged["artifact_store_root"]])
    merged.setdefault("fs_allowlist_write", [str(Path.home() / ".bioimage-mcp")])
    merged.setdefault("fs_denylist", [])

    return Config.model_validate(merged)
