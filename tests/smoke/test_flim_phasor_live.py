"""FLIM phasor workflow smoke test."""

from pathlib import Path

import pytest

FLIM_DATASET = Path("datasets/FLUTE_FLIM_data_tif")
FLIM_IMAGE = FLIM_DATASET / "hMSC control.tif"


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


@pytest.fixture
def flim_image():
    """Provide FLIM test image path."""
    if not FLIM_IMAGE.exists():
        pytest.skip(f"FLIM dataset missing: {FLIM_IMAGE}")
    return FLIM_IMAGE


@pytest.mark.smoke_full
@pytest.mark.anyio
@pytest.mark.timeout(300)
async def test_flim_phasor_workflow(live_server, flim_image):
    """Test complete FLIM phasor analysis workflow.

    Tests:
    1. Discovery: list() returns tool summaries
    2. Schema: describe() returns function schema
    3. Load: Load FLIM image from dataset
    4. Rename: Rename axes for phasor analysis
    5. Phasor: Compute phasor coordinates
    """
    # Step 1: Verify discovery
    list_result = await live_server.call_tool("list", {})
    assert list_result is not None

    # Step 2: Fetch schema for phasor function
    describe_result = await live_server.call_tool(
        "describe", {"fn_id": "base.phasorpy.phasor.phasor_from_signal"}
    )
    assert describe_result is not None

    # Step 3: Load FLIM image
    load_result = await live_server.call_tool(
        "run",
        {
            "fn_id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": str(flim_image.absolute())},
        },
    )
    assert load_result is not None

    # Extract output reference
    if isinstance(load_result, dict) and "outputs" in load_result:
        img_ref = load_result["outputs"].get("image") or load_result["outputs"].get("img")
    else:
        img_ref = load_result

    assert img_ref is not None, f"Failed to get image reference from {load_result}"
    assert_valid_artifact_ref(img_ref)

    # Step 4: Transpose so the signal axis is last
    # For FLIM stacks loaded as ZYX, move Z to the last axis (YXZ).
    transpose_result = await live_server.call_tool(
        "run",
        {
            "fn_id": "base.xarray.transpose",
            "inputs": {"image": img_ref},
            "params": {"dims": ["Y", "X", "Z"]},
        },
    )
    assert transpose_result is not None

    if isinstance(transpose_result, dict) and "outputs" in transpose_result:
        transposed_ref = (
            transpose_result["outputs"].get("output")
            or transpose_result["outputs"].get("image")
            or transpose_result["outputs"].get("img")
        )
    else:
        transposed_ref = transpose_result

    assert transposed_ref is not None, (
        f"Failed to get transposed image reference from {transpose_result}"
    )
    assert_valid_artifact_ref(transposed_ref)

    # Step 5: Compute phasors
    phasor_result = await live_server.call_tool(
        "run",
        {
            "fn_id": "base.phasorpy.phasor.phasor_from_signal",
            "inputs": {"signal": transposed_ref},
            "params": {"harmonic": 1, "axis": -1},
        },
    )
    assert phasor_result is not None

    # Validate output is an artifact reference
    if isinstance(phasor_result, dict) and "outputs" in phasor_result:
        outputs = phasor_result["outputs"]
        # Check for ref_id in any output
        found_ref = False
        for _key, value in outputs.items():
            if isinstance(value, dict) and "ref_id" in value:
                assert_valid_artifact_ref(value)
                found_ref = True
        assert found_ref, "No artifact reference found in outputs"
    elif isinstance(phasor_result, dict) and "ref_id" in phasor_result:
        assert_valid_artifact_ref(phasor_result)
    else:
        pytest.fail(f"Unexpected phasor result format: {phasor_result}")
