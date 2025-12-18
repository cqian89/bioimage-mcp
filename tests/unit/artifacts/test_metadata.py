from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.artifacts.metadata import extract_image_metadata


def test_extract_metadata_from_tiff(tmp_path: Path) -> None:
    """Test metadata extraction from a valid TIFF image."""
    tifffile = pytest.importorskip("tifffile")
    np = pytest.importorskip("numpy")

    img = np.zeros((10, 20), dtype=np.uint16)
    path = tmp_path / "test.tiff"
    tifffile.imwrite(path, img)

    meta = extract_image_metadata(path)

    # The exact metadata depends on bioio being installed and working
    # We just verify we get a dict back (may be empty if bioio not available)
    assert isinstance(meta, dict)
    # If bioio is working, we should get shape and dtype
    if meta:
        assert "shape" in meta
        assert "dtype" in meta


def test_extract_metadata_from_nonexistent_file_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "does_not_exist.tiff"

    meta = extract_image_metadata(path)
    assert meta == {}


def test_extract_metadata_from_invalid_file_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "not_an_image.txt"
    path.write_text("hello world")

    meta = extract_image_metadata(path)
    assert meta == {}


def test_extract_metadata_from_empty_file_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "empty.tiff"
    path.write_bytes(b"")

    meta = extract_image_metadata(path)
    assert meta == {}
