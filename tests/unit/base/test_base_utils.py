from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

from bioimage_mcp_base import utils


def test_uri_to_path_handles_file_uri(tmp_path: Path) -> None:
    sample = tmp_path / "sample.tif"
    path = utils.uri_to_path(f"file://{sample}")
    assert path == sample


def test_uri_to_path_passthrough(tmp_path: Path) -> None:
    sample = tmp_path / "sample.tif"
    path = utils.uri_to_path(str(sample))
    assert path == sample


def test_resolve_axis_alias() -> None:
    assert utils.resolve_axis("x", 3) == 2


def test_resolve_axis_out_of_bounds() -> None:
    with pytest.raises(ValueError, match="out of bounds"):
        utils.resolve_axis(5, 2)


def test_save_zarr_creates_dir(tmp_path: Path) -> None:
    data = np.zeros((2, 3), dtype="uint8")
    out_dir = utils.save_zarr(data, tmp_path, "out.ome.zarr")
    assert out_dir.exists()
    assert (out_dir / "0").exists()


def test_save_zarr_raises_if_exists(tmp_path: Path) -> None:
    out_dir = tmp_path / "out.ome.zarr"
    out_dir.mkdir()
    with pytest.raises(FileExistsError):
        utils.save_zarr(np.zeros((1, 1), dtype="uint8"), tmp_path, "out.ome.zarr")
