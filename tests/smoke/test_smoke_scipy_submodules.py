from __future__ import annotations

import pytest
import pandas as pd
from pathlib import Path


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


async def get_test_image(live_server):
    """Helper to obtain a BioImageRef from the synthetic test dataset."""
    res = await live_server.call_tool_checked(
        "run",
        {
            "fn_id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": "datasets/synthetic/test.tif"},
        },
    )
    assert res.get("status") == "success"
    assert "outputs" in res
    img_ref = res["outputs"].get("image")
    assert img_ref is not None
    assert_valid_artifact_ref(img_ref)
    return img_ref


@pytest.fixture(scope="module")
def smoke_tmp_dir():
    """Fixture to provide a temporary directory within datasets for smoke tests."""
    tmp_dir = Path.cwd() / "datasets" / "smoke_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    yield tmp_dir
    # Cleanup after module tests
    import shutil

    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)


async def get_test_table(live_server, tmp_dir, name="test", data=None):
    """Helper to obtain a TableRef from a dynamically created CSV."""
    if data is None:
        data = {"val": [1.0, 2.0, 3.0, 4.0, 5.0]}
    df = pd.DataFrame(data)

    csv_path = tmp_dir / f"{name}.csv"
    df.to_csv(csv_path, index=False)

    # Use relative path to avoid resolution issues if any
    rel_path = csv_path.relative_to(Path.cwd())

    res = await live_server.call_tool_checked(
        "run", {"fn_id": "base.io.table.load", "inputs": {}, "params": {"path": str(rel_path)}}
    )
    assert res.get("status") == "success"
    assert "outputs" in res
    table_ref = res["outputs"].get("table")
    assert table_ref is not None
    assert_valid_artifact_ref(table_ref)
    return table_ref


@pytest.mark.smoke_minimal
@pytest.mark.anyio
async def test_scipy_harness_sanity(live_server, smoke_tmp_dir):
    """Verify that helpers can produce artifacts via the live server."""
    img_ref = await get_test_image(live_server)
    assert img_ref["type"] == "BioImageRef"

    table_ref = await get_test_table(live_server, smoke_tmp_dir)
    assert table_ref["type"] == "TableRef"
