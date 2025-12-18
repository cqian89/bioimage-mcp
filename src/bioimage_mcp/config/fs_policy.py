from __future__ import annotations

from pathlib import Path
from typing import Literal

from bioimage_mcp.config.schema import Config

Operation = Literal["read", "write"]


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def assert_path_allowed(operation: Operation, path: str | Path, config: Config) -> Path:
    target = path if isinstance(path, Path) else Path(path)
    target = target.expanduser().absolute()

    for deny_root in config.fs_denylist:
        if _is_within(target, deny_root):
            raise PermissionError(f"Path denied by fs_denylist: {target}")

    allow_roots = config.fs_allowlist_read if operation == "read" else config.fs_allowlist_write
    if not allow_roots:
        raise PermissionError(f"No allowlist configured for {operation}")

    for allow_root in allow_roots:
        if _is_within(target, allow_root):
            return target

    raise PermissionError(f"Path not under any allowed {operation} root: {target}")
