from __future__ import annotations

from pathlib import Path

import yaml

from bioimage_mcp.config.schema import Config


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


def load_config(*, global_path: Path | None = None, local_path: Path | None = None) -> Config:
    global_path = global_path or (Path.home() / ".bioimage-mcp" / "config.yaml")
    local_path = local_path or (Path.cwd() / ".bioimage-mcp" / "config.yaml")

    merged: dict = {}
    merged.update(_read_yaml(global_path))
    merged.update(_read_yaml(local_path))

    # Provide minimal defaults to keep early phases runnable.
    merged.setdefault("artifact_store_root", str(Path.home() / ".bioimage-mcp" / "artifacts"))
    # Use discovered tool manifest roots if not explicitly configured
    merged.setdefault("tool_manifest_roots", _discover_tool_manifest_roots())
    merged.setdefault("fs_allowlist_read", [])
    merged.setdefault("fs_allowlist_write", [str(Path.home() / ".bioimage-mcp")])
    merged.setdefault("fs_denylist", [])

    return Config.model_validate(merged)
