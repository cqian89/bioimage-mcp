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
    assert set(described.keys()) == {"fn_id", "schema"}
    assert described["fn_id"] == "builtin.gaussian_blur"
    assert described["schema"]["type"] == "object"
