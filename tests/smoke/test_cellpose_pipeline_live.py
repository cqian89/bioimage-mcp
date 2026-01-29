"""Cellpose pipeline smoke test."""

from pathlib import Path

import pytest

SYNTHETIC_IMAGE = Path("datasets/synthetic/test.tif")


def assert_valid_artifact_ref(ref: dict, name: str = "output"):
    """Assert ref is a valid artifact reference.

    Per Constitution III: All I/O via typed, file-backed artifact references (URI + metadata).
    """
    assert isinstance(ref, dict), f"{name} is not a dict: {type(ref)}"
    assert "ref_id" in ref, f"Missing 'ref_id' in {name}: {ref}"
    assert isinstance(ref["ref_id"], str) and ref["ref_id"].strip(), (
        f"ref_id must be a non-empty string in {name}: {ref.get('ref_id')}"
    )
    assert "uri" in ref, f"Missing 'uri' in {name}: {ref}"
    assert isinstance(ref["uri"], str) and ref["uri"].strip(), (
        f"uri must be a non-empty string in {name}: {ref.get('uri')}"
    )


@pytest.fixture
def cellpose_image():
    """Provide test image for Cellpose."""
    if not SYNTHETIC_IMAGE.exists():
        pytest.skip(f"Test image missing: {SYNTHETIC_IMAGE}")
    return SYNTHETIC_IMAGE


@pytest.mark.smoke_full
@pytest.mark.requires_env("bioimage-mcp-cellpose")
@pytest.mark.anyio
@pytest.mark.timeout(300)
async def test_cellpose_pipeline(live_server, cellpose_image, interaction_logger):
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
        "describe", {"id": "cellpose.models.CellposeModel.eval"}
    )
    assert describe_result is not None

    # Step 3: Load image
    load_result = await live_server.call_tool(
        "run",
        {
            "id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": str(cellpose_image.absolute())},
        },
    )
    assert load_result is not None

    # Validate and extract load output
    assert isinstance(load_result, dict) and "outputs" in load_result, (
        f"Expected dict with 'outputs', got {type(load_result)}: {load_result}"
    )
    img_ref = (
        load_result["outputs"].get("image")
        or load_result["outputs"].get("img")
        or load_result["outputs"].get("output")
    )
    assert img_ref, f"Could not find image output in load outputs: {load_result['outputs'].keys()}"
    assert_valid_artifact_ref(img_ref, "load output")

    # Step 4: Sum projection (Z axis)
    sum_result = await live_server.call_tool(
        "run",
        {
            "id": "base.xarray.DataArray.sum",
            "inputs": {"image": img_ref},
            "params": {"dim": "Z"},
        },
    )
    assert sum_result is not None

    # Validate and extract sum output
    assert isinstance(sum_result, dict) and "outputs" in sum_result, (
        f"Expected dict with 'outputs', got {type(sum_result)}: {sum_result}"
    )
    summed_ref = (
        sum_result["outputs"].get("output")
        or sum_result["outputs"].get("image")
        or sum_result["outputs"].get("img")
    )
    assert summed_ref, f"Could not find output image in sum outputs: {sum_result['outputs'].keys()}"
    assert_valid_artifact_ref(summed_ref, "sum output")

    # Step 5: Export to OME-TIFF
    export_result = await live_server.call_tool(
        "run",
        {
            "id": "base.io.bioimage.export",
            "inputs": {"image": summed_ref},
            "params": {"format": "OME-TIFF"},
        },
    )
    assert export_result is not None

    if export_result.get("status") != "success":
        print(f"EXPORT RESULT: {export_result}")
        print(f"SERVER STDERR:\n{live_server.get_stderr()}")

    # Validate and extract export output
    assert isinstance(export_result, dict) and "outputs" in export_result, (
        f"Expected dict with 'outputs', got {type(export_result)}: {export_result}"
    )
    exported_ref = (
        export_result["outputs"].get("output")
        or export_result["outputs"].get("image")
        or export_result["outputs"].get("img")
        or export_result["outputs"].get("path")
    )
    assert exported_ref, (
        f"Could not find output artifact in export outputs: {export_result['outputs'].keys()}"
    )
    assert_valid_artifact_ref(exported_ref, "export output")

    # Step 6: Initialize Cellpose model
    model_init_result = await live_server.call_tool(
        "run",
        {
            "id": "cellpose.models.CellposeModel",
            "inputs": {},
            "params": {"model_type": "cyto3", "gpu": False},
        },
    )
    assert model_init_result is not None

    assert isinstance(model_init_result, dict) and "outputs" in model_init_result, (
        f"Expected dict with 'outputs', got {type(model_init_result)}: {model_init_result}"
    )
    model_ref = model_init_result["outputs"].get("model")
    assert model_ref, (
        f"Could not find 'model' in model init outputs: {model_init_result['outputs'].keys()}"
    )
    assert_valid_artifact_ref(model_ref, "cellpose model")

    # Step 7: Cellpose segmentation
    segment_result = await live_server.call_tool(
        "run",
        {
            "id": "cellpose.models.CellposeModel.eval",
            "inputs": {"model": model_ref, "x": exported_ref},
            "params": {"diameter": 0},
        },
    )
    assert segment_result is not None

    # Validate output contains artifact reference
    assert isinstance(segment_result, dict) and "outputs" in segment_result, (
        f"Expected dict with 'outputs', got {type(segment_result)}: {segment_result}"
    )
    outputs = segment_result["outputs"]
    assert outputs, f"Segment result outputs is empty: {segment_result}"

    # Check for ref_id in all outputs and verify format
    for key, value in outputs.items():
        assert_valid_artifact_ref(value, f"segment output '{key}'")
        if key == "labels":
            assert value.get("format") == "OME-Zarr", (
                f"Expected OME-Zarr for labels, got {value.get('format')}"
            )
