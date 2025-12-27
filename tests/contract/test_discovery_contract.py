from __future__ import annotations

import sqlite3

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import init_schema


def test_discovery_list_tools_contract_shape() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    service.upsert_tool(
        tool_id="tools.builtin",
        name="Built-ins",
        description="Built-in functions",
        tool_version="0.0.0",
        env_id="bioimage-mcp-base",
        manifest_path="/abs/manifest.yaml",
        available=True,
        installed=True,
    )

    page = service.list_tools(limit=20, cursor=None)

    assert set(page.keys()) == {"tools", "next_cursor"}
    assert isinstance(page["tools"], list)
    assert page["tools"][0]["tool_id"] == "tools.builtin"
    assert "name" in page["tools"][0]
    assert "description" in page["tools"][0]
    assert "tool_version" in page["tools"][0]
    conn.close()


def test_discovery_search_functions_contract_shape() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    service.upsert_tool(
        tool_id="tools.builtin",
        name="Built-ins",
        description="Built-in functions",
        tool_version="0.0.0",
        env_id="bioimage-mcp-base",
        manifest_path="/abs/manifest.yaml",
        available=True,
        installed=True,
    )
    service.upsert_function(
        fn_id="builtin.gaussian_blur",
        tool_id="tools.builtin",
        name="Gaussian blur",
        description="Blur an image",
        tags=["image", "filter"],
        inputs=[{"name": "image", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "output", "artifact_type": "BioImageRef", "required": True}],
        params_schema={"type": "object", "properties": {"sigma": {"type": "number"}}},
    )

    page = service.search_functions(query="blur", limit=20, cursor=None)

    assert set(page.keys()) == {"functions", "next_cursor"}
    assert isinstance(page["functions"], list)
    assert page["functions"][0]["fn_id"] == "builtin.gaussian_blur"
    assert "tool_id" in page["functions"][0]
    assert "tags" in page["functions"][0]
    conn.close()


def test_discovery_describe_function_returns_schema() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    service.upsert_tool(
        tool_id="tools.builtin",
        name="Built-ins",
        description="Built-in functions",
        tool_version="0.0.0",
        env_id="bioimage-mcp-base",
        manifest_path="/abs/manifest.yaml",
        available=True,
        installed=True,
    )
    service.upsert_function(
        fn_id="builtin.gaussian_blur",
        tool_id="tools.builtin",
        name="Gaussian blur",
        description="Blur an image",
        tags=["image", "filter"],
        inputs=[{"name": "image", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "output", "artifact_type": "BioImageRef", "required": True}],
        params_schema={"type": "object", "properties": {"sigma": {"type": "number"}}},
    )

    described = service.describe_function("builtin.gaussian_blur")
    allowed_keys = {"fn_id", "schema", "inputs", "outputs", "hints"}
    assert {"fn_id", "schema"}.issubset(described.keys())
    assert set(described.keys()).issubset(allowed_keys)
    assert described["fn_id"] == "builtin.gaussian_blur"
    assert described["schema"]["type"] == "object"
    conn.close()


# --- New tests for User Story 1: Discovery without ServerSession errors ---


def test_list_tools_returns_without_session_error() -> None:
    """DISC-001: Verify list_tools() returns valid response without AttributeError.

    Contract: specs/006-phasor-usability-fixes/contracts/api.yaml
    Given: Fresh MCP session (simulated with DiscoveryService)
    When: Call list_tools()
    Then: Returns ListToolsResponse with 'tools' key without AttributeError
    """
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    service.upsert_tool(
        tool_id="tools.base",
        name="Base Toolkit",
        description="Base image operations",
        tool_version="0.1.0",
        env_id="bioimage-mcp-base",
        manifest_path="/abs/tools/base/manifest.yaml",
        available=True,
        installed=True,
    )

    # This should not raise AttributeError: 'ServerSession' object has no attribute 'id'
    result = service.list_tools(limit=20, cursor=None)

    # Verify contract shape
    assert "tools" in result, "Response must contain 'tools' key"
    assert isinstance(result["tools"], list)
    assert len(result["tools"]) > 0
    assert result["tools"][0]["tool_id"] == "tools.base"
    assert result["tools"][0]["name"] == "Base Toolkit"
    conn.close()


def test_search_functions_returns_matching_results() -> None:
    """DISC-002: Verify search_functions(query="phasor") returns matching functions.

    Contract: specs/006-phasor-usability-fixes/contracts/api.yaml
    Given: Base toolkit loaded with phasor functions
    When: Call search_functions(query="phasor")
    Then: Returns functions containing "phasor" in fn_id or description
    """
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    service.upsert_tool(
        tool_id="tools.base",
        name="Base Toolkit",
        description="Base image operations",
        tool_version="0.1.0",
        env_id="bioimage-mcp-base",
        manifest_path="/abs/tools/base/manifest.yaml",
        available=True,
        installed=True,
    )

    # Add phasor-related function
    service.upsert_function(
        fn_id="base.phasor_from_flim",
        tool_id="tools.base",
        name="Phasor from FLIM",
        description="Calculate phasor coordinates from FLIM data",
        tags=["flim", "phasor"],
        inputs=[{"name": "flim_image", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "phasor_coords", "artifact_type": "BioImageRef", "required": True}],
        params_schema={"type": "object", "properties": {"harmonic": {"type": "integer"}}},
    )

    # Add non-matching function
    service.upsert_function(
        fn_id="base.gaussian_blur",
        tool_id="tools.base",
        name="Gaussian Blur",
        description="Apply Gaussian blur filter",
        tags=["filter", "blur"],
        inputs=[{"name": "image", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "blurred", "artifact_type": "BioImageRef", "required": True}],
        params_schema={"type": "object", "properties": {"sigma": {"type": "number"}}},
    )

    result = service.search_functions(query="phasor", limit=20, cursor=None)

    # Verify contract shape
    assert "functions" in result
    assert isinstance(result["functions"], list)

    # Verify query filtering: only phasor-related functions returned
    assert len(result["functions"]) > 0, "Should find at least one phasor function"
    for fn in result["functions"]:
        assert "phasor" in fn["fn_id"].lower() or "phasor" in fn["description"].lower(), (
            f"Function {fn['fn_id']} should match 'phasor' query"
        )
    conn.close()


def test_list_tools_returns_paginated_response() -> None:
    """DISC-003: Verify list_tools() returns paginated response with next_cursor.

    Contract: specs/006-phasor-usability-fixes/contracts/api.yaml
    Given: Multiple tools registered (more than page limit)
    When: Call list_tools() with small limit
    Then: Returns paginated response with next_cursor field when results exceed limit
    """
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)

    # Register multiple tools to trigger pagination
    for i in range(5):
        service.upsert_tool(
            tool_id=f"tools.pack_{i}",
            name=f"Tool Pack {i}",
            description=f"Description for tool pack {i}",
            tool_version="0.1.0",
            env_id=f"bioimage-mcp-pack-{i}",
            manifest_path=f"/abs/tools/pack_{i}/manifest.yaml",
            available=True,
            installed=True,
        )

    # Request with limit smaller than total tools
    result = service.list_tools(limit=2, cursor=None)

    # Verify contract shape
    assert "tools" in result
    assert "next_cursor" in result
    assert isinstance(result["tools"], list)

    # Verify pagination behavior
    assert len(result["tools"]) == 2, "Should return exactly 'limit' tools"
    assert result["next_cursor"] is not None, "Should provide next_cursor when more results exist"

    # Verify we can fetch next page
    next_page = service.list_tools(limit=2, cursor=result["next_cursor"])
    assert "tools" in next_page
    assert len(next_page["tools"]) > 0, "Next page should have more results"
    conn.close()
