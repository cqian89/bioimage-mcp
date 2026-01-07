from __future__ import annotations

from unittest.mock import MagicMock

from bioimage_mcp.api.artifacts import ArtifactsService
from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.api.interactive import InteractiveExecutionService
from bioimage_mcp.api.server import create_server
from bioimage_mcp.sessions.manager import SessionManager


def test_mcp_tool_count():
    """The MCP surface should expose exactly 8 tools."""
    import asyncio

    # Setup mocks
    discovery = MagicMock(spec=DiscoveryService)
    execution = MagicMock(spec=ExecutionService)
    interactive = MagicMock(spec=InteractiveExecutionService)
    artifacts = MagicMock(spec=ArtifactsService)
    session_manager = MagicMock(spec=SessionManager)

    # Create server
    mcp = create_server(
        discovery=discovery,
        execution=execution,
        interactive=interactive,
        artifacts=artifacts,
        session_manager=session_manager,
    )

    # FastMCP has a list_tools() method that returns registered tools
    tools = asyncio.run(mcp.list_tools())
    tool_names = [t.name for t in tools]

    expected_tools = {
        "list",
        "describe",
        "search",
        "run",
        "status",
        "artifact_info",
        "session_export",
        "session_replay",
    }

    print(f"Current tool names: {tool_names}")

    assert len(tool_names) == 8, f"Expected 8 tools, got {len(tool_names)}: {tool_names}"
    assert set(tool_names) == expected_tools
