from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from bioimage_mcp.api import server as server_module
from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.store import SessionStore

WORKFLOW_HINT = "TIP: Use activate_functions before run_function for better guidance"


class _FakeMCP:
    def __init__(self, name: str, **_kwargs):
        self.name = name
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class _DummyDiscovery:
    pass


class _DummyExecution:
    pass


class _DummyArtifacts:
    pass


class _CapturingInteractive:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def call_tool(
        self,
        *,
        session_id: str,
        fn_id: str,
        inputs: dict[str, Any],
        params: dict[str, Any],
        ordinal: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "session_id": session_id,
                "fn_id": fn_id,
                "inputs": inputs,
                "params": params,
                "ordinal": ordinal,
                "dry_run": dry_run,
            }
        )
        return {"ok": True}


def test_run_function_warns_when_unactivated(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(server_module, "FastMCP", _FakeMCP)
    server_module.FastMCP.__module__ = "fake_mcp"

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )
    session_manager = SessionManager(SessionStore(), config)
    interactive = _CapturingInteractive()

    mcp = server_module.create_server(
        _DummyDiscovery(),
        execution=_DummyExecution(),
        interactive=interactive,
        artifacts=_DummyArtifacts(),
        session_manager=session_manager,
    )

    ctx = SimpleNamespace(session=SimpleNamespace(id="session-1"))

    result = mcp.tools["run_function"](
        fn_id="fn.test",
        inputs={},
        session_id="session-1",
        ctx=ctx,
    )

    assert result["workflow_hint"] == WORKFLOW_HINT
    assert result["warnings"] == [WORKFLOW_HINT]

    session_manager.ensure_session("session-1")
    session_manager.store.replace_active_functions("session-1", ["fn.test"])

    result_active = mcp.tools["run_function"](
        fn_id="fn.test",
        inputs={},
        session_id="session-1",
        ctx=ctx,
    )

    assert result_active["workflow_hint"] is None
    assert "warnings" not in result_active
