"""Unit test for OME-Zarr format detection in base I/O.

Per spec 026-zarr-artifact, the base I/O module must detect OME-Zarr directories
and report the correct format and MIME type.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest


# Add tools/base to path for testing
sys.path.insert(0, str(Path(__file__).parents[3] / "tools" / "base"))


class TestOmeZarrFormatDetection:
    """Tests for OME-Zarr format detection in base I/O."""

    def test_detect_format_ome_zarr_directory(self, tmp_path: Path) -> None:
        """_detect_format must return 'OME-Zarr' for .ome.zarr directories."""
        from bioimage_mcp_base.ops.io import _detect_format

        zarr_dir = tmp_path / "test_image.ome.zarr"
        zarr_dir.mkdir()

        result = _detect_format(zarr_dir)
        assert result == "OME-Zarr", f"Expected 'OME-Zarr', got '{result}'"

    def test_detect_format_zarr_directory(self, tmp_path: Path) -> None:
        """_detect_format must return 'OME-Zarr' for .zarr directories."""
        from bioimage_mcp_base.ops.io import _detect_format

        zarr_dir = tmp_path / "test_image.zarr"
        zarr_dir.mkdir()

        result = _detect_format(zarr_dir)
        assert result == "OME-Zarr", f"Expected 'OME-Zarr', got '{result}'"

    def test_get_mime_type_ome_zarr(self, tmp_path: Path) -> None:
        """_get_mime_type must return 'application/zarr+ome' for OME-Zarr."""
        from bioimage_mcp_base.ops.io import _get_mime_type

        zarr_dir = tmp_path / "test_image.ome.zarr"
        zarr_dir.mkdir()

        result = _get_mime_type(zarr_dir)
        assert result == "application/zarr+ome", f"Expected 'application/zarr+ome', got '{result}'"

    def test_get_mime_type_zarr(self, tmp_path: Path) -> None:
        """_get_mime_type must return 'application/zarr+ome' for .zarr directories."""
        from bioimage_mcp_base.ops.io import _get_mime_type

        zarr_dir = tmp_path / "test_image.zarr"
        zarr_dir.mkdir()

        result = _get_mime_type(zarr_dir)
        assert result == "application/zarr+ome", f"Expected 'application/zarr+ome', got '{result}'"

    def test_ome_tiff_still_works(self, tmp_path: Path) -> None:
        """Ensure OME-TIFF detection still works after adding OME-Zarr support."""
        from bioimage_mcp_base.ops.io import _detect_format, _get_mime_type

        tiff_file = tmp_path / "test_image.ome.tif"
        tiff_file.touch()

        assert _detect_format(tiff_file) == "OME-TIFF"
        assert _get_mime_type(tiff_file) == "image/tiff"
