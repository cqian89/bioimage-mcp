"""Unit tests for metadata extraction (T014).

Tests the extraction of standardized metadata (pixel sizes, channel names)
from bioimages using bioio.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
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
    assert meta["axes"] == "CZYX"
    assert len(meta["shape"]) == 4
    assert len(meta["channel_names"]) == 3

    pps = meta["physical_pixel_sizes"]
    assert isinstance(pps, dict)
    assert pps["X"] > 0
    assert pps["Y"] > 0
    assert pps["Z"] > 0


def test_extract_metadata_graceful_fallback_nonexistent(tmp_path):
    """Test graceful fallback when file doesn't exist."""
    from bioimage_mcp.artifacts.metadata import extract_image_metadata

    nonexistent = tmp_path / "does_not_exist.tif"
    meta = extract_image_metadata(nonexistent)

    # Should return None for nonexistent files
    assert meta is None


def test_extract_metadata_graceful_fallback_minimal(tmp_path, monkeypatch):
    """Test graceful fallback when bioio is not available."""
    from bioimage_mcp.artifacts.metadata import extract_image_metadata

    # Create a dummy file
    dummy = tmp_path / "dummy.tif"
    dummy.write_bytes(b"FAKE TIFF DATA")

    # Mock ImportError for bioio
    import builtins
    import sys

    # Create a fake module that raises ImportError when bioio is imported
    original_import = builtins.__import__

    def fail_import(name, *args, **kwargs):
        if name == "bioio":
            raise ImportError("bioio not available")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_import)

    # Clear any cached bioio import
    if "bioio" in sys.modules:
        del sys.modules["bioio"]

    meta = extract_image_metadata(dummy)

    # Should return minimal metadata with file size
    assert meta is not None
    assert "file_size_bytes" in meta
    assert meta["file_size_bytes"] == len(b"FAKE TIFF DATA")

    # TIFF files fall back to tifffile when bioio is unavailable,
    # which returns minimal fields (even if empty)
    assert meta.get("axes") == ""
    assert meta.get("shape") == []


def test_extract_metadata_tifffile_preserves_ome_singletons(tmp_path):
    """OME-TIFFs with singleton axes should report full TCZYX sizes.

    tifffile collapses singleton dimensions (e.g., reports YX for a TCZYX image with
    singleton T/C/Z). For artifact consistency we preserve the full 5D shape.
    """
    from bioio.writers import OmeTiffWriter

    from bioimage_mcp.artifacts.metadata import extract_image_metadata

    path = tmp_path / "singletons.tif"
    data = np.ones((1, 1, 1, 2, 2), dtype=np.uint16)
    OmeTiffWriter.save(data, str(path), dim_order="TCZYX")

    meta = extract_image_metadata(path)
    assert meta is not None
    # New policy: Preserve native dimensions as reported by tifffile (YX for singletons)
    assert meta["axes"] == "YX"
    assert meta["ndim"] == 2
    assert meta["shape"] == [2, 2]
