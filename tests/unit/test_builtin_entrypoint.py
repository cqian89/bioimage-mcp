from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def test_builtin_entrypoint_inserts_tool_paths() -> None:
    entrypoint_path = (
        Path(__file__).resolve().parents[2]
        / "tools"
        / "builtin"
        / "bioimage_mcp_builtin"
        / "entrypoint.py"
    )
    tools_root = entrypoint_path.parent.parent
    repo_tools_root = tools_root.parent

    original_sys_path = list(sys.path)
    try:
        sys.path[:] = [
            p for p in sys.path if str(tools_root) not in p and str(repo_tools_root) not in p
        ]

        spec = importlib.util.spec_from_file_location("test_builtin_entrypoint", entrypoint_path)
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        assert str(tools_root) in sys.path
        assert str(repo_tools_root) in sys.path
    finally:
        sys.path[:] = original_sys_path
