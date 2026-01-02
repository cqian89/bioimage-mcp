from __future__ import annotations

import sys
from pathlib import Path

import bioio_ome_tiff
import numpy as np
import tifffile
from bioio import BioImage

# Inject BASE_TOOLS_ROOT sys.path injection consistent with other base tool tests
BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

from bioimage_mcp_base import io


def test_normalization_via_export_ome_tiff(tmp_path: Path):
    """
    Test that calling export_ome_tiff on a 2D TIFF results in a 5D OME-TIFF.

    This asserts that:
    1. The written output OME-TIFF can be loaded.
    2. It yields 5D data (TCZYX).
    3. The last two dimensions match the original YX dimensions.
    """
    # Create a simple 2D TIFF input
    tiff_path = tmp_path / "input_2d.tif"
    data_2d = np.random.randint(0, 255, (64, 64), dtype=np.uint8)
    tifffile.imwrite(str(tiff_path), data_2d)

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    # Call the production function
    result = io.export_ome_tiff(
        inputs={"image": {"uri": tiff_path.as_uri()}}, params={}, work_dir=work_dir
    )

    out_path = Path(result["outputs"]["output"]["path"])
    assert out_path.exists()

    # Verify the written output OME-TIFF can be loaded and yields 5D data (TCZYX)
    # Use bioio.BioImage and bioio_ome_tiff.Reader explicitly as requested
    img = BioImage(out_path, reader=bioio_ome_tiff.Reader)
    assert img.dims.order == "TCZYX"
    data_5d = img.data
    if hasattr(data_5d, "compute"):
        data_5d = data_5d.compute()

    assert data_5d.ndim == 5
    # TCZYX order: T=1, C=1, Z=1, Y=64, X=64
    assert data_5d.shape == (1, 1, 1, 64, 64)

    # Assert that the last two dims match original YX
    np.testing.assert_array_equal(data_5d[0, 0, 0, :, :], data_2d)


def test_normalization_preserves_higher_dims(tmp_path: Path):
    """
    Test that export_ome_tiff preserves existing dimensions and only pads to 5D.
    """
    # Create a 3D (Z, Y, X) TIFF input
    # Use 2 instead of 3 to avoid RGB ambiguity with some readers
    tiff_path = tmp_path / "input_3d.tif"
    data_3d = np.random.randint(0, 255, (2, 64, 64), dtype=np.uint8)
    tifffile.imwrite(str(tiff_path), data_3d)

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    result = io.export_ome_tiff(
        inputs={"image": {"uri": tiff_path.as_uri()}}, params={}, work_dir=work_dir
    )

    out_path = Path(result["outputs"]["output"]["path"])
    img = BioImage(out_path, reader=bioio_ome_tiff.Reader)
    assert img.dims.order == "TCZYX"
    data_5d = img.data
    if hasattr(data_5d, "compute"):
        data_5d = data_5d.compute()

    assert data_5d.shape == (1, 1, 2, 64, 64)
    np.testing.assert_array_equal(data_5d[0, 0, :, :, :], data_3d)
