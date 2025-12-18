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


def load_config(*, global_path: Path | None = None, local_path: Path | None = None) -> Config:
    global_path = global_path or (Path.home() / ".bioimage-mcp" / "config.yaml")
    local_path = local_path or (Path.cwd() / ".bioimage-mcp" / "config.yaml")

    merged: dict = {}
    merged.update(_read_yaml(global_path))
    merged.update(_read_yaml(local_path))

    # Provide minimal defaults to keep early phases runnable.
    merged.setdefault("artifact_store_root", str(Path.home() / ".bioimage-mcp" / "artifacts"))
    merged.setdefault("tool_manifest_roots", [str(Path.home() / ".bioimage-mcp" / "tools")])
    merged.setdefault("fs_allowlist_read", [])
    merged.setdefault("fs_allowlist_write", [str(Path.home() / ".bioimage-mcp")])
    merged.setdefault("fs_denylist", [])

    return Config.model_validate(merged)
