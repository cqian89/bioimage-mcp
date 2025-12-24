import asyncio
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.server import create_server
from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.store import SessionStore
from bioimage_mcp.storage.sqlite import init_schema


def test_resume_session_flow(tmp_path: Path):
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
        # Activate some functions
        session_manager.store.replace_active_functions(session_id, ["fn.a"])

        # Helper to call tools
        async def call_tool(name, **kwargs):
            tool_entry = mcp._tool_manager._tools[name]
            func = tool_entry.fn

            import inspect

            if inspect.iscoroutinefunction(func):
                return await func(**kwargs)
            else:
                return func(**kwargs)

        # --- Action 1: Resume existing session ---
        result = await call_tool("resume_session", session_id=session_id)

        assert result["session_id"] == session_id
        assert result["status"] == "active"
        # We expect active_functions to be present
        assert "active_functions" in result
        assert result["active_functions"] == ["fn.a"]

        # --- Action 2: Resume invalid session ---
        # The requirement says: Call resume_session("invalid"). Verify failure/error.
        try:
            await call_tool("resume_session", session_id="invalid_session")
            pytest.fail("Should have raised an error for invalid session")
        except ValueError:
            # This is what we expect after the fix
            pass
        except Exception as e:
            # Fallback if it raises something else, but we prefer ValueError
            if "not found" in str(e):
                pass
            else:
                raise e

    asyncio.run(run_test())
