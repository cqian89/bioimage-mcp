from __future__ import annotations

import sqlite3
from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import init_schema


def test_list_function_metadata_fields():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)

    service = DiscoveryService(conn)

    # 1. Upsert a tool
    service.upsert_tool(
        tool_id="cellpose",
        name="Cellpose",
        description="Cellpose tool",
        tool_version="2.0",
        env_id="bioimage-mcp-cellpose",
        manifest_path="/path/to/manifest.yaml",
        installed=True,
        available=True,
    )

    # 2. Upsert a function with module, io_pattern, introspection_source
    service.upsert_function(
        fn_id="cellpose.models",
        tool_id="cellpose",
        name="models",
        description="Cellpose models",
        tags=["segmentation"],
        inputs=[],
        outputs=[],
        params_schema={"type": "object", "properties": {}},
        module="cellpose.models",
        io_pattern="pure_constructor",
        introspection_source="python_api",
    )

    # 3. Call list_tools (which handles tools/list MCP command)
    result = service.list_tools(path="cellpose.models")

    assert "items" in result
    assert len(result["items"]) == 1
    node = result["items"][0]

    assert node["id"] == "cellpose.models"
    assert node["module"] == "cellpose.models"
    assert node["io_pattern"] == "pure_constructor"
    assert node["introspection_source"] == "python_api"
