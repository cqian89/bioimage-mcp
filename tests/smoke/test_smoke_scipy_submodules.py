from __future__ import annotations

import pytest
import pandas as pd
from pathlib import Path
import numpy as np


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

    # Use relative path to ensure the live server has read access
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
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-base")
@pytest.mark.anyio
@pytest.mark.parametrize(
    "fn_id, input_type, params, expected_output_type",
    [
        ("base.scipy.ndimage.gaussian_filter", "image", {"sigma": 1.0}, "BioImageRef"),
        ("base.scipy.stats.describe_table", "table", {"column": "val"}, "NativeOutputRef"),
        (
            "base.scipy.spatial.distance.cdist",
            "table_pair_xy",
            {"metric": "euclidean"},
            "NativeOutputRef",
        ),
        (
            "base.scipy.signal.periodogram",
            "table_as_input",
            {"column": "val", "fs": 10.0},
            "TableRef",
        ),
    ],
)
async def test_scipy_minimal_matrix(
    live_server, smoke_tmp_dir, fn_id, input_type, params, expected_output_type
):
    """Minimal smoke test covering one tool per SciPy submodule."""
    inputs = {}
    if input_type == "image":
        inputs["image"] = await get_test_image(live_server)
    elif input_type == "table":
        inputs["table"] = await get_test_table(live_server, smoke_tmp_dir)
    elif input_type == "table_as_input":
        inputs["input"] = await get_test_table(live_server, smoke_tmp_dir)
    elif input_type == "table_pair_xy":
        data_a = {"x": [0.0, 1.0, 2.0], "y": [0.0, 1.0, 2.0]}
        data_b = {"x": [1.0, 2.0, 3.0], "y": [1.0, 2.0, 3.0]}
        inputs["table_a"] = await get_test_table(
            live_server, smoke_tmp_dir, name="table_a_xy", data=data_a
        )
        inputs["table_b"] = await get_test_table(
            live_server, smoke_tmp_dir, name="table_b_xy", data=data_b
        )

    res = await live_server.call_tool_checked(
        "run", {"fn_id": fn_id, "inputs": inputs, "params": params}
    )
    assert res.get("status") == "success"
    assert "outputs" in res

    # Check for at least one output of expected type
    outputs = res["outputs"]
    found_expected = False
    for out in outputs.values():
        if isinstance(out, dict) and out.get("type") == expected_output_type:
            assert_valid_artifact_ref(out)
            found_expected = True
            break

    assert found_expected, f"Expected output type {expected_output_type} not found in {outputs}"


@pytest.mark.smoke_full
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-base")
@pytest.mark.anyio
@pytest.mark.parametrize(
    "fn_id, input_type, params, expected_output_type",
    [
        # ndimage
        ("base.scipy.ndimage.gaussian_filter", "image", {"sigma": 1.0}, "BioImageRef"),
        ("base.scipy.ndimage.median_filter", "image", {"size": 3}, "BioImageRef"),
        ("base.scipy.ndimage.uniform_filter", "image", {"size": 3}, "BioImageRef"),
        ("base.scipy.ndimage.binary_dilation", "image", {}, "BioImageRef"),
        ("base.scipy.ndimage.binary_erosion", "image", {}, "BioImageRef"),
        ("base.scipy.ndimage.label", "image", {}, "LabelImageRef"),
        # stats
        ("base.scipy.stats.mean_table", "table", {"column": "val"}, "NativeOutputRef"),
        ("base.scipy.stats.skew_table", "table", {"column": "val"}, "NativeOutputRef"),
        ("base.scipy.stats.kurtosis_table", "table", {"column": "val"}, "NativeOutputRef"),
        (
            "base.scipy.stats.ttest_1samp_table",
            "table",
            {"column": "val", "popmean": 0.0},
            "NativeOutputRef",
        ),
        ("base.scipy.stats.ttest_ind_table", "table_pair", {"column": "val"}, "NativeOutputRef"),
        ("base.scipy.stats.f_oneway_table", "multi_table", {"column": "val"}, "NativeOutputRef"),
        (
            "base.scipy.stats.norm.cdf",
            "params_only",
            {"x": [0.0, 1.0], "loc": 0, "scale": 1},
            "NativeOutputRef",
        ),
        # spatial
        (
            "base.scipy.spatial.distance.cdist",
            "table_pair_xy",
            {"metric": "euclidean"},
            "NativeOutputRef",
        ),
        ("base.scipy.spatial.Voronoi", "table_xy", {}, "NativeOutputRef"),
        ("base.scipy.spatial.Delaunay", "table_xy", {}, "NativeOutputRef"),
        # signal
        (
            "base.scipy.signal.periodogram",
            "table_as_input",
            {"column": "val", "fs": 10.0},
            "TableRef",
        ),
        ("base.scipy.signal.welch", "table_as_input", {"column": "val", "fs": 10.0}, "TableRef"),
    ],
)
async def test_scipy_full_matrix(
    live_server, smoke_tmp_dir, fn_id, input_type, params, expected_output_type
):
    """Broad smoke test matrix covering representative SciPy tools."""
    inputs = {}
    if input_type == "image":
        inputs["image"] = await get_test_image(live_server)
    elif input_type == "table":
        inputs["table"] = await get_test_table(live_server, smoke_tmp_dir)
    elif input_type == "table_as_input":
        inputs["input"] = await get_test_table(live_server, smoke_tmp_dir)
    elif input_type == "table_pair":
        inputs["table_a"] = await get_test_table(live_server, smoke_tmp_dir, name="table_a")
        inputs["table_b"] = await get_test_table(live_server, smoke_tmp_dir, name="table_b")
    elif input_type == "multi_table":
        inputs["tables"] = [
            await get_test_table(live_server, smoke_tmp_dir, name="t1"),
            await get_test_table(live_server, smoke_tmp_dir, name="t2"),
            await get_test_table(live_server, smoke_tmp_dir, name="t3"),
        ]
    elif input_type == "params_only":
        pass
    elif input_type == "table_pair_xy":
        data_a = {"x": [0.0, 1.0, 2.0], "y": [0.0, 1.0, 2.0]}
        data_b = {"x": [1.0, 2.0, 3.0], "y": [1.0, 2.0, 3.0]}
        inputs["table_a"] = await get_test_table(
            live_server, smoke_tmp_dir, name="table_a_xy", data=data_a
        )
        inputs["table_b"] = await get_test_table(
            live_server, smoke_tmp_dir, name="table_b_xy", data=data_b
        )
    elif input_type == "table_xy":
        data = {"x": [0.0, 1.0, 0.0, 1.0], "y": [0.0, 0.0, 1.0, 1.0]}
        inputs["table"] = await get_test_table(
            live_server, smoke_tmp_dir, name="table_xy", data=data
        )

    res = await live_server.call_tool_checked(
        "run", {"fn_id": fn_id, "inputs": inputs, "params": params}
    )
    assert res.get("status") == "success"
    assert "outputs" in res

    outputs = res["outputs"]
    found_expected = False
    for out in outputs.values():
        if isinstance(out, dict) and out.get("type") == expected_output_type:
            assert_valid_artifact_ref(out)
            found_expected = True
            break

    assert found_expected, f"Expected output type {expected_output_type} not found in {outputs}"


@pytest.mark.smoke_full
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-base")
@pytest.mark.anyio
async def test_scipy_spatial_kdtree_lifecycle(live_server, smoke_tmp_dir):
    """Test KDTree build and query lifecycle."""
    # 1. Build
    data = {"x": [0.0, 1.0, 2.0], "y": [0.0, 1.0, 2.0]}
    table_ref = await get_test_table(live_server, smoke_tmp_dir, name="kdtree_points", data=data)

    build_res = await live_server.call_tool_checked(
        "run",
        {
            "fn_id": "base.scipy.spatial.cKDTree",
            "inputs": {"table": table_ref},
            "params": {"columns": ["x", "y"]},
        },
    )
    assert build_res.get("status") == "success"
    obj_ref = build_res["outputs"].get("output") or list(build_res["outputs"].values())[0]
    assert obj_ref["type"] == "ObjectRef"
    assert_valid_artifact_ref(obj_ref)

    # 2. Query
    query_data = {"x": [0.5], "y": [0.5]}
    query_table = await get_test_table(
        live_server, smoke_tmp_dir, name="query_points", data=query_data
    )

    query_res = await live_server.call_tool_checked(
        "run",
        {
            "fn_id": "base.scipy.spatial.cKDTree.query",
            "inputs": {"object": obj_ref, "table": query_table},
            "params": {"columns": ["x", "y"], "k": 1},
        },
    )
    assert query_res.get("status") == "success"
    json_ref = query_res["outputs"].get("output") or list(query_res["outputs"].values())[0]
    assert json_ref["type"] == "NativeOutputRef"
    assert_valid_artifact_ref(json_ref)
