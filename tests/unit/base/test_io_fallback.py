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
    import tifffile
    from bioimage_mcp_base.utils import load_image_fallback

    # Create test data
    test_data = np.zeros((10, 10), dtype=np.uint8)
    test_path = tmp_path / "test.tif"
    tifffile.imwrite(str(test_path), test_data)

    result = load_image_fallback(test_path)

    assert isinstance(result, tuple)
    assert len(result) == 3
    data, warnings, reader_used = result
    assert isinstance(data, np.ndarray)
    assert isinstance(warnings, list)
    assert isinstance(reader_used, str)


def test_load_image_fallback_records_warnings(tmp_path: Path) -> None:
    """Test that fallback warnings are recorded."""
    import tifffile
    from bioimage_mcp_base.utils import load_image_fallback

    test_data = np.zeros((10, 10), dtype=np.uint8)
    test_path = tmp_path / "test.tif"
    tifffile.imwrite(str(test_path), test_data)

    # Force fallback to tifffile
    with patch("bioimage_mcp_base.utils.BioImage") as mock_bioimage:
        mock_bioimage.side_effect = Exception("BioImage error")

        data, warnings, reader = load_image_fallback(test_path)

        # Should have at least 1 warning entry
        assert len(warnings) >= 1
        assert reader == "tifffile"
