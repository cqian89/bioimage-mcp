from __future__ import annotations

from types import SimpleNamespace

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
    def list_tools(self, *, path=None, paths=None, flatten=None, limit=None, cursor=None):
        _ = path
        _ = paths
        _ = flatten
        _ = limit
        _ = cursor
        return {
            "tools": [
                {
                    "name": "base",
                    "full_path": "base",
                    "type": "environment",
                    "has_children": True,
                }
            ],
            "next_cursor": None,
            "expanded_from": None,
        }


class _DummyService:
    pass


def test_list_tools_ensures_session(monkeypatch, tmp_path) -> None:
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

    mcp = server_module.create_server(
        _DummyDiscovery(),
        execution=_DummyService(),
        interactive=_DummyService(),
        artifacts=_DummyService(),
        session_manager=session_manager,
    )

    ctx = SimpleNamespace(session=SimpleNamespace(id="session-1"))

    result = mcp.tools["list_tools"](ctx=ctx)

    assert result["tools"][0]["full_path"] == "base"
    assert session_manager.get_session("session-1").session_id == "session-1"
