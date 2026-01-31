from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from bioimage_mcp.api.server import create_server


@pytest.fixture
def mock_discovery():
    mock = MagicMock()
    mock.describe_function.return_value = {
        "id": "base.gauss",
        "type": "function",
        "name": "gaussian",
        "summary": "Apply Gaussian blur to an image.",
        "tags": ["filter"],
        "inputs": {
            "image": {
                "type": "BioImageRef",
                "required": True,
                "description": "Input image",
            }
        },
        "outputs": {
            "output": {
                "type": "BioImageRef",
                "description": "Output image",
            }
        },
        "params_schema": {
            "type": "object",
            "properties": {
                "sigma": {
                    "type": "number",
                    "default": 1.0,
                    "description": "Sigma value",
                }
            },
        },
        "hints": {"success_hints": {"next_steps": ["Threshold"]}},
    }
    return mock


@pytest.fixture
def mcp_server(mock_discovery):
    # We need to mock other services as well
    mock_execution = MagicMock()
    mock_interactive = MagicMock()
    mock_artifacts = MagicMock()
    mock_sessions = MagicMock()

    return create_server(
        mock_discovery,
        execution=mock_execution,
        interactive=mock_interactive,
        artifacts=mock_artifacts,
        session_manager=mock_sessions,
    )


def test_describe_defaults_to_minimal(mcp_server, mock_discovery):
    """Verify that describe tool defaults to minimal verbosity."""
    # Find the 'describe' tool in FastMCP
    # FastMCP stores tools in its own internal registry.
    # We can call it directly if we can find the decorated function.

    # In FastMCP, tools are registered and accessible.
    # Since we can't easily trigger the tool through MCP transport here without a full client,
    # we'll look for the function in the mcp instance.

    describe_tool = None
    for tool in mcp_server._tool_manager.list_tools():
        if tool.name == "describe":
            describe_tool = tool
            break

    assert describe_tool is not None

    # Call the tool function directly
    # FastMCP tool functions are the original functions or wrapped ones.
    result = describe_tool.fn(id="base.gauss")

    # Should have minimal verbosity fields
    assert result["id"] == "base.gauss"
    assert "summary" in result
    assert "params_schema" in result

    # Omitted fields in minimal verbosity
    assert "name" not in result
    assert "tags" not in result
    assert "hints" not in result
    assert "description" not in result["params_schema"]["properties"]["sigma"]


def test_describe_explicit_verbosity(mcp_server, mock_discovery):
    """Verify that describe tool respects explicit verbosity levels."""
    describe_tool = next(t for t in mcp_server._tool_manager.list_tools() if t.name == "describe")

    # Standard verbosity
    result_std = describe_tool.fn(id="base.gauss", verbosity="standard")
    assert "name" in result_std
    assert "tags" in result_std
    assert "hints" in result_std
    assert "description" in result_std["params_schema"]["properties"]["sigma"]

    # Full verbosity
    result_full = describe_tool.fn(id="base.gauss", verbosity="full")
    assert result_full == mock_discovery.describe_function.return_value
