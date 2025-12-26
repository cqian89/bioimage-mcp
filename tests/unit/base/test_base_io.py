from __future__ import annotations

import sys
from pathlib import Path

import pytest

BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

from bioimage_mcp_base import io


def test_convert_to_ome_zarr_requires_uri() -> None:
    with pytest.raises(ValueError, match="uri"):
        io.convert_to_ome_zarr(inputs={"image": {}}, params={}, work_dir=Path("."))


def test_export_ome_tiff_requires_uri() -> None:
    with pytest.raises(ValueError, match="uri"):
        io.export_ome_tiff(inputs={"image": {}}, params={}, work_dir=Path("."))
