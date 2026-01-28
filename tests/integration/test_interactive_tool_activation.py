import asyncio
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.server import create_server
from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.store import SessionStore
from bioimage_mcp.storage.sqlite import init_schema


def setup_discovery(discovery_service: DiscoveryService):
    # Tool 1: t1.pkg.mod.a, t1.pkg.mod.b
    discovery_service.upsert_tool(
        tool_id="tools.t1",
        name="Tool 1",
        description="Tool 1 desc",
        tool_version="0.0.0",
        env_id="env1",
        manifest_path="/t1/manifest.yaml",
        available=True,
        installed=True,
    )
    discovery_service.upsert_function(
        fn_id="t1.pkg.mod.a",
        tool_id="tools.t1",
        name="Function A",
        description="A",
        tags=[],
        inputs=[],
        outputs=[],
        params_schema={},
    )
    discovery_service.upsert_function(
        fn_id="t1.pkg.mod.b",
        tool_id="tools.t1",
        name="Function B",
        description="B",
        tags=[],
        inputs=[],
        outputs=[],
        params_schema={},
    )

    # Tool 2: t2.pkg.mod.c
    discovery_service.upsert_tool(
        tool_id="tools.t2",
        name="Tool 2",
        description="Tool 2 desc",
        tool_version="0.0.0",
        env_id="env2",
        manifest_path="/t2/manifest.yaml",
        available=True,
        installed=True,
    )
    discovery_service.upsert_function(
        fn_id="t2.pkg.mod.c",
        tool_id="tools.t2",
        name="Function C",
        description="C",
        tags=[],
        inputs=[],
        outputs=[],
        params_schema={},
    )


def test_interactive_tool_activation_flow(tmp_path: Path):
    async def run_test():
        # 1. Setup Session Manager
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[],
            fs_allowlist_write=[],
            fs_denylist=[],
        )
        session_store = SessionStore()
        session_manager = SessionManager(session_store, config)

        # 2. Setup Discovery Service
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        discovery_service = DiscoveryService(conn)
        setup_discovery(discovery_service)

        # Mock other services
        execution = MagicMock()
        interactive = MagicMock()
        artifacts = MagicMock()

        # Create server
        mcp = create_server(
            discovery=discovery_service,
            execution=execution,
            interactive=interactive,
            artifacts=artifacts,
            session_manager=session_manager,
        )

        session_id = "sess_01"
        session_manager.ensure_session(session_id)

        # Mock Context
        class MockSession:
            id = session_id

            async def send_tool_list_changed(self):
                pass

        class MockContext:
            session = MockSession()

        ctx = MockContext()

        # Helper to call tools
        async def call_tool(name, **kwargs):
            tool_entry = mcp._tool_manager._tools[name]
            func = tool_entry.fn

            # Inject ctx if needed
            import inspect

            sig = inspect.signature(func)
            if "ctx" in sig.parameters:
                kwargs["ctx"] = ctx

            if inspect.iscoroutinefunction(func):
                return await func(**kwargs)
            else:
                return func(**kwargs)

        # --- Action 1: List all tools (default) ---
        # Note: Using default limit/cursor
        page = await call_tool("list", limit=20, cursor=None)
        tools = page["items"]
        tool_paths = sorted([t["full_path"] for t in tools])
        assert tool_paths == ["t1", "t2"]

        # --- Action 2: Activate t1.pkg.mod.a ---
        session_store.replace_active_functions(session_id, ["t1.pkg.mod.a"])

        # Verify persistence
        active = session_store.get_active_functions(session_id)
        assert active == ["t1.pkg.mod.a"]

        # --- Action 3: Verify filtering (list_tools) ---

        # Should show tools.t1 because it has an active function
        # Should NOT show tools.t2 because it has NO active functions
        page = await call_tool("list", limit=20, cursor=None)
        tools = page["items"]
        tool_paths = [t["full_path"] for t in tools]
        assert "t1" in tool_paths
        assert "t2" not in tool_paths

        # --- Action 4: Verify filtering (search_functions) ---
        # Should show fn.a
        page = await call_tool("search", keywords="mod", limit=20, cursor=None)
        fns = page["results"]
        fn_ids = sorted([f["id"] for f in fns])
        assert fn_ids == ["t1.pkg.mod.a"]

        # --- Action 5: Switch to t2.pkg.mod.c ---
        session_store.replace_active_functions(session_id, ["t2.pkg.mod.c"])

        page = await call_tool("list", limit=20, cursor=None)
        tool_paths = [t["full_path"] for t in page["items"]]
        assert "t1" not in tool_paths
        assert "t2" in tool_paths

        # --- Action 6: Deactivate (Restore all) ---
        session_store.replace_active_functions(session_id, [])

        page = await call_tool("list", limit=20, cursor=None)
        tool_paths = sorted([t["full_path"] for t in page["items"]])
        assert tool_paths == ["t1", "t2"]

    asyncio.run(run_test())
