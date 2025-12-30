"""Unit tests for metadata extraction (T014).

Tests the extraction of standardized metadata (pixel sizes, channel names)
from bioimages using bioio.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_CZI = (
    Path(__file__).parent.parent.parent.parent
    / "datasets"
    / "sample_czi"
    / "Plate1-Blue-A-02-Scene-1-P2-E1-01.czi"
)


@pytest.mark.skipif(not FIXTURE_CZI.exists(), reason="CZI fixture not available")
def test_extract_physical_pixel_sizes():
    from bioio import BioImage

    img = BioImage(FIXTURE_CZI)
    pps = img.physical_pixel_sizes

    # physical_pixel_sizes is a namedtuple with Z, Y, X
    assert hasattr(pps, "Z")
    assert hasattr(pps, "Y")
    assert hasattr(pps, "X")
    # At least one dimension should have a real value
    assert pps.X is not None or pps.Y is not None or pps.Z is not None
    assert pps.X > 0 or pps.Y > 0 or pps.Z > 0


@pytest.mark.skipif(not FIXTURE_CZI.exists(), reason="CZI fixture not available")
def test_extract_channel_names():
    from bioio import BioImage

    img = BioImage(FIXTURE_CZI)
    channels = img.channel_names

    # Should return a list (may be empty for some images)
    assert isinstance(channels, (list, tuple))
    # Plate1-Blue-A-02-Scene-1-P2-E1-01.czi typically has channels
    if len(channels) > 0:
        assert all(isinstance(c, str) for c in channels)


@pytest.mark.skipif(not FIXTURE_CZI.exists(), reason="CZI fixture not available")
def test_extract_image_metadata_helper():
    """Test the internal metadata extraction helper used by the server."""
    from bioimage_mcp.artifacts.metadata import extract_image_metadata

    meta = extract_image_metadata(FIXTURE_CZI)

    assert "physical_pixel_sizes" in meta
    assert "channel_names" in meta
    assert "axes" in meta
    assert "shape" in meta
    assert "dtype" in meta

    # Verify values for the CZI fixture
    assert meta["axes"] == "TCZYX"
    assert len(meta["shape"]) == 5
    assert len(meta["channel_names"]) == 3

    pps = meta["physical_pixel_sizes"]
    assert isinstance(pps, dict)
    assert pps["X"] > 0
    assert pps["Y"] > 0
    assert pps["Z"] > 0
