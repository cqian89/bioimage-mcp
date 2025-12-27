from __future__ import annotations

import json

from bioimage_mcp.runtimes import executor


def test_execute_tool_exports_allowlist_env(monkeypatch) -> None:
    captured: dict[str, dict[str, str]] = {}

    class _DummyProc:
        def __init__(self, *args, **kwargs):
            captured["env"] = kwargs.get("env") or {}
            self.returncode = 0

        def communicate(self, input=None, timeout=None):
            _ = input
            _ = timeout
            return json.dumps({"ok": True}), ""

    monkeypatch.setattr(executor.subprocess, "Popen", _DummyProc)

    executor.execute_tool(
        entrypoint="tools.fake",
        request={"fs_allowlist_read": ["/tmp/allowed"]},
        env_id=None,
    )

    assert captured["env"]["BIOIMAGE_MCP_FS_ALLOWLIST_READ"] == json.dumps(["/tmp/allowed"])
