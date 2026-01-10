from __future__ import annotations

import numpy as np
import pytest
from pathlib import Path
from bioio.writers import OmeTiffWriter
from bioio import BioImage


@pytest.fixture
def create_test_image(tmp_path):
    def _create(shape, filename, content=None):
        path = tmp_path / filename
        if content is None:
            data = np.random.rand(*shape).astype(np.float32)
        else:
            data = content.astype(np.float32)

        # Expand to 5D for OmeTiffWriter
        data_5d = data
        while data_5d.ndim < 5:
            data_5d = np.expand_dims(data_5d, axis=0)

        OmeTiffWriter.save(data_5d, path, dim_order="TCZYX")
        return {
            "type": "BioImageRef",
            "uri": f"file://{path.absolute()}",
            "format": "OME-TIFF",
            "metadata": {"shape": list(data.shape), "dtype": str(data.dtype)},
        }

    return _create


@pytest.mark.real_execution
def test_tile_stitching_workflow(mcp_test_client, create_test_image):
    """Test stitching 4 tiles along X dimension using base.xarray.concat."""
    mcp_test_client.activate_functions(["base.xarray.concat"])

    # Create 4 tiles of 64x64
    tile_data = [np.full((1, 64, 64), i, dtype=np.float32) for i in range(4)]
    tiles = [
        create_test_image((1, 64, 64), f"tile_{i}.ome.tif", content=tile_data[i]) for i in range(4)
    ]

    # Concatenate along X (axis 2 of ZYX)
    # Note: In our system, native 2D is often YX. ZYX is (1, 64, 64).
    # Concat along "X"
    response = mcp_test_client.call_tool(
        fn_id="base.xarray.concat", inputs={"images": tiles}, params={"dim": "X"}
    )

    assert "outputs" in response
    output = response["outputs"]["output"]
    assert output["type"] == "BioImageRef"

    # Verify metadata
    metadata = output.get("metadata", {})
    # OME-TIFF expansion might make it 5D [1, 1, 1, 64, 256]
    shape = metadata.get("shape")
    assert shape[-1] == 256
    assert shape[-2] == 64

    # Verify pixel data
    out_uri = output["uri"]
    out_path = Path(out_uri.replace("file://", ""))
    img = BioImage(out_path)
    data = img.reader.xarray_data
    # data is likely 5D TCZYX
    assert data.shape[-1] == 256
    assert data.shape[-2] == 64
    for i in range(4):
        # Check a pixel in each tile's range
        # isel works on named dimensions regardless of where they are
        assert np.allclose(data.isel(X=i * 64 + 32, Y=32, Z=0).values, i)


@pytest.mark.real_execution
def test_background_subtraction_workflow(mcp_test_client, create_test_image):
    """Test subtracting background from signal image using base.xarray.ufuncs.subtract."""
    mcp_test_client.activate_functions(["base.xarray.ufuncs.subtract"])

    signal_data = np.full((100, 100), 10.0, dtype=np.float32)
    bg_data = np.full((100, 100), 2.0, dtype=np.float32)

    signal = create_test_image((100, 100), "signal.ome.tif", content=signal_data)
    bg = create_test_image((100, 100), "bg.ome.tif", content=bg_data)

    response = mcp_test_client.call_tool(
        fn_id="base.xarray.ufuncs.subtract", inputs={"image": signal, "background": bg}, params={}
    )

    assert "outputs" in response
    output = response["outputs"]["output"]

    # Verify result
    out_uri = output["uri"]
    out_path = Path(out_uri.replace("file://", ""))
    img = BioImage(out_path)
    data = img.reader.xarray_data
    assert np.allclose(data, 8.0)


@pytest.mark.real_execution
def test_max_projection_clip_workflow(mcp_test_client, create_test_image):
    """Test MIP followed by clipping using DataArray chaining (ObjectRef)."""
    mcp_test_client.activate_functions(
        [
            "base.xarray.DataArray",
            "base.xarray.DataArray.max",
            "base.xarray.DataArray.clip",
            "base.xarray.DataArray.to_bioimage",
        ]
    )

    # Create a 3D image (Z, Y, X)
    # Z=0: all 0.1, Z=1: all 0.9, Z=2: all 0.5
    z_stack = np.zeros((3, 64, 64), dtype=np.float32)
    z_stack[0, :, :] = 0.1
    z_stack[1, :, :] = 0.9
    z_stack[2, :, :] = 0.5

    img_ref = create_test_image((3, 64, 64), "stack.ome.tif", content=z_stack)

    # 1. Wrap in DataArray ObjectRef
    res_da = mcp_test_client.call_tool(
        fn_id="base.xarray.DataArray", inputs={"image": img_ref}, params={}
    )
    da_ref = res_da["outputs"]["da"]
    assert da_ref["type"] == "ObjectRef"

    # 2. Max projection along Z
    res_mip = mcp_test_client.call_tool(
        fn_id="base.xarray.DataArray.max", inputs={"image": da_ref}, params={"dim": "Z"}
    )
    mip_ref = res_mip["outputs"]["output"]
    assert mip_ref["type"] == "ObjectRef"

    # 3. Clip values to [0.2, 0.8]
    # The max should be 0.9 everywhere, clipped to 0.8
    res_clip = mcp_test_client.call_tool(
        fn_id="base.xarray.DataArray.clip",
        inputs={"image": mip_ref},
        params={"min": 0.2, "max": 0.8},
    )
    clipped_ref = res_clip["outputs"]["output"]
    assert clipped_ref["type"] == "ObjectRef"

    # 4. Convert back to BioImageRef
    res_final = mcp_test_client.call_tool(
        fn_id="base.xarray.DataArray.to_bioimage", inputs={"image": clipped_ref}, params={}
    )
    final_output = res_final["outputs"]["output"]
    assert final_output["type"] == "BioImageRef"

    # Verify results
    out_uri = final_output["uri"]
    out_path = Path(out_uri.replace("file://", ""))
    img = BioImage(out_path)
    data = img.reader.xarray_data
    # data might be 5D, but we can check values
    assert np.allclose(data, 0.8)


@pytest.mark.real_execution
def test_quantile_threshold_workflow(mcp_test_client, create_test_image):
    """Test computing quantile and using it for thresholding."""
    mcp_test_client.activate_functions(
        [
            "base.xarray.DataArray",
            "base.xarray.DataArray.quantile",
            "base.xarray.ufuncs.greater",
            "base.xarray.DataArray.to_bioimage",
        ]
    )

    # Create image with values 0 to 100
    data = np.linspace(0, 100, 10000).reshape(100, 100).astype(np.float32)
    img_ref = create_test_image((100, 100), "gradient.ome.tif", content=data)

    # 1. Load as DataArray
    res_da = mcp_test_client.call_tool(
        fn_id="base.xarray.DataArray", inputs={"image": img_ref}, params={}
    )
    da_ref = res_da["outputs"]["da"]

    # 2. Compute 0.9 quantile (should be 90.0)
    res_q = mcp_test_client.call_tool(
        fn_id="base.xarray.DataArray.quantile", inputs={"image": da_ref}, params={"q": 0.9}
    )
    q_ref = res_q["outputs"]["output"]
    assert q_ref["type"] == "ObjectRef"

    # 3. Greater than threshold
    res_mask = mcp_test_client.call_tool(
        fn_id="base.xarray.ufuncs.greater", inputs={"x1": da_ref, "x2": q_ref}, params={}
    )
    mask_ref = res_mask["outputs"]["output"]

    # 4. Convert to BioImageRef
    res_final = mcp_test_client.call_tool(
        fn_id="base.xarray.DataArray.to_bioimage", inputs={"image": mask_ref}, params={}
    )
    final_output = res_final["outputs"]["output"]

    # Verify result: about 10% of pixels should be True
    out_uri = final_output["uri"]
    out_path = Path(out_uri.replace("file://", ""))
    img = BioImage(out_path)
    mask_data = img.reader.xarray_data
    assert np.mean(mask_data) == pytest.approx(0.1, abs=0.01)
