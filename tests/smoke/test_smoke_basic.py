import pytest


def assert_valid_artifact_ref(ref: dict):
    """Validate that an artifact reference has required and non-empty fields."""
    assert isinstance(ref, dict), f"Expected dict, got {type(ref)}"
    assert "ref_id" in ref, f"Missing 'ref_id' in artifact ref: {ref}"
    assert isinstance(ref["ref_id"], str) and ref["ref_id"].strip(), (
        f"ref_id must be a non-empty string: {ref.get('ref_id')}"
    )
    assert "uri" in ref, f"Missing 'uri' in artifact ref: {ref}"
    assert isinstance(ref["uri"], str) and ref["uri"].strip(), (
        f"uri must be a non-empty string: {ref.get('uri')}"
    )


@pytest.mark.smoke_minimal
@pytest.mark.anyio
async def test_smoke_discovery(live_server):
    """Test MCP list() returns summaries and describe() returns schemas."""
    # Test list() returns items and counts (Constitution I: paginated with counts)
    list_result = await live_server.call_tool("list", {"include_counts": True})
    assert "items" in list_result, f"list() missing 'items': {list_result}"
    items = list_result["items"]
    assert isinstance(items, list), f"items must be a list: {type(items)}"

    # Validate counts for non-leaf nodes (Constitution I)
    non_leaf_items = [item for item in items if item.get("has_children")]
    for item in non_leaf_items:
        children = item.get("children", {})
        assert isinstance(children, dict), f"children field must be a dict: {item}"
        assert "total" in children and children["total"] > 0, (
            f"Non-leaf item missing counts (total > 0): {item}"
        )
        assert "by_type" in children, f"Non-leaf item missing by_type counts: {item}"

    # Test describe() for a known function (Constitution I: Full schemas)
    describe_result = await live_server.call_tool("describe", {"fn_id": "base.io.bioimage.load"})
    assert "inputs" in describe_result, f"describe() missing 'inputs': {describe_result}"
    assert "outputs" in describe_result, f"describe() missing 'outputs': {describe_result}"
    assert "params_schema" in describe_result, (
        f"describe() missing 'params_schema': {describe_result}"
    )


@pytest.mark.smoke_minimal
@pytest.mark.anyio
async def test_smoke_basic_run(live_server, sample_image):
    """Test basic run workflow: load image, squeeze."""
    # Load image
    load_result = await live_server.call_tool(
        "run",
        {
            "fn_id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": str(sample_image)},
        },
    )

    # Strengthened artifact validation: must have 'outputs' with valid references
    assert isinstance(load_result, dict) and "outputs" in load_result, (
        f"Load run result missing 'outputs': {load_result}"
    )

    # Extract and validate image reference
    img_ref = load_result["outputs"].get("image") or load_result["outputs"].get("img")
    assert img_ref is not None, (
        f"Failed to get image reference from outputs: {load_result['outputs']}"
    )
    assert_valid_artifact_ref(img_ref)

    # Squeeze the image
    squeeze_result = await live_server.call_tool(
        "run",
        {
            "fn_id": "base.xarray.DataArray.squeeze",
            "inputs": {"image": img_ref},
        },
    )

    # Strengthened validation for squeeze result
    assert squeeze_result.get("status") == "success", f"Squeeze run failed: {squeeze_result}"
    assert "outputs" in squeeze_result, f"Squeeze run result missing 'outputs': {squeeze_result}"

    squeezed_img_ref = (
        squeeze_result["outputs"].get("output")
        or squeeze_result["outputs"].get("image")
        or squeeze_result["outputs"].get("img")
    )
    assert squeezed_img_ref is not None, (
        f"Failed to get squeezed image reference from outputs: {squeeze_result['outputs']}"
    )
    assert_valid_artifact_ref(squeezed_img_ref)
