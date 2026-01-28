"""Unit tests for load_image_fallback function."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np

BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))


def test_load_image_fallback_returns_tuple(tmp_path: Path) -> None:
    """Test that load_image_fallback returns expected tuple."""
    from bioimage_mcp_base.utils import load_image_fallback

    # Create test data using OmeTiffWriter
    test_data = np.zeros((10, 10), dtype=np.uint8)
    test_path = tmp_path / "test.tif"

    from bioio.writers import OmeTiffWriter

    OmeTiffWriter.save(test_data, str(test_path), dim_order="YX")

    result = load_image_fallback(test_path)

    assert isinstance(result, tuple)
    assert len(result) == 3
    data, warnings, reader_used = result
    assert isinstance(data, np.ndarray)
    assert isinstance(warnings, list)
    assert isinstance(reader_used, str)
    assert reader_used == "bioio"  # Should always use bioio now


def test_load_image_fallback_tries_fallbacks_on_bioimage_error(tmp_path: Path) -> None:
    """Test that load_image_fallback uses fallback readers when BioImage fails."""
    from bioimage_mcp_base.utils import load_image_fallback

    test_data = np.zeros((10, 10), dtype=np.uint8)
    test_path = tmp_path / "test.tif"

    # Use OmeTiffWriter to create test file
    from bioio.writers import OmeTiffWriter

    OmeTiffWriter.save(test_data, str(test_path), dim_order="YX")

    # Force BioImage to fail
    with patch("bioimage_mcp_base.utils.BioImage") as mock_bioimage:
        mock_bioimage.side_effect = Exception("BioImage error")

        data, warnings, reader_used = load_image_fallback(test_path)

        assert data is not None
        assert any(w.get("code") == "BIOIMAGE_FALLBACK" for w in warnings)
        assert reader_used in {
            "bioio+ome-tiff-reader",
            "bioio+tifffile-reader",
            "bioio+bioformats-reader",
            "tifffile",
        }
