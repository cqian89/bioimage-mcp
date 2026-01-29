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
async def test_multi_artifact_concat(live_server, sample_image):
    """
    Test multi-artifact input workflow (Fix for critical bug).

    This test verifies that the MCP server correctly handles a list of artifact
    references passed to a tool, specifically base.xarray.concat.

    Steps:
    1. Load image using base.io.bioimage.load
    2. Run base.phasorpy.phasor.phasor_from_signal to get multiple outputs (mean, real, imag)
    3. Call base.xarray.concat with a LIST of ref_ids: [real_ref_id, imag_ref_id]
    4. Verify concatenated output has expected status and structure
    """
    # 1. Load image
    load_result = await live_server.call_tool(
        "run",
        {
            "id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": str(sample_image.absolute())},
        },
    )
    assert load_result["status"] == "success", f"Load failed: {load_result.get('error')}"
    img_ref = load_result["outputs"].get("image") or load_result["outputs"].get("img")
    assert img_ref is not None
    assert_valid_artifact_ref(img_ref)

    # 2. Run phasor_from_signal to produce multiple outputs
    # We use axis=2 (Z axis) for the synthetic test.tif which is 5D TCZYX (1, 1, 3, 64, 64)
    phasor_result = await live_server.call_tool(
        "run",
        {
            "id": "base.phasorpy.phasor.phasor_from_signal",
            "inputs": {"signal": img_ref},
            "params": {"axis": 2},
        },
    )
    assert phasor_result["status"] == "success", f"Phasor failed: {phasor_result.get('error')}"
    outputs = phasor_result["outputs"]
    assert "real" in outputs and "imag" in outputs

    real_ref = outputs["real"]
    imag_ref = outputs["imag"]
    assert_valid_artifact_ref(real_ref)
    assert_valid_artifact_ref(imag_ref)

    real_ref_id = real_ref["ref_id"]
    imag_ref_id = imag_ref["ref_id"]

    # 3. Call base.xarray.concat with a LIST of artifact ref_ids
    # This specifically tests the resolution of artifacts within a list.
    # The bug was that passing a list [ref1, ref2] failed to resolve the references.
    concat_result = await live_server.call_tool(
        "run",
        {
            "id": "base.xarray.concat",
            "inputs": {"images": [real_ref_id, imag_ref_id]},
            "params": {"dim": "C"},
        },
    )

    # 4. Verify the concatenated output
    assert concat_result["status"] == "success", (
        f"Concat failed with list input: {concat_result.get('error')}. "
        "This likely indicates the 'multi-artifact input' bug is still present."
    )

    assert "outputs" in concat_result
    concat_ref = concat_result["outputs"].get("output")
    assert concat_ref is not None
    assert_valid_artifact_ref(concat_ref)

    # Verify the concatenated shape: [1, 2, 1, 64, 64] (TCZYX)
    metadata = concat_ref.get("metadata", {})
    shape = metadata.get("shape")
    if shape:
        # Input real/imag were [1, 1, 64, 64] (CZYX) or similar
        # Concat along C should result in C=2
        assert 2 in shape, f"Expected dimension of size 2 in shape {shape}"

        dims = metadata.get("dims", [])
        if "C" in dims:
            c_idx = dims.index("C")
            assert shape[c_idx] == 2, f"Expected C dimension to be 2, got {shape[c_idx]}"
