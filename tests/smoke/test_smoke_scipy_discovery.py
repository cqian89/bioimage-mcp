from __future__ import annotations

import pytest


@pytest.mark.smoke_minimal
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-base")
@pytest.mark.anyio
async def test_scipy_discovery_list(live_server):
    """Verify that SciPy tools are discoverable via the 'list' tool."""
    # List root environments
    res = await live_server.call_tool_checked("list", {"include_counts": True})
    items = res.get("items", [])
    assert items, "Catalog root should not be empty"

    # Find the 'base' environment node
    base_node = next((item for item in items if item["id"] == "base"), None)
    assert base_node, f"Environment 'base' not found in {[i['id'] for i in items]}"

    # List packages in 'base'
    res = await live_server.call_tool_checked("list", {"path": "base"})
    base_items = res.get("items", [])
    assert base_items, "Environment 'base' should have children"

    # Search for scipy in the immediate children of 'base'
    scipy_found = any("scipy" in item["id"].lower() for item in base_items)
    assert scipy_found, f"SciPy package not found under 'base' in {[i['id'] for i in base_items]}"


@pytest.mark.smoke_minimal
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-base")
@pytest.mark.anyio
@pytest.mark.parametrize(
    "fn_id",
    [
        "base.scipy.ndimage.gaussian_filter",
        "base.scipy.stats.ttest_ind_table",
        "base.scipy.spatial.distance.cdist",
        "base.scipy.signal.periodogram",
    ],
)
async def test_scipy_discovery_describe(live_server, fn_id):
    """Verify that SciPy tools can be described with valid schemas."""
    res = await live_server.call_tool_checked("describe", {"id": fn_id})

    # Assertions based on standard describe output
    assert "id" in res
    assert res["id"] == fn_id

    # Core schema elements required by Task 2
    assert "inputs" in res, f"Missing 'inputs' in describe for {fn_id}"
    assert "outputs" in res, f"Missing 'outputs' in describe for {fn_id}"
    assert "params_schema" in res, f"Missing 'params_schema' in describe for {fn_id}"

    # Basic validation of params_schema
    assert isinstance(res["params_schema"], dict)
    assert res["params_schema"].get("type") == "object"
