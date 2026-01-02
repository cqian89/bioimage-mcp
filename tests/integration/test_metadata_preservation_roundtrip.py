from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

FIXTURE_CZI = (
    Path(__file__).parent.parent.parent
    / "datasets"
    / "sample_czi"
    / "Plate1-Blue-A-02-Scene-1-P2-E1-01.czi"
)


@pytest.mark.skipif(not FIXTURE_CZI.exists(), reason="CZI fixture not available")
@pytest.mark.integration
def test_metadata_preserved_through_transform():
    """T016/SC-004: metadata preserved through a transform + write step."""
    from bioio import BioImage
    from bioio.writers import OmeTiffWriter

    # Load original
    original = BioImage(FIXTURE_CZI)
    orig_pps = original.physical_pixel_sizes
    orig_channels = original.channel_names

    # Simple transform: extract and normalize
    # Using asarray to handle both dask and numpy arrays
    data = np.asarray(original.data)

    # Export with metadata
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "transformed.ome.tiff"
        OmeTiffWriter.save(
            data,
            output_path,
            dim_order="TCZYX",
            physical_pixel_sizes=orig_pps,
            channel_names=orig_channels,
        )

        # Re-load and verify metadata preserved
        result = BioImage(output_path)
        result_pps = result.physical_pixel_sizes
        result_channels = result.channel_names

        # Verify pixel sizes preserved
        assert result_pps.X == pytest.approx(orig_pps.X)
        assert result_pps.Y == pytest.approx(orig_pps.Y)
        # Note: Z may or may not be preserved depending on format
        if orig_pps.Z is not None:
            assert result_pps.Z == pytest.approx(orig_pps.Z)

        # Verify channel names preserved
        assert list(result_channels) == list(orig_channels)
