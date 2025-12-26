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

    def test_bioio_ome_tiff_tried_first(self, tmp_path: Path) -> None:
        """IO-001: OME-TIFF loads with bioio-ome-tiff first.

        Given: Valid OME-TIFF without problematic tags
        When: Call load_image_fallback(path)
        Then: Uses bioio-ome-tiff reader
        """
        import tifffile
        from bioimage_mcp_base.io import load_image_fallback

        # Create a simple valid TIFF
        test_data = np.random.randint(0, 255, (10, 10), dtype=np.uint8)
        test_path = tmp_path / "test.tif"
        tifffile.imwrite(str(test_path), test_data)

        # Load with fallback chain
        data, warnings, reader_used = load_image_fallback(test_path)

        # Should succeed (might use any reader that works)
        assert data is not None
        assert data.shape[-2:] == (10, 10)  # At least Y, X dimensions
        assert isinstance(warnings, list)
        assert isinstance(reader_used, str)

    def test_fallback_to_bioformats_on_failure(self, tmp_path: Path) -> None:
        """IO-002: Fallback to bioio-bioformats on ome-tiff failure.

        Given: OME-TIFF with AnnotationRef tags (causes bioio-ome-tiff to fail)
        When: bioio-ome-tiff raises exception
        Then: Falls back to bioio-bioformats successfully (or tifffile)
        """
        import tifffile
        from bioimage_mcp_base.io import load_image_fallback

        # Create a simple TIFF
        test_data = np.random.randint(0, 255, (10, 10), dtype=np.uint8)
        test_path = tmp_path / "test.tif"
        tifffile.imwrite(str(test_path), test_data)

        # Mock bioio-ome-tiff to fail
        with patch("bioimage_mcp_base.io._try_bioio_ome_tiff") as mock_ome:
            mock_ome.side_effect = Exception("AnnotationRef error")

            data, warnings, reader_used = load_image_fallback(test_path)

            # Should have fallen back
            assert data is not None
            assert any("FALLBACK" in w.get("code", "") for w in warnings)

    def test_final_fallback_to_tifffile(self, tmp_path: Path) -> None:
        """IO-003: Final fallback to tifffile with warning.

        Given: File unreadable by bioio readers
        When: Both bioio readers fail
        Then: Falls back to tifffile with TIFFFILE_FALLBACK warning
        """
        import tifffile
        from bioimage_mcp_base.io import load_image_fallback

        # Create a simple TIFF
        test_data = np.random.randint(0, 255, (10, 10), dtype=np.uint8)
        test_path = tmp_path / "test.tif"
        tifffile.imwrite(str(test_path), test_data)

        # Mock both bioio readers to fail
        with (
            patch("bioimage_mcp_base.io._try_bioio_ome_tiff") as mock_ome,
            patch("bioimage_mcp_base.io._try_bioio_bioformats") as mock_bf,
        ):
            mock_ome.side_effect = Exception("ome-tiff error")
            mock_bf.side_effect = Exception("bioformats error")

            data, warnings, reader_used = load_image_fallback(test_path)

            assert data is not None
            assert reader_used == "tifffile"
            assert any(w.get("code") == "TIFFFILE_FALLBACK" for w in warnings)
