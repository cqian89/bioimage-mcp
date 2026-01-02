from __future__ import annotations

from pathlib import Path

import dask.array as da
import pytest

FIXTURE_CZI = (
    Path(__file__).parent.parent.parent.parent
    / "datasets"
    / "sample_czi"
    / "Plate1-Blue-A-02-Scene-1-P2-E1-01.czi"
)


@pytest.mark.skipif(not FIXTURE_CZI.exists(), reason="CZI fixture not available")
def test_bioimage_returns_dask_array():
    """BioImage should provide access to dask-backed arrays for lazy loading."""
    from bioio import BioImage

    img = BioImage(FIXTURE_CZI)
    # We use .dask_data to ensure we get the dask-backed array regardless of reader defaults
    data = img.dask_data

    # Should be a dask array
    assert isinstance(data, da.Array)


@pytest.mark.skipif(not FIXTURE_CZI.exists(), reason="CZI fixture not available")
def test_bioimage_lazy_slicing():
    """Slicing should not load entire array into memory."""
    from bioio import BioImage

    img = BioImage(FIXTURE_CZI)

    # Get a small slice from dask_data
    # BioIO dask_data is also TCZYX
    small_slice = img.dask_data[0, 0, 0, :10, :10]

    # Should still be a dask array until compute()
    assert isinstance(small_slice, da.Array)

    # Compute the slice
    result = small_slice.compute()
    assert result.shape == (10, 10)


@pytest.mark.skipif(not FIXTURE_CZI.exists(), reason="CZI fixture not available")
def test_bioimage_compute_materializes():
    """compute() should return a numpy array."""
    import numpy as np
    from bioio import BioImage

    img = BioImage(FIXTURE_CZI)

    small_slice = img.dask_data[0, 0, 0, :10, :10]
    result = small_slice.compute()

    assert isinstance(result, np.ndarray)
