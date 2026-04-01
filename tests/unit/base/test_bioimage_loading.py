from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tests.fixtures.lfs_helpers import skip_if_lfs_pointer

# Path to the CZI fixture relative to this test file
FIXTURE_CZI = (
    Path(__file__).parent.parent.parent.parent
    / "datasets"
    / "sample_czi"
    / "Plate1-Blue-A-02-Scene-1-P2-E1-01.czi"
)


def _require_czi_fixture() -> Path:
    if not FIXTURE_CZI.exists():
        pytest.skip("CZI fixture not available")
    skip_if_lfs_pointer(FIXTURE_CZI)
    return FIXTURE_CZI


def test_bioimage_loads_czi_fixture():
    from bioio import BioImage

    img = BioImage(_require_czi_fixture())

    # Verify 5D TCZYX
    assert len(img.data.shape) == 5
    assert img.dims.order == "TCZYX"

    # Verify shape is accessible and reasonable
    shape = img.data.shape
    assert all(d >= 1 for d in shape)


def test_bioimage_shape_consistency():
    from bioio import BioImage

    img = BioImage(_require_czi_fixture())

    # Verify shape matches dims
    assert img.data.shape[0] == img.dims.T
    assert img.data.shape[1] == img.dims.C
    assert img.data.shape[2] == img.dims.Z
    assert img.data.shape[3] == img.dims.Y
    assert img.data.shape[4] == img.dims.X


def test_bioimage_data_access():
    from bioio import BioImage

    img = BioImage(_require_czi_fixture())

    # Access a small slice (first pixel of first T, C, Z)
    # TCZYX order
    # Use .compute() because bioio-czi often returns dask-backed arrays
    data_slice = img.data[0, 0, 0, 0, 0]

    if hasattr(data_slice, "compute"):
        val = data_slice.compute()
    else:
        val = data_slice

    assert isinstance(val, (np.ndarray, np.generic, int, float))
    # For a single pixel it's likely a numpy scalar or a small array
    if isinstance(val, np.ndarray):
        assert val.size == 1
