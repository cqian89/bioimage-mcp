import pytest
import numpy as np
from pathlib import Path
from bioimage_mcp.registry.dynamic.adapters.xarray import XarrayAdapterForRegistry
from bioimage_mcp.registry.dynamic.adapters.skimage import SkimageAdapter
from bioio.writers import OmeTiffWriter


@pytest.mark.integration
def test_squeeze_threshold_regionprops_pipeline(tmp_path):
    """T016: Squeeze → threshold → regionprops pipeline."""
    xarray_adapter = XarrayAdapterForRegistry()
    skimage_adapter = SkimageAdapter()

    # 1. Create 5D image with a single object
    img_path = tmp_path / "pipeline_input.ome.tiff"
    data = np.zeros((1, 1, 1, 128, 128), dtype=np.float32)
    data[0, 0, 0, 32:64, 32:64] = 1.0
    OmeTiffWriter.save(data, str(img_path), dim_order="TCZYX")

    artifact = {
        "uri": f"file://{img_path}",
        "format": "OME-TIFF",
        "type": "BioImageRef",
        "metadata": {"axes": "TCZYX", "shape": [1, 1, 1, 128, 128]},
    }

    # 2. Squeeze to 2D
    squeeze_results = xarray_adapter.execute(
        fn_id="xarray.squeeze", inputs=[artifact], params={}, work_dir=tmp_path / "step1"
    )
    squeezed_ref = squeeze_results[0]
    assert squeezed_ref["metadata"]["axes"] == "YX"
    assert squeezed_ref["metadata"]["shape"] == [128, 128]

    # 3. Apply a filter (surrogate for pipeline steps)
    gauss_results = skimage_adapter.execute(
        fn_id="skimage.filters.gaussian",
        inputs=[squeezed_ref],
        params={"sigma": 1.0},
        work_dir=tmp_path / "step2",
    )
    gauss_ref = gauss_results[0]
    assert gauss_ref["metadata"]["axes"] == "YX"

    # 4. measure.label (IMAGE_TO_LABELS)
    label_results = skimage_adapter.execute(
        fn_id="skimage.measure.label", inputs=[gauss_ref], params={}, work_dir=tmp_path / "step3"
    )
    label_ref = label_results[0]
    assert label_ref["metadata"]["axes"] == "YX"

    # 5. measure.regionprops_table (LABELS_TO_TABLE)
    table_results = skimage_adapter.execute(
        fn_id="skimage.measure.regionprops_table",
        inputs=[label_ref],
        params={"properties": ["label", "area", "centroid"]},
        work_dir=tmp_path / "step4",
    )
    table_ref = table_results[0]
    assert table_ref["type"] == "TableRef"
    assert table_ref["format"] == "csv"
    assert Path(table_ref["path"]).exists()
