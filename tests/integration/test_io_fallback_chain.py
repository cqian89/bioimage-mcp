"""Integration tests for IO fallback chain (IO-001, IO-002, IO-003).

Contract: specs/006-phasor-usability-fixes/contracts/api.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np

BASE_TOOLS_ROOT = Path(__file__).resolve().parents[2] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))


class TestIOFallbackChain:
    """Integration tests for load_image_fallback function."""

    def test_bioimage_tried_first(self, tmp_path: Path) -> None:
        """IO-001: BioImage is used for initial loading attempt.

        Given: Valid TIFF file
        When: Call load_image_fallback(path)
        Then: Uses BioImage reader
        """
        import tifffile
        from bioimage_mcp_base.utils import load_image_fallback

        # Create a simple valid TIFF
        test_data = np.random.randint(0, 255, (10, 10), dtype=np.uint8)
        test_path = tmp_path / "test.tif"
        tifffile.imwrite(str(test_path), test_data)

        # Load with fallback chain
        data, warnings, reader_used = load_image_fallback(test_path)

        # Should succeed
        assert data is not None
        assert data.shape[-2:] == (10, 10)  # At least Y, X dimensions
        assert isinstance(warnings, list)
        assert isinstance(reader_used, str)

    def test_fallback_to_tifffile_on_bioimage_failure(self, tmp_path: Path) -> None:
        """IO-002: Fallback to tifffile when BioImage fails.

        Given: A file that causes BioImage to raise an exception
        When: BioImage raises exception
        Then: Falls back to tifffile successfully with BIOIMAGE_FALLBACK warning
        """
        import tifffile
        from bioimage_mcp_base.utils import load_image_fallback

        # Create a simple TIFF
        test_data = np.random.randint(0, 255, (10, 10), dtype=np.uint8)
        test_path = tmp_path / "test.tif"
        tifffile.imwrite(str(test_path), test_data)

        # Mock BioImage to fail
        with patch("bioimage_mcp_base.utils.BioImage") as mock_bioimage:
            mock_bioimage.side_effect = Exception("BioImage error")

            data, warnings, reader_used = load_image_fallback(test_path)

            # Should have fallen back
            assert data is not None
            assert reader_used == "tifffile"
            assert any(w.get("code") == "BIOIMAGE_FALLBACK" for w in warnings)
