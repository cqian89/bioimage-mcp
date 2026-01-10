from pathlib import Path

import numpy as np
import pytest
from bioio.writers import OmeTiffWriter

from bioimage_mcp.registry.dynamic.adapters import ADAPTER_REGISTRY


def test_xarray_dataarray_constructor(tmp_path):
    """Test base.xarray.DataArray constructor returns ObjectRef."""
    if "xarray" not in ADAPTER_REGISTRY:
        pytest.skip("Xarray adapter not registered")

    adapter = ADAPTER_REGISTRY["xarray"]

    img_path = tmp_path / "test.ome.tiff"
    # Create a simple 2D image for easy testing
    data = np.random.randint(0, 255, (1, 1, 1, 10, 10), dtype=np.uint8)
    OmeTiffWriter.save(data, str(img_path), dim_order="TCZYX")

    input_artifact = {
        "type": "BioImageRef",
        "format": "OME-TIFF",
        "uri": img_path.as_uri(),
        "path": str(img_path),
        "metadata": {"axes": "TCZYX"},
    }

    outputs = adapter.execute(
        fn_id="base.xarray.DataArray",
        inputs=[("image", input_artifact)],
        params={},
        work_dir=tmp_path,
    )

    assert len(outputs) == 1
    artifact = outputs[0]
    assert artifact["type"] == "ObjectRef"
    assert artifact["python_class"] == "xarray.DataArray"
    assert artifact["uri"].startswith("obj://")
    assert artifact["storage_type"] == "memory"
    # Verify it has 3 parts after obj://
    parts = artifact["uri"][6:].split("/")
    assert len(parts) == 3


def test_xarray_dataarray_to_bioimage(tmp_path):
    """Test base.xarray.DataArray.to_bioimage converts ObjectRef to BioImageRef."""
    if "xarray" not in ADAPTER_REGISTRY:
        pytest.skip("Xarray adapter not registered")

    adapter = ADAPTER_REGISTRY["xarray"]

    # 1. Create a BioImageRef first
    img_path = tmp_path / "test_orig.ome.tiff"
    data = np.random.randint(0, 255, (1, 1, 1, 10, 10), dtype=np.uint8)
    OmeTiffWriter.save(data, str(img_path), dim_order="TCZYX")

    input_art = {
        "type": "BioImageRef",
        "format": "OME-TIFF",
        "uri": img_path.as_uri(),
        "path": str(img_path),
        "metadata": {"axes": "TCZYX"},
    }

    # 2. BioImageRef -> ObjectRef
    cons_outputs = adapter.execute(
        fn_id="base.xarray.DataArray",
        inputs=[("image", input_art)],
        params={},
        work_dir=tmp_path,
    )
    obj_ref = cons_outputs[0]

    # 3. ObjectRef -> BioImageRef
    outputs = adapter.execute(
        fn_id="base.xarray.DataArray.to_bioimage",
        inputs=[("obj", obj_ref)],
        params={},
        work_dir=tmp_path,
    )

    assert len(outputs) == 1
    assert outputs[0]["type"] == "BioImageRef"
    assert Path(outputs[0]["path"]).exists()

    # 4. Verify data preservation
    from bioio import BioImage

    img = BioImage(outputs[0]["path"])
    # OmeTiffWriter/BioImage always 5D TCZYX by default in .data
    np.testing.assert_array_equal(img.data, data)


def test_xarray_method_on_objectref(tmp_path):
    """Test that xarray methods can be called using ObjectRef as input."""
    if "xarray" not in ADAPTER_REGISTRY:
        pytest.skip("Xarray adapter not registered")

    adapter = ADAPTER_REGISTRY["xarray"]

    # 1. BioImageRef -> ObjectRef
    img_path = tmp_path / "test_method.ome.tiff"
    data = np.zeros((1, 1, 1, 10, 10), dtype=np.uint8)
    data[0, 0, 0, 0, 0] = 100
    OmeTiffWriter.save(data, str(img_path), dim_order="TCZYX")

    input_art = {
        "type": "BioImageRef",
        "format": "OME-TIFF",
        "uri": img_path.as_uri(),
        "path": str(img_path),
        "metadata": {"axes": "TCZYX"},
    }

    cons_outputs = adapter.execute(
        fn_id="base.xarray.DataArray",
        inputs=[("image", input_art)],
        params={},
        work_dir=tmp_path,
    )
    obj_ref = cons_outputs[0]

    # 2. Call xarray.isel on ObjectRef
    # The adapter should return another ObjectRef because isel is marked as returns: ObjectRef
    outputs = adapter.execute(
        fn_id="base.xarray.DataArray.isel",
        inputs=[("image", obj_ref)],
        params={"X": slice(0, 5)},
        work_dir=tmp_path,
    )

    assert len(outputs) == 1
    assert outputs[0]["type"] == "ObjectRef"
    assert outputs[0]["metadata"]["shape"][-1] == 5

    # 3. Verify we can convert this new ObjectRef back to BioImageRef
    final_outputs = adapter.execute(
        fn_id="base.xarray.DataArray.to_bioimage",
        inputs=[("obj", outputs[0])],
        params={},
        work_dir=tmp_path,
    )
    assert final_outputs[0]["type"] == "BioImageRef"
    assert Path(final_outputs[0]["path"]).exists()
