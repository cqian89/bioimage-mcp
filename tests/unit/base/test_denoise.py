from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

from bioimage_mcp_base import preprocess


def test_denoise_defaults_to_median(monkeypatch, tmp_path: Path) -> None:
    data = np.zeros((2, 4, 4), dtype="float32")
    axes = "CYX"
    captured: dict[str, str] = {}

    def _load_image_with_axes(_image_ref: dict) -> tuple[np.ndarray, str]:
        return data, axes

    def _apply_filter_2d(array: np.ndarray, filter_type: str, params: dict) -> np.ndarray:
        captured["filter_type"] = filter_type
        return array

    def _write_ome_tiff(
        array: np.ndarray,
        work_dir: Path,
        name: str,
        axes: str,
        **_kwargs: dict,
    ) -> Path:
        return work_dir / name

    monkeypatch.setattr(preprocess, "_load_image_with_axes", _load_image_with_axes)
    monkeypatch.setattr(preprocess, "_apply_filter_2d", _apply_filter_2d)
    monkeypatch.setattr(preprocess, "_write_ome_tiff", _write_ome_tiff)

    result = preprocess.denoise_image(
        inputs={"image": {"uri": "file:///tmp/sample.tif", "format": "OME-TIFF"}},
        params={},
        work_dir=tmp_path,
    )

    assert captured["filter_type"] == "median"
    assert result["outputs"]["output"]["format"] == "OME-TIFF"


def test_denoise_rejects_invalid_params(monkeypatch, tmp_path: Path) -> None:
    data = np.zeros((2, 4, 4), dtype="float32")
    axes = "CYX"

    def _load_image_with_axes(_image_ref: dict) -> tuple[np.ndarray, str]:
        return data, axes

    monkeypatch.setattr(preprocess, "_load_image_with_axes", _load_image_with_axes)
    monkeypatch.setattr(preprocess, "_write_ome_tiff", lambda *args, **kwargs: tmp_path)

    with pytest.raises(ValueError, match="sigma"):
        preprocess.denoise_image(
            inputs={"image": {"uri": "file:///tmp/sample.tif", "format": "OME-TIFF"}},
            params={"filter_type": "median", "sigma": 1.0},
            work_dir=tmp_path,
        )

    with pytest.raises(ValueError, match="radius"):
        preprocess.denoise_image(
            inputs={"image": {"uri": "file:///tmp/sample.tif", "format": "OME-TIFF"}},
            params={"filter_type": "gaussian", "radius": 2},
            work_dir=tmp_path,
        )


def test_denoise_applies_per_plane(monkeypatch, tmp_path: Path) -> None:
    data = np.zeros((2, 4, 4), dtype="float32")
    axes = "CYX"
    calls: list[tuple[int, ...]] = []

    def _load_image_with_axes(_image_ref: dict) -> tuple[np.ndarray, str]:
        return data, axes

    def _apply_filter_2d(array: np.ndarray, filter_type: str, params: dict) -> np.ndarray:
        assert array.ndim == 2
        calls.append(array.shape)
        return array

    def _write_ome_tiff(
        array: np.ndarray,
        work_dir: Path,
        name: str,
        axes: str,
        **_kwargs: dict,
    ) -> Path:
        return work_dir / name

    monkeypatch.setattr(preprocess, "_load_image_with_axes", _load_image_with_axes)
    monkeypatch.setattr(preprocess, "_apply_filter_2d", _apply_filter_2d)
    monkeypatch.setattr(preprocess, "_write_ome_tiff", _write_ome_tiff)

    preprocess.denoise_image(
        inputs={"image": {"uri": "file:///tmp/sample.tif", "format": "OME-TIFF"}},
        params={"filter_type": "median"},
        work_dir=tmp_path,
    )

    assert len(calls) == 2
