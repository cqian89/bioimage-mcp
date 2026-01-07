from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import tifffile

from bioimage_mcp.artifacts.metadata import extract_image_metadata


def test_extract_image_metadata_returns_native_dims(tmp_path: Path) -> None:
    """T022: metadata extraction returns ndim, dims, shape, dtype.

    Note: physical_pixel_sizes is only present if the source file contains OME metadata.
    """
    # Given an image file (TIFF)
    path = tmp_path / "test.tiff"
    data = np.zeros((1, 2, 3, 4, 5), dtype=np.uint16)  # TCZYX
    tifffile.imwrite(path, data)

    # When extract_image_metadata is called
    meta = extract_image_metadata(path)

    # Then returns dict with: shape, ndim, dims, dtype
    assert meta is not None
    assert "shape" in meta
    assert "ndim" in meta
    assert "dims" in meta
    assert "dtype" in meta
    # physical_pixel_sizes is optional for plain TIFFs

    assert meta["ndim"] == 5
    assert list(meta["shape"]) == [1, 2, 3, 4, 5]
    assert meta["dtype"] == "uint16"


def test_extract_table_metadata_returns_columns(tmp_path: Path) -> None:
    """T023: table metadata extraction returns columns with types."""
    # Given a CSV table file
    path = tmp_path / "test.csv"
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "area", "mean_intensity"])
        writer.writerow([1, 100.5, 200.0])
        writer.writerow([2, 150.2, 210.5])

    # When extract_table_metadata is called
    # NOTE: This function likely doesn't exist yet, so this will fail
    from bioimage_mcp.artifacts.metadata import extract_table_metadata

    meta = extract_table_metadata(path)

    # Then returns: columns=[{name, dtype}], row_count
    assert meta is not None
    assert "columns" in meta
    assert "row_count" in meta
    assert meta["row_count"] == 2

    columns = meta["columns"]
    assert len(columns) == 3
    assert columns[0]["name"] == "label"
    assert "dtype" in columns[0]
