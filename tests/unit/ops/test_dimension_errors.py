import numpy as np
import pytest
from bioio.writers import OmeTiffWriter

from bioimage_mcp.registry.dynamic.adapters.xarray import XarrayAdapterForRegistry


def test_squeeze_non_singleton_dimension_error(tmp_path):
    """T016a: Squeeze on non-singleton dimension produces clear error message."""
    adapter = XarrayAdapterForRegistry()

    # Create a 3D image [1, 1, 10, 100, 100] (Z=10, not 1)
    img_path = tmp_path / "input_3d.ome.tiff"
    data = np.zeros((1, 1, 10, 100, 100), dtype=np.uint8)
    OmeTiffWriter.save(data, str(img_path), dim_order="TCZYX")

    artifact = {
        "uri": f"file://{img_path}",
        "format": "OME-TIFF",
        "type": "BioImageRef",
        "metadata": {"axes": "TCZYX", "shape": [1, 1, 10, 100, 100]},
    }

    # When trying to squeeze Z (which is 10, not 1)
    # Then clear error message about dimension requirements
    # Note: xarray.DataArray.squeeze(dim='Z') raises ValueError
    with pytest.raises(ValueError, match="cannot select a dimension to squeeze out"):
        adapter.execute(
            fn_id="base.xarray.DataArray.squeeze",
            inputs=[artifact],
            params={"dim": "Z"},
            work_dir=tmp_path,
        )
