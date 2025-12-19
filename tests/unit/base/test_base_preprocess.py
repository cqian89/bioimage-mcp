from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

from bioimage_mcp_base import preprocess


def test_normalize_intensity_clips(monkeypatch, tmp_path: Path) -> None:
    data = np.array([[0, 1], [2, 3]], dtype="float32")
    monkeypatch.setattr(preprocess, "load_image", lambda _path: data)
    captured = {}

    def _save_zarr(array: np.ndarray, work_dir: Path, name: str) -> Path:
        captured["array"] = array
        return work_dir / name

    monkeypatch.setattr(preprocess, "save_zarr", _save_zarr)

    preprocess.normalize_intensity(
        inputs={"image": {"uri": "file:///tmp/sample.tif"}},
        params={"pmin": 0, "pmax": 100, "clip": True},
        work_dir=tmp_path,
    )

    assert captured["array"].min() >= 0
    assert captured["array"].max() <= 1


def test_threshold_otsu_apply_false(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(16, dtype="uint8").reshape(4, 4)
    monkeypatch.setattr(preprocess, "load_image", lambda _path: data)
    captured = {}

    def _save_zarr(array: np.ndarray, work_dir: Path, name: str) -> Path:
        captured["array"] = array
        return work_dir / name

    monkeypatch.setattr(preprocess, "save_zarr", _save_zarr)

    preprocess.threshold_otsu(
        inputs={"image": {"uri": "file:///tmp/sample.tif"}},
        params={"apply": False},
        work_dir=tmp_path,
    )

    np.testing.assert_array_equal(captured["array"], data)


def test_sobel_invalid_axis(monkeypatch, tmp_path: Path) -> None:
    data = np.zeros((4, 4), dtype="uint8")
    monkeypatch.setattr(preprocess, "load_image", lambda _path: data)
    monkeypatch.setattr(preprocess, "save_zarr", lambda arr, work_dir, name: work_dir / name)

    with pytest.raises(ValueError, match="Unknown axis"):
        preprocess.sobel(
            inputs={"image": {"uri": "file:///tmp/sample.tif"}},
            params={"axis": "q"},
            work_dir=tmp_path,
        )
