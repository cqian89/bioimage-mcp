"""Contract tests for the 'list' MCP tool.

These tests verify the new API behavior with:
- Deterministic ordering with cursor pagination
- Child counts for non-leaf nodes
- I/O summaries for function nodes
- NOT_FOUND error for invalid paths
"""

import sqlite3

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import init_schema


# T032: Deterministic ordering + cursor pagination
def test_list_returns_deterministic_order_with_pagination():
    """List should return items in deterministic order with cursor/limit/next_cursor."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    service = DiscoveryService(conn)

    # Setup multiple nodes
    for i in range(5):
        service.upsert_tool(
            tool_id=f"tools.pack_{i}",
            name=f"Pack {i}",
            description=f"Desc {i}",
            tool_version="0.1.0",
            env_id=f"env_{i}",
            manifest_path=f"/abs/{i}.yaml",
            available=True,
            installed=True,
        )
        service.upsert_function(
            fn_id=f"pack_{i}.fn",
            tool_id=f"tools.pack_{i}",
            name=f"Fn {i}",
            description=f"Fn {i} desc",
            tags=[],
            inputs=[],
            outputs=[],
            params_schema={},
        )

    # First page
    page1 = service.list_tools(limit=2)
    assert len(page1["items"]) == 2
    assert page1["next_cursor"] is not None

    # Second page
    page2 = service.list_tools(limit=2, cursor=page1["next_cursor"])
    assert len(page2["items"]) == 2
    assert page2["next_cursor"] is not None

    # Ensure deterministic (calling again with same cursor)
    page2_repeat = service.list_tools(limit=2, cursor=page1["next_cursor"])
    assert page2["items"] == page2_repeat["items"]

    # Ensure ordered by id
    ids = [item["id"] for item in page1["items"]] + [item["id"] for item in page2["items"]]
    assert ids == sorted(ids)

    conn.close()


# T033: Child counts
def test_list_includes_child_counts_for_non_leaf_nodes():
    """Non-leaf nodes should include children.total and children.by_type."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    service = DiscoveryService(conn)

    service.upsert_tool(
        tool_id="tools.base",
        name="Base",
        description="Base",
        tool_version="0.1.0",
        env_id="env_base",
        manifest_path="/abs/base.yaml",
        available=True,
        installed=True,
    )
    service.upsert_function(
        fn_id="base.ops.fn1",
        tool_id="tools.base",
        name="Fn1",
        description="Fn1",
        tags=[],
        inputs=[],
        outputs=[],
        params_schema={},
    )
    service.upsert_function(
        fn_id="base.utils.fn2",
        tool_id="tools.base",
        name="Fn2",
        description="Fn2",
        tags=[],
        inputs=[],
        outputs=[],
        params_schema={},
    )

    result = service.list_tools(path="base")
    # Immediate children are "base.ops" and "base.utils"
    assert len(result["items"]) == 2
    node = result["items"][0]
    assert node["id"] in ["base.ops", "base.utils"]
    assert "children" in node
    assert node["children"]["total"] == 1  # Each has one function
    assert node["children"]["by_type"]["function"] == 1

    conn.close()


# T034: I/O summaries for functions
def test_list_includes_io_summaries_for_function_nodes():
    """Function nodes should include io.inputs and io.outputs summaries."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    service = DiscoveryService(conn)

    service.upsert_tool(
        tool_id="tools.base",
        name="Base",
        description="Base",
        tool_version="0.1.0",
        env_id="env_base",
        manifest_path="/abs/base.yaml",
        available=True,
        installed=True,
    )
    service.upsert_function(
        fn_id="base.ops.gaussian",
        tool_id="tools.base",
        name="Gaussian",
        description="Gaussian",
        tags=[],
        inputs=[{"name": "image", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "output", "artifact_type": "BioImageRef"}],
        params_schema={},
    )

    result = service.list_tools(path="base.ops")
    assert len(result["items"]) == 1
    node = result["items"][0]
    assert node["type"] == "function"
    assert "io" in node
    assert len(node["io"]["inputs"]) == 1
    assert node["io"]["inputs"][0]["name"] == "image"
    assert node["io"]["inputs"][0]["type"] == "BioImageRef"
    assert len(node["io"]["outputs"]) == 1
    assert node["io"]["outputs"][0]["name"] == "output"
    assert node["io"]["outputs"][0]["type"] == "BioImageRef"

    conn.close()


# T035: NOT_FOUND error
def test_list_returns_not_found_for_invalid_path():
    """List should return NOT_FOUND error for non-existent paths."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    service = DiscoveryService(conn)

    result = service.list_tools(path="invalid.nonexistent.path")
    assert "error" in result
    assert result["error"]["code"] == "NOT_FOUND"
    assert "details" in result["error"]
    assert len(result["error"]["details"]) == 1
    assert result["error"]["details"][0]["path"] == "/path"

    conn.close()
