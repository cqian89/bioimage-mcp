from __future__ import annotations

import sys
from pathlib import Path

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
