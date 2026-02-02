from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from bioimage_mcp.artifacts.preview import (
    apply_tab20_colormap,
    generate_table_preview,
    get_label_metadata,
)


def test_apply_tab20_colormap_basic():
    # 2D array
    arr = np.array([[0, 1], [2, 3]], dtype=np.uint16)
    rgba = apply_tab20_colormap(arr)
    assert rgba.shape == (2, 2, 4)
    assert rgba.dtype == np.uint8


def test_apply_tab20_colormap_background_transparent():
    arr = np.array([[0]], dtype=np.uint16)
    rgba = apply_tab20_colormap(arr)
    assert rgba[0, 0, 3] == 0


def test_apply_tab20_colormap_cycles():
    # Label 21 should map to the same as label 1
    arr1 = np.array([[1]], dtype=np.uint16)
    arr21 = np.array([[21]], dtype=np.uint16)
    rgba1 = apply_tab20_colormap(arr1)
    rgba21 = apply_tab20_colormap(arr21)
    assert np.array_equal(rgba1[0, 0, 0:3], rgba21[0, 0, 0:3])
    assert rgba1[0, 0, 3] == 255
    assert rgba21[0, 0, 3] == 255


def test_get_label_metadata_count():
    arr = np.array([[0, 1, 0], [2, 0, 3]], dtype=np.uint16)
    meta = get_label_metadata(arr)
    assert meta["region_count"] == 3


def test_get_label_metadata_centroids():
    # Single label 1 at (1, 1)
    arr = np.zeros((3, 3), dtype=np.uint16)
    arr[1, 1] = 1
    meta = get_label_metadata(arr)
    assert meta["region_count"] == 1
    assert meta["centroids"] == [(1.0, 1.0)]


def test_generate_table_preview_basic(tmp_path: Path):
    csv_file = tmp_path / "test.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["A", "B"])
        writer.writerow([1, 2])

    result = generate_table_preview(csv_file)
    assert result is not None
    assert "| A | B |" in result["table_preview"]
    assert "| 1 | 2 |" in result["table_preview"]
    assert result["dtypes"]["A"] == "string"


def test_generate_table_preview_row_limit(tmp_path: Path):
    csv_file = tmp_path / "test.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["A"])
        writer.writerow([1])
        writer.writerow([2])
        writer.writerow([3])

    result = generate_table_preview(csv_file, preview_rows=2)
    assert result is not None
    # Header + separator + 2 rows
    lines = result["table_preview"].strip().split("\n")
    assert len(lines) == 4


def test_generate_table_preview_column_limit(tmp_path: Path):
    csv_file = tmp_path / "test.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["A", "B", "C"])
        writer.writerow([1, 2, 3])

    result = generate_table_preview(csv_file, preview_columns=2)
    assert result is not None
    assert "| A | B |" in result["table_preview"]
    assert "| C |" not in result["table_preview"]
