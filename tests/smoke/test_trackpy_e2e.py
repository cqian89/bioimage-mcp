from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.lfs_helpers import skip_if_lfs_pointer


def assert_valid_artifact_ref(ref: dict, name: str = "output"):
    """Assert ref is a valid artifact reference."""
    assert isinstance(ref, dict), f"{name} is not a dict: {type(ref)}"
    assert "ref_id" in ref, f"Missing 'ref_id' in {name}: {ref}"
    assert isinstance(ref["ref_id"], str) and ref["ref_id"].strip(), (
        f"ref_id must be a non-empty string in {name}"
    )
    assert "uri" in ref or "path" in ref, f"Missing 'uri' or 'path' in {name}: {ref}"


@pytest.fixture
def trackpy_image():
    """Path to the vendored trackpy example image."""
    path = Path.cwd() / "datasets" / "trackpy-examples" / "bulk_water" / "frame000_green.ome.tiff"
    if not path.exists():
        pytest.skip(f"Vendored trackpy data not found at {path}")
    skip_if_lfs_pointer(path)
    return path


@pytest.mark.smoke_extended
@pytest.mark.requires_env("bioimage-mcp-trackpy")
@pytest.mark.anyio
async def test_locate_link_batch_workflow(live_server, trackpy_image):
    """Test full Trackpy workflow: locate, link, and batch."""

    # 1. LOAD IMAGE
    # We use base.io.bioimage.load to get an image artifact
    load_res = await live_server.call_tool(
        "run",
        {
            "id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": str(trackpy_image.absolute())},
        },
    )
    assert load_res["status"] == "success", f"Load failed: {load_res.get('error')}"
    img_ref = load_res["outputs"]["image"]
    assert_valid_artifact_ref(img_ref, "load output")

    # 2. LOCATE
    # bulk_water has dark particles on light background, so invert=True
    # We use the generic 'image' input key which is mapped by the worker
    locate_res = await live_server.call_tool(
        "run",
        {
            "id": "trackpy.locate",
            "inputs": {"image": img_ref},
            "params": {"diameter": 11, "invert": True, "minmass": 100},
        },
    )
    assert locate_res["status"] == "success", f"Locate failed: {locate_res.get('error')}"
    features_ref = locate_res["outputs"]["table"]
    assert_valid_artifact_ref(features_ref, "locate output")

    # 3. BATCH
    # Test batch processing on the same image
    # batch also uses the generic 'image' input key (mapped to 'frames')
    batch_res = await live_server.call_tool(
        "run",
        {
            "id": "trackpy.batch",
            "inputs": {"image": img_ref},
            "params": {"diameter": 11, "invert": True, "minmass": 100},
            "verbosity": "full",
        },
    )
    assert batch_res["status"] == "success", f"Batch failed: {batch_res.get('error')}"
    batch_features_ref = batch_res["outputs"]["table"]
    assert_valid_artifact_ref(batch_features_ref, "batch output")

    # 4. LINK
    # link expects a table with a 'frame' column. batch output has it.
    # We use the generic 'table' input key which is mapped by the worker (to 'f')
    link_res = await live_server.call_tool(
        "run",
        {
            "id": "trackpy.link",
            "inputs": {"table": batch_features_ref},
            "params": {"search_range": 5},
            "verbosity": "full",
        },
    )
    assert link_res["status"] == "success", f"Link failed: {link_res.get('error')}"
    tracks_ref = link_res["outputs"]["table"]
    assert_valid_artifact_ref(tracks_ref, "link output")

    # 5. VERIFY Response
    # Check that we got results back
    assert tracks_ref["ref_id"]

    # Optional: Verify row count in tracks table
    # Since it's a single frame, row count should match batch features count
    assert tracks_ref["row_count"] == batch_features_ref["row_count"]
    # And it should have a 'particle' column (added by link)
    assert "particle" in tracks_ref["columns"]
