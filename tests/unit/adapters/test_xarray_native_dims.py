import numpy as np
from bioio.writers import OmeTiffWriter

from bioimage_mcp.registry.dynamic.adapters.xarray import XarrayAdapterForRegistry


def test_xarray_adapter_preserves_native_dimensions(tmp_path):
    """T013: XarrayAdapter preserves native dimensions (no 5D expansion)."""
    adapter = XarrayAdapterForRegistry()

    # Create a dummy 5D image first
    img_path = tmp_path / "input.ome.tiff"
    data = np.zeros((1, 1, 1, 100, 100), dtype=np.uint8)
    OmeTiffWriter.save(data, str(img_path), dim_order="TCZYX")

    artifact = {
        "uri": f"file://{img_path}",
        "format": "OME-TIFF",
        "type": "BioImageRef",
        "metadata": {"axes": "TCZYX", "shape": [1, 1, 1, 100, 100]},
    }

    # When XarrayAdapter processes it with squeeze
    results = adapter.execute(
        fn_id="xarray.squeeze", inputs=[artifact], params={}, work_dir=tmp_path
    )

    # Then output should be 2D, not expanded to 5D
    # CURRENT BEHAVIOR: it will be 5D, so this assertion will FAIL
    out_artifact = results[0]
    assert out_artifact["metadata"]["axes"] == "YX"
    assert out_artifact["metadata"]["shape"] == [100, 100]


def test_squeeze_produces_correct_ndim_metadata(tmp_path):
    """T014: Squeeze operation produces correct ndim/dims metadata."""
    adapter = XarrayAdapterForRegistry()

    img_path = tmp_path / "input_5d.ome.tiff"
    data = np.zeros((1, 1, 1, 64, 64), dtype=np.uint8)
    OmeTiffWriter.save(data, str(img_path), dim_order="TCZYX")

    artifact = {
        "uri": f"file://{img_path}",
        "format": "OME-TIFF",
        "type": "BioImageRef",
        "metadata": {"axes": "TCZYX", "shape": [1, 1, 1, 64, 64]},
    }

    results = adapter.execute(
        fn_id="xarray.squeeze", inputs=[artifact], params={}, work_dir=tmp_path
    )

    out_artifact = results[0]
    # CURRENT BEHAVIOR: axes="TCZYX", shape=[1,1,1,64,64]
    # EXPECTED BEHAVIOR after Phase 3: axes="YX", shape=[64,64]
    assert out_artifact["metadata"]["axes"] == "YX"
    assert out_artifact["metadata"]["shape"] == [64, 64]
    # Phase 3 will add 'ndim' and 'dims' to metadata
    assert out_artifact["metadata"].get("ndim") == 2
    assert out_artifact["metadata"].get("dims") == ["Y", "X"]
