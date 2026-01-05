"""Contract tests for the 'describe' MCP tool.

These tests verify:
- Separated inputs/outputs/params_schema for functions
- Describe works for non-function nodes
- NOT_FOUND error for invalid IDs
"""

import sqlite3
from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import init_schema


# T036: Separated inputs/outputs/params_schema
def test_describe_function_separates_inputs_outputs_params():
    """Describe should return inputs, outputs, and params_schema as separate fields."""
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
        params_schema={
            "type": "object",
            "properties": {
                "sigma": {"type": "number"},
                "image": {"type": "string"},  # Should be removed if it's an input
            },
        },
    )

    described = service.describe_function(fn_id="base.ops.gaussian")

    assert "inputs" in described
    assert "outputs" in described
    assert "params_schema" in described
    assert "image" in described["inputs"]
    assert "output" in described["outputs"]
    assert "sigma" in described["params_schema"]["properties"]
    # Contract: params_schema contains no artifact port keys
    assert "image" not in described["params_schema"]["properties"]

    conn.close()


# T037: Describe non-function node
def test_describe_non_function_node_returns_catalog_node():
    """Describe on non-function should return CatalogNode with child preview."""
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

    described = service.describe_function(fn_id="base.ops")
    assert described["id"] == "base.ops"
    assert described["type"] == "package"
    assert "children" in described

    conn.close()


# T038: NOT_FOUND error
def test_describe_returns_not_found_for_invalid_id():
    """Describe should return NOT_FOUND error for non-existent IDs."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    service = DiscoveryService(conn)

    described = service.describe_function(fn_id="invalid.function.id")
    assert "error" in described
    assert described["error"]["code"] == "NOT_FOUND"

    conn.close()
