"""FLIM phasor workflow smoke test."""

from pathlib import Path

import pytest

FLIM_DATASET = Path("datasets/FLUTE_FLIM_data_tif")
FLIM_IMAGE = FLIM_DATASET / "hMSC control.tif"


@pytest.fixture
def flim_image():
    """Provide FLIM test image path."""
    if not FLIM_IMAGE.exists():
        pytest.skip(f"FLIM dataset missing: {FLIM_IMAGE}")
    return FLIM_IMAGE


@pytest.mark.smoke_full
@pytest.mark.asyncio
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

    # Step 4: Rename axes (F -> H for phasor)
    # The manifest says 'image' as input and 'mapping' as param
    rename_result = await live_server.call_tool(
        "run",
        {
            "fn_id": "base.xarray.rename",
            "inputs": {"image": img_ref},
            "params": {"mapping": {"F": "H"}},
        },
    )
    assert rename_result is not None

    # Extract renamed image reference
    if isinstance(rename_result, dict) and "outputs" in rename_result:
        renamed_ref = (
            rename_result["outputs"].get("output")
            or rename_result["outputs"].get("image")
            or rename_result["outputs"].get("img")
        )
    else:
        renamed_ref = rename_result

    assert renamed_ref is not None, f"Failed to get renamed image reference from {rename_result}"

    # Step 5: Compute phasors
    phasor_result = await live_server.call_tool(
        "run",
        {
            "fn_id": "base.phasorpy.phasor.phasor_from_signal",
            "inputs": {"signal": renamed_ref},
            "params": {"harmonic": 1},
        },
    )
    assert phasor_result is not None

    # Validate output is an artifact reference
    if isinstance(phasor_result, dict) and "outputs" in phasor_result:
        outputs = phasor_result["outputs"]
        # Check for ref_id in any output
        found_ref = False
        for key, value in outputs.items():
            if isinstance(value, dict) and "ref_id" in value:
                assert value["ref_id"], f"Empty ref_id in {key}"
                assert "uri" in value, f"Missing uri in {key}"
                found_ref = True
        assert found_ref, "No artifact reference found in outputs"
    elif isinstance(phasor_result, dict) and "ref_id" in phasor_result:
        assert phasor_result["ref_id"], "Empty ref_id"
        assert "uri" in phasor_result, "Missing uri"
    else:
        pytest.fail(f"Unexpected phasor result format: {phasor_result}")
