from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest
import tifffile

from bioimage_mcp.artifacts.metadata import extract_image_metadata


def test_metadata_extraction_under_100ms(tmp_path: Path) -> None:
    """T024a: metadata inspection completes in under 100ms without data loading."""
    # Given a large image file
    path = tmp_path / "large_test.tiff"
    # Create a large file (e.g. 100MB of zeros)
    # 512 * 512 * 200 * 2 bytes (uint16) ~= 100MB
    data = np.zeros((200, 512, 512), dtype=np.uint16)
    tifffile.imwrite(path, data)

    # Ensure it's actually large-ish
    assert path.stat().st_size > 10 * 1024 * 1024

    # When extract_image_metadata is called
    start_time = time.perf_counter()
    meta = extract_image_metadata(path)
    end_time = time.perf_counter()

    duration_ms = (end_time - start_time) * 1000

    # Then completes in under 100ms
    assert meta is not None
    assert "shape" in meta
    assert list(meta["shape"]) == [200, 512, 512]

    # Metadata extraction should be fast because it only reads headers
    # If it loads the whole image, it will be much slower
    assert duration_ms < 100, f"Metadata extraction took {duration_ms:.2f}ms, expected < 100ms"
