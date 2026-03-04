from __future__ import annotations

import pytest
from types import SimpleNamespace
from typing import Any

from bioimage_mcp.api import server as server_module
from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.store import SessionStore


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


class _CapturingArtifacts:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def artifact_info(self, ref_id: str, **kwargs) -> dict[str, Any]:
        self.calls.append({"ref_id": ref_id, **kwargs})
        return {"ref_id": ref_id}


class _CapturingInteractive:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def call_tool(
        self,
        session_id: str,
        fn_id: str,
        inputs: dict[str, Any],
        params: dict[str, Any],
        ordinal: int | None = None,
        connection_hint: str | None = None,
        timeout_seconds: int | None = None,
        dry_run: bool = False,
        progress_callback: Any = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "session_id": session_id,
                "id": fn_id,
                "inputs": inputs,
                "params": params,
                "ordinal": ordinal,
                "connection_hint": connection_hint,
                "dry_run": dry_run,
                "timeout_seconds": timeout_seconds,
                "progress_callback": progress_callback,
            }
        )
        return {"status": "success", "session_id": session_id}


@pytest.mark.anyio
async def test_run_inputs_and_params_optional(monkeypatch, tmp_path) -> None:
    """Verify run works when both inputs and params are omitted."""
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
        artifacts=_CapturingArtifacts(),
        session_manager=session_manager,
    )

    session_manager.ensure_session("session-1")
    session_manager.store.replace_active_functions("session-1", ["fn.test"])

    ctx = SimpleNamespace(session=SimpleNamespace(id="session-1"))

    result = await mcp.tools["run"](
        id="fn.test",
        session_id="session-1",
        ctx=ctx,
    )

    assert result["status"] == "success"
    assert interactive.calls
    assert interactive.calls[0]["inputs"] == {}
    assert interactive.calls[0]["params"] == {}


def test_artifact_info_wiring(monkeypatch) -> None:
    """Verify artifact_info tool forwards all parameters to service."""
    monkeypatch.setattr(server_module, "FastMCP", _FakeMCP)
    server_module.FastMCP.__module__ = "fake_mcp"

    artifacts = _CapturingArtifacts()
    mcp = server_module.create_server(
        _DummyDiscovery(),
        execution=_DummyExecution(),
        interactive=_CapturingInteractive(),
        artifacts=artifacts,
        session_manager=None,  # Not used for artifact_info
    )

    mcp.tools["artifact_info"](
        ref_id="ref-123",
        text_preview_bytes=100,
        include_image_preview=True,
        image_preview_size=512,
        channels=[0, 1],
        projection={"Z": "max"},
        slice_indices={"T": 5},
    )

    assert len(artifacts.calls) == 1
    call = artifacts.calls[0]
    assert call["ref_id"] == "ref-123"
    assert call["text_preview_bytes"] == 100
    assert call["include_image_preview"] is True
    assert call["image_preview_size"] == 512
    assert call["channels"] == [0, 1]
    assert call["projection"] == {"Z": "max"}
    assert call["slice_indices"] == {"T": 5}
