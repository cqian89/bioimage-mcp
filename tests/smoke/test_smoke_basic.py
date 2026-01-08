import pytest


@pytest.mark.smoke_minimal
@pytest.mark.asyncio
async def test_smoke_discovery(live_server):
    """Test MCP list() returns summaries and describe() returns schemas."""
    # Test list() returns items
    list_result = await live_server.call_tool("list", {})
    assert "items" in list_result or isinstance(list_result, list)

    # Test describe() for a known function
    describe_result = await live_server.call_tool("describe", {"fn_id": "base.io.bioimage.load"})
    assert "inputs" in describe_result or "summary" in describe_result


@pytest.mark.smoke_minimal
@pytest.mark.asyncio
async def test_smoke_basic_run(live_server, sample_image):
    """Test basic run workflow: load image, squeeze."""
    # Load image
    # Note: 'path' is a parameter for load, not an input artifact.
    load_result = await live_server.call_tool(
        "run",
        {
            "fn_id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": str(sample_image)},
        },
    )
    assert "ref_id" in str(load_result) or "outputs" in load_result

    # Get the output reference for next step
    # Extract the image reference from load_result
    if isinstance(load_result, dict) and "outputs" in load_result:
        # Check both names just in case, but manifest says 'image'
        img_ref = load_result["outputs"].get("image") or load_result["outputs"].get("img")
    else:
        img_ref = load_result

    assert img_ref is not None, f"Failed to get image reference from {load_result}"

    # Squeeze the image (if it has dimensions to squeeze)
    # Note: 'image' is the input name for squeeze.
    squeeze_result = await live_server.call_tool(
        "run",
        {
            "fn_id": "base.xarray.squeeze",
            "inputs": {"image": img_ref},
        },
    )
    assert squeeze_result is not None
    assert squeeze_result.get("status") == "success"
