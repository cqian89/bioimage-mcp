from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

from bioimage_mcp_base import transforms


def test_project_sum_uses_axis_alias(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)

    monkeypatch.setattr(transforms, "load_image", lambda _path: data)
    captured = {}

    def _save_zarr(array: np.ndarray, work_dir: Path, name: str) -> Path:
        captured["array"] = array
        captured["name"] = name
        return work_dir / name

    monkeypatch.setattr(transforms, "save_zarr", _save_zarr)

    out_path = transforms.project_sum(
        inputs={"image": {"uri": "file:///tmp/sample.tif"}},
        params={"axis": "z"},
        work_dir=tmp_path,
    )

    assert out_path == tmp_path / "project_sum.ome.zarr"
    assert captured["name"] == "project_sum.ome.zarr"
    np.testing.assert_array_equal(captured["array"], np.sum(data, axis=0))


def test_flip_axis(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(6, dtype="uint8").reshape(2, 3)

    monkeypatch.setattr(transforms, "load_image", lambda _path: data)
    captured = {}

    def _save_zarr(array: np.ndarray, work_dir: Path, name: str) -> Path:
        captured["array"] = array
        return work_dir / name

    monkeypatch.setattr(transforms, "save_zarr", _save_zarr)

    transforms.flip(
        inputs={"image": {"uri": "file:///tmp/sample.tif"}},
        params={"axis": "x"},
        work_dir=tmp_path,
    )

    np.testing.assert_array_equal(captured["array"], np.flip(data, axis=1))


def test_crop_requires_matching_dims(monkeypatch, tmp_path: Path) -> None:
    data = np.zeros((2, 3, 4), dtype="uint8")
    monkeypatch.setattr(transforms, "load_image", lambda _path: data)
    monkeypatch.setattr(transforms, "save_zarr", lambda arr, work_dir, name: work_dir / name)

    with pytest.raises(ValueError, match="dimensions"):
        transforms.crop(
            inputs={"image": {"uri": "file:///tmp/sample.tif"}},
            params={"start": [0, 0], "stop": [1, 1]},
            work_dir=tmp_path,
        )
