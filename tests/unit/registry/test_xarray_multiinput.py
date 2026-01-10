from pathlib import Path

import numpy as np
import pytest
from bioio.writers import OmeTiffWriter

from bioimage_mcp.registry.dynamic.adapters import ADAPTER_REGISTRY


@pytest.fixture
def adapter():
    if "xarray" not in ADAPTER_REGISTRY:
        pytest.skip("Xarray adapter not registered")
    return ADAPTER_REGISTRY["xarray"]


def create_test_image(path, shape=(1, 1, 1, 10, 10), value=0):
    data = np.full(shape, value, dtype=np.uint8)
    OmeTiffWriter.save(data, str(path), dim_order="TCZYX")
    return {
        "type": "BioImageRef",
        "format": "OME-TIFF",
        "uri": Path(path).as_uri(),
        "path": str(Path(path).absolute()),
        "metadata": {"axes": "TCZYX", "shape": list(shape)},
    }


def test_xarray_concat(adapter, tmp_path):
    img1_path = tmp_path / "img1.ome.tiff"
    img2_path = tmp_path / "img2.ome.tiff"

    img1 = create_test_image(img1_path, value=1)
    img2 = create_test_image(img2_path, value=2)

    # Concatenate along T dimension
    outputs = adapter.execute(
        fn_id="base.xarray.concat",
        inputs=[("images", [img1, img2])],
        params={"dim": "T"},
        work_dir=tmp_path,
    )

    assert len(outputs) == 1
    assert outputs[0]["type"] == "BioImageRef"
    assert outputs[0]["metadata"]["shape"][0] == 2  # 1+1=2 along T


def test_xarray_merge(adapter, tmp_path):
    img1_path = tmp_path / "img1.ome.tiff"
    img2_path = tmp_path / "img2.ome.tiff"

    img1 = create_test_image(img1_path, value=1)
    img2 = create_test_image(img2_path, value=2)

    outputs = adapter.execute(
        fn_id="base.xarray.merge",
        inputs=[("images", [img1, img2])],
        params={},
        work_dir=tmp_path,
    )

    assert len(outputs) == 1
    assert outputs[0]["type"] == "BioImageRef"
    # Merging two 5D images with to_array(dim="variable") will add a 'variable' dim
    # The result shape should have one more dimension at the beginning (variable=2)
    assert outputs[0]["metadata"]["shape"][0] == 2
    assert "variable" in outputs[0]["metadata"]["axes"]


def test_xarray_ufunc_subtract(adapter, tmp_path):
    img1_path = tmp_path / "img1.ome.tiff"
    img2_path = tmp_path / "img2.ome.tiff"

    img1 = create_test_image(img1_path, value=10)
    img2 = create_test_image(img2_path, value=3)

    outputs = adapter.execute(
        fn_id="base.xarray.ufuncs.subtract",
        inputs=[("a", img1), ("b", img2)],
        params={},
        work_dir=tmp_path,
    )

    assert len(outputs) == 1
    assert outputs[0]["type"] == "BioImageRef"


def test_xarray_ufunc_add(adapter, tmp_path):
    img1_path = tmp_path / "img1.ome.tiff"
    img2_path = tmp_path / "img2.ome.tiff"

    img1 = create_test_image(img1_path, value=10)
    img2 = create_test_image(img2_path, value=3)

    outputs = adapter.execute(
        fn_id="base.xarray.ufuncs.add",
        inputs=[("a", img1), ("b", img2)],
        params={},
        work_dir=tmp_path,
    )

    assert len(outputs) == 1
    assert outputs[0]["type"] == "BioImageRef"


def test_xarray_ufunc_sqrt(adapter, tmp_path):
    img1_path = tmp_path / "img1.ome.tiff"
    img1 = create_test_image(img1_path, value=16)

    outputs = adapter.execute(
        fn_id="base.xarray.ufuncs.sqrt", inputs=[("x", img1)], params={}, work_dir=tmp_path
    )

    assert len(outputs) == 1
    assert outputs[0]["type"] == "BioImageRef"
