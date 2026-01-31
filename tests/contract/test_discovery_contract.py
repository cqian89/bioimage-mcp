from __future__ import annotations

import sqlite3

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import init_schema


def test_discovery_list_tools_contract_shape() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    service.upsert_tool(
        tool_id="tools.base",
        name="Built-ins",
        description="Built-in functions",
        tool_version="0.0.0",
        env_id="bioimage-mcp-base",
        manifest_path="/abs/manifest.yaml",
        available=True,
        installed=True,
    )

    service.upsert_function(
        id="base.skimage.filters.gaussian",
        tool_id="tools.base",
        name="Gaussian blur",
        description="Blur an image",
        tags=["image", "filter"],
        inputs=[{"name": "image", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "output", "artifact_type": "BioImageRef", "required": True}],
        params_schema={"type": "object", "properties": {"sigma": {"type": "number"}}},
    )

    page = service.list_tools(limit=20, cursor=None)

    assert {"items", "next_cursor", "expanded_from"}.issubset(page.keys())
    assert isinstance(page["items"], list)

    assert page["items"][0]["name"] == "base"
    assert page["items"][0]["type"] == "environment"
    conn.close()


def test_discovery_search_functions_contract_shape() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    service.upsert_tool(
        tool_id="tools.base",
        name="Built-ins",
        description="Built-in functions",
        tool_version="0.0.0",
        env_id="bioimage-mcp-base",
        manifest_path="/abs/manifest.yaml",
        available=True,
        installed=True,
    )
    service.upsert_function(
        id="base.bioimage_mcp_base.preprocess.gaussian",
        tool_id="tools.base",
        name="Gaussian blur",
        description="Blur an image",
        tags=["image", "filter"],
        inputs=[{"name": "image", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "output", "artifact_type": "BioImageRef", "required": True}],
        params_schema={"type": "object", "properties": {"sigma": {"type": "number"}}},
    )

    page = service.search_functions(keywords="blur", limit=20, cursor=None)

    assert set(page.keys()) == {"results", "next_cursor"}
    assert isinstance(page["results"], list)
    assert page["results"][0]["id"] == "base.bioimage_mcp_base.preprocess.gaussian"
    assert "tags" in page["results"][0]
    assert "score" in page["results"][0]
    assert "match_count" in page["results"][0]
    conn.close()


def test_discovery_describe_function_returns_schema() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    service.upsert_tool(
        tool_id="tools.base",
        name="Built-ins",
        description="Built-in functions",
        tool_version="0.0.0",
        env_id="bioimage-mcp-base",
        manifest_path="/abs/manifest.yaml",
        available=True,
        installed=True,
    )
    service.upsert_function(
        id="base.bioimage_mcp_base.preprocess.gaussian",
        tool_id="tools.base",
        name="Gaussian blur",
        description="Blur an image",
        tags=["image", "filter"],
        inputs=[{"name": "image", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "output", "artifact_type": "BioImageRef", "required": True}],
        params_schema={"type": "object", "properties": {"sigma": {"type": "number"}}},
    )

    described = service.describe_function(id="base.bioimage_mcp_base.preprocess.gaussian")
    allowed_keys = {
        "id",
        "type",
        "summary",
        "params_schema",
        "inputs",
        "outputs",
        "hints",
    }
    assert {"id", "params_schema"}.issubset(described.keys())
    assert set(described.keys()).issubset(allowed_keys)
    assert described["id"] == "base.bioimage_mcp_base.preprocess.gaussian"
    assert "type" not in described["params_schema"]
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

    service.upsert_function(
        id="base.skimage.filters.gaussian",
        tool_id="tools.base",
        name="Gaussian Blur",
        description="Apply Gaussian blur filter",
        tags=["filter", "blur"],
        inputs=[{"name": "image", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "blurred", "artifact_type": "BioImageRef", "required": True}],
        params_schema={"type": "object", "properties": {"sigma": {"type": "number"}}},
    )

    # This should not raise AttributeError: 'ServerSession' object has no attribute 'id'
    result = service.list_tools(limit=20, cursor=None)

    # Verify contract shape
    assert "items" in result, "Response must contain 'items' key"
    assert isinstance(result["items"], list)
    assert len(result["items"]) > 0
    assert result["items"][0]["name"] == "base"
    conn.close()


def test_search_functions_returns_matching_results() -> None:
    """DISC-002: Verify search_functions(query="phasor") returns matching functions.

    Contract: specs/006-phasor-usability-fixes/contracts/api.yaml
    Given: Base toolkit loaded with phasor functions
    When: Call search_functions(query="phasor")
    Then: Returns functions containing "phasor" in id or description
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
        id="base.phasorpy.phasor.phasor_from_signal",
        tool_id="tools.base",
        name="Phasor from FLIM",
        description="Calculate phasor coordinates from FLIM data",
        tags=["flim", "phasor"],
        inputs=[{"name": "signal", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "output", "artifact_type": "BioImageRef", "required": True}],
        params_schema={"type": "object", "properties": {"harmonic": {"type": "integer"}}},
    )

    # Add non-matching function
    service.upsert_function(
        id="base.bioimage_mcp_base.preprocess.gaussian",
        tool_id="tools.base",
        name="Gaussian Blur",
        description="Apply Gaussian blur filter",
        tags=["filter", "blur"],
        inputs=[{"name": "image", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "blurred", "artifact_type": "BioImageRef", "required": True}],
        params_schema={"type": "object", "properties": {"sigma": {"type": "number"}}},
    )

    result = service.search_functions(keywords="phasor", limit=20, cursor=None)

    # Verify contract shape
    assert "results" in result
    assert isinstance(result["results"], list)

    # Verify query filtering: only phasor-related functions returned
    assert len(result["results"]) > 0, "Should find at least one phasor function"
    for fn in result["results"]:
        assert "phasor" in fn["id"].lower() or "phasor" in fn["summary"].lower(), (
            f"Function {fn['id']} should match 'phasor' query"
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

    # Register multiple tools and functions to trigger pagination
    for i in range(5):
        tool_id = f"tools.pack_{i}"
        env_name = f"pack_{i}"
        service.upsert_tool(
            tool_id=tool_id,
            name=f"Tool Pack {i}",
            description=f"Description for tool pack {i}",
            tool_version="0.1.0",
            env_id=f"bioimage-mcp-pack-{i}",
            manifest_path=f"/abs/tools/pack_{i}/manifest.yaml",
            available=True,
            installed=True,
        )
        service.upsert_function(
            id=f"{env_name}.pkg.module.fn{i}",
            tool_id=tool_id,
            name=f"Function {i}",
            description=f"Function {i}",
            tags=["test"],
            inputs=[],
            outputs=[],
            params_schema={},
        )

    # Request with limit smaller than total environments
    result = service.list_tools(limit=2, cursor=None)

    # Verify contract shape
    assert "items" in result
    assert "next_cursor" in result
    assert isinstance(result["items"], list)

    # Verify pagination behavior
    assert len(result["items"]) == 2, "Should return exactly 'limit' tools"
    assert result["next_cursor"] is not None, "Should provide next_cursor when more results exist"

    # Verify we can fetch next page
    next_page = service.list_tools(limit=2, cursor=result["next_cursor"])
    assert "items" in next_page
    assert len(next_page["items"]) > 0, "Next page should have more results"
    conn.close()
