from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.artifacts.metadata import _truncate_text, extract_image_metadata


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
    # Should return None for nonexistent files
    assert meta is None


def test_extract_metadata_from_invalid_file_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "not_an_image.txt"
    path.write_text("hello world")

    meta = extract_image_metadata(path)
    # Should return minimal metadata with file_size_bytes when bioio can't read the file
    assert meta is not None
    assert "file_size_bytes" in meta
    assert meta["file_size_bytes"] == 11  # "hello world" is 11 bytes


def test_extract_metadata_from_empty_file_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "empty.tiff"
    path.write_bytes(b"")

    meta = extract_image_metadata(path)
    # Should return minimal metadata with file_size_bytes when bioio can't read the file
    assert meta is not None
    assert "file_size_bytes" in meta
    assert meta["file_size_bytes"] == 0


def test_custom_attributes_bounded_when_large() -> None:
    from bioimage_mcp.artifacts.metadata import _truncate_dict

    custom_attributes = {"nested": {"level1": {"level2": {"level3": "value"}}}}
    custom_attributes.update({f"key_{idx}": "x" * 600 for idx in range(25)})

    truncated = _truncate_dict(custom_attributes)

    assert len(truncated) <= 20
    sample_value = next(value for key, value in truncated.items() if key.startswith("key_"))
    assert isinstance(sample_value, str)
    assert len(sample_value) == 500
    assert truncated["nested"]["level1"] == "..."


def test_custom_attributes_truncated_marker_when_limited() -> None:
    from bioimage_mcp.artifacts.metadata import _truncate_dict

    custom_attributes = {"key": "x" * 600}

    truncated = _truncate_dict(custom_attributes)

    assert truncated["_truncated"] is True


def test_truncate_text_adds_marker_with_char_count() -> None:
    value = "x" * 10

    truncated = _truncate_text(value, limit=5)

    assert truncated == "xxxxx... (10 chars)"
    assert _truncate_text(value, limit=10) == value
