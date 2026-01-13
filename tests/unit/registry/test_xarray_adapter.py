import json
import sys
from io import StringIO
from pathlib import Path

import numpy as np
import pytest
from bioio.writers import OmeTiffWriter

from bioimage_mcp.registry.dynamic.adapters import ADAPTER_REGISTRY


def test_xarray_adapter_registered():
    """Test that xarray adapter is registered in ADAPTER_REGISTRY."""
    assert "xarray" in ADAPTER_REGISTRY


def test_xarray_adapter_execution(tmp_path):
    """Test that xarray adapter can execute a simple isel."""
    if "xarray" not in ADAPTER_REGISTRY:
        pytest.skip("Xarray adapter not registered")

    adapter = ADAPTER_REGISTRY["xarray"]

    img_path = tmp_path / "test.ome.tiff"
    data = np.zeros((1, 1, 1, 10, 10), dtype=np.uint8)  # TCZYX
    OmeTiffWriter.save(data, str(img_path), dim_order="TCZYX")

    input_artifact = {
        "type": "BioImageRef",
        "format": "OME-TIFF",
        "uri": img_path.as_uri(),
        "metadata": {"axes": "TCZYX"},
    }

    # Try isel to select a slice
    outputs = adapter.execute(
        fn_id="base.xarray.DataArray.isel",
        inputs=[("image", input_artifact)],
        params={"X": slice(0, 5)},
        work_dir=tmp_path,
    )

    assert len(outputs) == 1
    assert outputs[0]["type"] == "ObjectRef"
    assert outputs[0]["metadata"]["shape"][-1] == 5
    assert outputs[0]["metadata"]["dims"] == ["T", "C", "Z", "Y", "X"]


def test_axis_padding_standard_order_2d(tmp_path):
    """Test that 2D results (YX) preserve native dimensions."""
    if "xarray" not in ADAPTER_REGISTRY:
        pytest.skip("Xarray adapter not registered")

    adapter = ADAPTER_REGISTRY["xarray"]

    # Create 2D input image (YX)
    img_path = tmp_path / "test_2d.ome.tiff"
    data = np.zeros((1, 1, 1, 10, 10), dtype=np.uint8)  # TCZYX
    OmeTiffWriter.save(data, str(img_path), dim_order="TCZYX")

    input_artifact = {
        "type": "BioImageRef",
        "format": "OME-TIFF",
        "uri": img_path.as_uri(),
        "metadata": {"axes": "TCZYX"},
    }

    # Squeeze to get 2D result (should drop T, C, Z)
    outputs = adapter.execute(
        fn_id="base.xarray.DataArray.squeeze",
        inputs=[("image", input_artifact)],
        params={},
        work_dir=tmp_path,
    )

    assert len(outputs) == 1
    # The output should preserve native YX
    assert outputs[0]["type"] == "BioImageRef"
    assert outputs[0]["metadata"]["dims"] == ["Y", "X"]
    assert outputs[0]["metadata"]["shape"] == [10, 10]


def test_axis_padding_standard_order_3d(tmp_path):
    """Test that 3D results (ZYX) preserve native dimensions."""
    if "xarray" not in ADAPTER_REGISTRY:
        pytest.skip("Xarray adapter not registered")

    adapter = ADAPTER_REGISTRY["xarray"]

    # Create 3D input image (ZYX after squeezing T and C)
    img_path = tmp_path / "test_3d.ome.tiff"
    data = np.zeros((1, 1, 5, 10, 10), dtype=np.uint8)  # TCZYX
    OmeTiffWriter.save(data, str(img_path), dim_order="TCZYX")

    input_artifact = {
        "type": "BioImageRef",
        "format": "OME-TIFF",
        "uri": img_path.as_uri(),
        "metadata": {"axes": "TCZYX"},
    }

    # Squeeze to get 3D result (drops T and C, keeps Z)
    outputs = adapter.execute(
        fn_id="base.xarray.DataArray.squeeze",
        inputs=[("image", input_artifact)],
        params={},
        work_dir=tmp_path,
    )

    assert len(outputs) == 1
    # The output should preserve native ZYX
    assert outputs[0]["type"] == "BioImageRef"
    assert outputs[0]["metadata"]["dims"] == ["Z", "Y", "X"]
    assert outputs[0]["metadata"]["shape"] == [5, 10, 10]


def test_io_bioimage_export_works(tmp_path):
    """Test that base.io.bioimage.export works (statically mapped)."""
    # Add tools/base to sys.path
    tools_base = Path(__file__).resolve().parents[3] / "tools" / "base"
    if str(tools_base) not in sys.path:
        sys.path.insert(0, str(tools_base))

    from bioimage_mcp_base.entrypoint import main

    img_path = tmp_path / "input.ome.tiff"
    data = np.zeros((1, 1, 1, 10, 10), dtype=np.uint8)
    OmeTiffWriter.save(data, str(img_path), dim_order="TCZYX")

    request = {
        "fn_id": "base.io.bioimage.export",
        "inputs": {
            "image": {"type": "BioImageRef", "format": "OME-TIFF", "uri": img_path.as_uri()}
        },
        "params": {"format": "OME-TIFF"},
        "work_dir": str(tmp_path),
    }

    # Mock stdin/stdout
    old_stdin = sys.stdin
    old_stdout = sys.stdout
    sys.stdin = StringIO(json.dumps(request))
    sys.stdout = StringIO()

    try:
        main()
        response = json.loads(sys.stdout.getvalue())
    finally:
        sys.stdin = old_stdin
        sys.stdout = old_stdout

    assert response["ok"] is True
    assert "output" in response["outputs"]
    assert Path(response["outputs"]["output"]["path"]).exists()


def test_xarray_adapter_handles_reduced_y_dimension(tmp_path):
    """Ensure native dimensions are preserved when Y is reduced."""
    if "xarray" not in ADAPTER_REGISTRY:
        pytest.skip("Xarray adapter not registered")

    adapter = ADAPTER_REGISTRY["xarray"]

    # Create 5D input image (TCZYX)
    img_path = tmp_path / "test_5d.ome.tiff"
    data = np.zeros((1, 2, 3, 4, 5), dtype=np.uint8)  # TCZYX
    OmeTiffWriter.save(data, str(img_path), dim_order="TCZYX")

    input_artifact = {
        "type": "BioImageRef",
        "format": "OME-TIFF",
        "uri": img_path.as_uri(),
        "metadata": {"axes": "TCZYX"},
    }

    # Use xarray.mean over Y dimension
    # This should result in dims (T, C, Z, X)
    outputs = adapter.execute(
        fn_id="base.xarray.DataArray.mean",
        inputs=[("image", input_artifact)],
        params={"dim": "Y"},
        work_dir=tmp_path,
    )

    assert len(outputs) == 1
    # The output should preserve native TCZX
    assert outputs[0]["type"] == "ObjectRef"
    assert outputs[0]["metadata"]["dims"] == ["T", "C", "Z", "X"]
    # Shape should be [1, 2, 3, 5] (Y is removed)
    assert outputs[0]["metadata"]["shape"] == [1, 2, 3, 5]


def test_xarray_save_output_expands_1d_to_2d(tmp_path):
    """Ensure xarray adapter can persist 1D results.

    Some reductions yield 1D arrays, but BioImageRef outputs must be written as
    files. The adapter expands singleton spatial dimensions so the output is at
    least 2D.
    """
    if "xarray" not in ADAPTER_REGISTRY:
        pytest.skip("Xarray adapter not registered")

    adapter = ADAPTER_REGISTRY["xarray"]

    import xarray as xr

    result_da = xr.DataArray(np.ones((10,), dtype=np.uint8), dims=("Y",))
    outputs = adapter._save_output(result_da, method_name="sum", work_dir=tmp_path)

    assert len(outputs) == 1
    assert outputs[0]["type"] == "BioImageRef"
    assert Path(outputs[0]["path"]).exists()
    assert outputs[0]["metadata"]["axes"] == "YX"
    assert outputs[0]["metadata"]["shape"] == [10, 1]


def test_load_da_case_insensitive_axes_no_squeeze_yx(tmp_path):
    """Test that _load_da handles case mismatch and only squeezes singletons.

    Regression test for ghost dimension squeeze bug where uppercase metadata.axes
    ("TCZYX") didn't match lowercase DataArray dims ("t","c","z","y","x"),
    causing all dims to be marked for squeezing.
    """
    if "xarray" not in ADAPTER_REGISTRY:
        pytest.skip("Xarray adapter not registered")

    adapter = ADAPTER_REGISTRY["xarray"]

    # Create a simple 2D image (YX only)
    img_path = tmp_path / "test_2d.ome.tiff"
    data = np.ones((10, 10), dtype=np.uint8)  # 2D YX
    OmeTiffWriter.save(data, str(img_path), dim_order="YX")

    # Simulate metadata claiming 5D axes (common in pipelines)
    input_artifact = {
        "type": "BioImageRef",
        "format": "OME-TIFF",
        "uri": img_path.as_uri(),
        "metadata": {"axes": "TCZYX"},  # Uppercase, doesn't match lowercase dims
    }

    # This should NOT crash - the fix normalizes case and checks singleton
    da = adapter._load_da(input_artifact)

    # Verify we got a valid DataArray with correct shape
    assert da is not None
    assert da.shape == (10, 10) or da.shape[-2:] == (10, 10)  # At least YX preserved
    # Should not have crashed trying to squeeze non-singleton Y/X
