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
    # Tool 1: fn.a, fn.b
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
        fn_id="fn.a",
        tool_id="tools.t1",
        name="Function A",
        description="A",
        tags=[],
        inputs=[],
        outputs=[],
        params_schema={},
    )
    discovery_service.upsert_function(
        fn_id="fn.b",
        tool_id="tools.t1",
        name="Function B",
        description="B",
        tags=[],
        inputs=[],
        outputs=[],
        params_schema={},
    )

    # Tool 2: fn.c
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
        fn_id="fn.c",
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
        page = await call_tool("list_tools", limit=20, cursor=None)
        tools = page["tools"]
        tool_ids = sorted([t["tool_id"] for t in tools])
        assert tool_ids == ["tools.t1", "tools.t2"]

        # --- Action 2: Activate fn.a ---
        await call_tool("activate_functions", fn_ids=["fn.a"])

        # Verify persistence
        active = session_store.get_active_functions(session_id)
        assert active == ["fn.a"]

        # --- Action 3: Verify filtering (list_tools) ---

        # Should show tools.t1 because it has an active function
        # Should NOT show tools.t2 because it has NO active functions
        page = await call_tool("list_tools", limit=20, cursor=None)
        tools = page["tools"]
        tool_ids = [t["tool_id"] for t in tools]
        assert "tools.t1" in tool_ids
        assert "tools.t2" not in tool_ids

        # --- Action 4: Verify filtering (search_functions) ---
        # Should show fn.a
        page = await call_tool("search_functions", query="", limit=20, cursor=None)
        fns = page["functions"]
        fn_ids = sorted([f["fn_id"] for f in fns])
        assert fn_ids == ["fn.a"]

        # --- Action 5: Switch to fn.c ---
        await call_tool("activate_functions", fn_ids=["fn.c"])

        page = await call_tool("list_tools", limit=20, cursor=None)
        tool_ids = [t["tool_id"] for t in page["tools"]]
        assert "tools.t1" not in tool_ids
        assert "tools.t2" in tool_ids

        # --- Action 6: Deactivate (Restore all) ---
        await call_tool("deactivate_functions")

        page = await call_tool("list_tools", limit=20, cursor=None)
        tool_ids = sorted([t["tool_id"] for t in page["tools"]])
        assert tool_ids == ["tools.t1", "tools.t2"]

    asyncio.run(run_test())
