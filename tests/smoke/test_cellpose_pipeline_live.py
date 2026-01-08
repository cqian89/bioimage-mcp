"""Cellpose pipeline smoke test."""

from pathlib import Path

import pytest

SYNTHETIC_IMAGE = Path("datasets/synthetic/test.tif")


@pytest.fixture
def cellpose_image():
    """Provide test image for Cellpose."""
    if not SYNTHETIC_IMAGE.exists():
        pytest.skip(f"Test image missing: {SYNTHETIC_IMAGE}")
    return SYNTHETIC_IMAGE


@pytest.mark.smoke_full
@pytest.mark.requires_env("bioimage-mcp-cellpose")
@pytest.mark.asyncio
@pytest.mark.timeout(300)
async def test_cellpose_pipeline(live_server, cellpose_image):
    """Test Cellpose segmentation pipeline.

    Tests:
    1. Discovery: list() returns tool summaries
    2. Schema: describe() returns Cellpose function schema
    3. Load: Load test image
    4. Sum: Z-projection via sum
    5. Export: Convert to OME-TIFF
    6. Segment: Run Cellpose segmentation
    """
    # Step 1: Verify discovery
    list_result = await live_server.call_tool("list", {})
    assert list_result is not None

    # Step 2: Fetch schema for Cellpose function
    describe_result = await live_server.call_tool(
        "describe", {"fn_id": "cellpose.models.CellposeModel.eval"}
    )
    assert describe_result is not None

    # Step 3: Load image
    load_result = await live_server.call_tool(
        "run",
        {
            "fn_id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": str(cellpose_image.absolute())},
        },
    )
    assert load_result is not None

    # Extract output reference
    if isinstance(load_result, dict) and "outputs" in load_result:
        img_ref = load_result["outputs"].get("img") or load_result["outputs"].get("image")
    else:
        img_ref = load_result

    # Step 4: Sum projection (Z axis)
    sum_result = await live_server.call_tool(
        "run",
        {
            "fn_id": "base.xarray.sum",
            "inputs": {"img": img_ref},
            "params": {"dim": "Z"},
        },
    )
    assert sum_result is not None

    # Extract summed reference
    if isinstance(sum_result, dict) and "outputs" in sum_result:
        summed_ref = sum_result["outputs"].get("img") or sum_result["outputs"].get("image")
    else:
        summed_ref = sum_result

    # Step 5: Export to OME-TIFF
    export_result = await live_server.call_tool(
        "run",
        {
            "fn_id": "base.io.bioimage.export",
            "inputs": {"img": summed_ref},
            "params": {"format": "ome-tiff"},
        },
    )
    assert export_result is not None

    # Extract exported reference
    if isinstance(export_result, dict) and "outputs" in export_result:
        exported_ref = export_result["outputs"].get("img") or export_result["outputs"].get("path")
    else:
        exported_ref = export_result

    # Step 6: Cellpose segmentation
    segment_result = await live_server.call_tool(
        "run",
        {
            "fn_id": "cellpose.models.CellposeModel.eval",
            "inputs": {"img": exported_ref},
            "params": {"model_type": "cyto"},
        },
    )
    assert segment_result is not None

    # Validate output contains artifact reference
    if isinstance(segment_result, dict) and "outputs" in segment_result:
        outputs = segment_result["outputs"]
        # Check for ref_id in any output
        for key, value in outputs.items():
            if isinstance(value, dict) and "ref_id" in value:
                assert value["ref_id"], f"Empty ref_id in {key}"
